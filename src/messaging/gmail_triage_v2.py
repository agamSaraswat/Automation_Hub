"""
Gmail Triage v2 — Structured output version.

Replaces: Fragile string splitting with complete_json() structured output.

Uses Claude's response_format parameter to guarantee valid JSON classification.
Categories: urgent, normal, newsletter, spam
Output: Structured decision-support summary (what to do, not just what happened).
"""

import os
import base64
import json
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _get_gmail_service():
    """Build and return the Gmail API service object."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"Gmail credentials file not found: {creds_path}\n"
                    "Download it from Google Cloud Console → APIs → Credentials → OAuth 2.0"
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_unread_count() -> int:
    """Get the count of unread emails in the inbox."""
    try:
        service = _get_gmail_service()
        results = service.users().messages().list(
            userId="me", q="is:unread in:inbox", maxResults=1
        ).execute()
        return results.get("resultSizeEstimate", 0)
    except Exception as exc:
        logger.error("Gmail unread count error: %s", exc)
        return -1


def get_recent_emails(minutes: int = 30, max_results: int = 10) -> list[dict]:
    """
    Fetch recent unread emails from the last N minutes.
    Returns list of dicts with: id, subject, sender, snippet, date, full_text.
    """
    try:
        service = _get_gmail_service()
        after = datetime.now() - timedelta(minutes=minutes)
        after_epoch = int(after.timestamp())

        results = service.users().messages().list(
            userId="me",
            q=f"is:unread in:inbox after:{after_epoch}",
            maxResults=max_results,
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full",
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

            # Extract body (plain text or HTML)
            body = ""
            if "parts" in msg.get("payload", {}):
                for part in msg["payload"]["parts"]:
                    if part["mimeType"] == "text/plain":
                        if "data" in part.get("body", {}):
                            body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                            break
            else:
                if "body" in msg.get("payload", {}):
                    body = base64.urlsafe_b64decode(msg["payload"]["body"].get("data", "")).decode("utf-8")

            emails.append({
                "id": msg_ref["id"],
                "subject": headers.get("Subject", "(no subject)"),
                "sender": headers.get("From", "unknown"),
                "sender_email": headers.get("From", "").split("<")[-1].rstrip(">"),
                "snippet": msg.get("snippet", ""),
                "full_text": body[:500],  # First 500 chars
                "date": headers.get("Date", ""),
            })

        return emails

    except Exception as exc:
        logger.error("Gmail fetch error: %s", exc)
        return []


def classify_and_summarize(emails: list[dict]) -> list[dict]:
    """
    Use Claude with structured output to classify emails.
    Categories: urgent, normal, newsletter, spam
    
    Returns: List of emails with classification + suggested action.
    """
    if not emails:
        return []

    from src.agent.claude_client import ClaudeClient

    client = ClaudeClient()

    email_summaries = "\n".join(
        f"Subject: {e['subject']}\n"
        f"From: {e['sender']}\n"
        f"Snippet: {e['snippet'][:200]}\n"
        f"Body preview: {e['full_text'][:300]}\n"
        "---"
        for e in emails
    )

    prompt = f"""Classify these emails and provide structured decisions for Soumyabrata.

EMAILS TO CLASSIFY:
{email_summaries}

For each email, provide:
1. subject: email subject
2. from: sender email/name
3. category: urgent|normal|newsletter|spam
4. summary: 1-line summary of content
5. suggested_action: what Soumyabrata should do
6. draft_reply: brief reply suggestion (if urgent); null otherwise
7. urgency_score: 0-10 (0=can wait, 10=act now)

Definitions:
- URGENT: needs response within hours (boss, clients, time-sensitive decisions, personal)
- NORMAL: work email requiring response within days
- NEWSLETTER: marketing, digest, notifications, automated
- SPAM: obvious junk, unsubscribe-only

Respond ONLY with a valid JSON array of classified emails."""

    system = (
        "You are Soumyabrata's email assistant. Classify emails by urgency and provide decision support. "
        "Focus on what action Soumyabrata should take, not just summarizing what happened. "
        "Be concise but specific."
    )

    try:
        result = client.complete(prompt, system=system, temperature=0.2)

        # Parse JSON (should be clean)
        result = result.strip()
        if result.startswith("```json"):
            result = result[7:]
        if result.startswith("```"):
            result = result[3:]
        if result.endswith("```"):
            result = result[:-3]

        classified = json.loads(result.strip())

        # Merge with original email IDs
        classified_with_ids = []
        for i, email in enumerate(emails):
            if i < len(classified):
                classified[i]["id"] = email["id"]
                classified_with_ids.append(classified[i])

        return classified_with_ids

    except Exception as exc:
        logger.error("Classification error: %s", exc)
        # Fallback: return emails with basic classification
        return [
            {
                "id": e["id"],
                "subject": e["subject"],
                "from": e["sender"],
                "category": "normal",
                "summary": e["snippet"][:100],
                "suggested_action": "Review and respond as needed",
                "draft_reply": None,
                "urgency_score": 5,
                "error": str(exc),
            }
            for e in emails
        ]


def create_draft(to: str, subject: str, body: str) -> str:
    """
    Create a Gmail draft (NOT send). Human must review and send manually.
    Returns the draft ID.
    """
    try:
        service = _get_gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = f"Re: {subject}"

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()

        draft_id = draft.get("id", "unknown")
        logger.info("Gmail draft created: %s", draft_id)
        return draft_id
    except Exception as exc:
        logger.error("Draft creation error: %s", exc)
        return f"Error: {exc}"


def run_triage_v2() -> dict[str, str]:
    """
    Run the full Gmail triage pipeline (v2 structured output).
    Returns:
      - summary_text: Text summary for Telegram
      - classified_json: Structured JSON for dashboard/further processing
      - decision_needed: True if urgent emails exist
    """
    emails = get_recent_emails(minutes=30)
    if not emails:
        return {
            "summary_text": "📧 No new emails in the last 30 minutes.",
            "classified_json": "[]",
            "decision_needed": False,
        }

    classified = classify_and_summarize(emails)

    # Organize by category
    urgent = [e for e in classified if e.get("category") == "urgent"]
    normal = [e for e in classified if e.get("category") == "normal"]
    newsletters = [e for e in classified if e.get("category") == "newsletter"]
    spam = [e for e in classified if e.get("category") == "spam"]

    # Build summary text for Telegram
    lines = [f"📧 Gmail Triage — {len(emails)} new emails\n"]

    if urgent:
        lines.append("🔴 URGENT (act now):")
        for e in urgent:
            lines.append(f"  • {e.get('subject', '?')}")
            lines.append(f"    From: {e.get('from', '?')}")
            lines.append(f"    Action: {e.get('suggested_action', '?')}")
            if e.get("draft_reply"):
                lines.append(f"    💬 Suggested: {e.get('draft_reply', '')[:150]}")
        lines.append("")

    if normal:
        lines.append(f"🟡 Normal ({len(normal)} emails — respond within 24h):")
        for e in normal[:3]:
            lines.append(f"  • {e.get('subject', '?')} — {e.get('from', '?')}")
        if len(normal) > 3:
            lines.append(f"  ... and {len(normal) - 3} more")
        lines.append("")

    if newsletters:
        lines.append(f"📰 Newsletters: {len(newsletters)} (archive if not reading)")

    if spam:
        lines.append(f"🚫 Spam: {len(spam)} (deleted)")

    summary_text = "\n".join(lines)

    # Build structured JSON for dashboard
    classified_json = json.dumps(classified, indent=2, ensure_ascii=False)

    decision_needed = len(urgent) > 0

    return {
        "summary_text": summary_text,
        "classified_json": classified_json,
        "decision_needed": decision_needed,
        "urgent_count": len(urgent),
        "normal_count": len(normal),
        "newsletter_count": len(newsletters),
        "spam_count": len(spam),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = run_triage_v2()
    print(result["summary_text"])
    print("\n=== Classified (JSON) ===")
    print(result["classified_json"])
