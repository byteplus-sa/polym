# Design — openai-clean preset

Inspired-by treatment of OpenAI's recent product video aesthetic (Codex / ChatGPT mobile launches). Copyright-safe — shares spirit (palette family, typography density, motion curves) but uses no trademarked marks.

## Palette

```yaml
bg_primary: "#FAFAF9"      # off-white title cards
bg_scene: "radial-gradient(circle at 30% 25%, #c2b3ff 0%, #9b89ee 30%, #7763d9 65%, #4f3fb0 100%)"
fg_primary: "#0B0B10"      # near-black text
fg_dim: "#6B6B78"          # muted captions / subtext
accent: "#7763D9"          # lavender — the "OpenAI purple" feel
accent_alt: "#B7A2FF"      # lighter lavender for highlights
terminal_bg: "#0E0E12"
terminal_fg: "#E6E6EC"
```

## Typography

```yaml
display: "Inter"           # variable-weight; use weight 700-900 for hero text
display_fallback: "-apple-system, 'Helvetica Neue', system-ui, sans-serif"
mono: "JetBrains Mono"
mono_fallback: "ui-monospace, 'SF Mono', monospace"

scale:
  hero: 124px              # opening/closing title cards
  sub_hero: 92px           # secondary titles
  body: 30px               # subtitles / taglines
  caption: 22px            # chip labels
  term_body: 17px          # in-terminal mono

letter_spacing:
  hero: -0.045em
  body: -0.012em
  uppercase: 0.18em
```

## Corners + depth

```yaml
radius_lg: 22px            # device frames, large cards
radius_md: 18px            # chips, buttons
radius_sm: 12px            # icons / monograms

shadow_floating: "0 60px 90px rgba(20, 8, 60, 0.45)"   # devices on liquid bg
shadow_card: "0 1px 2px rgba(11, 11, 16, 0.06), 0 8px 20px rgba(11, 11, 16, 0.08)"
```

## Motion preset

```yaml
entrance_default: "power3.out"
entrance_playful: "back.out(1.5)"
camera: "power1.inOut"
drift: "sine.inOut"
duration_entrance: 0.55-0.7s
duration_camera: 2.0-4.5s
```

See `references/motion-house-style.md` for the full ruleset — this preset complies with the house style.

## Tone of voice

- Title cards: confident, sparse, sentence-case ("Make explainer videos in your agent")
- No exclamation marks
- Tagline length 4-7 words max
- Avoid corporate buzzwords ("revolutionary", "game-changing")
- One product attribute per line

## Default scene recipe

The pure-broll-product-demo recipe (see PR #5) defaults to:
1. **Opening title card** (3-4s) — white bg, two-line bold display text
2. **Device-mockup long shot #1** (12-18s) — lavender liquid background + MacBook or iPhone with live UI on screen showing the FIRST product moment (the problem-to-solution beat), slow progressive zoom 0.86 → 1.10
3. **Device-mockup long shot #2** (6-8s) — same device, different UI state — the SECOND product moment (outcome / second feature / proof). Continues camera push to ~1.14
4. **Closing title card** (3-4s) — white bg, two-line text
5. **Logo-outro / wordmark** (3-5s)

> **Meta-output beat is NOT in the default**. The "QuickTime window playing the result" beat is an opt-in for video/media products or recursive self-demos (see `references/meta-output-beat.md`). For ordinary product launches, a second UI walkthrough beat communicates the value more directly than showing the rendered MP4.

Total target: 30-35s (single-message profile). Stretch to 40-55s for few-features profile.

## What this preset is NOT for

- Brand-heavy videos (use `brand-bold` instead)
- Dark-mode product demos (use `linear-minimal`)
- Data-dense business content (use `apple-keynote`)
- Warm/lifestyle products (use `anthropic-warm`)
