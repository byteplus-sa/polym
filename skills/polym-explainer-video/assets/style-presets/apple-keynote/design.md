# Design — apple-keynote preset

Inspired-by Apple keynote / event video aesthetic — deep dark backdrop, hero typography, smooth depth-of-field, dramatic single-product reveals. Copyright-safe.

## Palette

```yaml
bg_primary: "#000000"        # true black
bg_scene: "radial-gradient(ellipse at 50% 60%, #1A1A22 0%, #050508 70%, #000000 100%)"
fg_primary: "#FFFFFF"
fg_dim: "#A0A0A8"            # neutral grey
accent: "#0A84FF"            # Apple system blue
accent_alt: "#FF453A"        # Apple system red (sparingly)
terminal_bg: "#0A0A0C"
terminal_fg: "#F5F5F7"
```

## Typography

```yaml
display: "SF Pro Display"    # Apple's system font; falls back gracefully
display_fallback: "-apple-system, 'Helvetica Neue', 'Inter', system-ui, sans-serif"
mono: "SF Mono"
mono_fallback: "ui-monospace, 'JetBrains Mono', monospace"

scale:
  hero: 140px                # bigger than other presets — keynote scale
  sub_hero: 96px
  body: 32px
  caption: 22px
  term_body: 17px

letter_spacing:
  hero: -0.05em              # tight, large headlines
  body: -0.015em
  uppercase: 0.1em
```

## Corners + depth

```yaml
radius_lg: 24px              # generous, premium
radius_md: 18px
radius_sm: 12px

shadow_floating: "0 100px 200px rgba(0, 0, 0, 0.6), 0 40px 80px rgba(0, 0, 0, 0.4)"
shadow_card: "0 0 0 1px rgba(255, 255, 255, 0.08), 0 8px 32px rgba(0, 0, 0, 0.4)"
```

## Motion preset

```yaml
entrance_default: "power3.out"
entrance_playful: "back.out(1.4)"        # less playful than openai-clean — premium reserve
camera: "expo.inOut"                     # slow build, decisive arrival
drift: "sine.inOut"
duration_entrance: 0.7-1.0s              # slower — gives weight
duration_camera: 4.0-6.0s                # cinematic
```

Hero entrances should feel **inevitable** — slow build, decisive landing. Apple keynotes never rush.

## Tone of voice

- Title cards: declarative, capitalized for product features ("**Pro performance. Mini size.**")
- One adjective max per line — restraint signals confidence
- Use the "X. Y." structure ("Built for speed. Made to last.")
- Avoid asking questions in titles

## Default scene recipe

1. **Hero title** (4-5s) — pure black, single line of huge display text fading in slowly
2. **Product hero** (15-20s) — single product centered on near-black, slow rotate or push-in, hard-edge rim light
3. **Feature reveal** (8-12s) — feature name with metric below, generous whitespace
4. **Closing line** (4-5s) — single quotable line, dramatic spacing
5. **Logo-outro** (4-5s)

Total: 40-50s — keynote feel needs breathing room. Don't compress below 35s.

## Depth-of-field rule

Always treat the hero element as the only object in sharp focus. Background gradient + glow simulates depth-of-field. Multiple sharp elements competing = looks designed, not photographed.
