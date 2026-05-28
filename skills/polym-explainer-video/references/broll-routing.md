# B-roll routing — HyperFrames vs Seedance vs Hybrid

Picking the right tool for each B-roll segment is the most consequential storyboard
decision. The rules below are based on what each tool does well.

> **Mode-aware** (PR #1): the storyboard's `mode` field decides whether A-roll exists at all.
> - `pure-broll-product-demo` → **NO A-roll**, skip § A-roll routing entirely. All content is HyperFrames (occasionally Seedance for atmospheric B-roll if budget allows).
> - `aroll-broll-hybrid` → A-roll for hook + CTA only, B-roll is the bulk.
> - `aroll-only` → Avatar fills the whole video, B-roll is minimal/optional.

This file is about **B-roll routing**. For A-roll generation, see `SKILL.md` § A-roll generation (skipped in pure-broll mode).

## Pure-broll-product-demo default scene structure

For `mode: "pure-broll-product-demo"`, use this default skeleton (per the chosen style preset's "default scene recipe" in `assets/style-presets/<name>/design.md`):

| Segment type | Tool | Block | Duration |
|---|---|---|---|
| `title-card` | hyperframes | (CSS-only) | 3-4s |
| `device-mockup` | hyperframes | `vfx-iphone-device` or custom MacBook CSS | 15-25s |
| `meta-output` | hyperframes | multi-shot brand preview (PR #8) | 5-7s |
| `title-card` (closing) | hyperframes | (CSS-only) | 3-4s |
| `wordmark` | hyperframes | `logo-outro` or CSS-only | 3-5s |

See `templates/openai-product-demo.json` (PR #5) for the canonical recipe spec.

---

## What each tool is good at

### HyperFrames (programmatic HTML/CSS/GSAP animation) — the B-roll default

**Strengths:**
- Pixel-perfect control over text, numbers, layout.
- Free — renders locally, deterministic (same code = same output).
- Fast iteration: edit HTML, re-render in ~2 minutes.
- Can embed user-provided screenshots as `<img>` elements (not regenerated).
- Great for: kinetic-typography hooks, counters, comparisons, charts, quotes,
  feature/skill demos, CTAs, brand reveals.

**Weaknesses:**
- Can't generate "real-looking" footage.
- Looks "designed" rather than "shot".

**Cost:** $0 (local Chromium render).

**Use it for:** anything with specific text / numbers / data / UI, kinetic typography,
before-after comparisons, quotes, CTAs, transitions, feature lists — the large majority of
B-roll in this skill.

### Seedance 2.0 cinematic B-roll (BytePlus ModelArk)

**Strengths:**
- Cinematic generative motion for abstract / atmospheric scenes.
- Same engine as A-roll — one API, one key.

**Weaknesses:**
- Cannot reproduce specific UI / text / numbers accurately.
- Non-deterministic; generation takes 1–3 min per clip; costs tokens.
- Humanoid robots / mech / anime can trigger output moderation.

**Cost:** BytePlus token-based pricing (see `references/cost-rates.md`).

**Use it for:** non-person mood / atmosphere / abstract conceptual scenes where exact
accuracy doesn't matter but cinematic feeling does.

**API reference:** `references/seedance-api.md`

### Hybrid (HyperFrames frame + Seedance fill)

A HyperFrames-style structure (a card layout, a labeled comparison) with cinematic
Seedance content inside one zone. Use only when there's a clear creative reason —
otherwise prefer a single tool.

---

## Decision matrix

| If the segment shows... | Use | Why |
|---|---|---|
| The actual product UI being used | **HyperFrames + screenshots** | Generated UI looks fake; real screenshots feel real |
| Numbers (counts, %, $, ratios) | **HyperFrames** | Precise typography, animatable counters |
| Trends, time-series, growth curves | **HyperFrames** | SVG/CSS animation, exact control |
| A kinetic-typography hook / opener | **HyperFrames** | Rhythmic word animation, full type control |
| Skill / feature demo (typed prompt → result) | **HyperFrames** | Exact UI mockups + deliverable cards |
| Feature comparison side-by-side | **HyperFrames** | Layout precision |
| Quote or testimonial overlay | **HyperFrames** | Typography control |
| Abstract concept (AI agents, data flow) | **Seedance** | Cinematic feel hard to fake with HTML |
| Mood / establishing scene (city, office) | **Seedance** | Generative atmosphere |
| CTA / link / "go try it now" | **HyperFrames** | Must be readable, branded |
| Logo + tagline ending | **HyperFrames** | Brand consistency |

---

## Anti-patterns (don't do these)

### ❌ Seedance for screenshots / UI demos
Generated UI text looks garbled. Always use real screenshots in HyperFrames for product UI.

### ❌ HyperFrames for atmospheric scenes
A static designed graphic of "AI agents collaborating" looks corporate-cringe. Use a
Seedance cinematic prompt instead.

### ❌ Seedance for any specific number
If a segment needs to display "61.5k stars" precisely, never trust a generative model to
render that text — use HyperFrames with a counter animation.

### ❌ Excessive hybrid segments
Hybrid is more complex to author. Use it only when there's a clear creative reason.

---

## Cost-aware routing

If the storyboard's cost is too high, shift **Seedance B-roll segments to HyperFrames**
wherever the segment can be expressed with text / data / animation — that drops the
segment to $0. Often a "demo of feature X" can be a "screenshot of feature X with a
HyperFrames zoom-in" at zero cost and similar visual quality.

---

## Routing checklist for storyboard.md

For every B-roll segment, the storyboard must answer:

1. **Tool**: `hyperframes` | `seedance` | `hybrid`
2. **Why this tool** (1 sentence) — tie back to the rules above.
3. **Spec**: the layout description (HyperFrames) or cinematic prompt (Seedance).
4. **Duration**: seconds.
5. **Cost**: $0 (HyperFrames) or tokens (Seedance).

If a segment is ambiguous, default to HyperFrames — cheaper and more reliable.
