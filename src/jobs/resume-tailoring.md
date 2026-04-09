# Resume Tailoring Skill

**Single-line description:** Transform master resume into job-specific tailored versions, with Evaluator checking truthfulness against master resume; every claim must be traceable to source material.

## Purpose

One-shot resume tailoring is unreliable. This skill implements a Planner → Generator → Evaluator harness. Planner analyzes JD for required competencies. Generator produces tailored resume highlighting relevant sections. Evaluator challenges each claim: "Is this statement true to the master resume? Can it be verified?"

## Implementation

**Harness pattern:**
1. **Planner:** Parse job description, extract 5–10 key competencies, search master resume for matching sections
2. **Generator:** Create tailored resume with keyword-optimized bullets, ATS-friendly formatting
3. **Evaluator:** Challenges each new claim
   - ✓ Traceable to master resume? 
   - ✓ Avoids hallucination? 
   - ✓ Specific numbers/metrics?
   - ✓ Reads naturally?

**Inputs:**
- `master_resume`: Full resume Markdown
- `job_description`: Full JD text
- `job_id`: Reference for audit trail

**Outputs:**
```json
{
  "job_id": "abc123",
  "tailored_resume": "...markdown...",
  "harness_trace": {
    "planner_competencies": ["ML", "Python", "production systems"],
    "planner_matched_sections": ["Professional Experience > Humana", "Technical Skills > ML & AI"],
    "generator_output": "...draft...",
    "evaluator_challenges": [
      {
        "claim": "Built NLP pipelines processing 500K+ records",
        "traced_to": "master_resume.md line 51",
        "verdict": "✓ verified",
        "reason": "Exact match to master resume"
      },
      {
        "claim": "Designed feature stores for 15+ teams",
        "traced_to": "master_resume.md line 62",
        "verdict": "✓ verified",
        "reason": "Matches 'feature stores... enabling self-service analytics for 15+ downstream business teams'"
      }
    ],
    "evaluation_passed": true,
    "flagged_claims": []
  },
  "tokens_used": 3124,
  "timestamp": "2026-04-09T14:35:00Z"
}
```

## SLA Contract

**WILL:**
- Produce tailored resumes aligned to each job's top 8–10 competencies
- Show full harness trace (Planner → Generator → Evaluator decisions)
- Flag any claims not traceable to master resume (before returning)
- Preserve formatting: ATS-safe, PDF-exportable Markdown
- Never hallucinate experience or education
- Log token cost per job per application artifact

**WON'T:**
- Send resumes to companies (human gate required)
- Modify dates, education, or credentials
- Add skills not present in master resume
- Create fictional projects or companies
- Operate without Evaluator validation

## Configuration

```yaml
resume_tailoring:
  enabled: true
  harness_mode: adversarial  # Planner → Generator → Evaluator
  evaluator_strictness: high  # Flag any untraced claims
  master_resume_path: "master_resume/agam_master_resume.md"
  output_format: markdown  # markdown or pdf (requires latex)
  max_tailored_length: 2500  # chars
```

## Error Handling

- If master_resume missing → fail with clear error
- If harness deadlock (Evaluator rejects all) → return original resume + warning
- If Claude times out → partial trace + warning in metadata
- If JD unparseable → flag as "insufficient job description"

## Testing

```bash
python -m src.jobs.test_resume_tailoring --job-id abc --dry-run
# Output: tailored_resumes/abc.md, harness_trace.json
```

---

**Status:** Active | **Last Updated:** 2026-04-09 | **Owner:** Soumyabrata
