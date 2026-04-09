"""
Token Instrumentation — Log token usage per run for cost tracking and ROI analysis.

Tracks:
  - Tokens per skill (job-discovery, resume-tailoring, linkedin-content)
  - Tokens per pipeline run (jobs, briefing, gmail)
  - Cost estimation (input/output rates from Claude pricing)
  - Supabase logging for aggregated ROI reporting

Used by AKTIVIQ to track CAiO (Claude-as-an-Operator) cost per client.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SkillName(Enum):
    """Skill identifier for token tracking."""
    JOB_DISCOVERY = "job_discovery"
    RESUME_TAILORING = "resume_tailoring"
    LINKEDIN_CONTENT = "linkedin_content"
    GMAIL_TRIAGE = "gmail_triage"
    BRIEFING = "briefing"
    UNKNOWN = "unknown"


@dataclass
class TokenUsage:
    """Token usage record for a single Claude API call."""
    skill_name: SkillName
    input_tokens: int
    output_tokens: int
    model: str = "claude-opus-4-6"
    timestamp: str = None
    run_id: str = None
    user_id: str = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}

    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.input_tokens + self.output_tokens

    def estimated_cost_usd(self) -> float:
        """
        Estimate cost in USD based on current Claude pricing (as of Apr 2026).
        
        Pricing (approximate):
          - claude-opus-4-6: $15/1M input, $75/1M output
          - claude-sonnet-4-6: $3/1M input, $15/1M output
          - claude-haiku-4-5: $0.80/1M input, $4/1M output
        """
        pricing = {
            "claude-opus-4-6": {"input": 15 / 1_000_000, "output": 75 / 1_000_000},
            "claude-sonnet-4-6": {"input": 3 / 1_000_000, "output": 15 / 1_000_000},
            "claude-haiku-4-5": {"input": 0.80 / 1_000_000, "output": 4 / 1_000_000},
        }

        rates = pricing.get(self.model, pricing["claude-opus-4-6"])
        return (self.input_tokens * rates["input"]) + (self.output_tokens * rates["output"])

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for logging."""
        return {
            "skill_name": self.skill_name.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens(),
            "model": self.model,
            "estimated_cost_usd": round(self.estimated_cost_usd(), 6),
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
        }


class TokenInstrumenter:
    """
    Log token usage for cost tracking and ROI analysis.
    
    Usage:
        instrumenter = TokenInstrumenter(run_id="job_search_20260409_143000")
        instrumenter.record(
            skill=SkillName.JOB_DISCOVERY,
            input_tokens=2000,
            output_tokens=840,
            metadata={"query_count": 5, "jobs_found": 12}
        )
        instrumenter.save()  # Write to logs/ and Supabase
    """

    def __init__(self, run_id: str, user_id: str = "agam", skill: SkillName = SkillName.UNKNOWN):
        self.run_id = run_id
        self.user_id = user_id
        self.skill = skill
        self.start_time = datetime.now()
        self.records: list[TokenUsage] = []

        # Output directory
        self.output_dir = Path(__file__).resolve().parent.parent.parent / "output" / "token_logs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        skill: SkillName,
        input_tokens: int,
        output_tokens: int,
        model: str = "claude-opus-4-6",
        metadata: Optional[dict[str, Any]] = None,
    ) -> TokenUsage:
        """Record token usage for a single API call."""
        usage = TokenUsage(
            skill_name=skill,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            run_id=self.run_id,
            user_id=self.user_id,
            metadata=metadata or {},
        )
        self.records.append(usage)
        logger.info(f"[{skill.value}] {input_tokens + output_tokens} tokens (${usage.estimated_cost_usd():.4f})")
        return usage

    def total_tokens(self) -> int:
        """Total tokens across all recorded calls."""
        return sum(r.total_tokens() for r in self.records)

    def total_cost_usd(self) -> float:
        """Total estimated cost across all recorded calls."""
        return sum(r.estimated_cost_usd() for r in self.records)

    def summary(self) -> dict[str, Any]:
        """Get summary of token usage for this run."""
        by_skill = {}
        for record in self.records:
            skill_key = record.skill_name.value
            if skill_key not in by_skill:
                by_skill[skill_key] = {
                    "count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                }
            by_skill[skill_key]["count"] += 1
            by_skill[skill_key]["input_tokens"] += record.input_tokens
            by_skill[skill_key]["output_tokens"] += record.output_tokens
            by_skill[skill_key]["total_tokens"] += record.total_tokens()
            by_skill[skill_key]["estimated_cost_usd"] += record.estimated_cost_usd()

        return {
            "run_id": self.run_id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_records": len(self.records),
            "total_tokens": self.total_tokens(),
            "total_estimated_cost_usd": round(self.total_cost_usd(), 6),
            "by_skill": by_skill,
        }

    def save(self, format: str = "jsonl") -> str:
        """
        Save token logs to disk (and optionally to Supabase).
        
        Args:
            format: "jsonl" (one record per line) or "json" (full summary)
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().isoformat().replace(":", "-")
        
        if format == "jsonl":
            filename = f"{self.run_id}_{timestamp}.jsonl"
            filepath = self.output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                for record in self.records:
                    f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            logger.info(f"Token logs saved: {filepath}")
        else:  # json
            filename = f"{self.run_id}_{timestamp}_summary.json"
            filepath = self.output_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.summary(), f, indent=2, ensure_ascii=False)
            logger.info(f"Token summary saved: {filepath}")

        # Optional: save to Supabase for aggregated ROI reporting
        try:
            self._save_to_supabase()
        except Exception as exc:
            logger.warning(f"Supabase save failed (non-critical): {exc}")

        return str(filepath)

    def _save_to_supabase(self) -> None:
        """
        Save token usage to Supabase for centralized ROI tracking.
        
        Table: automation_runs (if it exists)
        Columns: run_id, user_id, skill, tokens_used, cost_usd, timestamp
        
        TODO: Implement Supabase client call
        """
        # For now, this is a placeholder
        logger.debug("Supabase save: not yet implemented")
        pass


# ── Global instrumentation instance ──────────────────────────────────

_current_instrumenter: Optional[TokenInstrumenter] = None


def init_instrumentation(run_id: str, user_id: str = "agam") -> TokenInstrumenter:
    """Initialize global token instrumenter."""
    global _current_instrumenter
    _current_instrumenter = TokenInstrumenter(run_id, user_id)
    return _current_instrumenter


def record_tokens(
    skill: SkillName,
    input_tokens: int,
    output_tokens: int,
    model: str = "claude-opus-4-6",
    metadata: Optional[dict[str, Any]] = None,
) -> TokenUsage:
    """Record token usage in the current instrumenter."""
    if _current_instrumenter is None:
        logger.warning("Token instrumenter not initialized; creating one now")
        init_instrumentation(run_id="default")

    return _current_instrumenter.record(skill, input_tokens, output_tokens, model, metadata)


def get_current_summary() -> dict[str, Any]:
    """Get summary of token usage so far."""
    if _current_instrumenter is None:
        return {}
    return _current_instrumenter.summary()


def finalize_instrumentation(format: str = "jsonl") -> str:
    """Finalize and save token logs."""
    if _current_instrumenter is None:
        logger.warning("Token instrumenter not initialized")
        return ""
    return _current_instrumenter.save(format=format)


# ── Test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: track a job discovery run
    run_id = f"job_discovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    instrumenter = TokenInstrumenter(run_id, user_id="agam")

    # Simulate multiple skill calls
    instrumenter.record(
        SkillName.JOB_DISCOVERY,
        input_tokens=2000,
        output_tokens=840,
        metadata={"queries": 5, "jobs_found": 12},
    )
    instrumenter.record(
        SkillName.JOB_DISCOVERY,
        input_tokens=1500,
        output_tokens=620,
        metadata={"evaluation_phase": True},
    )

    print("\n=== Token Usage Summary ===")
    print(json.dumps(instrumenter.summary(), indent=2))
    print(f"\nTotal: {instrumenter.total_tokens()} tokens (${instrumenter.total_cost_usd():.6f})")

    # Save
    instrumenter.save(format="json")
