# Job Discovery Skill

**Single-line description:** Discover relevant job postings via Claude-powered web search, deduplicate against history, and evaluate semantic relevance with explainable reasoning.

## Purpose

Replace dead/unreliable scrapers (RemoteOK, Himalayas, Indeed RSS) with a Claude agent that searches the web for jobs matching target roles, companies, and keywords. Every discovered job gets explainable relevance scoring. No naked scoring — humans see WHY a job was included/excluded.

## Implementation

**Mechanism:** Planner → search strategy. Generator → web_search calls. Evaluator → semantic relevance check against resume + job criteria. Returns deduplicated job list with scoring rationale.

**Inputs:**
- `target_roles`: ["Senior Data Scientist", "ML Engineer", "Analytics Engineer"]
- `target_keywords`: ["ML", "Python", "PostgreSQL", "FastAPI", "production systems"]
- `exclude_keywords`: ["React", "DevOps", "C++", "legacy code"]
- `locations`: ["Remote", "Boston", "San Francisco", "Singapore"]
- `daily_limit`: 10 (max jobs to queue per day)

**Outputs:**
```json
{
  "jobs": [
    {
      "title": "Senior Data Scientist",
      "company": "Anthropic",
      "url": "https://...",
      "location": "Remote",
      "jd_text": "...",
      "source": "web_search",
      "discovered_at": "2026-04-09T14:30:00Z",
      "relevance_score": 0.85,
      "scoring_reasons": [
        "Title match: Senior Data Scientist (+30)",
        "Keyword match: ML, Python, production systems (+35)",
        "Remote location preferred (+15)",
        "No blocked keywords"
      ],
      "decision": "kept",
      "unique_id": "sha256(url)"
    }
  ],
  "run_metadata": {
    "timestamp": "2026-04-09T14:30:00Z",
    "total_discovered": 12,
    "deduplicated": 2,
    "kept_after_filtering": 10,
    "tokens_used": 2840
  }
}
```

## SLA Contract

**WILL:**
- Discover 5–20 relevant jobs per run
- Deduplicate against last 30 days of history
- Provide explainable scoring (0–100) with at least 3 reasons
- Return structured JSON with all required fields
- Log token usage per discovery run
- Gate output: human reviews before queueing to DB

**WON'T:**
- Auto-apply to jobs (human gate required)
- Modify job titles or descriptions
- Store passwords or API keys in logs
- Send emails or notifications without explicit call
- Operate on undefined target roles or locations

## Configuration

```yaml
job_discovery:
  enabled: true
  strategy: web_search
  search_freshness: daily  # run once per 24h
  target_roles:
    - "Senior Data Scientist"
    - "ML Engineer"
    - "Analytics Engineer"
  target_keywords:
    - "machine learning"
    - "Python"
    - "production systems"
    - "PostgreSQL"
    - "FastAPI"
  exclude_keywords:
    - "React"
    - "DevOps"
    - "legacy"
  locations:
    - "Remote"
    - "Boston"
  daily_limit: 10
```

## Error Handling

- If web_search unavailable → fall back to cached results from last 7 days
- If deduplication DB fails → skip dedup (human reviews will catch duplicates)
- If Claude API times out → partial results with warning in metadata
- If invalid config → raise ConfigError at startup; fail fast

## Testing

```bash
python -m src.jobs.test_job_discovery --dry-run
# Output: discovered_jobs.json, token_report.jsonl
```

---

**Status:** Active | **Last Updated:** 2026-04-09 | **Owner:** Soumyabrata
