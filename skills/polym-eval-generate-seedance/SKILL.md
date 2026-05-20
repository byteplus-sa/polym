---
name: polym-eval-generate-seedance
description: Generate videos with BytePlus Seedance. Use for Seedance text-to-video, image-to-video, camera control, and draft video workflows.
---

# Generate Seedance Videos

Generate videos using BytePlus Seedance via the Ark SDK.

**API Reference:** https://docs.byteplus.com/en/docs/ModelArk/1366799

## Pre-flight Check

Before generating, verify in `.env`:
- `BYTEPLUS_API_KEY` (Required)
- `BYTEPLUS_BASE_URL` (default: `https://ark.ap-southeast.bytepluses.com/api/v3`)
- `SEEDANCE_MODEL` (optional, default from env)
- For reference images: `TOS_BUCKET`, `TOS_ACCESS_KEY`, `TOS_SECRET_KEY`

## Quick Start

```bash
# Text-to-Video
python skills/polym-eval-generate-seedance/scripts/generate.py \
  --prompt "A cat playing with a ball of yarn" \
  --model seedance-1-5-pro-251215

# Image-to-Video (first frame)
python skills/polym-eval-generate-seedance/scripts/generate.py \
  --prompt "The scene comes alive with gentle motion" \
  --first-frame photo.jpg \
  --model seedance-1-5-pro-251215
```

## Parameter Reference

| Parameter | CLI Flag | Type | Description | Default |
|-----------|----------|------|-------------|---------|
| `prompt` | `--prompt, -p` | string | Text prompt | **Required** |
| `model` | `--model, -m` | string | Model ID | env `SEEDANCE_MODEL` |
| `first_frame` | `--first-frame` | string | First frame image path/URL (I2V) | None |
| `last_frame` | `--last-frame` | string | Last frame image path/URL | None |
| `seconds` | `--seconds, -d` | int | Duration (2-12s, 1.5-pro: 4-12s) | 8 |
| `size` | `--size, -s` | string | Resolution: `480p`, `720p`, `1080p` | `720p` |
| `aspect_ratio` | `--aspect-ratio` | string | `16:9`, `9:16`, `1:1`, `4:3`, `3:4`, `21:9`, `adaptive` | auto-detect |
| `watermark` | `--watermark` | flag | Add watermark | False |
| `camerafixed` | `--camerafixed` | flag | Fix camera position | False |
| `draft` | `--draft` | flag | Draft mode (480p only, faster) | False |
| `seed` | `--seed` | int | Random seed | None |
| `output` | `--output, -o` | string | Output path | `generated/{id}.mp4` |

## Available Models

| Model | Resolution | Duration | Notes |
|-------|-----------|----------|-------|
| `seedance-1-5-pro-251215` | 480p/720p/1080p | 4-12s | Latest, native audio |
| `seedance-1-0-pro-250528` | 480p/720p/1080p | 2-12s | Strong visual consistency |
| `seedance-1-0-pro-fast-251015` | 480p/720p/1080p | 2-12s | Low latency |
| `seedance-1-0-lite-t2v-250428` | 480p/720p/1080p | 2-12s | T2V only |
| `seedance-1-0-lite-i2v-250428` | 480p/720p | 2-12s | I2V only |

## Generation Modes

- **T2V** — text only, no reference images
- **I2V (First Frame)** — `--first-frame photo.jpg`
- **I2V (Last Frame)** — `--last-frame photo.jpg`
- **First & Last Frame** — both `--first-frame` and `--last-frame`

Aspect ratio is auto-detected from reference images. Params are auto-validated/adjusted per model capabilities.

## Dependencies

```
byteplussdkarkruntime
Pillow
requests
python-dotenv
tqdm
tos  # for reference image upload
```

## Troubleshooting

### "BYTEPLUS_API_KEY is not set"
Set it in `.env`.

### "参考图模式不支持 1080p"
Use `720p` for lite I2V models.

### Draft mode forces 480p
This is by design — draft mode only supports 480p for faster generation.
