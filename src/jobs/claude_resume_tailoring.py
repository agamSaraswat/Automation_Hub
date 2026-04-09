"""
Resume Tailoring with Adversarial Harness

Flow:
  1. Planner: Parse JD, extract key competencies, find matching sections in master resume
  2. Generator: Create tailored resume highlighting relevant skills/experience
  3. Evaluator: Challenge each claim—is it traceable to master resume? No hallucination?
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.agent.claude_client import ClaudeClient
from src.jobs.harness import PlannerGeneratorEvaluator, SprintContract

logger = logging.getLogger(__name__)

MASTER_RESUME_PATH = Path(__file__).resolve().parent.parent.parent / "master_resume" / "agam_master_resume.md"


def load_master_resume() -> str:
    """Load the master resume."""
    try:
        with open(MASTER_RESUME_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Master resume not found: {MASTER_RESUME_PATH}")
        raise


def tailor_resume_for_job(
    job_id: str,
    job_title: str,
    job_description: str,
    max_iterations: int = 2,
) -> dict[str, Any]:
    """
    Tailor master resume for a specific job using adversarial harness.

    Args:
        job_id: Unique job ID for audit trail
        job_title: Job title (e.g., "Senior Data Scientist")
        job_description: Full job description text
        max_iterations: Max harness iterations (Planner → Generator → Evaluator)

    Returns:
        {
            "job_id": "...",
            "tailored_resume": "markdown...",
            "harness_trace": {...},
            "tokens_used": 0,
            "timestamp": "...",
        }
    """
    master_resume = load_master_resume()

    # Build harness contract
    contract = SprintContract(
        name="resume_tailoring",
        required_fields=["tailored_resume", "harness_trace"],
        max_iterations=max_iterations,
        evaluator_strictness="high",
    )

    harness = PlannerGeneratorEvaluator(contract)

    # Context for harness
    context = {
        "job_id": job_id,
        "job_title": job_title,
        "job_description": job_description[:2000],  # Limit to first 2000 chars
        "master_resume": master_resume[:5000],  # Limit to first 5000 chars
    }

    # Planner prompt
    planner_prompt = """
Analyze the job description and the master resume.
Identify the top 8-10 competencies required for this job.
For each competency, find relevant sections in the master resume.

Output JSON:
{
  "competencies": [
    {"competency": "Machine Learning", "evidence_in_resume": "Section: Professional Experience > Humana > bullet 1"},
    ...
  ],
  "strategy": "How to emphasize these competencies in the tailored resume",
  "sections_to_highlight": ["Professional Experience", "Technical Skills"],
  "keywords_to_prioritize": ["keyword1", "keyword2", ...]
}
"""

    # Generator prompt
    generator_prompt = """
Based on the Planner's analysis, create a tailored resume.

Rules:
1. Start with the master resume structure
2. Reorder bullet points to highlight top competencies first
3. Use exact language from master resume (no paraphrasing)
4. Add quantified metrics where available
5. Drop sections/bullets not relevant to this job
6. Keep formatting: markdown, ATS-safe
7. Max length: 2500 characters

Output JSON:
{
  "tailored_resume": "...markdown...",
  "removed_sections": ["..."],
  "reordered_bullets": {...},
  "highlighted_keywords": ["..."],
  "changes_explanation": "Why these changes"
}
"""

    # Evaluator prompt
    evaluator_prompt = """
Evaluate the tailored resume critically.

For each major claim or bullet point in the tailored resume:
1. Is it present in the master resume (exactly or closely paraphrased)?
2. Are numbers/metrics accurate?
3. Does it avoid hallucination?
4. Is it specific enough to be credible?

Output JSON:
{
  "verdict": "pass|needs_revision|fail",
  "score": 0.0–1.0,
  "challenges": [
    {"line": "...", "issue": "...", "severity": "critical|warning|minor"},
    ...
  ],
  "approved_claims": [
    {"line": "...", "verified": true},
    ...
  ],
  "suggestions": ["suggestion1", "suggestion2"],
  "confidence": 0.0–1.0,
  "flagged_hallucinations": []
}
"""

    try:
        logger.info(f"Tailoring resume for job {job_id}: {job_title}")

        result = harness.run(
            planner_prompt=planner_prompt,
            generator_prompt=generator_prompt,
            evaluator_prompt=evaluator_prompt,
            context=context,
            system_prompt=(
                "You are a resume tailoring expert. "
                "Your goal is to create credible, ATS-optimized tailored resumes from a master resume. "
                "Every claim must be traceable to the original. Never hallucinate experience."
            ),
        )

        if result.get("success"):
            logger.info(f"Resume tailoring succeeded for job {job_id}")
            return {
                "job_id": job_id,
                "job_title": job_title,
                "tailored_resume": result.get("output", {}).get("output", {}).get("tailored_resume", ""),
                "harness_trace": result.get("harness_trace", {}),
                "tokens_used": result.get("tokens_used", 0),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "verdict": result.get("verdict"),
            }
        else:
            logger.warning(f"Resume tailoring failed for job {job_id}: {result.get('error')}")
            return {
                "job_id": job_id,
                "job_title": job_title,
                "tailored_resume": "",
                "harness_trace": result.get("harness_trace", {}),
                "tokens_used": result.get("tokens_used", 0),
                "timestamp": __import__("datetime").datetime.now().isoformat(),
                "verdict": "fail",
                "error": result.get("error"),
            }

    except Exception as exc:
        logger.error(f"Resume tailoring error for job {job_id}: {exc}", exc_info=True)
        return {
            "job_id": job_id,
            "job_title": job_title,
            "tailored_resume": "",
            "harness_trace": {},
            "tokens_used": 0,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "verdict": "error",
            "error": str(exc),
        }


def save_tailored_resume(job_id: str, tailored_resume: str, output_dir: Optional[Path] = None) -> Path:
    """Save tailored resume to disk."""
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent.parent.parent / "output" / "tailored_resumes"

    output_dir.mkdir(parents=True, exist_ok=True)
    resume_path = output_dir / f"{job_id}.md"

    with open(resume_path, "w", encoding="utf-8") as f:
        f.write(tailored_resume)

    logger.info(f"Tailored resume saved: {resume_path}")
    return resume_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Example JD
    sample_jd = """
    Senior Data Scientist — Predictive Analytics & Healthcare AI

    We're looking for a Sr. Data Scientist to build production ML systems.

    Requirements:
    - 5+ years ML experience
    - Proficiency in Python, SQL, PySpark
    - Experience with healthcare data (EHR, claims) a plus
    - Ability to build end-to-end ML pipelines
    - Experience with Kubernetes and Docker
    - Communication skills to translate models for non-technical stakeholders

    Responsibilities:
    - Design and implement ML models for patient risk prediction
    - Build data pipelines and feature stores
    - Collaborate with clinical teams to deploy models
    - Monitor model performance and drift
    """

    result = tailor_resume_for_job(
        job_id="test_001",
        job_title="Senior Data Scientist — Anthropic",
        job_description=sample_jd,
        max_iterations=1,  # Quick test
    )

    print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])  # Print first 2000 chars

    if result.get("tailored_resume"):
        save_tailored_resume(result["job_id"], result["tailored_resume"])
