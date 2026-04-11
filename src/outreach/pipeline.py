"""Phase 2 outreach pipeline (draft-only, human-gated)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from src.agent.claude_client import ClaudeClient
from src.network.graph import NetworkGraph, NetworkNode
from src.network.will_introduce_gate import will_introduce_check

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class OutreachTarget:
    company: str
    role: str
    job_url: str
    contact_name: str
    contact_linkedin: str
    contact_role: str
    outreach_type: str  # warm_intro / cold / recruiter_response
    warm_path: list[NetworkNode] = field(default_factory=list)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", (value or "").strip())
    return cleaned.strip("_") or "unknown_company"


def _save_draft(kind: str, company: str, content: str) -> str:
    day = date.today().isoformat()
    out_dir = REPO_ROOT / "output" / "outreach" / kind / day
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{_slug(company)}.md"
    out_path.write_text(content, encoding="utf-8")
    return str(out_path)


def _parse_json_or_fallback(text: str, fallback_reason: str) -> dict[str, str]:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    if cleaned.startswith("{") and '"message"' in cleaned:
        try:
            import json

            parsed = json.loads(cleaned)
            if parsed.get("message") and parsed.get("reasoning"):
                return {"message": parsed["message"], "reasoning": parsed["reasoning"]}
        except Exception:
            pass
    return {"message": text.strip(), "reasoning": fallback_reason}


def generate_warm_intro_ask(target: OutreachTarget, user_profile: dict) -> str:
    """Draft specific warm intro ask; never auto-send."""
    client = ClaudeClient()
    warm_path_text = " -> ".join([f"{n.name} ({n.company})" for n in target.warm_path]) or "No path provided"
    prompt = f"""
Draft a concise warm intro message to a mutual connection.

Constraints:
- Must reference the specific job URL: {target.job_url}
- Must reference how the contact relates to the company via this path: {warm_path_text}
- Must include one specific reason the user is a fit from this profile: {user_profile}
- No generic templates. Must be specific and contextual.
- Return JSON with keys: message, reasoning

Target:
- Company: {target.company}
- Role: {target.role}
- Contact: {target.contact_name} ({target.contact_role})
- Contact LinkedIn: {target.contact_linkedin}
"""
    raw = client.complete(prompt, temperature=0.2)
    parsed = _parse_json_or_fallback(raw, "Warm path exists and contact can provide trusted introduction.")
    draft = (
        f"# Warm Intro Draft — {target.company}\n\n"
        f"## Message\n{parsed['message']}\n\n"
        f"## Reasoning\n{parsed['reasoning']}\n"
    )
    _save_draft("warm_intros", target.company, draft)
    return draft


def generate_cold_outreach(target: OutreachTarget, user_profile: dict) -> str:
    """Draft personalized cold outreach; only used with explicit force-cold override."""
    client = ClaudeClient()
    prompt = f"""
Draft a personalized cold outreach message.

Constraints:
- Mention specific company work/product area (infer from available context)
- Mention the exact role and job URL
- Include one concrete relevant achievement from this profile: {user_profile}
- Be concise, professional, and specific
- Return JSON with keys: message, reasoning

Target:
- Company: {target.company}
- Role: {target.role}
- Job URL: {target.job_url}
- Contact: {target.contact_name} ({target.contact_role})
- Contact LinkedIn: {target.contact_linkedin}
"""
    raw = client.complete(prompt, temperature=0.25)
    parsed = _parse_json_or_fallback(raw, "No warm path available; cold outreach forced by human override.")
    draft = (
        f"# Cold Outreach Draft — {target.company}\n\n"
        f"## Message\n{parsed['message']}\n\n"
        f"## Reasoning\n{parsed['reasoning']}\n"
    )
    _save_draft("cold", target.company, draft)
    return draft


def generate_recruiter_response(job_description: str, user_profile: dict) -> str:
    """Draft a response to inbound recruiter messages; never auto-send."""
    client = ClaudeClient()
    company = _extract_company(job_description) or user_profile.get("company", "unknown_company")
    prompt = f"""
Draft a response to an inbound recruiter message.

Job description / recruiter context:
{job_description}

User profile:
{user_profile}

Requirements:
- Personalized and specific (no boilerplate)
- Mention role alignment + one concrete achievement from profile
- Keep concise and friendly
- Return JSON with keys: message, reasoning
"""
    raw = client.complete(prompt, temperature=0.2)
    parsed = _parse_json_or_fallback(raw, "Inbound recruiter context exists; response optimizes clarity and fit.")
    draft = (
        f"# Recruiter Response Draft — {company}\n\n"
        f"## Message\n{parsed['message']}\n\n"
        f"## Reasoning\n{parsed['reasoning']}\n"
    )
    _save_draft("recruiter", company, draft)
    return draft


def _extract_company(text: str) -> str | None:
    for pattern in [r"company\s*:\s*(.+)", r"at\s+([A-Z][A-Za-z0-9&.\- ]+)"]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()[:80]
    return None


def run_outreach_pipeline(jobs_queue: list) -> dict:
    """
    Draft outreach for jobs queue with strict human gate (nothing auto-sent).
    """
    force_cold = os.getenv("OUTREACH_FORCE_COLD", "0") == "1"
    graph = NetworkGraph.import_from_json()

    summary = {
        "warm_intros_drafted": 0,
        "cold_drafted": 0,
        "skipped": 0,
        "human_review_required": 0,
    }

    for job in jobs_queue:
        company = job.get("company", "")
        role = job.get("title", "")
        job_url = job.get("url", "")
        paths = graph.find_path_to_company(company)

        if paths:
            candidates = graph.get_warm_intro_candidates(company)
            if not candidates:
                summary["skipped"] += 1
                continue
            candidate = candidates[0]
            gate = will_introduce_check(candidate["contact_id"], company)
            if gate.get("can_introduce"):
                target = OutreachTarget(
                    company=company,
                    role=role,
                    job_url=job_url,
                    contact_name=candidate["contact_name"],
                    contact_linkedin="",
                    contact_role=candidate["role"],
                    outreach_type="warm_intro",
                    warm_path=paths[0],
                )
                generate_warm_intro_ask(target, user_profile={"headline": "Data Scientist", "focus": "ML systems"})
                summary["warm_intros_drafted"] += 1
                summary["human_review_required"] += 1
                continue

        # No warm path or gate rejected
        if force_cold:
            target = OutreachTarget(
                company=company,
                role=role,
                job_url=job_url,
                contact_name="Hiring Team",
                contact_linkedin="",
                contact_role="Recruiter",
                outreach_type="cold",
                warm_path=[],
            )
            generate_cold_outreach(target, user_profile={"headline": "Data Scientist", "focus": "ML systems"})
            summary["cold_drafted"] += 1
            summary["human_review_required"] += 1
        else:
            summary["skipped"] += 1

    return summary
