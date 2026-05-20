---
name: polym-eval-generate-gpt-image
description: Generate or edit images with GPT Image via ByteDance AIDP. Use for gpt-image-1 text-to-image, multi-image edits, and masks.
---

# GPT Image Generation & Editing

Generate or edit images using `gpt-image-1` via ByteDance AIDP.

## Two Modes

| Mode | Description | Endpoint |
|------|-------------|----------|
| `generate` (default) | Text-to-image | `/images/generations` |
| `edit` | Edit/composite reference images with a prompt | `/images/edits` |

## Pre-flight Check (IMPORTANT - Do this BEFORE generating)

Read the `.env` file and verify `AIDP_API_KEY` is set. If missing, ask the user for the key before proceeding.

## Quick Start

```bash
# Text-to-image
python skills/polym-eval-generate-gpt-image/scripts/generate.py \
  --prompt "A serene mountain landscape at sunset"

# Image editing
python skills/polym-eval-generate-gpt-image/scripts/generate.py \
  --mode edit \
  --prompt "给水獭穿上宇航员服装" \
  --images photo.jpg

# Image editing with mask
python skills/polym-eval-generate-gpt-image/scripts/generate.py \
  --mode edit \
  --prompt "Replace background with a beach" \
  --images photo.jpg --mask mask.png
```

## Required Configuration

```bash
# .env
AIDP_API_KEY=your_aidp_key

# Optional overrides
GPT_IMAGE_MODEL=gpt-image-1   # default model
```

## Available Models

| Model ID | Status | Notes |
|----------|--------|-------|
| `gpt-image-1` | ✅ Available (~21s) | **Default** |
| `gpt-image-2` | ❌ Not yet available | Server error on AIDP |

## Complete Parameter Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt / -p` | required | Text prompt |
| `--mode` | `generate` | `generate` or `edit` |
| `--model / -m` | `gpt-image-1` | Model ID |
| `--size / -s` | `1024x1024` | `1024x1024`, `1536x1024`, `1024x1536`, `auto` |
| `--quality / -q` | `low` | `low`, `medium`, `high`, `auto` |
| `--images / -i` | — | Reference image paths/URLs (edit mode, required) |
| `--mask` | — | Mask image path (edit mode, optional) |
| `--output / -o` | `generated/{timestamp}.png` | Output file path |
| `--n` | `1` | Number of images to generate |

## AIDP API Details

### Generate
`POST https://aidp.bytedance.net/api/modelhub/online/v2/crawl/openai/images/generations?ak={ak}`

Headers: `Content-Type: application/json`, `api-key: {ak}`

```json
{
  "model": "gpt-image-1",
  "prompt": "A cute cat",
  "n": 1,
  "size": "1024x1024",
  "quality": "low"
}
```

### Edit
`POST https://aidp.bytedance.net/gpt/openapi/online/v2/crawl/openai/images/edits?ak={ak}`

Headers: `api-key: {ak}` (multipart/form-data, no Content-Type header)

Form fields: `image[]` (one or more files), `prompt`, `model`, `quality`, `size`, `n`, `mask` (optional)

### Response (both modes)
```json
{
  "created": 1745742988,
  "data": [{"b64_json": "<base64 encoded image>"}],
  "usage": {"total_tokens": 284, "input_tokens": 12, "output_tokens": 272}
}
```

## Programmatic Usage

```python
from generate import generate_image, edit_image

# Generate
result = generate_image(
    prompt="A beautiful sunset",
    output_file="generated/sunset.png",
    model="gpt-image-1",
    size="1024x1024",
    quality="low",
)

# Edit
result = edit_image(
    prompt="给水獭穿上宇航员服装",
    image_paths=["photo.jpg"],
    output_file="generated/edited.png",
    model="gpt-image-1",
    quality="high",
    mask_path=None,
)

# Returns: {"gen_success": bool, "gen_image_path": str, "gen_url": str}
```

## Dependencies

```
Pillow
requests
python-dotenv
```

## Troubleshooting

### `no model permission: gpt-image-1`
The AIDP AK does not have permission for this model. Apply on the ModelHub platform.

### `gpt-image-2` server error
`gpt-image-2` is not yet available on AIDP. Use `gpt-image-1`.

### Edit mode: image not updating
Provide a more specific prompt. For targeted edits, use a `--mask` image to indicate the region to modify.
