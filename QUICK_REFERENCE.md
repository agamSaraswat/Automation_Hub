# Quick Reference — Automation Hub Commands

## Profile Management

```bash
# Switch to your profile
python -m src.config.profile_manager --set soumyabrata

# Show current profile
python -m src.config.profile_manager --show

# List all profiles
python -m src.config.profile_manager --list

# Verify profile is valid
python -m src.config.profile_manager --verify
```

## Job Search

```bash
# Dry run (no API calls, demo data)
python dry_run_phase1.py

# Full pipeline: discover + tailor + queue
python run.py --jobs

# Review discovered jobs
python run.py --jobs review

# Check system status
python run.py --status
```

## Daily Automation

```bash
# Morning briefing (decision-support summary)
python run.py --briefing

# Gmail triage (urgent emails)
python run.py --gmail

# Generate LinkedIn post (draft mode)
python run.py --linkedin

# Start full scheduler (all jobs)
python run.py --schedule
```

## Configuration & Setup

```bash
# Interactive setup wizard
python run.py --setup

# Validate configuration
python run.py --status

# Edit environment
nano .env
```

## Token Tracking

```bash
# View token usage report
ls output/token_logs/

# Check latest summary
cat output/token_logs/*_summary.json | tail -n 50
```

## Logs & Debugging

```bash
# View today's logs
tail -f logs/$(date +%Y-%m-%d).log

# Enable debug mode
export LOG_LEVEL=DEBUG
python run.py --jobs

# View output artifacts
ls output/jobs/
ls output/tailored_resumes/
ls output/token_logs/
```

## File Locations

```
agam-automation-hub/
├── config/
│   ├── profiles/
│   │   ├── agam.yaml              (example)
│   │   ├── soumyabrata.yaml       (YOUR profile)
│   │   └── active_profile.txt     (current)
│   └── job_search.yaml            (discovery config)
├── master_resume/
│   └── soumyabrata_master_resume.md  (YOUR resume)
├── output/
│   ├── jobs/                       (discovered jobs)
│   ├── tailored_resumes/           (tailored resumes)
│   ├── linkedin/                   (draft posts)
│   ├── token_logs/                 (cost tracking)
│   └── briefings/                  (morning summaries)
├── logs/                           (daily logs)
└── src/
    ├── jobs/
    │   ├── harness.py              (P→G→E pattern)
    │   ├── claude_job_discovery.py (web search)
    │   └── claude_resume_tailoring.py (tailoring)
    ├── messaging/
    │   └── gmail_triage_v2.py      (structured output)
    └── services/
        ├── automation.py           (orchestration)
        └── token_instrumentation.py (cost tracking)
```

## Setup Sequence (Quick)

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env: add ANTHROPIC_API_KEY

# 2. Activate your profile
python -m src.config.profile_manager --set soumyabrata

# 3. Create your master resume
# Edit: master_resume/soumyabrata_master_resume.md

# 4. Test dry-run
python dry_run_phase1.py

# 5. Run real pipeline
python run.py --jobs
```

## Common Errors & Fixes

| Error | Fix |
|-------|-----|
| `ANTHROPIC_API_KEY not set` | `echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env` |
| `Profile not found` | `python -m src.config.profile_manager --set soumyabrata` |
| `Master resume not found` | Create `master_resume/soumyabrata_master_resume.md` |
| `Gmail credentials missing` | Download from Google Cloud Console, save to repo |
| `Module not found` | `pip install -r requirements.txt` |
| `Permission denied` | `chmod +x run.py cli.py dry_run_phase1.py` |

## Performance Expectations

| Component | Time | Cost | Output |
|-----------|------|------|--------|
| Job Discovery | 2–3 min | $0.12 | 5–10 jobs |
| Resume Tailoring | 1 min/job | $0.09 | Tailored resume + trace |
| Gmail Triage | 1 min | $0.014 | Classification + decisions |
| LinkedIn Draft | 1–2 min | $0.065 | Draft + evaluator assessment |
| **Total** | **~10 min** | **~$0.30** | **Complete workflow** |

## Architecture at a Glance

```
User Profile (config/profiles/your-name.yaml)
    ↓
Job Discovery Agent (Claude web search)
    ↓
Planner → Generator → Evaluator (Adversarial harness)
    ↓
Semantic Relevance Scoring (0–1 with reasons)
    ↓
Deduplication (30-day history)
    ↓
Resume Tailoring Harness (Evaluator checks truth)
    ↓
Token Instrumentation (Cost tracking)
    ↓
Output Queue (Human reviews before applying)
    ↓
Decision-Support Summaries (Gmail triage, briefings)
```

## Key Principles

✅ **No Naked Scoring** — Every evaluation has ≥3 reasons  
✅ **No Hallucination** — Every claim traceable to master resume  
✅ **Human Gates** — All outbound actions require approval  
✅ **Explainable** — Full harness traces available  
✅ **Token Tracked** — Cost visibility for ROI  

---

**Quick Start:** `python dry_run_phase1.py` → `python run.py --jobs` → Review output

**Full Guide:** See `SETUP_FOR_SOUMYABRATA.md`

**Architecture:** See `PHASE1_SUMMARY.md`
