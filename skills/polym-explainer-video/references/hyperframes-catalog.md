# HyperFrames registry catalog — curated for explainer-video

The HyperFrames registry has 80+ blocks/components. Most aren't relevant to this skill's pure-broll-product-demo style. This file curates the ~15 that are, organized by use case.

**Install command**: `npx hyperframes add <name>` (auto-pasted into `compositions/`). See `~/.claude/skills/hyperframes-registry/SKILL.md` for full details on wiring.

`scripts/fetch_registry.py` fetches and caches the full registry under `~/.explainer-video/registry-cache.json` (24h TTL) — use it to discover new blocks without manually browsing the GitHub repo.

---

## Core (pure-broll-product-demo mode default-installs)

| Name | Type | What it does | When to use |
|---|---|---|---|
| `vfx-iphone-device` | block | Real GLTF iPhone 15 Pro Max + MacBook Pro with HTML-in-canvas screens; 360° turntable, lens morph, camera choreography. 1920×1080, 15s. | Device-mockup hero shots (the OpenAI Codex / ChatGPT mobile video pattern) |
| `vfx-liquid-background` | block | Drifting liquid-gradient background, configurable colors. | Default backdrop behind device-mockup or kinetic-text |
| `liquid-glass-notification` | block | iOS-style frosted-glass notification overlay with title + body + action button. | Showing in-product notifications / approval prompts |
| `logo-outro` | block | Brand wordmark reveal with morphing logo pieces. | Closing wordmark beat (replaces hand-built scenes) |

## Captions (PR #3 — replaces PIL+ffmpeg overlay pattern)

Use these for any title card / hook / emphasis text. **Never** raster-render text via PIL anymore.

| Name | Type | What it does | When to use |
|---|---|---|---|
| `caption-kinetic-slam` | component | Words punch in one at a time with mixed entrances + yellow keyword highlights. | High-energy hooks; opening kinetic type |
| `caption-weight-shift` | component | Variable-font weight axis animates between light and bold during reveal. | Premium reveal / brand moments |
| `caption-gradient-fill` | component | Text fills with an animated gradient sweep. | CTAs, climactic single-word callouts |
| `caption-pill-karaoke` | component | Word-by-word pill highlight synced to audio. | A-roll segments with spoken VO |
| `caption-highlight` | component | Marker-sweep over key phrases as they're spoken. | Emphasizing one phrase in a longer line |

## Transitions (PR #6 — replaces concat-only stitching)

Default: cross-fade. For higher-energy transitions between B-roll scenes:

| Name | Type | What it does | When to use |
|---|---|---|---|
| `whip-pan` | block | Fast lateral pan-blur transition. | Energy boost between adjacent fast scenes |
| `flash-through-white` | block | White flash wipe transition. | Reveal moments (product unveil) |
| `cross-warp-morph` | block | Shader-based warp morph between two frames. | Premium transitions; use sparingly |
| `transitions-light` | block | Soft light-leak crossfade. | Default polished transition (slightly fancier than CSS fade) |
| `cinematic-zoom` | block | Push-in transition with motion blur. | Going from wide context → tight detail |

## Liquid Glass / iOS 26 / macOS Tahoe UI (PR #5 — device-mockup recipe)

| Name | Type | What it does |
|---|---|---|
| `liquid-glass-context-menu` | block | Frosted contextual menu overlay |
| `liquid-glass-media-controls` | block | Floating media player chrome |
| `liquid-glass-widgets` | block | Home-screen widget mockups |
| `ios26-liquid-glass` | block | Complete iOS 26 frosted-glass scene |
| `macos-tahoe-liquid-glass` | block | macOS Tahoe-style frosted window |

## Data viz (when storyboard needs numbers)

| Name | Type | What it does |
|---|---|---|
| `data-chart` | block | Animated bar/line chart with title + tabular data |
| `flowchart` | block | Animated nodes-and-arrows flowchart |
| `world-map`, `us-map`, `spain-map` | block | Animated geographic maps |

## Quality / texture overlays

| Name | Type | What it does |
|---|---|---|
| `grain-overlay` | component | Subtle film-grain noise overlay |
| `vignette` | component | Soft corner-darkening |
| `shimmer-sweep` | component | One-time light sweep across an element |
| `parallax-zoom`, `parallax-unzoom` | component | Slow continuous camera zoom |

---

## Discovery

Browse the full registry (refreshed every 24h):

```bash
python3 <skill>/scripts/fetch_registry.py
python3 <skill>/scripts/fetch_registry.py --tag captions
python3 <skill>/scripts/fetch_registry.py --type block
```

Each registry item has `name`, `type`, `title`, `description`, `tags`, `dimensions` (blocks only), `duration` (blocks only) — see `registry-item.json` in the upstream repo.

## Anti-patterns

**Don't** bulk-install all 80 blocks "just in case." Each adds ~5-50KB to the project and slows the lint pass. Only `hyperframes add` what the storyboard actually wires.

**Don't** mix kinetic-slam with weight-shift in the same scene — both compete for attention. Pick one per scene.

**Don't** use shader transitions (`cross-warp-morph`, `domain-warp-dissolve`) for every cut — they're impressive once, exhausting thrice. Default to `transitions-light` or CSS cross-fade.

## When to skip the registry entirely

For a single static title card or wordmark, raw HTML+CSS+GSAP is fine — adding a registry block is overkill. Use the registry for **mechanically complex** scenes (3D devices, shader transitions, liquid-glass effects) where the registry block represents real engineering you don't want to re-author.
