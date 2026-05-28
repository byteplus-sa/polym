# Style presets — when-to-use

Five built-in copyright-safe presets ship under `assets/style-presets/<name>/design.md`. The Phase 1 preflight (PR #12) asks the user to pick one (or supply their own brand `design.md`).

| Preset | Vibe | Best for | Avoid for |
|---|---|---|---|
| `openai-clean` | Calm, lavender liquid bg, geometric bold sans, white title cards | Repo/product demos, AI-tooling launches, dev-platform announcements | Lifestyle, luxury, brand-heavy |
| `anthropic-warm` | Warm earth tones, sparkle accents, serif/sans pairing | Editorial-feel product reveals, thoughtful B2B | High-energy hype, sales-y |
| `linear-minimal` | Dark mode, neon teal accents, technical | Developer tools, engineering products, infra | Consumer-facing, lifestyle |
| `apple-keynote` | Pure black, hero typography, slow cinematic | Single hero-product reveals, premium consumer | Multi-feature dense info |
| `brand-bold` | High-contrast color blocks, oversized type, hard shadows | Bold brand identity, fundraising / launch announcements | Subtle / restrained / luxury |

## Preflight UX (Phase 1 sub-step)

The skill asks:

> "Where should I source the visual style?
>   (a) Your own brand — paste a design.md path, or describe colors/fonts inline
>   (b) Built-in preset (copyright-safe, inspired-by treatment):
>       · openai-clean      — white bg, geometric bold sans, lavender liquid, minimal
>       · anthropic-warm    — warm earth tones, sparkle accents, serif/sans pairing
>       · linear-minimal    — dark mode, neon accent, technical
>       · apple-keynote     — dark backdrop, hero typography, soft depth
>       · brand-bold        — high-contrast, oversized type, color-block"

Default suggestion based on content profile:
- AI/coding agent + repo demo → `openai-clean`
- Quiet B2B / consultative product → `anthropic-warm`
- Developer infrastructure → `linear-minimal`
- Single-product launch with hero shot → `apple-keynote`
- Loud launch / fundraising / event → `brand-bold`

## How the preset flows through the pipeline

1. **Phase 1 preflight** writes `style_preset: "<name>"` into `storyboard.json`.
2. **Phase 3 storyboard review** displays: "This storyboard targets {channel} at {aspect_ratio} using **{style}** — confirm before I generate assets."
3. **Phase 4 composition** copies the preset's `design.md` into the project root so the hyperframes skill picks it up automatically (per HyperFrames convention).
4. **Motion choices** during composition authoring read the preset's motion section and apply the documented easings / durations.

## When to override the preset partially

The preset is the **defaults**; per-task overrides are common. Examples:

- Brand color swap: keep `openai-clean` motion + typography, but accent → user's brand color
- Aspect ratio: preset doesn't dictate aspect — that's the separate channel question
- Length: preset's "default scene recipe" is a suggestion; the content profile + channel target supersedes

Override pattern in storyboard.json:
```json
{
  "style_preset": "openai-clean",
  "style_overrides": {
    "accent": "#FF6B35",
    "shadow_floating": "0 60px 90px rgba(255, 107, 53, 0.35)"
  }
}
```

## Adding a new preset

To add a new preset (e.g. `cyberpunk-neon`):
1. `mkdir <skill>/assets/style-presets/cyberpunk-neon/`
2. Author a `design.md` in the same format as the existing five
3. Add a row to the table at the top of this file
4. Update the preflight question text in SKILL.md Phase 1

Each preset must include: palette / typography / corners / motion / tone / default recipe / "not for" guidance.

## Anti-patterns

- **Don't mix preset motion presets within one video.** Pick one and commit. Half-power3-half-expo motion looks broken.
- **Don't override the preset's `fg_primary` or `bg_primary`** without a strong reason — these set the read-vs-contrast baseline. Override accents.
- **Don't use brand-bold + apple-keynote together** ("bold + restrained" is a contradiction).
