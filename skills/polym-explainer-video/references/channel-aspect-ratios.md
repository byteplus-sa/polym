# Channel × aspect ratio reference

Source of truth for the Phase 1 preflight Q2 (PR #12) and the storyboard.json `aspect_ratio` + `channel` fields. Pick channel first; aspect ratio follows.

## Channel → recommended spec

| Channel | Default aspect | Default resolution | Sweet-spot duration | Notes |
|---|---|---|---|---|
| **X (Twitter)** | 1:1 | 1440×1440 (or 2160×2160) | 30-60s | Square dominates engagement; auto-plays muted — make titles readable without sound |
| **LinkedIn feed** | 1:1 | 1440×1440 | 30-90s | Feed prefers square; thought-leadership posts can go 16:9 |
| **LinkedIn featured** | 16:9 | 1920×1080 | 60-180s | Longer form, more polished posts |
| **Instagram Feed** | 1:1 or 4:5 | 1440×1440 / 1080×1350 | 15-60s | 4:5 takes more screen real estate but crops badly on link previews |
| **Instagram Reels** | 9:16 | 1080×1920 | 15-30s | Native vertical, audio-on culture |
| **TikTok** | 9:16 | 1080×1920 | **21-34s** | Algorithmic sweet spot per current TikTok research |
| **YouTube Shorts** | 9:16 | 1080×1920 | <60s (target <30s) | Similar to TikTok |
| **YouTube long** | 16:9 | 1920×1080 | 60-180s+ | Title/thumbnail drives discovery |
| **Website hero** | 16:9 | 1920×1080 | 10-30s loop | Often muted autoplay — design for silence |
| **Product page** | 1:1 or 16:9 | varies | 20-40s | Should work without sound |
| **Email embed (GIF fallback)** | 1:1 | 720×720 | 5-12s | GIF fallback strict size limits |

## The 3 canonical aspect ratios

| Aspect | Resolution recipe | Use-case anchor |
|---|---|---|
| **1:1 (square)** | 1440×1440 default; 2160×2160 for hi-res social | X / LinkedIn / IG feed |
| **9:16 (portrait)** | 1080×1920 default | TikTok / Reels / Shorts |
| **16:9 (landscape)** | 1920×1080 default | YouTube long / website hero |

## Multi-channel rule of thumb

If the user picks "multi-channel", generate the **primary** in 1:1 (works on most platforms with center-crop tolerance), then derive 9:16 + 16:9 variants only when explicitly needed. Don't render variants speculatively — each variant is ~ 1.0× the render cost again.

Layout reflow between aspect ratios is **not free**:
- 1:1 → 9:16: drop 33% horizontal content; stack horizontal layouts vertically
- 1:1 → 16:9: add 33% horizontal space; centered content gets generous margins
- 9:16 → 16:9: nearly impossible to direct-port; usually requires re-layout

The recipe templates (PR #5) should ship pre-tuned layouts for all 3 aspect ratios per recipe. If a recipe only has one aspect layout defined, the skill must warn before render that a non-primary aspect will use auto-letterboxing (looks unpolished).

## Safe zones

For platforms with UI overlays (TikTok captions/profile, IG Story chrome, YouTube subscribe overlay):

| Platform | Top safe (px from top) | Bottom safe | Left/Right |
|---|---:|---:|---:|
| TikTok | 220px | 480px | 50px |
| IG Reels | 250px | 400px | 50px |
| YouTube Shorts | 200px | 350px | 60px |
| X video | 80px | 80px | 40px |
| LinkedIn video | 80px | 80px | 60px |

For 9:16 portrait (1080×1920) heading to TikTok: keep critical content within `x ∈ [50, 1030]` and `y ∈ [220, 1440]`. Anything in the unsafe zones gets overlaid by the platform's UI chrome.

## Frame rate

Always 60fps regardless of aspect (per `motion-house-style.md` §1). Platforms downsample fine; uploading 60fps gives better motion than uploading 30fps.

## Audio

Most social channels auto-play muted. **Critical info must work without audio.** Captions are mandatory on TikTok/Reels/Shorts — use `caption-pill-karaoke` or `caption-highlight` synced to VO if A-roll exists.

For pure-broll-product-demo (no VO), the music bed is supplementary — design the visual to tell the story alone.

## How this flows through the pipeline

1. **Phase 1 preflight Q2** asks the user to pick a channel (or multi-channel).
2. The choice writes `channel: "x"` and `aspect_ratio: "1:1"` (or equivalent) into storyboard.json.
3. **Phase 3 storyboard review** surfaces: "Targeting **{channel}** at **{aspect_ratio}**. Sweet-spot duration {lo}-{hi}s — your storyboard is {actual}s." This is the user's chance to catch a length mismatch BEFORE render.
4. **Phase 4 composition** reads `aspect_ratio` and picks the matching layout template / canvas size.
5. **Phase 5 delivery** names the file with the aspect/channel hint (e.g. `seed2-launch-x-1x1.mp4`).
