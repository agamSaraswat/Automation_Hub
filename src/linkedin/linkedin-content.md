# LinkedIn Content Skill

**Single-line description:** Generate thoughtful LinkedIn posts from seed ideas, with Evaluator checking engagement potential, brand alignment, and absence of polarizing language; human reviews all drafts before publishing.

## Purpose

LinkedIn is a relationship engine. Content should demonstrate expertise without being salesy. This skill generates thoughtful posts on AI, learning systems, productivity, job search, and career strategy — each evaluated for authenticity, engagement potential, and brand safety.

## Implementation

**Harness pattern:**
1. **Planner:** Review content calendar, recent posts, trending topics → decide angle
2. **Generator:** Draft post (headline, body, CTA) optimized for LinkedIn algorithm
3. **Evaluator:** Check
   - Is it authentic to voice/brand?
   - Will it engage target audience (CTOs, startup founders, ML engineers)?
   - Any unintended polarization?
   - Too promotional/salesy?
   - Real experience behind every claim?

**Inputs:**
- `seed_idea`: Topic/angle ("Job search automation", "Building with Claude", "Learning systems design")
- `tone`: "thought-leadership", "narrative", "advice", "behind-the-scenes"
- `target_audience`: ["CTOs", "ML Engineers", "Founders"]
- `recent_posts`: Last 5 post URLs for reference

**Outputs:**
```json
{
  "idea": "Job search automation with AI",
  "tone": "thought-leadership",
  "draft_post": {
    "headline": "Why manual job search is like debugging with print statements 🤔",
    "body": "...",
    "cta": "What's your approach to job search? Drop a thought below.",
    "format": "carousel"  // or "text", "document"
  },
  "evaluator_assessment": {
    "authenticity": {
      "score": 0.92,
      "reason": "Personal experience with job search + AKTIVIQ architecture alignment"
    },
    "engagement_potential": {
      "score": 0.78,
      "reason": "Relatable metaphor but not controversial; targets ML/startup community"
    },
    "brand_alignment": {
      "score": 0.88,
      "reason": "Consistent with thought-leadership positioning; mentions AI/automation subtly"
    },
    "polarization_risk": {
      "score": 0.05,  // low risk
      "reason": "Neutral tone; no political/personal attacks"
    }
  },
  "evaluator_verdict": "✓ approved",
  "suggested_edits": [
    "Consider softening 'like debugging with print statements' — some might find it condescending"
  ],
  "tokens_used": 1420,
  "timestamp": "2026-04-09T14:40:00Z"
}
```

## SLA Contract

**WILL:**
- Generate 1–3 draft posts per request
- Show Evaluator reasoning for each assessment
- Flag polarizing content before publishing
- Suggest post timing based on audience timezone
- Support carousel, video, and document formats
- Track performance metrics (impressions, engagement) if LinkedIn token valid

**WON'T:**
- Auto-publish (human gate required)
- Create content unrelated to tech/career/learning
- Boost engagement via fake interactions
- Copy competitor posts or famous quotes without attribution
- Generate multiple accounts or spam

## Configuration

```yaml
linkedin_content:
  enabled: true
  harness_mode: adversarial  # Planner → Generator → Evaluator
  auto_publish: false  # Always require human approval
  content_calendar:
    - "Job search automation"
    - "Building with Claude"
    - "Learning systems design"
  tone_preferences: ["thought-leadership", "narrative", "behind-the-scenes"]
  target_audience: ["CTOs", "ML Engineers", "Founders", "Data Scientists"]
  posting_hours: [8, 11]  # EST
  post_frequency: "2–3 per week"
```

## Error Handling

- If LinkedIn token expired → warn, skip publishing
- If Claude times out → return partial draft + warning
- If content flagged as spam → human review required
- If image/video upload fails → text-only fallback

## Testing

```bash
python -m src.linkedin.test_content --seed "Job search automation" --dry-run
# Output: draft_posts.json, evaluator_report.json
```

---

**Status:** Active | **Last Updated:** 2026-04-09 | **Owner:** Soumyabrata
