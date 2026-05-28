# Design — anthropic-warm preset

Inspired-by Anthropic's brand language — warm earth tones, sparkle accents, serif-meets-sans pairing. Copyright-safe — no trademarked marks.

## Palette

```yaml
bg_primary: "#F7F3EC"        # warm off-white
bg_scene: "linear-gradient(180deg, #FFF8EE 0%, #F4E8D6 100%)"
fg_primary: "#1A1612"        # warm near-black
fg_dim: "#7D6E5E"            # taupe muted
accent: "#D97706"            # Anthropic orange
accent_alt: "#E8945B"        # softer coral
terminal_bg: "#1A1612"
terminal_fg: "#F2E8D8"
```

## Typography

```yaml
display: "Fraunces"          # variable serif with optical sizes — warm, editorial
display_fallback: "Georgia, 'Times New Roman', serif"
body: "Inter"
body_fallback: "-apple-system, system-ui, sans-serif"
mono: "JetBrains Mono"
mono_fallback: "ui-monospace, monospace"

scale:
  hero: 116px
  sub_hero: 88px
  body: 28px
  caption: 22px
  term_body: 17px

letter_spacing:
  hero: -0.025em             # serifs need less negative tracking than sans
  body: -0.005em
```

## Corners + depth

```yaml
radius_lg: 16px              # less rounded than openai-clean — more editorial
radius_md: 12px
radius_sm: 8px

shadow_floating: "0 40px 80px rgba(60, 35, 10, 0.25)"
shadow_card: "0 1px 2px rgba(60, 35, 10, 0.05), 0 6px 18px rgba(60, 35, 10, 0.08)"
```

## Motion preset

```yaml
entrance_default: "power2.out"           # softer than power3
entrance_playful: "back.out(1.3)"        # gentler spring
camera: "sine.inOut"                     # very smooth
drift: "sine.inOut"
duration_entrance: 0.6-0.85s             # slightly slower than openai-clean
duration_camera: 3.0-5.5s
```

## Tone of voice

- Title cards: thoughtful, declarative ("Let your agent draft the launch video")
- Allow longer titles (up to 8 words on a line — serifs read well at length)
- Capitalize for emphasis: "Built to think. Built to ship."
- Lean lifestyle-ish — talk about the experience, not the spec sheet

## Default scene recipe

1. **Opening title** (3-4s) — warm off-white bg, serif display, slight sparkle accent
2. **Device hero #1** (12-18s) — soft warm gradient bg, MacBook with the FIRST product moment (problem→solution UI)
3. **Device hero #2** (6-8s) — same MacBook, SECOND UI state showing the outcome / second feature / proof
4. **Closing title** (3-4s)
5. **Sparkle wordmark** (3-5s) — small Anthropic-style 8-point asterisk + name

> **No meta-output beat by default.** For editorial/B2B products (the main fit for this preset), showing a "rendered MP4 inside a window" feels off-brand. The second device hero communicates value more directly. See `references/meta-output-beat.md` if your product is actually a video/media tool.

Total: 32-40s typical.

## Sparkle motif (signature element)

Anthropic's visual identity centers on an 8-point sparkle/asterisk. Use sparingly:
- One small sparkle in the opening title corner as a quiet brand mark
- One on the wordmark
- NEVER as a "look at me" decoration — it's a punctuation, not a feature
