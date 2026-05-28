## Hard Disqualifiers — Flag in hard_disqualifiers array
Only confirmed negatives belong here. Tentative or uncertain items go in unknowns.

Confirmed auto-disqualify triggers:
- Wrong industry with no cinematic or visual content workflow: logistics, insurance, legal, finance, government, healthcare, B2B SaaS without creative production
- Junior role with no buying power: intern, junior, assistant, coordinator, analyst
- Irrelevant function: accountant, recruiter, HR, DevOps (unless AI/ML role)
- No plausible use case: government agency, utilities company, professional services with no brand content
- Explicit Kling competitor: Runway, Sora, Pika, Luma Dream Machine, Stability AI video, Seedance, Veo, Hailuo — if company is confirmed building competing video generation technology

IMPORTANT: only put CONFIRMED negatives in hard_disqualifiers.
- If competitor status is uncertain or ambiguous, put it in unknowns instead.
- A company using a competitor product is NOT a hard disqualifier (they may be switching).
- Only hard-disqualify if company is confirmed BUILDING or SELLING a competing video AI product.

What is NOT a hard disqualifier for Kling:
- High-volume content production focus (prefer quality; volume buyers may still qualify if persona and segment fit)
- Small company size (soft factor, reduces commercial_fit only)
- Liked content only (soft signal, reduces workflow_fit only)
- Brand focused on speed over quality (reduces segment/pain fit scores, but not auto-disqualify)
