# Production techniques — Phase 4 patterns

Battle-tested patterns for the production phase. Use these when the storyboard calls for them.

---

## 1. Animated text overlays — use HyperFrames caption-* components (updated PR #3)

> **The old PIL+ffmpeg pattern is deprecated.** It produced hard cut-in/cut-out only, which looks amateur in 2026 product video. See `references/caption-components.md` for the full replacement.

For any timeline-synced text overlay, install one of the registry caption components and render via HyperFrames — `caption-kinetic-slam` for hooks, `caption-weight-shift` for premium reveals, `caption-gradient-fill` for CTAs, `caption-pill-karaoke` for VO sync.

```bash
# In the project root after Phase 4 npm install:
npx hyperframes add caption-weight-shift --no-clipboard
```

`scripts/compose_and_render.py` calls `npx hyperframes add` automatically for any caption components declared in the storyboard's segments (via `block` or `template` fields). You do not need to install manually.

See `references/caption-components.md` for the curated 4-component starter set + selection guide per style preset.

### When raster text IS still appropriate

The PIL pattern remains useful in one narrow case: annotating an existing video clip post-render with a static label (think: "DEBUG OUTPUT" stamp on a screen recording). For that, the old pattern works fine but isn't the skill's default any more.

### Annotation styling guidance (still valid)

These rules apply regardless of caption tech:
- **Skip border boxes.** They're hard to size correctly (text overflows) and look heavy on cinematic content.
- Default style: a colored bullet/dot + text with a clear contrast layer (stroke or pill bg). Reads cleanly over any background.
- Bullet color signals tone: red for problems / criticisms, green for wins, blue/cyan for neutral facts.

---

## 2. Split-screen B-roll: cinematic + data

When a narrative beat calls for both a cinematic moment AND structured data (benchmark numbers, comparison stats, feature list), compose a horizontal split: cinematic on the left, data panel on the right.

**Layout (9:16 portrait 720×1280):**

```
┌─────────────┬─────────────┐
│ 360×1280    │ 360×1280    │
│ cinematic   │ HF data     │
│ (Seedance)  │ (PIL+ffmpeg)│
└─────────────┴─────────────┘
```

**ffmpeg pattern:**

```bash
ffmpeg -y -i seedance_clip.mp4 -i hf_data_panel.mp4 -i vo.wav \
  -filter_complex "
    [0:v]scale=360:640,pad=360:1280:0:320:color=0x0F0F12,setsar=1,fps=25[left];
    [1:v]scale=360:1280,setsar=1,fps=25[right];
    [left][right]hstack=inputs=2[v];
    [2:a]apad=whole_dur=5.04[a]
  " -map "[v]" -map "[a]" ...
```

### Letterbox vs crop on the cinematic side

If the cinematic source is 720×1280 portrait but needs to fit a 360-wide panel, you have two options:

- **Crop center column** (`crop=360:1280:180:0`) — fills the full panel height, but cuts off horizontal detail. Use only when the subject is centered AND vertically dominant.
- **Scale + letterbox** (`scale=360:640,pad=360:1280:0:320`) — preserves the entire frame but the subject is half-height. Use whenever the subject extends horizontally or has any cropping risk.

**Default to letterbox.** Crop almost always loses something the user wanted to see.

---

## 3. Wordmark / brand reveal animation

For a moment that needs an emphasis text reveal (brand name, key claim, product name) over an existing video segment, pre-render a PIL animation as a PNG sequence and composite via ffmpeg `-itsoffset` + image2 demuxer.

```python
# render_wordmark.py — generates 62 RGBA PNGs (2.5s @ 25fps)
# Animation: scale-in 0.5→1.05 with back-out (0–0.4s), hold (0.4–1.5s),
#            fade-out + slight zoom-out (1.5–2.5s)
# Glow halo from multiple Gaussian-blurred copies of the text
```

```bash
ffmpeg -y -i video.mp4 \
  -framerate 25 -itsoffset 8.0 -i 'wordmark_frames/frame_%04d.png' \
  -filter_complex "[0:v][1:v]overlay=x=0:y=0:eof_action=pass[v]" \
  -map "[v]" -map 0:a ...
```

`-itsoffset 8.0` shifts the PNG sequence by 8 seconds, so the wordmark first appears at t=8 in the output. `eof_action=pass` keeps the base video showing after the wordmark frames run out.

Sync the wordmark to a meaningful audio cue: a key word in the avatar's line, a beat drop in the music, or a transition between two B-roll clips.

---

## 4. Frame-rate alignment — 60fps end-to-end (updated PR #2)

The skill now renders at **60fps `--quality high`** by default — see [`motion-house-style.md`](./motion-house-style.md) §1. `scripts/compose_and_render.py` passes this automatically.

A-roll Seedance clips usually return at 24fps. **Frame-interpolate UP to 60fps** before concat — never sample down to 25fps (the old approach silently capped every video's smoothness):

```bash
# Lift Seedance A-roll from 24fps → 60fps
ffmpeg -y -i seedance_aroll.mp4 \
  -vf "scale=1080:1920,fps=60" \
  -c:v libx264 -pix_fmt yuv420p -preset medium -crf 18 \
  -c:a aac -b:a 192k -ar 48000 \
  aroll_60fps.mp4
```

For the concat filter, render every clip at 60fps before stitching. ffmpeg's `concat` filter
handles mismatched framerates with a re-encode, but the result inherits the lowest input
fps — so any 24fps source dragged through will create stutter regardless of the final
container fps. Always pre-process.

The Seedance A-roll already carries its own audio (generated voice, or the reference
video's voice in r2v mode) — keep it; do not strip or replace it.

> **Why this changed**: the old §4 normalized everything to 25fps for concat-compatibility
> safety, which silently capped every video's perceived smoothness at 25fps. The hyperframes
> CLI now supports `--fps 60 --quality high` natively, and 60fps rendering is 2× slower but
> visibly more polished. The render is the cheap step relative to total iteration time.

---

## 5. Actual-duration timing

Storyboard durations are estimates; the actual Seedance A-roll clips run slightly longer
or shorter (a 5–10s request often returns ~5s). Always:

1. After each A-roll task succeeds, download the clip and `ffprobe` its real duration.
2. Build the final timeline from the **actual** A-roll durations — the HyperFrames render
   uses the planned gap, and the concat absorbs the small drift (a 90s plan landing at
   ~91–94s is fine).
3. Update `storyboard.json` with actual durations so cost/length stays accurate.

Seedance A-roll has native audio baked in — there is no separate TTS step to time against.

---

## 6. Seedance content-policy avoidance

Seedance frequently returns `OutputVideoSensitiveContentDetected.PolicyViolation` for prompts that look like character IP. Failure-prone subjects:

- ❌ Humanoid robots, mech-style figures, anime characters
- ❌ Vehicles or props that look like specific brands
- ❌ Fictional characters or stylized creatures

Reliable subjects:

- ✅ Industrial machinery (six-axis robotic arms, gears, mechanical joints)
- ✅ Abstract geometric sculptures with clear "original" framing
- ✅ Generic mechanical/architectural details (panels, bolts, brushed metal)

**If a Seedance task fails with the policy code:** simplify the subject toward generic engineering. Add explicit disclaimers in the prompt: "no logos, no text overlays, original generic design, no IP, no brand markings."

---

## 7. Cinematic + benchmark visualization combos

When the storyboard calls for "show numbers AND deliver a cinematic moment", combine a Seedance clip with a HyperFrames data panel using the split-screen pattern above. Examples:

- **Win-rate benchmark**: cinematic product shot left, animated bar chart right
- **Before/after**: low-quality Seedance left (with annotations), beauty render right
- **Feature lineup**: feature spotlight Seedance left, feature list HF panel right

For benchmark bars specifically, use a **two-color segmented bar** (green = your product wins, red = competitor wins) with model labels positioned semantically — your label on the left over green, competitor name on the right over red. Show absolute percentages inside each segment.

---

## 8. Audio mix: sidechain ducking by default

See `references/volcengine-music-api.md` for the full pattern. Key points:

- Always sidechain-duck the music against the voice track. Static-volume mixing always compromises one direction.
- Settings that work across most TikTok/Shorts content: `threshold=0.03 ratio=10 attack=10 release=300`.
- Verify: voice should land near -18 dB RMS, music-only gaps near -22 to -28 dB.

---

## 9. Concat strategy: filter, not demuxer

Always use the **concat filter** (re-encodes) for the final assembly when stitching segments from different sources (Seedance A-roll + HyperFrames B-roll slices).

**Why not `-c copy`:**
- AAC frame-boundary clicks → perceived as cut-offs at segment seams
- Mismatched framerates can cause freezing
- Different encoder configs lead to subtle audio glitches

```bash
ffmpeg -y -i s1.mp4 -i s2.mp4 -i s3.mp4 ... \
  -filter_complex "[0:v][0:a][1:v][1:a][2:v][2:a]...concat=n=N:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -pix_fmt yuv420p -preset medium -crf 18 \
  -c:a aac -b:a 192k -ar 48000 \
  /tmp/concat_clean.mp4
```

CRF 18 is visually lossless on the source quality these segments come from.

Then mix music as a final pass with `-c:v copy` (no further video re-encode):

```bash
ffmpeg -y -i /tmp/concat_clean.mp4 -i music_bed.m4a \
  -filter_complex "[0:a]asplit=2[trig][out];[1:a]volume=0.5[m];
    [m][trig]sidechaincompress=threshold=0.03:ratio=10:attack=10:release=300:makeup=1[ducked];
    [out][ducked]amix=inputs=2:duration=first:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 \
  dist/main.mp4
```

---

## 10. Iterative refinement loop

Phase 4 production is rarely one-shot. Plan for 2–3 iterations:

1. **First pass**: storyboard timings often turn out wrong because TTS durations differ from estimates. Adjust segment lengths to match actual TTS.
2. **Sync pass**: voice not lining up with footage → check that A-roll videos aren't being re-encoded unnecessarily; check AAC boundary handling on concat.
3. **Visual polish**: text overflowing boxes, animation timing, music too loud/soft, content not matching narration.
4. **Content quality**: pain-point demos may need to be more concrete; cinematic shots may need to be more closely tied to the talking head.

Save every paid asset in `assets/` so iterations don't re-spend credits. Save the storyboard.json after each change so cost tracking stays accurate.

---

## File naming conventions

```
~/projects/<slug>-video/
  product-brief.md
  research.md
  storyboard.md
  storyboard.json
  scripts/
    render_broll.py            # static HF B-roll
    render_benchmark_panel.py  # data viz for split-screen
    render_wordmark.py         # brand reveal frames
  assets/
    aroll-N.mp4                # Seedance 2.0 A-roll segments (with native audio)
    hf-render.mp4              # full HyperFrames B-roll render
    hf-sliceN.mp4              # HyperFrames slices between A-roll inserts
    music_volc_raw.wav         # raw Volcengine output
    music_volc.m4a             # trimmed + faded music bed
    anno_N.png                 # annotation overlays
    wordmark_frames/           # brand reveal PNG sequence
  dist/
    main.mp4                   # final output
```
