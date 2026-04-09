#!/usr/bin/env python3
"""
Dry-run demonstration of Phase 1 pipeline.

Shows the complete flow without requiring actual API calls.

Usage:
  python dry_run_phase1.py
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_job_discovery():
    """Demo job discovery pipeline."""
    print_section("PHASE 1A: Job Discovery (Claude Web Search Agent)")

    print("Step 1: Load Configuration")
    print("  ✓ Loaded job_search.yaml")
    print("  ✓ Target roles: 7 roles configured")
    print("  ✓ Target keywords: 9 keywords configured")
    print("  ✓ Daily limit: 10 jobs")

    print("\nStep 2: Planner Phase")
    print("  [Planner] Analyzing target roles and keywords...")
    planner_output = {
        "search_queries": [
            "Senior Data Scientist machine learning Python remote",
            "ML Engineer production systems PostgreSQL Boston",
            "Healthcare ML NLP predictive analytics",
            "Data Science FastAPI Kubernetes AWS",
        ],
        "rationale": "Combined role + keywords + location for high-signal searches",
    }
    print(f"  ✓ Generated {len(planner_output['search_queries'])} search queries")

    print("\nStep 3: Generator Phase")
    print("  [Generator] Executing web searches...")
    raw_jobs = [
        {
            "title": "Senior Data Scientist",
            "company": "Anthropic",
            "url": "https://jobs.anthropic.com/senior-ds-001",
            "location": "Remote",
            "jd_snippet": "Building production ML systems. Python, SQL, production focus...",
            "source": "web_search",
        },
        {
            "title": "ML Engineer — Healthcare",
            "company": "Flatiron Health",
            "url": "https://flatiron.jobs/ml-healthcare-001",
            "location": "New York, NY",
            "jd_snippet": "NLP for clinical data. Healthcare experience preferred...",
            "source": "web_search",
        },
        {
            "title": "Principal Data Scientist",
            "company": "React DevOps Shop",  # Will be rejected
            "url": "https://devops.jobs/principal-001",
            "location": "Remote",
            "jd_snippet": "Frontend React developer. DevOps pipeline management...",
            "source": "web_search",
        },
    ]
    print(f"  ✓ Found {len(raw_jobs)} raw jobs from web search")

    print("\nStep 4: Evaluator Phase")
    print("  [Evaluator] Scoring relevance with explainable reasoning...")
    evaluated_jobs = [
        {
            **raw_jobs[0],
            "relevance_score": 0.92,
            "decision": "keep",
            "scoring_reasons": [
                "Title match: Senior Data Scientist (+30)",
                "Keywords: ML, Python, production systems (+35)",
                "Remote location preferred (+15)",
                "No blocked keywords (+12)",
            ],
        },
        {
            **raw_jobs[1],
            "relevance_score": 0.78,
            "decision": "keep",
            "scoring_reasons": [
                "Title match: ML Engineer (+25)",
                "Keywords: NLP, healthcare (+28)",
                "Location: New York (preferred region +15)",
                "Healthcare domain match (+10)",
            ],
        },
        {
            **raw_jobs[2],
            "relevance_score": 0.12,
            "decision": "reject",
            "scoring_reasons": [
                "Blocked keyword: React (-50)",
                "Blocked keyword: DevOps (-50)",
            ],
            "reject_reason": "Contains blocked keywords (React, DevOps)",
        },
    ]
    print(f"  ✓ Scored {len(evaluated_jobs)} jobs")
    print(f"  ✓ Kept: 2 jobs (Anthropic, Flatiron)")
    print(f"  ✓ Rejected: 1 job (React DevOps — blocked keywords)")

    print("\nStep 5: Deduplication")
    print("  [Dedup] Filtering against 30-day history...")
    final_jobs = [j for j in evaluated_jobs if j["decision"] == "keep"]
    print(f"  ✓ No duplicates found")
    print(f"  ✓ {len(final_jobs)} unique jobs ready for tailoring")

    print("\nStep 6: Token Instrumentation")
    print("  ✓ Planner: 2,000 input, 840 output tokens")
    print("  ✓ Generator: 1,500 input, 620 output tokens")
    print("  ✓ Evaluator: 1,800 input, 950 output tokens")
    print(f"  ✓ TOTAL: 5,300 input + 2,410 output = 7,710 tokens")
    print(f"  ✓ COST (estimate): $0.12 USD")

    return final_jobs


def demo_resume_tailoring(jobs):
    """Demo resume tailoring with adversarial harness."""
    print_section("PHASE 1B: Resume Tailoring (Adversarial Harness)")

    if not jobs:
        print("  [Skip] No jobs to tailor")
        return

    job = jobs[0]
    print(f"Job: {job['title']} @ {job['company']}")
    print(f"URL: {job['url']}\n")

    print("Step 1: Planner Phase")
    print("  [Planner] Analyzing job description...")
    planner_output = {
        "competencies": [
            "Machine Learning (production systems)",
            "Python & SQL",
            "Data pipelines & engineering",
            "Model evaluation & metrics",
            "Team collaboration",
            "Documentation & communication",
        ],
        "strategy": "Emphasize production systems, data engineering, metrics",
        "sections_to_highlight": ["Professional Experience @ Humana", "Technical Skills > ML"],
    }
    print(f"  ✓ Identified {len(planner_output['competencies'])} key competencies")

    print("\nStep 2: Generator Phase")
    print("  [Generator] Creating tailored resume...")
    print("  ✓ Reordered bullets to lead with relevant experience")
    print("  ✓ Added job-specific keywords (NLP, production, metrics)")
    print("  ✓ Dropped irrelevant sections (frontend, low-level details)")
    print("  ✓ Maintained original language (no paraphrasing)")

    print("\nStep 3: Evaluator Phase")
    print("  [Evaluator] Challenging claims for truthfulness...")
    challenges = [
        {"claim": "Built NLP pipelines...", "status": "✓ verified", "source": "Line 51 master resume"},
        {"claim": "Reduced BI load by 45%", "status": "✓ verified", "source": "Line 54 master resume"},
        {"claim": "Healthcare compliance (HIPAA)", "status": "✓ verified", "source": "Line 53 master resume"},
    ]
    for challenge in challenges:
        print(f"  {challenge['status']}: {challenge['claim'][:50]}")
        print(f"      (Source: {challenge['source']})")

    print("\n  ✓ All claims traceable to master resume")
    print("  ✓ No hallucinations detected")
    print("  ✓ VERDICT: PASS ✅")

    print("\nStep 4: Output")
    print(f"  ✓ Tailored resume saved: output/tailored_resumes/{job['company'].lower()}_tailored.md")
    print(f"  ✓ Harness trace saved: output/tailored_resumes/{job['company'].lower()}_trace.json")

    print("\nStep 5: Token Instrumentation")
    print("  ✓ Planner: 1,200 input, 600 output tokens")
    print("  ✓ Generator: 1,500 input, 800 output tokens")
    print("  ✓ Evaluator: 1,000 input, 500 output tokens")
    print(f"  ✓ TOTAL: 3,700 input + 1,900 output = 5,600 tokens")
    print(f"  ✓ COST (estimate): $0.09 USD")


def demo_gmail_triage():
    """Demo Gmail triage v2 with structured output."""
    print_section("PHASE 1C: Gmail Triage (Structured Output)")

    print("Step 1: Fetch Recent Emails")
    print("  [Gmail API] Fetching last 30 minutes of unread emails...")
    emails = [
        {
            "subject": "Code review needed: PR #2847",
            "from": "Sanjoy Dey <sanjoy@readlepress.in>",
            "snippet": "Can you review the HPC deployment PR? Needs your approval.",
        },
        {
            "subject": "Weekly digest",
            "from": "news@techcrunch.com",
            "snippet": "This week in tech: AI regulations, new startups...",
        },
        {
            "subject": "Meeting confirmed: 3pm today",
            "from": "calendar@google.com",
            "snippet": "Your meeting with the team has been confirmed.",
        },
    ]
    print(f"  ✓ Found {len(emails)} unread emails")

    print("\nStep 2: Classify with Claude (Structured Output)")
    print("  [Claude] Classifying emails...")
    classified = [
        {
            "subject": emails[0]["subject"],
            "from": emails[0]["from"],
            "category": "urgent",
            "summary": "Code review needed for HPC deployment",
            "suggested_action": "Review PR #2847 within next hour",
            "urgency_score": 9,
        },
        {
            "subject": emails[1]["subject"],
            "from": emails[1]["from"],
            "category": "newsletter",
            "summary": "Weekly tech digest",
            "suggested_action": "Archive or skim if interested",
            "urgency_score": 1,
        },
        {
            "subject": emails[2]["subject"],
            "from": emails[2]["from"],
            "category": "normal",
            "summary": "Calendar notification",
            "suggested_action": "Check time and prepare for meeting",
            "urgency_score": 4,
        },
    ]
    print(f"  ✓ Classified {len(classified)} emails")

    print("\nStep 3: Output (Decision-Support Format)")
    print("  🔴 URGENT (act now):")
    print("    • Code review needed: PR #2847")
    print("    • From: Sanjoy Dey")
    print("    • Action: Review PR #2847 within next hour")

    print("\n  🟡 NORMAL (respond within 24h):")
    print("    • Meeting confirmed: 3pm today")

    print("\n  📰 NEWSLETTERS: 1 email")

    print("\nStep 4: Output Formats")
    print("  ✓ Summary (text): Ready for Telegram")
    print("  ✓ Classified (JSON): Ready for dashboard")
    print("  ✓ Decision-needed flag: True (1 urgent email)")
    print(json.dumps(classified, indent=4)[:300])
    print("  ...")

    print("\nStep 5: Token Instrumentation")
    print("  ✓ Email fetch: 0 tokens (API call)")
    print("  ✓ Classification: 800 input, 400 output tokens")
    print(f"  ✓ COST (estimate): $0.014 USD")


def demo_linkedin_content():
    """Demo LinkedIn content generation."""
    print_section("PHASE 1D: LinkedIn Content (Adversarial Harness)")

    print("Seed Idea: 'Building with Claude'\n")

    print("Step 1: Planner Phase")
    print("  [Planner] Analyzing content angle...")
    print("  ✓ Angle: Behind-the-scenes technical insight")
    print("  ✓ Target audience: ML Engineers, CTOs, Founders")
    print("  ✓ Tone: Thought-leadership + narrative")

    print("\nStep 2: Generator Phase")
    print("  [Generator] Creating draft post...")
    draft = """
🚀 Building with Claude — Why it's different

Started rebuilding Agam Automation Hub for production use. The key difference?
Every decision is explainable. Every claim is verifiable. No black boxes.

Planner → Generator → Evaluator harness. Same pattern we use at ReadlePress.

Generator produces the output. Evaluator challenges it: "Is this true? Will this work?"

Result: Higher quality. More robust. Auditable.

Job discovery, resume tailoring, Gmail triage — all using the same pattern.

Thoughts on how you architect decision-making in production? 👇
"""
    print("  ✓ Draft created (148 words)")

    print("\nStep 3: Evaluator Phase")
    print("  [Evaluator] Assessing authenticity & engagement...")
    print("  ✓ Authenticity score: 0.92 (personal experience)")
    print("  ✓ Engagement potential: 0.78 (relatable metaphor)")
    print("  ✓ Brand alignment: 0.88 (consistent positioning)")
    print("  ✓ Polarization risk: 0.05 (low)")
    print("  ✓ VERDICT: APPROVED ✅")

    print("\nStep 4: Gate (Human Approval)")
    print("  ⏳ Waiting for human approval before posting...")
    print("  Status: DRAFT (in queue)")

    print("\nStep 5: Token Instrumentation")
    print("  ✓ Planner: 600 input, 300 output tokens")
    print("  ✓ Generator: 1,200 input, 700 output tokens")
    print("  ✓ Evaluator: 900 input, 450 output tokens")
    print(f"  ✓ COST (estimate): $0.065 USD")


def demo_summary():
    """Print final summary."""
    print_section("PHASE 1 Summary & Metrics")

    print("✅ Completed Components:")
    print("  • Job Discovery (Claude web search agent)")
    print("  • Resume Tailoring (Adversarial harness)")
    print("  • Gmail Triage (Structured output)")
    print("  • LinkedIn Content (Evaluator assessment)")
    print("  • Token Instrumentation (Cost tracking)")

    print("\n📊 Token Usage (Dry-Run Estimates):")
    print("  • Job Discovery: 7,710 tokens → $0.12 USD")
    print("  • Resume Tailoring: 5,600 tokens → $0.09 USD")
    print("  • Gmail Triage: ~1,200 tokens → $0.014 USD")
    print("  • LinkedIn Content: ~2,700 tokens → $0.065 USD")
    print("  ────────────────────────────────────────")
    print("  • TOTAL: ~17,200 tokens → ~$0.30 USD per run")

    print("\n🚀 Next Steps (Phase 2):")
    print("  1. Outreach pipeline (warm intros + cold personalized)")
    print("  2. NetMap connection layer (trust graph)")
    print("  3. Feedback loop (track responses, adjust scoring)")
    print("  4. Swap in Soumyabrata's profile (resume + LinkedIn)")
    print("  5. Frontend updates (review gates, token tracking)")
    print("  6. TypeScript port + Supabase integration")

    print("\n📚 Documentation:")
    print("  • PHASE1_GUIDE.md — Setup & usage guide")
    print("  • config/job_search.yaml — Configuration")
    print("  • tests/test_phase1.py — Test suite")

    print("\n✅ Status: Phase 1 COMPLETE")
    print("   Production-ready for job search automation")
    print("\n   Ready for Phase 2? Let's go! 🎯\n")


if __name__ == "__main__":
    print("\n╔════════════════════════════════════════════════════════════════════╗")
    print("║  AGAM AUTOMATION HUB — PHASE 1 DRY-RUN DEMONSTRATION             ║")
    print("║  Rebuilt for AKTIVIQ Standard (Adversarial Harness Pattern)      ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    # Run all demos
    jobs = demo_job_discovery()
    demo_resume_tailoring(jobs)
    demo_gmail_triage()
    demo_linkedin_content()
    demo_summary()
