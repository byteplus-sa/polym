# Caption components — replaces PIL+ffmpeg overlay pattern (PR #3)

The old `references/production-techniques.md` §1 documented a PIL→PNG→ffmpeg-overlay pattern for text. That pattern produced **hard cut-in / cut-out only** — no easing, no motion, no weight changes. Modern product video text deserves real animation.

This file replaces that pattern. Use HyperFrames `caption-*` registry components for **every** timeline-synced text overlay.

## Install

```bash
npx hyperframes add caption-kinetic-slam --no-clipboard
```

For all caption components, install into the project at Phase 4 (`compose_and_render.py` does this automatically when the storyboard's segments reference them).

## Recommended starter set (4)

For the explainer-video skill's default scene structures, these four cover ~95% of needs. Pick one per segment — don't combine.

### `caption-kinetic-slam` — high-energy hooks

Words punch in one at a time with mixed entrance modes (slide-down, slide-side, scale-pop), with yellow keyword highlights. Best for the opening 2-4 seconds of a video where you want to grab attention.

```html
<!-- After install, the file lives at compositions/components/caption-kinetic-slam.html.
     Edit the WORDS array inside the script section to your script.
     Reference from your scene as a normal sub-composition. -->
```

When to use: opening hook, mid-video "wait, what?" moment.
When NOT to use: closing scenes (too busy), VO-sync (use caption-pill-karaoke instead).

### `caption-weight-shift` — premium reveal

Variable-font weight axis animates from light → bold during the reveal. Reads as "refined" and "considered" — Apple/Linear feel.

When to use: brand moments, hero title cards, premium product reveals.
When NOT to use: high-energy hype videos (mismatch).

### `caption-gradient-fill` — CTAs / single-word climax

Text fills with an animated gradient sweep. Strong visual signal — use once per video at most.

When to use: the climactic single-word callout, the CTA line.
When NOT to use: more than once per video (becomes wallpaper).

### `caption-pill-karaoke` — A-roll VO sync

Word-by-word pill highlights synced to spoken audio. The right choice when there's a Seedance A-roll segment and the spoken script needs to be readable for mobile-muted-audio viewers.

When to use: every A-roll segment in `aroll-broll-hybrid` mode (TikTok/Reels require captions; this is the cleanest).
When NOT to use: pure-broll videos with no speech.

## Other captions in the registry (use selectively)

| Component | One-liner | When |
|---|---|---|
| `caption-neon-glow` | Glowing text with halo | linear-minimal preset, dark scenes |
| `caption-highlight` | Marker-sweep over phrases | Emphasizing a phrase mid-speech |
| `caption-emoji-pop` | Emoji-paired bouncy entrance | Lifestyle / fun content |
| `caption-glitch-rgb` | RGB-channel-separated jitter | Tech/cyberpunk vibes only |
| `caption-matrix-decode` | Characters resolve from random | Sci-fi / "compute happening" moments |
| `caption-clip-wipe` | Letters revealed via clip-path mask | Cinematic title reveals |
| `caption-texture` | Text filled with a texture image | Brand-style title cards |
| `caption-particle-burst` | Particles burst on word entrance | High-energy hooks (alternative to kinetic-slam) |
| `caption-blend-difference` | Blend-mode difference over moving bg | Avant-garde / fashion |
| `caption-editorial-emphasis` | Italic/bold mix mid-sentence | Editorial / longform feel |
| `caption-parallax-layers` | Multi-depth parallax on words | Dramatic title cards |
| `caption-neon-accent` | Neon underline / accent | linear-minimal preset accents |

Curate per task — don't over-stack. **One caption pattern per scene** is the rule.

## Anti-patterns

- **Don't** raster text with PIL anymore. The old §1 pattern is deprecated; production-techniques.md now points here.
- **Don't** use `caption-kinetic-slam` AND `caption-weight-shift` in the same scene — both compete for attention.
- **Don't** use shader-heavy captions (`caption-matrix-decode`, `caption-glitch-rgb`) for >3s — they fatigue the eye.
- **Don't** edit a caption component's internals to hack timing. Adjust the component's `WORDS` array (kinetic-slam) or input parameters; if you need different motion, pick a different caption.

## Per-style-preset recommendations

| Preset | Default opening caption | Default closing caption |
|---|---|---|
| `openai-clean` | caption-weight-shift | caption-gradient-fill |
| `anthropic-warm` | caption-clip-wipe | caption-weight-shift |
| `linear-minimal` | caption-neon-glow | caption-gradient-fill |
| `apple-keynote` | caption-clip-wipe | caption-weight-shift |
| `brand-bold` | caption-kinetic-slam | caption-particle-burst |
