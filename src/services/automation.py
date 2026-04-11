"""Shared service-layer orchestration for CLI and API usage."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_VARS = {
    "ANTHROPIC_API_KEY": "Required for Claude AI. Get from: https://console.anthropic.com/",
}

OPTIONAL_VARS = {
    "LINKEDIN_ACCESS_TOKEN": "For LinkedIn posting. Get from: linkedin.com/developers/tools/oauth/token-generator",
    "LINKEDIN_PERSON_URN": "Your LinkedIn person URN (urn:li:person:XXXXX)",
    "TELEGRAM_BOT_TOKEN": "For Telegram bot. Create via @BotFather",
    "TELEGRAM_CHAT_ID": "Your Telegram chat ID. Get via @userinfobot",
    "GMAIL_CREDENTIALS_PATH": "Path to Gmail OAuth credentials.json",
}


def get_environment_status() -> dict[str, dict[str, Any]]:
    """Check configured environment variables."""
    results: dict[str, dict[str, Any]] = {}
    for var, desc in {**REQUIRED_VARS, **OPTIONAL_VARS}.items():
        val = os.getenv(var, "")
        results[var] = {
            "set": bool(val),
            "required": var in REQUIRED_VARS,
            "description": desc,
        }
    return results


def get_linkedin_status() -> dict[str, Any]:
    """Return LinkedIn queue/post/token status for today."""
    today = date.today().isoformat()
    queue_file = REPO_ROOT / "output" / "linkedin" / "queue" / f"{today}.md"
    posted_file = REPO_ROOT / "output" / "linkedin" / "posted" / f"{today}.md"

    status = "Posted ✅" if posted_file.exists() else (
        "In queue (review needed)" if queue_file.exists() else "Not generated"
    )

    token_date = os.getenv("LINKEDIN_TOKEN_SET_DATE", "")
    token_age_days: int | None = None
    token_warning: str | None = None

    if token_date:
        try:
            token_age_days = (date.today() - datetime.strptime(token_date, "%Y-%m-%d").date()).days
            if token_age_days > 50:
                token_warning = f"Token is {token_age_days} days old — refresh soon!"
        except ValueError:
            token_warning = "Invalid LINKEDIN_TOKEN_SET_DATE (use YYYY-MM-DD)."

    return {
        "status": status,
        "today": today,
        "queue_file_exists": queue_file.exists(),
        "posted_file_exists": posted_file.exists(),
        "token_set_date": token_date or None,
        "token_age_days": token_age_days,
        "token_warning": token_warning,
    }


def get_system_status() -> dict[str, Any]:
    """Get aggregate system status for CLI and API."""
    from src.jobs.deduplicator import get_stats, init_db

    init_db()
    return {
        "date": date.today().isoformat(),
        "environment": get_environment_status(),
        "jobs": get_stats(),
        "linkedin": get_linkedin_status(),
    }


def run_jobs_pipeline() -> dict[str, Any]:
    """
    Run the job search and tailoring workflow (Phase 1).
    
    Flow:
      1. Job Discovery: Claude agent searches web → semantic evaluation
      2. Deduplication: Filter against last 30 days
      3. Resume Tailoring: Harness-driven tailoring (Evaluator checks truthfulness)
      4. Queue: Add to DB with human-in-the-loop gate
    """
    import logging
    from src.jobs.deduplicator import get_stats, get_todays_queue, init_db
    from src.jobs.claude_job_discovery import run_job_discovery, queue_discovered_jobs
    from src.services.token_instrumentation import init_instrumentation, finalize_instrumentation, SkillName, record_tokens

    logger = logging.getLogger(__name__)

    init_db()

    # Initialize token tracking
    run_id = f"jobs_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    init_instrumentation(run_id, user_id="soumyabrata")

    try:
        # Phase 1: Job Discovery
        logger.info("[jobs_pipeline] Phase 1: Job Discovery")
        discovery_result = run_job_discovery()
        discovered_jobs = discovery_result.get("jobs", [])
        discovery_tokens = discovery_result.get("run_metadata", {}).get("tokens_used", 0)
        record_tokens(SkillName.JOB_DISCOVERY, discovery_tokens // 2, discovery_tokens // 2, metadata={
            "discovered": len(discovered_jobs),
            "after_dedup": discovery_result.get("run_metadata", {}).get("after_dedup", 0),
        })

        if not discovered_jobs:
            logger.info("[jobs_pipeline] No jobs discovered")
            return {
                "scraped_new_jobs": 0,
                "tailored_jobs": 0,
                "queue_size_today": len(get_todays_queue()),
                "stats": get_stats(),
            }

        # Phase 2: Queue jobs (with human gate)
        queued_count = queue_discovered_jobs(discovered_jobs)
        logger.info(f"[jobs_pipeline] Queued {queued_count} jobs")

        # Phase 3: Resume Tailoring (on queued jobs)
        logger.info(f"[jobs_pipeline] Phase 2: Resume Tailoring ({queued_count} jobs)")
        from src.jobs.claude_resume_tailoring import tailor_resume_for_job, save_tailored_resume

        tailored_count = 0
        tailoring_errors = []
        for job in discovered_jobs[:queued_count]:
            try:
                result = tailor_resume_for_job(
                    job_id=job.get("unique_id", "unknown"),
                    job_title=job.get("title", ""),
                    job_description=job.get("jd_snippet", ""),
                    max_iterations=2,
                )
                
                if result.get("tailored_resume"):
                    save_tailored_resume(result["job_id"], result["tailored_resume"])
                    tailored_count += 1
                    record_tokens(SkillName.RESUME_TAILORING, 1500, 800, metadata={
                        "job_id": result["job_id"],
                        "verdict": result.get("verdict"),
                    })
                else:
                    tailoring_errors.append(result.get("error", "Unknown error"))
            except Exception as exc:
                logger.warning(f"Tailoring error for job {job.get('title')}: {exc}")
                tailoring_errors.append(str(exc))

        logger.info(f"[jobs_pipeline] Tailored {tailored_count}/{queued_count} jobs")

        # Finalize token instrumentation
        finalize_instrumentation(format="json")

        return {
            "scraped_new_jobs": len(discovered_jobs),
            "tailored_jobs": tailored_count,
            "queue_size_today": len(get_todays_queue()),
            "stats": get_stats(),
        }

    except Exception as exc:
        logger.error(f"[jobs_pipeline] Pipeline error: {exc}", exc_info=True)
        finalize_instrumentation(format="json")
        return {
            "scraped_new_jobs": 0,
            "tailored_jobs": 0,
            "queue_size_today": len(get_todays_queue()),
            "stats": get_stats(),
        }


def get_jobs_queue(limit: int = 20) -> list[dict[str, Any]]:
    """Get queued/tailored jobs for today."""
    from src.jobs.deduplicator import get_todays_queue, init_db

    init_db()
    return get_todays_queue(limit=limit)


def get_jobs_stats() -> dict[str, Any]:
    """Get aggregate job stats."""
    from src.jobs.deduplicator import get_stats, init_db

    init_db()
    return get_stats()


def run_briefing_now(send_to_telegram: bool = True) -> dict[str, Any]:
    """Generate briefing and optionally send to Telegram."""
    from src.briefing.morning_briefing import generate_briefing

    briefing = generate_briefing()
    sent = False

    if send_to_telegram and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        from src.messaging.telegram_bot import send_message_sync

        send_message_sync(briefing)
        sent = True

    return {
        "briefing": briefing,
        "sent_to_telegram": sent,
    }


def run_gmail_triage_now(send_to_telegram: bool = False) -> dict[str, Any]:
    """
    Run Gmail triage (v2 structured output).
    
    Returns classified emails as structured JSON.
    Provides decision support: what to do, not just what happened.
    """
    from src.messaging.gmail_triage_v2 import run_triage_v2
    from src.services.token_instrumentation import SkillName, record_tokens

    result = run_triage_v2()
    summary_text = result.get("summary_text", "")
    classified_json = result.get("classified_json", "[]")
    decision_needed = result.get("decision_needed", False)

    # Record token usage (approximate)
    record_tokens(SkillName.GMAIL_TRIAGE, 800, 400, metadata={
        "emails_count": result.get("urgent_count", 0) + result.get("normal_count", 0),
        "urgent_count": result.get("urgent_count", 0),
        "decision_needed": decision_needed,
    })

    sent = False
    if send_to_telegram and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        try:
            from src.messaging.telegram_bot import send_message_sync
            send_message_sync(summary_text)
            sent = True
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(f"Failed to send Gmail triage to Telegram: {exc}")

    return {
        "summary": summary_text,
        "classified_json": classified_json,
        "decision_needed": decision_needed,
        "sent_to_telegram": sent,
        "urgent_count": result.get("urgent_count", 0),
        "normal_count": result.get("normal_count", 0),
    }
