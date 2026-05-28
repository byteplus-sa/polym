# Design — linear-minimal preset

Inspired-by Linear's brand — dark mode, neon accents, technical precision. Copyright-safe.

## Palette

```yaml
bg_primary: "#08080B"        # near-black
bg_scene: "linear-gradient(180deg, #08080B 0%, #14141A 100%)"
fg_primary: "#F2F2F4"        # off-white text on dark
fg_dim: "#6E6E78"            # muted slate
accent: "#5E6AD2"            # Linear purple-blue
accent_alt: "#26FFE0"        # neon teal for highlights
terminal_bg: "#0A0A0E"
terminal_fg: "#F2F2F4"
```

## Typography

```yaml
display: "Inter"             # same as openai but bolder weight floor
display_fallback: "-apple-system, system-ui, sans-serif"
mono: "JetBrains Mono"
mono_fallback: "ui-monospace, monospace"

scale:
  hero: 116px
  sub_hero: 84px
  body: 28px
  caption: 20px
  term_body: 17px

letter_spacing:
  hero: -0.04em
  body: -0.012em
  uppercase: 0.12em
```

## Corners + depth

```yaml
radius_lg: 14px              # less rounded, more technical
radius_md: 10px
radius_sm: 6px

shadow_floating: "0 0 80px rgba(94, 106, 210, 0.35)"   # glow, not drop-shadow
shadow_card: "0 0 0 1px rgba(255, 255, 255, 0.06), 0 1px 3px rgba(0, 0, 0, 0.4)"
```

Linear's signature: subtle 1px borders + soft glows instead of drop shadows.

## Motion preset

```yaml
entrance_default: "expo.out"             # sharper, more "technical"
entrance_playful: "back.out(1.4)"
camera: "expo.inOut"
drift: "sine.inOut"
duration_entrance: 0.4-0.6s              # faster — Linear is precise
duration_camera: 2.0-3.5s
```

## Tone of voice

- Title cards: declarative, technical ("Ship faster. Track everything.")
- Allow product-feature naming directly
- OK to mention metrics inline ("3× faster reviews")
- Avoid soft adjectives ("beautiful", "delightful")

## Default scene recipe

1. **Opening title** (3s) — dark bg, off-white text, subtle neon accent on key word
2. **Code/UI hero** (15-20s) — dark scene, terminal or code editor as main visual, glow accents
3. **Data callout** (4-6s) — typeset metrics with neon accent
4. **Outcome / second-feature beat** (5-7s) — same dark UI showing the result, NOT a meta video window
5. **Wordmark** (3-4s) — single line with glow

> Skip the meta-output beat unless the product is literally a video/media tool. See `references/meta-output-beat.md`.

Total: 30-40s.

## Glow guidance

Use the accent_alt (#26FFE0 neon teal) for ONE highlight per scene, max. Glow gives Linear's "designed for engineers" feel but becomes club-lighting fast if overused. Apply as:
- Text-shadow on a single keyword
- Soft border-glow on the hero card edge
- Subtle particle/glint near a focal point

Never glow the whole scene.
