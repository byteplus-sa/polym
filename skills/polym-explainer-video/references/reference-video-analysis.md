# Analyzing user-provided reference videos

If the user provides a reference video (e.g., "make it like this TikTok"), extract style cues to inform the storyboard design.

## What to extract from the reference

1. **Total duration** — set the project length to match (or the closest 15/30/60 mark)
2. **Cut count** — how many distinct shots? Determines pacing
3. **Cut rhythm** — even (every 2s) or accelerating (slow → fast)?
4. **Color palette** — dominant hues across frames
5. **Text overlay style** — bold sans-serif, handwritten, none?
6. **Audio bed** — voiceover only? music + voiceover? music only?
7. **Aspect ratio** — confirm it's 9:16 (else adapt)
8. **Avatar style** — talking head? voiceover only? animated character?

## Tools

### ffprobe (already installed)

Get duration, frame rate, dimensions:
```bash
ffprobe -v error -show_entries format=duration,bit_rate -show_entries stream=width,height,r_frame_rate -of json reference.mp4
```

### Frame extraction for visual analysis

Pull 6 evenly-spaced key frames:
```bash
mkdir -p frames
ffmpeg -i reference.mp4 -vf "fps=1/2.5,scale=480:-1" frames/frame_%03d.jpg -y
```

(`fps=1/2.5` = one frame every 2.5 seconds; for a 15s clip → 6 frames)

### Cut detection (rough)

```bash
ffmpeg -i reference.mp4 -filter:v "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep showinfo | wc -l
```

Counts scene changes above a 0.3 difference threshold. Approximate but useful.

### Audio analysis

```bash
ffmpeg -i reference.mp4 -ac 1 -ar 16000 -map 0:a -y audio.wav
ffprobe -v error -show_entries stream=codec_type,sample_rate,bit_rate audio.wav
```

If there's a voice track, you can transcribe it with `hyperframes transcribe audio.wav` (which uses local Whisper) to get the script structure of the reference.

## Analysis script

Use `scripts/analyze_reference_video.py`. It runs all the above and produces:

```json
{
  "duration_seconds": 14.8,
  "frame_rate": 30,
  "resolution": "720x1280",
  "aspect_ratio": "9:16",
  "estimated_cut_count": 7,
  "average_shot_duration": 2.1,
  "key_frames_extracted_to": "./frames/",
  "has_audio": true,
  "audio_codec": "aac",
  "voiceover_transcript_available": false
}
```

## How to use the analysis in storyboard design

After analyzing the reference video, use Claude vision to look at the extracted frames. Note:

1. **What's on screen at each frame** — is it a face, UI, abstract motion, text?
2. **Visual mood** — bright/dark, warm/cool, busy/minimal
3. **Text style if any** — match font weight, color, animation style
4. **Camera energy** — handheld feel vs static? quick cuts vs slow zooms?

Then incorporate these style cues into the storyboard:
- "Reference video uses 7 cuts in 15s → match with 6-7 segments"
- "Reference uses dark background with neon green accents → use that palette"
- "Reference has bold yellow text overlays → match for our captions"
- "Reference has voiceover-only (no avatar) → consider voiceover instead of A-roll"

## When to NOT match the reference

If the reference is in a different category (e.g., user gives a fashion brand TikTok as reference for a B2B SaaS launch), match the *energy* and *pacing* but NOT the visual content. Use Phase 2 research to ground the visual style for the actual audience.

If user explicitly says "I want EXACTLY this style", match more strictly. Otherwise, treat reference as inspiration not template.

## Output for Phase 1 brief

Add a section to `product-brief.md`:

```markdown
## Reference style notes

Source: <reference filename>

- Duration: 14.8s (will target 15s)
- Cut style: 7 cuts, average 2.1s per shot
- Palette: dark base #0a0a0a with neon green #34d399 accents
- Text style: bold sans-serif, yellow #fbbf24
- Audio: voiceover + light synth music bed
- Energy: high, quick cuts in second half

These will inform the Phase 3 storyboard:
- Match the cut count (7 segments in 15s)
- Use the dark + neon green palette
- Consider voiceover-only treatment for some segments
```
