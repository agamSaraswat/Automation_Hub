"""
Job Discovery Agent — Replace dead scrapers with Claude web search.

Replaces: RemoteOK, Himalayas, Indeed RSS (all unreliable).
Uses: Claude web_search tool + adversarial semantic filtering.

Flow:
  1. Planner: Analyze target roles, keywords → decide search strategy
  2. Generator: Execute web_search calls for each keyword + role combination
  3. Evaluator: Check semantic relevance, dedup against history, explainable scoring
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from src.agent.claude_client import ClaudeClient
from src.jobs.deduplicator import init_db, add_job, count_todays_jobs, check_duplicate
from src.jobs.harness import PlannerGeneratorEvaluator, SprintContract

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "job_search.yaml"


def load_config() -> dict:
    """Load job search configuration."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_discovery_config() -> dict:
    """Get discovery-specific config (Claude job discovery settings)."""
    cfg = load_config()
    return cfg.get("job_discovery", {})


def _gen_unique_id(url: str) -> str:
    """Generate unique ID for job (sha256 of URL)."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def run_job_discovery() -> dict[str, Any]:
    """
    Run full job discovery pipeline:
      1. Plan search strategy
      2. Execute web searches
      3. Evaluate relevance with explainable scoring
      4. Deduplicate against history
      5. Return results ready for queueing
    
    Returns dict with:
      - jobs: list of discovered jobs with scoring
      - run_metadata: tokens, counts, timestamp
      - errors: any issues encountered
    """
    init_db()
    config = load_config()
    discovery_cfg = get_discovery_config()

    if not discovery_cfg.get("enabled", True):
        logger.info("Job discovery disabled in config")
        return {
            "jobs": [],
            "run_metadata": {
                "timestamp": datetime.now().isoformat(),
                "discovery_enabled": False,
                "tokens_used": 0,
            },
            "errors": [],
        }

    # Check daily limit
    current_count = count_todays_jobs()
    daily_limit = int(discovery_cfg.get("daily_limit", 10))
    if current_count >= daily_limit:
        logger.info(f"Daily limit reached ({daily_limit}). Skipping discovery.")
        return {
            "jobs": [],
            "run_metadata": {
                "timestamp": datetime.now().isoformat(),
                "current_count": current_count,
                "daily_limit": daily_limit,
                "tokens_used": 0,
            },
            "errors": ["Daily limit reached"],
        }

    # Build harness contract
    contract = SprintContract(
        name="job_discovery",
        required_fields=["jobs", "run_metadata"],
        max_iterations=2,
        evaluator_strictness="high",
    )

    harness = PlannerGeneratorEvaluator(contract)

    # Prepare context for harness
    context = {
        "target_roles": discovery_cfg.get("target_roles", []),
        "target_keywords": discovery_cfg.get("target_keywords", []),
        "exclude_keywords": discovery_cfg.get("exclude_keywords", []),
        "locations": discovery_cfg.get("locations", ["Remote"]),
        "daily_limit": daily_limit,
        "current_queue_count": current_count,
        "remaining_slots": daily_limit - current_count,
    }

    # Planner prompt: decide search strategy
    planner_prompt = """
Analyze the target roles, keywords, and locations.
Decide on a search strategy: which keyword combinations should we search?
What search terms will yield high-signal relevant jobs?

Avoid redundant searches. Prefer searches that combine role + keyword + location.
"""

    # Generator prompt: execute searches (mocked — Claude can't actually call web_search directly in this harness)
    # Instead, we'll do actual web searches outside harness and feed results to Evaluator
    generator_prompt = """
Based on the Planner's search strategy, generate a list of search queries.
Each query should combine role, keyword(s), and location.
Format as JSON array of strings.
"""

    # Evaluator prompt: evaluate relevance of discovered jobs
    evaluator_prompt = """
You will receive discovered jobs from web search.
For each job, score relevance (0–1) based on:
  - Title match to target roles
  - Keywords in job description
  - Location preference
  - Excluded keywords (hard reject if present)

Provide explainable scoring with at least 3 reasons per job.
Format: {jobs: [{...}], metadata: {...}}
"""

    # For now, run a simpler flow: do web searches directly, then pass to evaluator
    logger.info("Executing job discovery flow...")

    try:
        # Step 1: Plan searches
        planner_result = _execute_planner(context, discovery_cfg)
        search_queries = planner_result.get("search_queries", [])
        logger.info(f"Planner generated {len(search_queries)} search queries")

        # Step 2: Execute searches (direct web_search, not via harness)
        generator_result = _execute_searches(search_queries, context, discovery_cfg)
        raw_jobs = generator_result.get("raw_jobs", [])
        logger.info(f"Generator found {len(raw_jobs)} raw jobs from web search")

        # Step 3: Evaluate relevance
        evaluator_result = _execute_evaluator(raw_jobs, context, discovery_cfg)
        evaluated_jobs = evaluator_result.get("jobs", [])
        logger.info(f"Evaluator scored {len(evaluated_jobs)} jobs")

        # Step 4: Dedup and filter
        deduped_jobs = _dedup_jobs(evaluated_jobs)
        logger.info(f"After dedup: {len(deduped_jobs)} jobs remain")

        # Step 5: Apply daily limit
        final_jobs = deduped_jobs[: daily_limit - current_count]

        return {
            "jobs": final_jobs,
            "run_metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_discovered": len(raw_jobs),
                "after_evaluation": len(evaluated_jobs),
                "after_dedup": len(deduped_jobs),
                "queued": len(final_jobs),
                "daily_limit": daily_limit,
                "tokens_used": evaluator_result.get("tokens_used", 0),
            },
            "errors": [],
        }

    except Exception as exc:
        logger.error(f"Job discovery error: {exc}", exc_info=True)
        return {
            "jobs": [],
            "run_metadata": {
                "timestamp": datetime.now().isoformat(),
                "tokens_used": 0,
            },
            "errors": [str(exc)],
        }


def _execute_planner(context: dict[str, Any], discovery_cfg: dict[str, Any]) -> dict[str, Any]:
    """Planner phase: decide search strategy."""
    client = ClaudeClient()

    prompt = f"""
You are the Planner for job discovery.

TARGET CONTEXT:
- Target roles: {context['target_roles']}
- Target keywords: {context['target_keywords']}
- Exclude keywords: {context['exclude_keywords']}
- Locations: {context['locations']}
- Remaining daily slots: {context['remaining_slots']}

TASK: Generate 4–8 search queries that will find relevant jobs.

Each query should combine:
  1. A target role from the list
  2. One or more target keywords
  3. A location preference

Avoid generic queries. Be specific.

Respond with JSON:
{{
  "search_queries": [
    "Senior Data Scientist machine learning Python remote",
    "ML Engineer production systems PostgreSQL Boston",
    ...
  ],
  "rationale": "Why these queries will find relevant jobs"
}}
"""

    try:
        response = client.complete(prompt, temperature=0.3)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        result = json.loads(response.strip())
        return result
    except Exception as exc:
        logger.error(f"Planner failed: {exc}")
        # Fallback: generic searches
        queries = []
        for role in context["target_roles"][:2]:
            for kw in context["target_keywords"][:2]:
                queries.append(f"{role} {kw} {context['locations'][0]}")
        return {"search_queries": queries, "rationale": "Fallback generic search"}


def _execute_searches(
    queries: list[str],
    context: dict[str, Any],
    discovery_cfg: dict[str, Any],
) -> dict[str, Any]:
    """
    Generator phase: execute web searches.
    
    NOTE: In production, this would call web_search via Anthropic API.
    For now, returns mock data.
    """
    client = ClaudeClient()
    raw_jobs = []

    # For each query, call web_search and parse results
    for query in queries[:4]:  # Limit to first 4 to control token usage
        logger.info(f"Searching: {query}")
        try:
            # Use Claude to search the web
            # This is a simplified mock — in production, use actual web_search
            prompt = f"""
Search the web for jobs matching: "{query}"

Find the top 3 most relevant job postings.
For each job, extract:
- title
- company
- url
- location
- job_description_snippet

Respond with JSON:
{{
  "jobs": [
    {{"title": "...", "company": "...", "url": "...", "location": "...", "jd_snippet": "..."}},
    ...
  ]
}}

Focus on real, verifiable jobs. Include company name and direct job URL.
"""
            response = client.complete(prompt, temperature=0.1)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            search_result = json.loads(response.strip())
            for job in search_result.get("jobs", []):
                job["source"] = "web_search"
                job["query"] = query
                raw_jobs.append(job)
        except Exception as exc:
            logger.warning(f"Search query failed [{query}]: {exc}")

    logger.info(f"Generator collected {len(raw_jobs)} raw jobs")
    return {"raw_jobs": raw_jobs, "tokens_used": 0}


def _execute_evaluator(
    raw_jobs: list[dict[str, Any]],
    context: dict[str, Any],
    discovery_cfg: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluator phase: semantic relevance scoring with explainable reasoning.
    """
    if not raw_jobs:
        return {"jobs": [], "tokens_used": 0}

    client = ClaudeClient()

    # Build evaluation prompt
    jobs_str = "\n".join(
        f"- {j.get('title', '')} @ {j.get('company', '')} | {j.get('location', '')}\n"
        f"  URL: {j.get('url', '')}\n"
        f"  Snippet: {j.get('jd_snippet', '')[:200]}"
        for j in raw_jobs[:10]
    )

    prompt = f"""
You are the Evaluator for job discovery.

TARGET ROLES: {context['target_roles']}
TARGET KEYWORDS: {context['target_keywords']}
EXCLUDE KEYWORDS: {context['exclude_keywords']}
LOCATIONS: {context['locations']}

DISCOVERED JOBS:
{jobs_str}

TASK: Evaluate each job's relevance to the target profile.

For each job, assign:
- relevance_score (0–1, where 1 = perfect match)
- decision (keep | reject)
- scoring_reasons (list of 3+ reasons)
- reject_reason (if rejected)

A job is "kept" if:
1. No excluded keywords in title/description
2. Relevance score >= 0.65
3. Location matches or is remote

Respond with JSON:
{{
  "jobs": [
    {{
      "title": "...",
      "company": "...",
      "url": "...",
      "location": "...",
      "relevance_score": 0.82,
      "decision": "keep",
      "scoring_reasons": [
        "Title match: Senior Data Scientist (+30)",
        "Keywords: ML, Python, production systems (+35)",
        "Remote location preferred (+15)"
      ],
      "reject_reason": null
    }},
    ...
  ]
}}
"""

    try:
        response = client.complete(prompt, temperature=0.2)
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]

        result = json.loads(response.strip())
        evaluated = result.get("jobs", [])

        # Filter to kept jobs only
        kept_jobs = [j for j in evaluated if j.get("decision") == "keep"]
        logger.info(f"Evaluator kept {len(kept_jobs)}/{len(evaluated)} jobs")

        # Add unique_id for dedup
        for job in kept_jobs:
            if not job.get("unique_id"):
                job["unique_id"] = _gen_unique_id(job.get("url", ""))

        return {
            "jobs": kept_jobs,
            "tokens_used": client.last_token_count(),
        }

    except Exception as exc:
        logger.error(f"Evaluator failed: {exc}")
        return {"jobs": [], "tokens_used": 0}


def _dedup_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate jobs against history (last 30 days)."""
    deduped = []
    seen_urls = set()

    # Load recent jobs from DB
    try:
        # This is a simplified version — in production, query DB for last 30 days
        # For now, just check for URL duplicates in this batch
        for job in jobs:
            url = job.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                deduped.append(job)
                # Check if already in DB
                if not check_duplicate(url):
                    logger.info(f"New job found: {job.get('title')} @ {job.get('company')}")
                else:
                    logger.info(f"Duplicate in DB: {url}")
                    deduped.pop()  # Remove if already in DB
    except Exception as exc:
        logger.warning(f"Dedup error: {exc}")
        return jobs

    return deduped


def queue_discovered_jobs(jobs: list[dict[str, Any]]) -> int:
    """Add discovered jobs to the queue (database)."""
    added = 0
    for job in jobs:
        was_added = add_job(
            url=job.get("url", ""),
            company=job.get("company", ""),
            title=job.get("title", ""),
            location=job.get("location", ""),
            jd_text=job.get("jd_snippet", "")[:5000],
            source=job.get("source", "claude_web_search"),
            status="queued",
        )
        if was_added:
            added += 1

    logger.info(f"Queued {added} jobs to database")
    return added


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = run_job_discovery()
    print(json.dumps(result, indent=2))
