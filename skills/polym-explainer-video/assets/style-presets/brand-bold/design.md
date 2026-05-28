# Design — brand-bold preset

High-contrast, oversized type, color-block aesthetic — Stripe / Notion / Vercel / Linear-Light vibe. For products that need to feel **loud and confident** rather than restrained.

## Palette

```yaml
bg_primary: "#FFFFFF"        # pure white
bg_scene: "#FFE600"          # signature accent color block (overrideable per-task)
fg_primary: "#000000"        # pure black for max contrast
fg_dim: "#525252"            # neutral grey
accent: "#FF3D00"            # bold red-orange
accent_alt: "#00DC82"        # bright green
terminal_bg: "#000000"
terminal_fg: "#FFFFFF"
```

The `bg_scene` is **intentionally configurable per-task** — bold brand videos often use one specific accent color (Vercel black, Notion white-on-blackboard, Stripe purple, Linear lavender). Ask the user during preflight if they want to override the default yellow.

## Typography

```yaml
display: "Geist"             # geometric, very legible at huge sizes
display_fallback: "Inter, -apple-system, 'Helvetica Neue', system-ui, sans-serif"
mono: "Geist Mono"
mono_fallback: "JetBrains Mono, ui-monospace, monospace"

scale:
  hero: 168px                # massive — fills the canvas
  sub_hero: 108px
  body: 36px
  caption: 26px
  term_body: 18px

letter_spacing:
  hero: -0.055em             # very tight on huge type
  body: -0.02em
```

## Corners + depth

```yaml
radius_lg: 8px               # nearly sharp — anti-rounded for "bold" feel
radius_md: 6px
radius_sm: 4px

shadow_floating: "8px 8px 0 #000000"     # offset hard-shadow ("brutalist")
shadow_card: "4px 4px 0 #000000"
```

Hard offset shadows are a signature of this preset. Never use soft Gaussian shadows.

## Motion preset

```yaml
entrance_default: "back.out(2.0)"        # exaggerated overshoot
entrance_playful: "elastic.out(1, 0.5)"  # bouncy
camera: "expo.out"                       # snap into place
drift: "none"                            # static color blocks don't drift
duration_entrance: 0.35-0.55s            # fast and punchy
duration_camera: 1.5-3.0s
```

## Tone of voice

- Title cards: short, demanding ("Ship it.", "Try it now.")
- All-caps allowed for hero text (sparingly — 1-2 words)
- Exclamation marks allowed (1 per video max)
- Address the viewer directly ("YOU build it.")
- Numbers in huge type ("**3×** faster")

## Default scene recipe

1. **Title slam** (2-3s) — color-block bg, oversized 1-line declaration
2. **Feature pile** (8-15s) — 3-5 features stacked rapidly with offset shadows + bouncy entrances
3. **Mid-video pivot** (3-5s) — color-block flip (yellow → black → yellow), maintains energy
4. **Mega-CTA** (3-5s) — single huge button or wordmark
5. **Wordmark** (2-3s) — fast snap-in

Total: 22-32s — bold-brand videos peak around 25s. Don't pad.

## What this preset is NOT for

- Premium / luxury feel (use `apple-keynote`)
- Subtle / editorial (use `anthropic-warm`)
- Developer-technical (use `linear-minimal`)
- Quiet product UI demos (use `openai-clean`)
