# Getting Started with Your Personal Automation Engine

**For:** Soumyabrata Ghosh  
**From:** Phase 1 Build (April 9, 2026)  
**Time to Setup:** ~30 minutes

---

## What You Have

A production-ready **AKTIVIQ-standard automation engine** for:
1. **Job Discovery** — Claude searches the web for relevant jobs with semantic evaluation
2. **Resume Tailoring** — Adversarial harness ensures no hallucination
3. **Gmail Triage** — Structured decision-support summaries
4. **LinkedIn Content** — Evaluator-checked posts (human gate before publishing)
5. **Token Tracking** — Cost per skill for ROI analysis

**Ready to plug in YOUR profile and run it for your own job search.**

---

## Step 1: Clone & Setup (5 minutes)

```bash
# Clone to local machine
git clone <repo-url> agam-automation-hub
cd agam-automation-hub

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## Step 2: Configure Your API Keys (10 minutes)

Edit `.env`:

```bash
# REQUIRED: Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE

# OPTIONAL: LinkedIn (for posting)
# Get from: https://www.linkedin.com/developers/apps
LINKEDIN_ACCESS_TOKEN=YOUR-TOKEN
LINKEDIN_PERSON_URN=urn:li:person:YOUR-URN
LINKEDIN_TOKEN_SET_DATE=2026-04-09

# OPTIONAL: Telegram (for notifications)
# Get from: Message @BotFather on Telegram
TELEGRAM_BOT_TOKEN=YOUR-BOT-TOKEN
TELEGRAM_CHAT_ID=YOUR-CHAT-ID

# OPTIONAL: Gmail (for triage)
# Download credentials.json from Google Cloud Console
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json

# System
TIMEZONE=America/New_York
DAILY_JOB_LIMIT=10
POST_TIME_WINDOW_START=8
POST_TIME_WINDOW_END=11
```

**Get API keys:**
- **Claude:** https://console.anthropic.com/
- **LinkedIn:** https://www.linkedin.com/developers/apps
- **Telegram:** Message @BotFather on Telegram
- **Gmail:** https://console.cloud.google.com/apis/credentials

## Step 3: Verify Setup (5 minutes)

```bash
python run.py --status
# Should show:
#   ✓ ANTHROPIC_API_KEY: Set
#   ○ LINKEDIN_ACCESS_TOKEN: Not set (optional)
#   etc.
```

## Step 4: Swap Your Profile (5 minutes)

### Option A: Use Pre-Built Template

Edit `config/profiles/soumyabrata.yaml`:

```yaml
name: "Soumyabrata Ghosh"
email: "soumyabrata@readlepress.in"
phone: "+1 (978) 555-XXXX"  # Update
location: "Worcester, MA, USA"

# Update LinkedIn
linkedin_profile: "https://linkedin.com/in/your-profile"

# Path to YOUR master resume (see Step 5)
master_resume_path: "master_resume/soumyabrata_master_resume.md"

job_preferences:
  target_roles:
    - "CTO"
    - "Co-founder"
    - "Founding Engineer"
    # ... add your target roles

  target_keywords:
    - "AI"
    - "Claude"
    - "systems"
    # ... add your keywords

  locations:
    - "Remote"
    - "Boston"
    # ... your locations
```

### Option B: Start from Scratch

```bash
# Create new profile
cp config/profiles/agam.yaml config/profiles/your-name.yaml

# Edit your-name.yaml with your details
```

### Activate Your Profile

```bash
python -m src.config.profile_manager --set soumyabrata

# Verify it loaded
python -m src.config.profile_manager --show
```

## Step 5: Add Your Master Resume (5 minutes)

Your master resume is the **source of truth** for all job tailoring. Every claim in tailored resumes must trace back to it.

### Create Master Resume

Create `master_resume/soumyabrata_master_resume.md`:

```markdown
# Soumyabrata Ghosh

**CTO & Co-founder — ReadlePress | AI Systems & Product**

Email: soumyabrata@readlepress.in | Phone: +1 (978) 555-XXXX | Location: Worcester, MA

---

## Professional Summary

...your full resume here...

## Experience

### CTO & Co-founder — ReadlePress
Jan 2026 – Present | Remote

- Founded ReadlePress with Sanjoy & Subhojit
- Architecture: HPC OS, AKTIVIQ, NetMap, Zwitter
- Tech stack: Python, TypeScript, FastAPI, Next.js, Supabase, Railway
- Building AI-first education platform

...rest of resume...
```

**Key Rule:** Include ALL experience, education, skills. Tailoring will selectively highlight relevant parts.

Update `config/profiles/soumyabrata.yaml`:

```yaml
master_resume_path: "master_resume/soumyabrata_master_resume.md"
```

## Step 6: Test the Full Pipeline (5 minutes)

### Dry-Run (No API Calls)

```bash
python dry_run_phase1.py
```

Shows complete pipeline with mock data. No API keys needed.

Expected output:
```
Job Discovery: 2 jobs → $0.12 USD
Resume Tailoring: 2 resumes → $0.18 USD
Gmail Triage: 3 emails → $0.014 USD
Total: ~17K tokens → $0.30 USD per run
```

### Run Real Pipeline

```bash
python run.py --jobs
```

**What happens:**
1. Claude searches web for jobs matching your profile
2. Evaluator scores each job (0–1) with explainable reasons
3. Resumes tailored (harness checks for hallucination)
4. Results queued for your review
5. Token cost tracked

**Output:**
- `output/jobs/{date}/discovered_jobs.json` — Raw results
- `output/tailored_resumes/{job_id}.md` — Tailored resumes
- `output/token_logs/{run_id}_summary.json` — Token tracking

### Review Job Queue

```bash
python run.py --jobs review
# Shows discovered jobs awaiting your review
```

### Try Gmail Triage

```bash
python run.py --gmail
# Classifies your recent unread emails
# Urgency scoring + decision support
```

## Step 7: Run Your First Full Automation (2 days from now)

Once everything is tested:

```bash
# Morning routine
python run.py --briefing              # Decision-support summary
python run.py --gmail                 # Email triage
python run.py --jobs                  # Discover + tailor resumes
python run.py --linkedin              # Generate LinkedIn post

# Or start scheduler for everything
python run.py --schedule
```

---

## Your Configuration Checklist

- [ ] `.env` configured with ANTHROPIC_API_KEY
- [ ] Optional APIs configured (LinkedIn, Telegram, Gmail)
- [ ] Profile swapped to `soumyabrata` via `profile_manager`
- [ ] Master resume created at `master_resume/soumyabrata_master_resume.md`
- [ ] Job preferences in `config/profiles/soumyabrata.yaml` match your target roles
- [ ] Dry-run passes: `python dry_run_phase1.py`
- [ ] Status shows all required APIs set: `python run.py --status`

---

## How It Works For You

### Job Discovery

**Your Needs:** CTO/Founder roles in AI with global opportunities

**What Happens:**
1. **Planner** analyzes your target roles + keywords
2. **Generator** searches web for "CTO AI" + "Founding Engineer" + etc.
3. **Evaluator** scores each job (0–1)
   - ✓ Title match
   - ✓ Keywords (AI, Claude, systems, product, founding)
   - ✓ Location (Remote, Boston, SF, Singapore)
   - ✗ Rejects: sales roles, junior positions, contract-only
4. **Dedup** filters against last 30 days
5. **Tailor** creates job-specific resume for each
6. **Gate** human reviews before applying

**Cost:** ~$0.12 per discovery run

### Resume Tailoring

**Your Need:** Different resume for "AI Product at Anthropic" vs "Systems at Google" vs "Founding at Startup"

**What Happens:**
1. **Planner** extracts key competencies from job description
2. **Generator** reorders your experience to lead with relevant bullets
3. **Evaluator** challenges each claim
   - "Did you really build this?"
   - "Is this in your master resume?"
   - "Can you verify with line number?"
4. **Output** tailored markdown + harness trace

**Cost:** ~$0.09 per job

**Zero hallucination:** Every claim traced to master resume

### Gmail Triage

**Your Need:** Quick scan of urgent items (visa, RFE, funding, board decisions)

**What Happens:**
1. Fetch last 30 min of unread emails
2. Claude classifies each (urgent, normal, newsletter, spam)
3. Structured JSON output with **decision support**
   - Not: "You have an email from Sanjoy"
   - But: "CEO needs approval on HPC deployment — act within 2 hours"
4. Summary sent to Telegram (optional)

**Cost:** ~$0.014 per triage

### Token Tracking

**Your Need:** ROI reporting for AKTIVIQ (how much does CAiO cost per client?)

**What Happens:**
1. Every Claude call logs input/output tokens
2. Cost calculated per skill (job discovery, resume tailoring, etc.)
3. Logs saved to `output/token_logs/{run_id}_summary.json`
4. Aggregated for monthly/quarterly reports

**Example Output:**
```json
{
  "run_id": "jobs_20260410_143000",
  "total_tokens": 17210,
  "total_cost_usd": 0.298,
  "by_skill": {
    "job_discovery": {
      "count": 3,
      "tokens": 7710,
      "cost": 0.12
    },
    "resume_tailoring": {
      "count": 2,
      "tokens": 5600,
      "cost": 0.09
    }
  }
}
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
# Edit .env and add your key
nano .env
# ANTHROPIC_API_KEY=sk-ant-YOUR-KEY
```

### "Profile not found: soumyabrata"
```bash
# Verify profile exists
ls config/profiles/soumyabrata.yaml

# If not, create it
cp config/profiles/agam.yaml config/profiles/soumyabrata.yaml
```

### "Master resume not found"
```bash
# Create it
touch master_resume/soumyabrata_master_resume.md

# Copy/paste your resume content into it
# Update master_resume_path in your profile YAML
```

### "Gmail credentials not found"
```bash
# Download credentials.json from Google Cloud Console
# Save to repo root or update GMAIL_CREDENTIALS_PATH in .env
GMAIL_CREDENTIALS_PATH=credentials.json
```

### Tokens very high/low?
```bash
# Check logs
cat output/token_logs/*.json | grep total_tokens

# Audit specific runs
python -m src.services.token_instrumentation --report
```

---

## Advanced: Running for Your Multiple Projects

You can create separate profiles for different contexts:

```bash
# Profile for full-time job search
python -m src.config.profile_manager --set soumyabrata-job-search

# Profile for founder role focus
python -m src.config.profile_manager --set soumyabrata-founder

# Profile for consulting/advisory roles
python -m src.config.profile_manager --set soumyabrata-advisory
```

Each profile has:
- Different target roles/keywords
- Different salary expectations
- Different resume emphasis

---

## Next: Phase 2 (When Ready)

Once Phase 1 is running smoothly, Phase 2 adds:

1. **Outreach Pipeline** — Warm intros via NetMap + cold personalized via Claude
2. **Feedback Loop** — Track which jobs get responses, adjust scoring
3. **TypeScript Port** — Python → TypeScript for AKTIVIQ merge
4. **Supabase** — SQLite → multi-tenant Supabase RLS
5. **GUI Dashboard** — Review queues, token tracking, harness traces

---

## Your Next Actions

### Today
- [ ] Clone repo
- [ ] Install dependencies
- [ ] Setup `.env` with ANTHROPIC_API_KEY
- [ ] Run `python dry_run_phase1.py` (see it work)

### Tomorrow
- [ ] Configure optional APIs (LinkedIn, Telegram, Gmail)
- [ ] Create master resume
- [ ] Activate your profile
- [ ] Test full pipeline

### In 2 Days
- [ ] Run `python run.py --jobs` (discover real jobs)
- [ ] Review queue and approve tailored resumes
- [ ] Use for your actual job search

---

## Support

**Questions?**
- Check `PHASE1_GUIDE.md` for full documentation
- See `PHASE1_SUMMARY.md` for architecture overview
- Run `python dry_run_phase1.py` to see full flow
- Review test cases: `tests/test_phase1.py`

**Issues?**
- Enable debug: `export LOG_LEVEL=DEBUG; python run.py --jobs`
- Check logs: `tail -f logs/$(date +%Y-%m-%d).log`
- Verify config: `python cli.py config validate`

---

**Ready? Let's go! 🎯**

Start with: `python dry_run_phase1.py`

Then: Set up your profile and run your first real job discovery.

You'll have tailored resumes + token cost tracking within 2 days.

---

*Built for Soumyabrata @ ReadlePress | April 2026*
