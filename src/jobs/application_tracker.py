"""Application tracking + conversion feedback loop for Phase 2."""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.jobs.deduplicator import DB_PATH, add_job, init_db

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "job_search.yaml"
SUCCESS_RESPONSES = {"interview", "offer"}
VALID_RESPONSES = {"interview", "rejection", "ghosted", "offer"}


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _confidence_indicator(sample_size: int) -> str:
    if sample_size >= 30:
        return "high"
    if sample_size >= 10:
        return "medium"
    return "low"


def _role_type(title: str) -> str:
    t = (title or "").lower()
    if "scientist" in t:
        return "data_science"
    if "ml" in t or "machine learning" in t or "ai" in t:
        return "ml_ai_engineering"
    if "platform" in t:
        return "platform"
    if "analyst" in t:
        return "analytics"
    return "other"


def _company_size(company: str) -> str:
    c = (company or "").lower()
    enterprise_markers = ("google", "amazon", "microsoft", "meta", "apple", "ibm", "oracle")
    startup_markers = ("labs", "ai", "tech", "stealth", "startup")
    if any(m in c for m in enterprise_markers):
        return "enterprise"
    if any(m in c for m in startup_markers):
        return "startup"
    return "unknown"


def _get_or_create_job_id(company: str, title: str, url: str, channel: str) -> int:
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute("SELECT id FROM seen_jobs WHERE url = ?", (url,)).fetchone()
        if row:
            return int(row[0])
    finally:
        conn.close()

    add_job(
        url=url,
        company=company,
        title=title,
        status="applied",
        source=channel,
    )

    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute("SELECT id FROM seen_jobs WHERE url = ?", (url,)).fetchone()
        if not row:
            raise ValueError(f"Unable to resolve job_id for URL: {url}")
        return int(row[0])
    finally:
        conn.close()


def record_application(
    job_id: int | None,
    company: str,
    title: str,
    url: str,
    applied_at: str,
    channel: str,
) -> dict[str, Any]:
    """Insert/update an application row in application_outcomes."""
    if job_id is None:
        job_id = _get_or_create_job_id(company, title, url, channel)

    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            """
            INSERT INTO application_outcomes
                (job_id, company, title, url, applied_at, channel)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                company=excluded.company,
                title=excluded.title,
                url=excluded.url,
                applied_at=excluded.applied_at,
                channel=excluded.channel
            """,
            (job_id, company, title, url, applied_at, channel),
        )
        conn.execute("UPDATE seen_jobs SET status = 'applied' WHERE id = ?", (job_id,))
        conn.commit()
        return {"ok": True, "job_id": job_id}
    finally:
        conn.close()


def record_response(job_id: int, response_type: str, response_at: str) -> dict[str, Any]:
    """Record response/outcome for an already-tracked application."""
    response = response_type.strip().lower()
    if response not in VALID_RESPONSES:
        raise ValueError(f"Invalid response_type '{response_type}'. Use one of: {sorted(VALID_RESPONSES)}")

    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            "SELECT applied_at FROM application_outcomes WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"No application record found for job_id={job_id}")

        applied_at = row[0]
        days_to_response = None
        if applied_at:
            days_to_response = (_parse_iso(response_at).date() - _parse_iso(applied_at).date()).days

        conn.execute(
            """
            UPDATE application_outcomes
            SET response_type = ?, response_at = ?, days_to_response = ?
            WHERE job_id = ?
            """,
            (response, response_at, days_to_response, job_id),
        )

        status = "tailored"
        if response == "rejection":
            status = "rejected"
        elif response == "offer":
            status = "applied"
        elif response == "interview":
            status = "applied"
        elif response == "ghosted":
            status = "applied"
        conn.execute("UPDATE seen_jobs SET status = ? WHERE id = ?", (status, job_id))
        conn.commit()
        return {"ok": True, "job_id": job_id, "days_to_response": days_to_response}
    finally:
        conn.close()


def _rate_bucket(rows: list[sqlite3.Row], key_name: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        key = row[key_name] or "unknown"
        grouped[key].append(row)

    output = []
    for key, group in grouped.items():
        sample_size = len(group)
        successes = sum(1 for r in group if (r["response_type"] or "") in SUCCESS_RESPONSES)
        rate = successes / sample_size if sample_size else 0.0
        output.append(
            {
                "segment": key,
                "conversion_rate": round(rate, 4),
                "sample_size": sample_size,
                "confidence_indicator": _confidence_indicator(sample_size),
            }
        )
    output.sort(key=lambda x: (x["conversion_rate"], x["sample_size"]), reverse=True)
    return output


def get_conversion_stats() -> dict[str, Any]:
    """
    Return conversion analytics with sample sizes + confidence indicators.
    """
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                ao.job_id,
                ao.company,
                ao.title,
                ao.channel,
                ao.applied_at,
                ao.response_type,
                sj.location,
                sj.source
            FROM application_outcomes ao
            LEFT JOIN seen_jobs sj ON sj.id = ao.job_id
            """
        ).fetchall()
    finally:
        conn.close()

    enriched = []
    for row in rows:
        payload = dict(row)
        payload["company_size"] = _company_size(payload.get("company", ""))
        payload["role_type"] = _role_type(payload.get("title", ""))
        payload["source_channel"] = payload.get("channel") or payload.get("source") or "unknown"
        try:
            payload["application_day_of_week"] = _parse_iso(payload.get("applied_at", "")).strftime("%A")
        except Exception:
            payload["application_day_of_week"] = "unknown"
        enriched.append(payload)

    # convert back to row-like for re-use
    class R(dict):
        def __getitem__(self, item: str) -> Any:  # type: ignore[override]
            return self.get(item)

    wrapped = [R(r) for r in enriched]

    return {
        "total_applications": len(wrapped),
        "company_size": _rate_bucket(wrapped, "company_size"),
        "role_type": _rate_bucket(wrapped, "role_type"),
        "location": _rate_bucket(wrapped, "location"),
        "source_channel": _rate_bucket(wrapped, "source_channel"),
        "application_day_of_week": _rate_bucket(wrapped, "application_day_of_week"),
    }


def get_feedback_signal() -> dict[str, Any]:
    """Summarize what appears to be working based on conversion performance."""
    stats = get_conversion_stats()

    def top_segments(bucket: list[dict[str, Any]], top_n: int = 3) -> list[dict[str, Any]]:
        return [b for b in bucket if b["sample_size"] > 0][:top_n]

    role_top = top_segments(stats.get("role_type", []), 3)
    source_top = top_segments(stats.get("source_channel", []), 3)
    day_top = top_segments(stats.get("application_day_of_week", []), 1)

    return {
        "top_converting_role_types": role_top,
        "top_converting_sources": source_top,
        "best_day_to_apply": day_top[0] if day_top else None,
        "stats_snapshot": stats,
    }


def adjust_relevance_weights(evaluator_config: dict[str, Any]) -> dict[str, Any]:
    """
    Adjust evaluator weights in-memory and in config/job_search.yaml using feedback data.
    """
    feedback = get_feedback_signal()
    stats = feedback.get("stats_snapshot", {})

    base = evaluator_config.get("weights", {})
    updated = {
        "title_match": float(base.get("title_match", 0.35)),
        "keyword_match": float(base.get("keyword_match", 0.35)),
        "location_match": float(base.get("location_match", 0.15)),
        "source_channel": float(base.get("source_channel", 0.15)),
    }

    top_sources = feedback.get("top_converting_sources", [])
    if top_sources and top_sources[0]["confidence_indicator"] in {"medium", "high"}:
        updated["source_channel"] = min(updated["source_channel"] + 0.05, 0.35)
        updated["keyword_match"] = max(updated["keyword_match"] - 0.03, 0.2)
        updated["location_match"] = max(updated["location_match"] - 0.02, 0.1)

    total = sum(updated.values()) or 1.0
    normalized = {k: round(v / total, 4) for k, v in updated.items()}
    evaluator_config["weights"] = normalized
    evaluator_config["feedback_last_updated"] = datetime.now().isoformat()
    evaluator_config["feedback_sample_size"] = stats.get("total_applications", 0)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        discovery = cfg.setdefault("job_discovery", {})
        evaluator_section = discovery.setdefault("evaluator", {})
        evaluator_section["weights"] = normalized
        evaluator_section["feedback_sample_size"] = stats.get("total_applications", 0)
        evaluator_section["feedback_confidence"] = _confidence_indicator(stats.get("total_applications", 0))
        evaluator_section["top_sources"] = [
            {
                "segment": s["segment"],
                "conversion_rate": s["conversion_rate"],
                "sample_size": s["sample_size"],
                "confidence_indicator": s["confidence_indicator"],
            }
            for s in top_sources[:3]
        ]
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
    except Exception as exc:
        logger.warning("Unable to persist evaluator feedback weights: %s", exc)

    return evaluator_config


def find_latest_job_id_for_company(company: str) -> int | None:
    """Resolve latest tracked application for a company."""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        row = conn.execute(
            """
            SELECT job_id
            FROM application_outcomes
            WHERE lower(company) = lower(?)
            ORDER BY applied_at DESC
            LIMIT 1
            """,
            (company,),
        ).fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()
