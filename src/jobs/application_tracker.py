"""
Enhanced Job Application Tracking with Response Analytics

Extends deduplicator.py to track:
  - Job status lifecycle (queued → applied → response → outcome)
  - Response tracking (no response, rejection, interview, offer)
  - Application metadata (resume used, cover letter, custom link)
  - Analytics (response rate, time to response, success metrics)

Used by AKTIVIQ to:
  - Track which jobs get responses (feedback for relevance scoring)
  - Calculate success metrics per skill/profile
  - Identify patterns in responses (by company, role, location)
  - Report ROI: cost to discover vs. probability of response
"""

import json
import logging
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"

# ── Enhanced schema with response tracking ──────────────────────────────

CREATE_APPLICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS applications (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id                  INTEGER NOT NULL UNIQUE,
    applied_at              TEXT NOT NULL,
    applied_via             TEXT DEFAULT '',  -- direct, link, email, platform
    tailored_resume_id      TEXT DEFAULT '',  -- reference to tailored resume
    cover_letter_custom     BOOLEAN DEFAULT 0,
    
    -- Response tracking
    first_response_at       TEXT DEFAULT NULL,
    response_type           TEXT DEFAULT NULL,  -- no_response, rejection, interview, offer
    response_source         TEXT DEFAULT NULL,  -- email, platform, phone, linkedin
    response_text           TEXT DEFAULT '',
    
    -- Engagement metrics
    email_opened            BOOLEAN DEFAULT 0,
    email_opened_at         TEXT DEFAULT NULL,
    interview_scheduled     BOOLEAN DEFAULT 0,
    interview_date          TEXT DEFAULT NULL,
    
    -- Outcomes
    offer_received          BOOLEAN DEFAULT 0,
    offer_amount            TEXT DEFAULT NULL,  -- e.g., "150k-180k"
    final_outcome           TEXT DEFAULT NULL,  -- rejected, withdrawn, accepted, pending
    outcome_date            TEXT DEFAULT NULL,
    
    -- Notes
    notes                   TEXT DEFAULT '',
    
    FOREIGN KEY (job_id) REFERENCES seen_jobs(id)
);
"""

CREATE_APPLICATION_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS application_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id      INTEGER NOT NULL,
    event_type          TEXT NOT NULL,  -- applied, response_received, interview_scheduled, offer_received
    event_data          TEXT NOT NULL,  -- JSON: { response_type, source, text, ... }
    recorded_at         TEXT NOT NULL,
    
    FOREIGN KEY (application_id) REFERENCES applications(id)
);
"""


def init_tracking_db() -> None:
    """Initialize enhanced tracking tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        conn.execute(CREATE_APPLICATIONS_TABLE)
        conn.execute(CREATE_APPLICATION_EVENTS_TABLE)
        conn.commit()
        logger.info("Application tracking database initialized")
    except sqlite3.OperationalError as exc:
        logger.warning(f"Tracking tables already exist: {exc}")
    finally:
        conn.close()


def apply_to_job(
    job_id: int,
    via: str = "direct",
    tailored_resume_id: str = "",
    cover_letter_custom: bool = False,
) -> bool:
    """
    Record that we applied to a job.
    
    Args:
        job_id: ID from seen_jobs table
        via: "direct" (apply button), "link" (job link), "email", "platform"
        tailored_resume_id: Reference to tailored resume used
        cover_letter_custom: Whether custom cover letter was used
        
    Returns:
        True if recorded, False if already applied
    """
    init_tracking_db()
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        # Check if already applied
        existing = conn.execute(
            "SELECT id FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()
        
        if existing:
            logger.info(f"Job {job_id} already applied")
            return False
        
        # Record application
        conn.execute(
            """
            INSERT INTO applications (job_id, applied_at, applied_via, tailored_resume_id, cover_letter_custom)
            VALUES (?, ?, ?, ?, ?)
            """,
            (job_id, datetime.now().isoformat(), via, tailored_resume_id, cover_letter_custom),
        )
        
        # Create event
        conn.execute(
            """
            INSERT INTO application_events (application_id, event_type, event_data, recorded_at)
            SELECT id, 'applied', ?, ? FROM applications WHERE job_id = ?
            """,
            (
                json.dumps({"via": via, "resume": tailored_resume_id}),
                datetime.now().isoformat(),
                job_id,
            ),
        )
        
        conn.commit()
        logger.info(f"Applied to job {job_id}")
        return True
        
    except sqlite3.IntegrityError:
        logger.warning(f"Job {job_id} duplicate application")
        return False
    finally:
        conn.close()


def record_response(
    job_id: int,
    response_type: str,
    response_source: str,
    response_text: str = "",
) -> bool:
    """
    Record a response to an application.
    
    Args:
        job_id: ID from seen_jobs table
        response_type: "rejection", "interview", "offer", "no_response"
        response_source: "email", "platform", "phone", "linkedin"
        response_text: Full response text/summary
        
    Returns:
        True if recorded
    """
    init_tracking_db()
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        conn.execute(
            """
            UPDATE applications 
            SET first_response_at = ?, response_type = ?, response_source = ?, response_text = ?
            WHERE job_id = ?
            """,
            (datetime.now().isoformat(), response_type, response_source, response_text, job_id),
        )
        
        # Create event
        app_id = conn.execute(
            "SELECT id FROM applications WHERE job_id = ?", (job_id,)
        ).fetchone()[0]
        
        conn.execute(
            """
            INSERT INTO application_events (application_id, event_type, event_data, recorded_at)
            VALUES (?, 'response_received', ?, ?)
            """,
            (
                app_id,
                json.dumps({
                    "response_type": response_type,
                    "source": response_source,
                    "text_length": len(response_text),
                }),
                datetime.now().isoformat(),
            ),
        )
        
        conn.commit()
        logger.info(f"Recorded {response_type} for job {job_id}")
        return True
        
    except Exception as exc:
        logger.error(f"Error recording response: {exc}")
        return False
    finally:
        conn.close()


def get_applications_summary() -> dict:
    """
    Get comprehensive application summary with analytics.
    
    Returns dict with:
      - total_applications
      - by_response_type
      - response_rate (%)
      - avg_time_to_response (days)
      - success_rate (interviews + offers)
    """
    init_tracking_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    try:
        # Total applications
        total = conn.execute(
            "SELECT COUNT(*) FROM applications"
        ).fetchone()[0]
        
        if total == 0:
            return {
                "total_applications": 0,
                "by_response_type": {},
                "response_rate": 0.0,
                "avg_time_to_response_days": 0,
                "success_rate": 0.0,
            }
        
        # By response type
        by_type = {}
        for row in conn.execute(
            "SELECT response_type, COUNT(*) FROM applications GROUP BY response_type"
        ).fetchall():
            by_type[row[0] or "pending"] = row[1]
        
        # Response rate
        responded = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE response_type IS NOT NULL"
        ).fetchone()[0]
        response_rate = (responded / total) * 100 if total > 0 else 0.0
        
        # Time to response (avg)
        time_rows = conn.execute(
            """
            SELECT AVG(julianday(first_response_at) - julianday(applied_at))
            FROM applications
            WHERE first_response_at IS NOT NULL
            """
        ).fetchone()
        avg_time = time_rows[0] if time_rows[0] else 0
        
        # Success rate (interviews + offers)
        successes = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE response_type IN ('interview', 'offer')"
        ).fetchone()[0]
        success_rate = (successes / total) * 100 if total > 0 else 0.0
        
        return {
            "total_applications": total,
            "by_response_type": by_type,
            "response_rate": round(response_rate, 2),
            "avg_time_to_response_days": round(avg_time, 1) if avg_time else 0,
            "success_rate": round(success_rate, 2),
        }
        
    finally:
        conn.close()


def get_applications_by_status(status: str = "pending", limit: int = 20) -> list[dict]:
    """
    Get applications filtered by response status.
    
    Args:
        status: "pending" (no response), "responded", "interview", "offer", "rejected"
        limit: Max results
        
    Returns:
        List of application records
    """
    init_tracking_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    try:
        if status == "pending":
            query = """
            SELECT a.*, j.company, j.title, j.url
            FROM applications a
            JOIN seen_jobs j ON a.job_id = j.id
            WHERE a.response_type IS NULL
            ORDER BY a.applied_at DESC
            LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()
        elif status == "responded":
            query = """
            SELECT a.*, j.company, j.title, j.url
            FROM applications a
            JOIN seen_jobs j ON a.job_id = j.id
            WHERE a.response_type IS NOT NULL
            ORDER BY a.first_response_at DESC
            LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()
        elif status in ("interview", "offer", "rejected"):
            query = """
            SELECT a.*, j.company, j.title, j.url
            FROM applications a
            JOIN seen_jobs j ON a.job_id = j.id
            WHERE a.response_type = ?
            ORDER BY a.first_response_at DESC
            LIMIT ?
            """
            rows = conn.execute(query, (status, limit)).fetchall()
        else:
            return []
        
        return [dict(r) for r in rows]
        
    finally:
        conn.close()


def get_roi_analysis() -> dict:
    """
    Calculate ROI: cost to discover/tailor vs. probability of response.
    
    Returns dict with:
      - total_cost_usd (discovery + tailoring)
      - total_applications
      - applications_per_dollar
      - responses_per_dollar
      - cost_per_response_usd
      - cost_per_interview_usd
      - estimated_cost_to_offer_usd
    """
    init_tracking_db()
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        # Get application stats
        total_apps = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        responded = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE response_type IS NOT NULL"
        ).fetchone()[0]
        interviews = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE response_type IN ('interview', 'offer')"
        ).fetchone()[0]
        
        if total_apps == 0:
            return {
                "total_cost_usd": 0.0,
                "total_applications": 0,
                "applications_per_dollar": 0.0,
                "responses_per_dollar": 0.0,
                "cost_per_response_usd": 0.0,
                "cost_per_interview_usd": 0.0,
                "estimated_cost_to_offer_usd": 0.0,
            }
        
        # Estimated cost: $0.30/run (discovery+tailoring) = ~0.15/job
        # This is rough; actual cost depends on token usage
        total_cost = total_apps * 0.15
        
        return {
            "total_cost_usd": round(total_cost, 2),
            "total_applications": total_apps,
            "applications_per_dollar": round(total_apps / (total_cost or 1), 2),
            "responses_per_dollar": round(responded / (total_cost or 1), 2),
            "cost_per_response_usd": round(total_cost / (responded or 1), 2),
            "cost_per_interview_usd": round(total_cost / (interviews or 1), 2),
            "estimated_cost_to_offer_usd": round(total_cost / (max(interviews, 1) or 1) * 3, 2),  # Rough: 1 offer per 3 interviews
        }
        
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    init_tracking_db()
    
    # Example: Record an application
    apply_to_job(job_id=1, via="direct", tailored_resume_id="anthropic_tailored.md")
    
    # Example: Record a response
    record_response(
        job_id=1,
        response_type="interview",
        response_source="email",
        response_text="Thank you for your interest. We'd like to schedule an interview...",
    )
    
    # Show summary
    print("=== Application Summary ===")
    print(json.dumps(get_applications_summary(), indent=2))
    
    print("\n=== ROI Analysis ===")
    print(json.dumps(get_roi_analysis(), indent=2))
    
    print("\n=== Pending Applications ===")
    pending = get_applications_by_status("pending")
    print(f"Waiting on responses from {len(pending)} companies")
