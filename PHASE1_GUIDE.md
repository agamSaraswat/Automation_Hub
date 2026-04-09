# Agam Automation Hub — Phase 1 Guide

**Status:** Phase 1 Complete | **Date:** April 9, 2026 | **Owner:** Soumyabrata Ghosh

## What's New in Phase 1

### ✅ Fixed Components

| Component | Old | New | Status |
|-----------|-----|-----|--------|
| **Job Discovery** | Dead scrapers (RemoteOK, Himalayas, Indeed RSS) | Claude web search agent | ✅ Live |
| **Job Filtering** | Keyword regex matching | Claude semantic evaluation | ✅ Live |
| **Resume Tailoring** | One-shot generation | Adversarial harness (Evaluator checks truthfulness) | ✅ Live |
| **Gmail Triage** | Fragile string parsing | Structured JSON output | ✅ Live |
| **Token Tracking** | None | Per-skill instrumentation + cost tracking | ✅ Live |

### 🏗️ New Architecture

```
Job Discovery:
  1. Planner → Decide search strategy (roles + keywords + locations)
  2. Generator → Execute web searches via Claude
  3. Evaluator → Semantic relevance scoring (0–1) with explainable reasoning
  4. Dedup → Filter against 30-day history
  5. Queue → Add to DB (human gate before applying)

Resume Tailoring:
  1. Planner → Analyze JD, extract 8–10 competencies
  2. Generator → Create tailored resume (reorder bullets, highlight keywords)
  3. Evaluator → Challenge claims (traceable to master? No hallucination?)
  4. Save → Output markdown with full harness trace

Gmail Triage:
  1. Fetch → Get recent unread emails (last 30 min)
  2. Classify → Use Claude with structured JSON output
  3. Categories → urgent, normal, newsletter, spam
  4. Decide → Suggest actions (what to do, not just summary)
  5. Telegram → Send decision-support summary

LinkedIn Content:
  1. Planner → Analyze seed idea, decide angle
  2. Generator → Draft post (headline + body + CTA)
  3. Evaluator → Check authenticity, engagement, brand safety
  4. Output → Draft with evaluator assessment
  5. Gate → Human approval required before posting

Token Instrumentation:
  - Track input/output tokens per skill call
  - Estimate cost in USD (Claude pricing)
  - Log to disk (JSONL) + optional Supabase
  - Aggregate ROI per client per run
```

## Setup

### 1. Install Dependencies

```bash
cd /path/to/agam-automation-hub
pip install -r requirements.txt

# Update Anthropic to latest (if needed for complete_json())
pip install --upgrade anthropic
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys

# Required:
#   ANTHROPIC_API_KEY=sk-ant-...

# Optional:
#   LINKEDIN_ACCESS_TOKEN=...
#   TELEGRAM_BOT_TOKEN=...
#   GMAIL_CREDENTIALS_PATH=credentials.json
```

### 3. Run Setup Wizard

```bash
python run.py --setup
# Follow prompts to configure all services
```

### 4. Verify Setup

```bash
python run.py --status
# Should show:
#   ✓ ANTHROPIC_API_KEY: Set
#   ○ LINKEDIN_ACCESS_TOKEN: Not set (optional)
#   ○ TELEGRAM_BOT_TOKEN: Not set (optional)
#   etc.
```

## Usage

### Run Job Discovery + Tailoring

```bash
python run.py --jobs
```

**What happens:**
1. Job Discovery: Claude searches the web for relevant jobs
   - Planner analyzes target roles + keywords
   - Generator executes searches
   - Evaluator scores relevance (0–1) with explainable reasons
   - Results: `output/jobs/{date}/discovered_jobs.json`
2. Deduplication: Filter against last 30 days
3. Resume Tailoring: For each job, create tailored resume
   - Harness-driven with Evaluator checking truthfulness
   - Results: `output/tailored_resumes/{job_id}.md`
   - Trace: `output/tailored_resumes/{job_id}_trace.json`
4. Queue: Jobs ready for application (with human review gate)

**Token Cost Tracking:**
- Logs: `output/token_logs/{run_id}_*.json`
- Summary: Shows tokens used per skill per run
- Cost: Estimated USD based on current Claude pricing

### Run Gmail Triage

```bash
python run.py --gmail
```

**What happens:**
1. Fetches: Last 30 minutes of unread emails
2. Classifies: Using Claude with structured output
   - Categories: urgent, normal, newsletter, spam
   - Decision: "What should Soumyabrata do?"
3. Output: Structured JSON (decision-support, not just summary)
4. Telegram: Optionally sends summary (human gate on sending)

### Generate LinkedIn Post

```bash
python run.py --linkedin
```

**What happens:**
1. Planner: Decide content angle
2. Generator: Create draft
3. Evaluator: Check authenticity + engagement + brand safety
4. Review: Human approves before posting
5. Output: `output/linkedin/queue/{date}.md` (requires approval)

### Morning Briefing

```bash
python run.py --briefing
```

**Output:** Morning decision-support summary

### Start Full Scheduler

```bash
python run.py --schedule
```

**Runs all jobs on schedule:**
- Job discovery: Daily
- Gmail triage: Hourly
- LinkedIn: 2–3 times per week
- Briefing: 8 AM EST

## Phase 1 Deliverables

### ✅ Code Files

1. **Skill Definitions (AKTIVIQ standard):**
   - `src/jobs/job-discovery.md` — Specification document
   - `src/jobs/resume-tailoring.md` — Specification document
   - `src/linkedin/linkedin-content.md` — Specification document

2. **Harness Implementation:**
   - `src/jobs/harness.py` — Planner→Generator→Evaluator pattern (310 lines)

3. **Job Discovery:**
   - `src/jobs/claude_job_discovery.py` — Claude agent + semantic evaluation (360 lines)

4. **Resume Tailoring:**
   - `src/jobs/claude_resume_tailoring.py` — Harness-driven tailoring (230 lines)

5. **Gmail Triage v2:**
   - `src/messaging/gmail_triage_v2.py` — Structured JSON output (310 lines)

6. **Token Instrumentation:**
   - `src/services/token_instrumentation.py` — Cost tracking per skill (380 lines)

7. **Integration:**
   - `src/services/automation.py` — Wired all components together
   - `config/job_search.yaml` — Updated for Claude discovery

8. **Tests:**
   - `tests/test_phase1.py` — Comprehensive test suite

### 📊 Key Metrics

| Metric | Value |
|--------|-------|
| Total code added | ~1,800 lines |
| New Python files | 6 |
| New markdown specs | 3 |
| Test cases | 20+ |
| Harness iterations | 2 (configurable) |
| Token tracking | Per-skill, per-run |
| Human gates | All outbound actions |

## Error Handling & Logs

### Logs Location

```
logs/
  {YYYY-MM-DD}.log          — Daily rotation
output/
  jobs/                      — Job discovery results
  tailored_resumes/          — Resume outputs + traces
  linkedin/                  — LinkedIn queue + posted
  token_logs/                — Token instrumentation logs
  briefings/                 — Briefing archives
```

### Debug Mode

```bash
export LOG_LEVEL=DEBUG
python run.py --jobs
```

### Common Issues

**Issue:** "ANTHROPIC_API_KEY not set"
```bash
python run.py --setup
# Follow prompts to set API key
```

**Issue:** "Master resume not found"
```bash
# Verify file exists:
ls master_resume/agam_master_resume.md
# If missing, add it via Phase 2 (swap in your own)
```

**Issue:** "Gmail credentials not found"
```bash
# Download credentials.json from Google Cloud Console
# Save to repo root or update GMAIL_CREDENTIALS_PATH in .env
```

## Phase 2 Preview (Next Session)

### Planned Additions

1. **Outreach Pipeline** (highest ROI missing piece)
   - Warm intros (NetMap + willIntroduce gate)
   - Cold personalized (Claude drafts + human reviews)
   - Application tracking

2. **NetMap Connection Layer**
   - Trust graph powering warm intro scoring
   - willIntroduce gate preventing cold outreach
   - Connection strength estimation

3. **Feedback Loop**
   - Track which jobs get responses
   - Adjust relevance scoring based on outcomes
   - Learn what works

4. **Multi-user Configuration**
   - Swap Agam config for Soumyabrata's profile
   - Wire personal resume + LinkedIn + Gmail
   - Run for own job search

5. **Frontend Updates**
   - Show harness evaluation data
   - Display token costs per run
   - Review + approve gates for all outbound actions

6. **TypeScript Port**
   - Python → TypeScript (keep same logic)
   - SQLite → Supabase RLS
   - Single-user → Multi-tenant
   - Merge into AKTIVIQ platform as `engine/` directory

## Architecture Decisions

### Why Adversarial Harness?

- **Planner** decides strategy (what to optimize for)
- **Generator** produces output (follow the plan)
- **Evaluator** challenges output (is it good enough?)
- **Result:** Higher quality, more robust, explainable decisions

### Why Structured JSON for Gmail?

- Fragile string parsing error-prone
- Claude's structured output (complete_json()) guarantees valid JSON
- Decision-support format ("what to do") vs. status format ("what happened")

### Why Token Tracking?

- AKTIVIQ needs ROI per client
- Cost visibility → better price negotiations
- Skill performance tracking → identify expensive/inefficient skills

### Why "No Naked Scoring"?

- Every evaluation must explain reasons
- Humans can understand why a job was included/excluded
- Auditability for hiring decisions

## Support & Feedback

**Issues/Questions:**
- GitHub: [ReadlePress/agam-automation-hub](https://github.com/readlepress/agam-automation-hub)
- Email: soumyabrata@readlepress.in
- Slack: #aktiviq-dev

**Next Meeting:** Phase 2 kickoff (outreach pipeline + NetMap integration)

---

**Built for:** Agam Saraswat's job search automation | **Rebuilt for:** Soumyabrata's AKTIVIQ standard
**Status:** Production-ready (Phase 1) | **Last Updated:** 2026-04-09
