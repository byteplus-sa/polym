# Meta-output beat — OPT-IN multi-shot result preview (PR #8)

> **2026-05-27 reframe (post-Syncore feedback)**: this beat was previously documented as the "signature finish" for every pure-broll video. **That was wrong** — it was projection from the v1-v5 self-demos where the skill was demonstrating itself producing a video. For ordinary product launches, opening a QuickTime window to "play the result" is **distracting and project-specific**, not a universal beat.
>
> This beat is now **opt-in only**, used in these specific cases:
> 1. **The product IS a video / media tool** — Premiere alternative, Loom, video AI generator, etc. Then "here's what it makes" IS the product story.
> 2. **Recursive self-demo** — when the skill is showcasing itself (the explainer-video skill making a video about the explainer-video skill). Rare.
> 3. **Multi-format reveal** — when the product's output is the visible artifact (a design tool's exported deliverable, a chart maker's chart).
>
> **Default for product launches**: pick a "second moment" of UI walkthrough or a key benefit beat instead. The openai-product-demo recipe defaults to a second device-mockup state, not meta-output.

## When this beat IS appropriate

Use it when the rendered/produced artifact is itself the product value. Examples:
- Video editor → window shows the edited timeline output playing
- AI image generator → window shows the generated image revealing
- Slideware → window shows the deck playing
- Chart/dashboard maker → window shows the live chart updating
- The explainer-video skill itself → recursive demo (this skill's own marketing video)

## When this beat is NOT appropriate (i.e., most products)

- SaaS productivity apps (Linear, Notion, Things, Syncore)
- Developer infrastructure
- Consumer apps that aren't about output artifacts
- B2B tools where the value is workflow, not a rendered file

## What "multi-shot" means here (PR #8 finding)

The first iteration of this beat used a single static brand frame inside the QT window for 7s. User feedback: "太单薄了" (too thin). Replacing it with **3 sub-shots** inside the same window made the same time budget feel like a real product launch reel.

Default multi-shot structure inside the QT window (7 seconds):

| Sub-shot | Duration | Content |
|---|---|---|
| A — Brand hero | 2.5s | Wordmark + tagline reveal |
| B — Capability grid | 2.0s | 2×2 grid of capability pills with brand icons |
| C — Variants row | 1.5s | 3-card row (Pro/Lite/Mini-style or 3 use-cases) |

Cross-fades between sub-shots: ~0.25s. The QT window chrome and play-time bar stay constant across all 3 sub-shots — the **inside** of the window is what cuts.

## Two implementation strategies

### Strategy 1 — Synthetic content (no video embedding)

The QT window's content is **programmatic** — the 3 sub-shots are layered HTML with GSAP cross-fades. The shots match the chosen style preset's tone but are NOT a real rendered video.

Pros: simple, deterministic, no two-pass render needed, no keyframe-density issues.
Cons: the QT window technically isn't "playing" anything — but visually indistinguishable.

This is the **default** for pure-broll product demos. The QT window adds the "look at this output" framing; the content inside is just a brand reveal.

### Strategy 2 — Recursive video embed (two-pass render)

For the rare case where you want the QT window to literally play the rendered video (the meta-meta loop), use a two-pass render:

**Pass 1** — render WITHOUT the meta-output beat:
```bash
python3 compose_and_render.py storyboard.json --skip-meta-output
# produces dist/main-pass1.mp4
```

**Re-encode with dense keyframes** (HyperFrames `<video>` needs ≤1s keyframe intervals or it freeze-frames on seek):
```bash
ffmpeg -y -i dist/main-pass1.mp4 \
  -c:v libx264 -r 60 -g 60 -keyint_min 60 \
  -movflags +faststart -c:a copy \
  assets/v1.mp4
```

**Pass 2** — render WITH the meta-output beat, which embeds `assets/v1.mp4` as a `<video>` clip framed by the macOS window chrome:
```bash
python3 compose_and_render.py storyboard.json
# produces dist/main.mp4 with the embedded v1 visible inside the QT window
```

Pros: literally recursive — the most "wow" version.
Cons: two passes (~2× render time); keyframe gotcha; brittle if keyframe re-encode is skipped.

`compose_and_render.py` supports both strategies via the storyboard's segment config:
```json
{
  "id": "meta-output",
  "type": "meta-output",
  "strategy": "synthetic",       // or "recursive-video"
  "shots": [ ... ]               // synthetic mode
  "embed_video": "assets/v1.mp4" // recursive mode
}
```

## QT window chrome

Comes from `assets/macos-window-chrome.html` (CSS-only macOS-style window: titlebar with traffic lights, optional QuickTime transport bar). Drop into the meta-output segment; size 1000×1080 fits a 1440×1440 canvas with comfortable margins.

## Recommended per-style-preset

| Preset | Sub-shot palette | Background |
|---|---|---|
| `openai-clean` | Dark navy bg with violet accents | Soft blue-purple radial gradient |
| `anthropic-warm` | Warm earth tones, sparkle | Cream-to-clay gradient |
| `linear-minimal` | Pure black with neon teal | Solid black, glow on text |
| `apple-keynote` | True black, white hero text | Single product-color radial |
| `brand-bold` | Brand color block, white text | Solid brand color |

## When NOT to use the meta-output beat

- If the storyboard is under 20s — there isn't time for it without crowding
- If the product literally has no visual artifact to show (consultancy, service)
- If the user explicitly says "no meta loop" (some brands prefer to keep it simple)

In those cases, end on the closing title card + wordmark, no QT window.

## Audit checks (PRs #7 + #11 cover these automatically)

- A meta-output segment with 0 or 1 shot triggers a "too thin" warning
- A meta-output segment > 9s triggers a "too long" warning (default 5-7s)
- A meta-output segment without a `shots[]` array (synthetic strategy) or without `embed_video` (recursive strategy) is invalid
