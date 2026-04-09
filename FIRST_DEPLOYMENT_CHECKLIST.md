# ✅ FIRST DEPLOYMENT CHECKLIST

**For:** Soumyabrata Ghosh  
**Objective:** Deploy automation engine and run first job discovery  
**Estimated Time:** 45 minutes total  
**Deadline:** Use today or tomorrow to start your search  

---

## PRE-DEPLOYMENT (10 minutes)

- [ ] Downloaded `agam-automation-hub-phase1-complete/` to local machine
- [ ] Located repo on your computer: `~/agam-automation-hub/` or similar
- [ ] Verified Python 3.8+ installed: `python --version`
- [ ] Verified pip is accessible: `pip --version`
- [ ] Verified git installed: `git --version`

---

## ENVIRONMENT SETUP (5 minutes)

- [ ] Navigated to repo directory: `cd agam-automation-hub/`
- [ ] Copied environment template: `cp .env.example .env`
- [ ] Opened `.env` in editor: `nano .env` or VS Code
- [ ] Added ANTHROPIC_API_KEY: `ANTHROPIC_API_KEY=sk-ant-YOUR-KEY-HERE`
- [ ] Saved `.env` file (Ctrl+O, Enter, Ctrl+X in nano)
- [ ] Verified no other credentials needed yet (Gmail, LinkedIn are optional)
- [ ] Checked .env is in `.gitignore` (should be, don't commit it)

**Where to get API key:**
- Go to: https://console.anthropic.com/
- Sign in with your account
- Create API key
- Copy and paste into `.env`

---

## DEPENDENCIES INSTALLATION (10 minutes)

- [ ] Installed dependencies: `pip install -r requirements.txt`
- [ ] Wait for installation to complete (should take 3–5 min)
- [ ] Verify no errors in output
- [ ] Check PyYAML, sqlite3, requests installed: `pip list | grep -E "pyyaml|requests"`

---

## PROFILE SETUP (5 minutes)

- [ ] Verified profile exists: `ls config/profiles/soumyabrata.yaml`
- [ ] Opened profile in editor: `nano config/profiles/soumyabrata.yaml`
- [ ] Filled in your details:
  - [ ] `name`: "Soumyabrata Ghosh"
  - [ ] `email`: Your working email
  - [ ] `phone`: Your phone (format: +1 (978) 555-XXXX)
  - [ ] `location`: "Worcester, MA, USA" or your location
  - [ ] `linkedin_profile`: Your LinkedIn URL
  - [ ] `github_profile`: Your GitHub URL
- [ ] Added target job roles (at least 3–5):
  - [ ] CTO
  - [ ] Co-founder
  - [ ] Founding Engineer
  - [ ] Principal Engineer
  - [ ] Head of Engineering
- [ ] Added target keywords (at least 5–10):
  - [ ] AI, Claude, ML, Python, TypeScript, Systems, Product, Founding, Infrastructure
- [ ] Added target locations (at least 3):
  - [ ] Remote
  - [ ] San Francisco
  - [ ] Boston
  - [ ] (Add more as desired)
- [ ] Set salary range: $150,000–$300,000 (adjust if needed)
- [ ] Set equity importance: true
- [ ] Saved profile

---

## MASTER RESUME (5 minutes)

- [ ] Verified resume exists: `ls master_resume/soumyabrata_master_resume.md`
- [ ] Opened resume: `nano master_resume/soumyabrata_master_resume.md`
- [ ] Reviewed content (already filled in for you):
  - [ ] All your experience is there
  - [ ] ReadlePress details accurate
  - [ ] Clark University info correct
  - [ ] Skills section comprehensive
- [ ] Made any personal corrections:
  - [ ] Phone number (if different from +1 (978) 555-XXXX)
  - [ ] Email (if different from soumyabrata@readlepress.in)
  - [ ] LinkedIn/GitHub URLs correct
  - [ ] Any other inaccuracies
- [ ] Saved resume (Ctrl+X in nano)

**Important:** This resume is your SOURCE OF TRUTH. Every tailored resume will reference it. Make sure everything here is accurate.

---

## PROFILE ACTIVATION (2 minutes)

- [ ] Activated your profile: `python -m src.config.profile_manager --set soumyabrata`
- [ ] Verified activation:
  ```bash
  python -m src.config.profile_manager --show
  ```
- [ ] Output should show:
  - Your name
  - Your email
  - Your job preferences
  - Your locations
- [ ] No errors in output

---

## SYSTEM STATUS CHECK (5 minutes)

- [ ] Checked system status: `python run.py --status`
- [ ] Output should show:
  - [ ] ✓ ANTHROPIC_API_KEY: Set
  - [ ] ○ LINKEDIN_ACCESS_TOKEN: Not set (optional)
  - [ ] ○ TELEGRAM_BOT_TOKEN: Not set (optional)
  - [ ] ○ GMAIL_CREDENTIALS_PATH: Not set (optional)
- [ ] At minimum, ANTHROPIC_API_KEY must be ✓ Set

**If ANTHROPIC_API_KEY shows as ✗ Not set:**
- Recheck your `.env` file
- Make sure there are no typos in the key
- Try again: `python run.py --status`

---

## DRY-RUN TEST (5 minutes)

- [ ] Ran dry-run (no API calls): `python dry_run_phase1.py`
- [ ] Output should show:
  - Job discovery process
  - Resume tailoring process
  - Gmail triage process
  - LinkedIn content generation
  - Token costs estimated
- [ ] All 4 components showed ✅ Success
- [ ] Final summary showed approximate costs ($0.30 total)

**If dry-run fails:**
- Check for Python errors
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check if any imports are missing
- Try running one component at a time (see TROUBLESHOOTING below)

---

## FIRST REAL RUN (5 minutes)

- [ ] Ready to run real job discovery: `python run.py --jobs`
- [ ] Output should show:
  - Connecting to Claude API
  - Running job discovery
  - Number of jobs discovered (5–10)
  - Token count and estimated cost
- [ ] Check output directory: `ls -la output/jobs/$(date +%Y-%m-%d)/`
- [ ] Should contain `discovered_jobs.json`
- [ ] Check tailored resumes: `ls output/tailored_resumes/`
- [ ] Should see tailored resume files (*.md)
- [ ] Check token logs: `ls output/token_logs/`
- [ ] Should contain cost summary JSON

**First run expected output:**
```
🔍 Running job discovery pipeline...

✅ Pipeline complete

  Discovered: 8 jobs
  Queued: 8 jobs
  Tailored: 8 resumes
  Total cost: $0.28 USD
  Tokens: ~16,800
```

---

## REVIEW OUTPUT (10 minutes)

- [ ] Opened discovered jobs: `cat output/jobs/$(date +%Y-%m-%d)/discovered_jobs.json | head -50`
- [ ] Sample job record should show:
  - Job title, company, URL
  - Relevance score (0–1)
  - ≥3 scoring reasons
  - No hallucination
- [ ] Opened a tailored resume: `cat output/tailored_resumes/job_*.md | head -100`
- [ ] Resume should show:
  - Your name and contact info
  - Relevant experience highlighted
  - Keywords from job description emphasized
  - Evaluator trace (why these changes)
- [ ] Opened token log: `cat output/token_logs/*_summary.json`
- [ ] Should show:
  - Total_tokens
  - Total_cost_usd
  - Breakdown by skill

---

## APPLICATION TRACKING (5 minutes)

- [ ] Checked application dashboard: `python -m src.jobs.applications_dashboard --status`
- [ ] Output should show: `Total Applications: 0` (first run)
- [ ] Verified command works (no errors)

**When you apply to jobs later:**
```bash
# Log an application
python -m src.jobs.applications_dashboard --log-response

# Check pending applications
python -m src.jobs.applications_dashboard --pending

# Check ROI metrics
python -m src.jobs.applications_dashboard --roi
```

---

## DOCUMENTATION REVIEW (Optional but Recommended)

Read in this order (20 minutes):
- [ ] `README_PHASE1_COMPLETE.md` (5 min) — What was built
- [ ] `QUICK_REFERENCE.md` (5 min) — All commands
- [ ] `YOUR_JOB_SEARCH_GUIDE.md` (10 min) — Your strategy

---

## CONFIGURATION VALIDATION (5 minutes)

- [ ] Validated configuration: `python run.py --config validate`
- [ ] Output should show all required fields present
- [ ] No errors or warnings

---

## TROUBLESHOOTING CHECKLIST

If something goes wrong, check:

### "ModuleNotFoundError: No module named..."
- **Fix:** Reinstall dependencies
  ```bash
  pip install -r requirements.txt --force-reinstall
  ```

### "ANTHROPIC_API_KEY not set"
- **Fix:** Check .env file
  ```bash
  cat .env | grep ANTHROPIC_API_KEY
  ```
- Should show: `ANTHROPIC_API_KEY=sk-ant-...`
- No quotes, no spaces

### "Profile not found: soumyabrata"
- **Fix:** Verify profile file exists
  ```bash
  ls config/profiles/soumyabrata.yaml
  ```
- If not, copy from agam: `cp config/profiles/agam.yaml config/profiles/soumyabrata.yaml`

### "Master resume not found"
- **Fix:** Verify resume file exists
  ```bash
  ls master_resume/soumyabrata_master_resume.md
  ```
- If not, create it: touch the file and paste content

### "Database locked" error
- **Fix:** Remove stale database
  ```bash
  rm -f data/jobs.db
  python run.py --jobs
  ```

### API rate limit or timeout
- **Fix:** Wait 60 seconds and retry
- Claude API has rate limits; most queries succeed on retry

### "Output directory not found"
- **Fix:** Create output directory
  ```bash
  mkdir -p output/{jobs,tailored_resumes,token_logs,linkedin,briefings}
  ```

---

## WHAT'S NEXT

### Today (After Deployment)
- [ ] Review the discovered jobs manually
- [ ] Read YOUR_JOB_SEARCH_GUIDE.md (your targeting strategy)
- [ ] Assess: Are these the types of companies/roles I want?

### Tomorrow
- [ ] Research top 2–3 discovered jobs
- [ ] Customize cover letters (specific, not generic)
- [ ] Apply to jobs you're genuinely interested in
- [ ] Log applications: `python -m src.jobs.applications_dashboard --log-response`

### This Week
- [ ] Run job discovery 2–3 times (daily or every other day)
- [ ] Build up pipeline of 10–15 applications
- [ ] Track responses as they come in
- [ ] Adjust keywords if response rate is low (<5%)

### Next Week
- [ ] Have your first interviews scheduled (hopefully)
- [ ] Analyze what types of companies respond best
- [ ] Refine your profile keywords based on results
- [ ] Run ROI analysis: `python -m src.jobs.applications_dashboard --roi`

---

## GOTCHAS & THINGS TO KNOW

### Your Master Resume is Sacred
- Every tailored resume pulls from this
- Make sure everything here is accurate
- If you add accomplishments, update it FIRST, then run discovery again

### Profiles Are Swappable
- You can switch between users: `--set soumyabrata`, `--set agam`
- Each profile has its own config, keywords, preferences
- Great for testing or running for multiple people

### "No Naked Scoring" is Real
- Every job gets a score + 3+ reasons why
- You'll see: "0.85 because: Title match (+30), Keywords (+35), Location (+15)"
- This helps you understand why a job was included

### Resumes Don't Hallucinate
- The Evaluator checks: "Is this in the master resume?"
- Every claim is verifiable
- You can trust tailored resumes (unlike typical AI outputs)

### All Costs Are Tracked
- See estimated USD cost per run
- This data feeds into AKTIVIQ ROI reporting
- You're paying ~$0.30–0.50 per discovery run
- At 10 applications/day = $0.50/day or $15/month

### Human Gates Are Enforced
- No auto-apply, auto-post, auto-send
- You review everything before it goes out
- This is intentional — you stay in control

---

## SUCCESS CRITERIA

You'll know deployment worked if:

✅ First run completed without errors  
✅ 5–10 jobs discovered  
✅ Tailored resumes generated  
✅ Token cost shown (~$0.30–0.50)  
✅ All output files created (jobs JSON, resumes MD, token logs JSON)  
✅ Dashboard commands work (no errors)  

---

## CONTACT & SUPPORT

**Questions?**
- Check `SETUP_FOR_SOUMYABRATA.md` for full setup guide
- See `PHASE1_GUIDE.md` for detailed walkthrough
- Review `QUICK_REFERENCE.md` for command reference

**Issues?**
- Enable debug logging: `export LOG_LEVEL=DEBUG` before running
- Check logs: `tail -f logs/$(date +%Y-%m-%d).log`
- Verify config: `python run.py --status`

**Want to modify something?**
- Profile keywords: Edit `config/profiles/soumyabrata.yaml`
- Job search config: Edit `config/job_search.yaml`
- API key: Edit `.env` (never commit this file)

---

## FINAL CHECKLIST

- [ ] All pre-deployment items complete
- [ ] Environment setup done (.env created with API key)
- [ ] Dependencies installed (no errors)
- [ ] Profile activated (your name shows up)
- [ ] Dry-run passed (all 4 components worked)
- [ ] First real run completed (jobs discovered)
- [ ] Output files verified (jobs, resumes, tokens)
- [ ] Dashboard tested (no command errors)
- [ ] Documentation reviewed (at least QUICK_REFERENCE.md)
- [ ] Troubleshooting checklist reviewed (know how to fix common issues)

---

## YOU'RE READY! 🚀

All systems go.

**Next action:** `python run.py --jobs`

Your automation engine is live.

Go find your next role! 💼

---

*Last updated: April 9, 2026*  
*For: Soumyabrata Ghosh*  
*Deployment Time: ~45 minutes*  
*Status: Ready to deploy*
