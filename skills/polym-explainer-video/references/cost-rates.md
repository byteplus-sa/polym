# Cost rates reference

Current pricing (as of May 2026). Verify before each project — these change.

The skill uses three paid/free services: **Seedance 2.0** (A-roll + optional cinematic
B-roll), **Seedream 4.5** (optional portrait restyle), **Volcengine music** (optional BGM
— only when AI music is enabled in onboarding). HyperFrames B-roll is free.

---

## Seedance 2.0 (BytePlus ModelArk) — A-roll + cinematic B-roll

Token-based pricing on the BytePlus ModelArk account. A 5–10 s 720p 9:16 clip is
inexpensive; cost scales with duration and resolution. See the ModelArk console for the
current token rate and the account balance.

- A-roll: typically 2 clips per video (hook + CTA), 5–10 s each.
- Cinematic B-roll: only when a non-person atmospheric shot is needed — most B-roll is
  free HyperFrames instead.

Rough planning figure: a ~90 s explainer with 2 short A-roll clips is a small token spend
(single-digit USD-equivalent). Confirm against the live ModelArk rate.

---

## Seedream 4.5 (BytePlus ModelArk) — portrait restyle

Per-image generation cost on the same ModelArk account. The Phase 2 restyle generates
**4 images** for review; budget for 4 image generations per restyle round (plus more if
the user asks for another round). Small relative to video cost.

---

## Volcengine music API — BGM

Optional — incurred only when `config.music_enabled` is `true`. Per-generation cost for one
music track. The similarity-detection check occasionally rejects a generation; a retry then
costs one more generation. Budget for 1–3 generations per video. Small. If AI music is
disabled, this cost is $0.

---

## HyperFrames — B-roll

**$0.** Local headless Chromium render. The only "cost" is local CPU + a one-time
~140 MB Chromium download.

---

## Lark CLI / Drive

**$0** for uploads/downloads via the user's existing Lark plan. A 9:16 1080p ~90 s MP4 is
roughly 8–12 MB.

---

## Cost decision rules for the Phase 3 storyboard

1. **Most B-roll → HyperFrames** ($0). Reserve Seedance B-roll for genuine cinematic /
   atmospheric shots only.
2. **A-roll** — keep to ~2 clips (hook + CTA), 5–10 s each. Extra A-roll clips add token cost.
3. Always show the cost estimate in the Phase 3 storyboard so the user approves with eyes open.

## Cost reduction tactics

If the storyboard cost is too high:
1. Convert any Seedance B-roll segment to HyperFrames (saves the whole clip's tokens).
2. Shorten or drop one A-roll clip.
3. Reduce overall video length.

Always show the user the cost-reduced alternative alongside the original.
