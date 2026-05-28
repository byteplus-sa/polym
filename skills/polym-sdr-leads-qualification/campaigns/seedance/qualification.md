## Scoring Model — Total: 100 points

### Segment Fit (20 points) — PRIMARY FILTER

- 18–20: Film studio, film production, broadcast network, television production company, major media production organization, short drama producer, AI tools company
- 12–17: Creative agency, advertising agency, performance marketing / creative-performance company, adtech or martech company with clear video or creative-generation workflow, content creator at scale
- 5–11:  Adjacent — general marketing team with high video volume, publisher/media company without clear production ownership, adtech/martech company without confirmed creative or video workflow ownership
- 0–4:   No fit — B2C, SaaS, finance, legal, government, healthcare

### Buyer Fit (20 points) — CRITICAL

Award higher scores for newly appointed executives (< 12 months) — they are under pressure to deliver.

- 18–20: C-suite, Founder, Co-founder, VP, Head of Production/Content/Creative, Head of AI, Director of AI, Director of Production/Content/Creative, Director of Creative Production, Executive Producer, AI Stragtegist, Head of Programming Production, Head of AI Automation, Head of Product / Product Lead for creative-generation or ad-creative workflows OR any senior role newly appointed
- 12–17: Director, Television Director, Broadcast Director, Creative Director, Innovation Director, Director of Innovation, Senior Producer, AI Architect/Architects, AI Engineer/Consultant, AI, Senior Manager, Lead, Product Manager / Group Product Manager in adtech, martech, creative-performance, or AI-creative tooling with meaningful workflow influence
- 5–11:  Individual contributor in right department (designer, editor, producer — no seniority)
- 0–4:   Junior, intern, coordinator, assistant, analyst — no buying power. Also: Creative Partner, Creative AI Partner — partnership roles with no production budget authority.

### Pain Fit (25 points)

- 22–25: Explicit pain — production too slow, too expensive, or can't scale to demand
- 14–21: Implied pain — content volume pressure, team bandwidth constraints, cost signals, ad-creative iteration needs, localization needs, or performance-testing pressure
- 5–13:  Generic growth signal with loose connection to video production
- 0–4:   No pain identified

### Workflow Fit (20 points)

This factor reflects BOTH signal engagement quality AND whether a relevant workflow exists.

- 17–20: Person POSTED about video/AI/creative OR active video workflow explicitly confirmed
- 10–16: Person COMMENTED on video/AI content OR adjacent workflow confirmed (content, social, creative ops) OR person LIKED highly relevant Seedance content and their company/role strongly maps to creative, ad, or video workflow ownership
- 4–9:   Person LIKED video/AI content OR general creative/marketing workflow inferred
- 0–3:   No relevant workflow, no signal engagement with video/AI content

### Commercial Fit (15 points)

- 13–15: Established company (50–5,000 employees), VC-backed, or recognised studio/agency
- 8–12:  SMB (<50) with real content operation, early-stage funded startup
- 3–7:   Very small or unclear scale
- 0–2:   Freelancer, solo operator, nano-company
  Add 1–2 pts if company momentum signal present: hiring AI/video roles, new leadership, funding, expansion.

## Confidence Levels

- **high**: signal is direct (post/comment), ICP segment clear, persona is decision maker
- **medium**: signal is a like OR persona is an influencer not a decision maker, some unknowns
- **low**: signal is weak, significant data gaps, inferences outnumber observations

## Output Requirements

- `score` MUST equal the exact sum of all five sub-scores
- Each sub-score MUST be within its maximum: segment≤20, buyer≤20, pain≤25, workflow≤20, commercial≤15
- `decision` MUST match the threshold applied to `score`
- `reasoning_summary`: 2–3 sentences max, factual, reference specific evidence
- `qualification_reasons` and `disqualification_reasons`: short evidence-based bullets
- `suggested_use_case`: match to the segment → use case table in seedance/icp.md
