## Hard Disqualifiers — Flag in hard_disqualifiers array
Only confirmed negatives belong here. Tentative or uncertain items go in unknowns.

Confirmed auto-disqualify triggers:
- Wrong industry with no video workflow: logistics, insurance, legal, finance, government, healthcare
- Junior role with no buying power: intern, junior, assistant, coordinator, analyst
- Irrelevant function: accountant, recruiter, HR, DevOps (unless AI/ML role)
- No plausible use case: dentist, plumber, government agency with no media production
- Explicit Seedance competitor: Runway, Sora, Kling, Pika, Luma, Stability AI video

IMPORTANT: only put CONFIRMED negatives in hard_disqualifiers.
- If competitor status is uncertain, potential, ambiguous, or "needs review", do NOT put it in hard_disqualifiers.
- Put uncertain competitor/partner risk in inferred_evidence or unknowns instead.
- "Potential competitor", "unclear if competitor", and "needs review" must NOT trigger hard_disqualifiers.

What is NOT a hard disqualifier:
- Small company size (soft factor, reduces commercial_fit only)
- Liked content only (soft signal, reduces workflow_fit only)
- Indirect or inferred pain (soft factor, reduces pain_fit only)
- Unknown time in role (missing data, goes in unknowns)
