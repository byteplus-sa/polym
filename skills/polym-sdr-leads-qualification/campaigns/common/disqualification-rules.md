## Universal Disqualification Rules

### Hard Disqualifiers — apply BEFORE scoring
These are checked in Stage 1 and placed in the `hard_disqualifiers` array.
If ANY hard disqualifier is present, Python forces `decision = "disqualified"` regardless of score.

**1. Wrong Industry — No Video / AI / Creative Workflow**
Company operates in an industry with zero plausible video production need.
Examples: logistics, insurance, accounting, legal services, clinical healthcare, government
Be specific: "Company is a logistics firm — no video production workflow identified"

**2. Junior Role — No Buying Power**
Title indicates too junior to influence a purchasing decision.
Apply when title contains: intern, junior, assistant, coordinator, analyst (without senior prefix)
AND there is no seniority indicator elsewhere in the signal.
Be specific: "Junior Animator — no purchasing authority"

**3. Irrelevant Role Function**
Person works in a department completely unrelated to content, video, AI, or creative production.
Examples: accountant, recruiter, legal counsel, HR business partner, finance analyst, DevOps engineer (unless AI/ML context)

**4. No Plausible Use Case**
Even with generous inference, there is no scenario where this company would use AI video.
Examples: dentist office, plumbing company, physical retail with no digital presence, government agency

**5. Wrong Company Type (Confirmed)**
- Pure B2C consumer app with no content production team
- Government / public sector entity
- Non-profit or academic institution (unless AI research lab)
- Freelancer with no team and no commercial scale

**6. Explicit Competitor Signal**
Person works at or company is confirmed building a direct AI video competitor.
Campaign-specific competitor lists are defined in each campaign's disqualification.md.

### What Is NOT a Hard Disqualifier

A LinkedIn like is NOT a hard disqualifier on its own.
A like from a Creative Director at a film studio is medium-low signal — score it, don't disqualify it.
Only hard-disqualify on likes when BOTH are true: wrong ICP segment AND wrong persona.

Small company size is NOT a hard disqualifier.
A 5-person film studio beats a 500-person insurance company. Size is a soft commercial_fit factor only.

Indirect or inferred pain is NOT a hard disqualifier.
Most leads engage passively. Score it lower, don't eliminate it.

Unknown data is NOT a hard disqualifier.
Missing information goes in unknowns. Only confirmed negatives go in hard_disqualifiers.

### Soft Disqualifiers (reduce score, do not hard-disqualify)

These lower scoring but must not trigger immediate disqualification:
- Like interaction only (right ICP but weak signal) → lower workflow_fit
- Individual contributor with no seniority in right department → lower buyer_fit
- Company too small to scale (<5 employees, solo operation) → lower commercial_fit
- No company momentum signals present → lower commercial_fit
- Geographic market with no product availability → lower commercial_fit
- Time in role unknown → flag as unknown, do not penalise

### Application Rules

1. Check hard disqualifiers FIRST in Stage 1 before any scoring
2. If `hard_disqualifiers` list is non-empty → Python forces `decision = "disqualified"`
3. List each disqualifier as a separate specific string in the array
4. Be precise: "Junior Animator at ad agency — no buying power" not just "junior role"
5. Do NOT hard-disqualify on unknowns — only on confirmed negative signals
6. When in doubt between hard-disqualify and low score: use low score (review is safer than lost leads)
