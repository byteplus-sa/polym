---
name: polym-eval-generate-seedream
description: Generate images with BytePlus Seedream 4.x/4.5. Use for Seedream text-to-image, AI art, product images, and batch image generation.
---

# Generate Seedream Images

Generate high-quality images using BytePlus Seedream 4.0/4.5 AI model via the Ark API.

**API Reference:** https://docs.byteplus.com/en/docs/ModelArk/1541523

## Pre-flight Check (IMPORTANT - Do this BEFORE generating)

Before running any generation command, the Agent MUST check that required environment variables are configured:

1. **Read the `.env` file** at the project root and verify these variables exist and are non-empty:
   - `BYTEPLUS_API_KEY` (Required for ALL generation)
   - `BYTEPLUS_BASE_URL` (Required, default: `https://ark.ap-southeast.bytepluses.com/api/v3`)
   - If using reference images, also check: `TOS_BUCKET`, `TOS_ACCESS_KEY`, `TOS_SECRET_KEY`

2. **If any required variable is missing or empty**, do NOT proceed with generation. Instead:
   - Tell the user which variables are missing
   - Ask the user to provide the values
   - Once provided, write them to the `.env` file using the edit tool
   - Then proceed with generation

3. **If `.env` file doesn't exist**, create it at the project root with the required variables (ask user for values first).

Example check flow:
```
Agent reads .env → BYTEPLUS_API_KEY is empty →
Agent tells user: "BYTEPLUS_API_KEY is not configured. Please provide your BytePlus API key." →
User provides key →
Agent writes to .env →
Agent proceeds with generation
```

## Quick Start

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py --prompt "your prompt here"
```

## Required Configuration

Set these environment variables in your `.env` file:

```bash
# Required: BytePlus Ark API credentials
BYTEPLUS_API_KEY=your_api_key_here
BYTEPLUS_BASE_URL=https://ark.ap-southeast.bytepluses.com/api/v3

# Optional: Default model
SEEDREAM_MODEL=seedream-4-5-251128

# Required for reference images: TOS configuration
TOS_ENDPOINT=tos-ap-southeast-1.bytepluses.com
TOS_BUCKET=your_bucket_name
TOS_ACCESS_KEY=your_access_key
TOS_SECRET_KEY=your_secret_key
TOS_REGION=ap-southeast-1
```

## Usage Examples

### Basic text-to-image

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py \
  --prompt "A serene mountain landscape at sunset with golden clouds" \
  --output generated/mountain.png
```

### With guidance scale (stronger prompt adherence)

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py \
  --prompt "A photorealistic portrait of a cat" \
  --guidance-scale 10.0 \
  --size 4K
```

### With prompt optimization

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py \
  --prompt "A simple flower" \
  --optimize-prompt
```

### With reference images

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py \
  --prompt "A cat in this artistic style" \
  --ref-images path/to/style.png \
  --output generated/styled_cat.png
```

### Sequential generation (multi-panel)

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py \
  --prompt "A comic strip showing a day in the life of a cat" \
  --sequential \
  --num-images 4
```

### With seed for reproducibility

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py \
  --prompt "Abstract geometric art" \
  --seed 42 \
  --output generated/abstract.png
```

### Get base64 response

```bash
python skills/polym-eval-generate-seedream/scripts/generate.py \
  --prompt "A beautiful sunset" \
  --response-format b64_json
```

## Complete Parameter Reference

| Parameter | CLI Flag | Type | Description | Default |
|-----------|----------|------|-------------|---------|
| `prompt` | `--prompt, -p` | string | Text description for image generation | **Required** |
| `model` | `--model, -m` | string | Model ID | `seedream-4-5-251128` |
| `size` | `--size, -s` | string | Image size: `1K`, `2K`, `4K` | `2K` |
| `seed` | `--seed` | int | Random seed for reproducibility | None |
| `image` | `--ref-images, -r` | list | Reference image paths/URLs | None |
| `guidance_scale` | `--guidance-scale, -g` | float | Prompt adherence (1.0-20.0) | ~7.0 |
| `sequential_image_generation` | `--sequential` | flag | Enable sequential generation | disabled |
| `num_images` | `--num-images, -n` | int | Images in sequential mode | 1 |
| `response_format` | `--response-format` | string | `url` or `b64_json` | `url` |
| `watermark` | `--watermark` | flag | Add watermark | False |
| `optimize_prompt_options` | `--optimize-prompt` | flag | Enable prompt optimization | False |
| `stream` | `--stream` | flag | Enable streaming response | False |
| `output` | `--output, -o` | string | Output file path | `generated/{timestamp}.png` |

## Available Models

| Model ID | Name | Notes |
|----------|------|-------|
| `seedream-4-5-251128` | Seedream 4.5 | Latest, doesn't support 1K size |
| `seedream-4-0-250828` | Seedream 4.0 | Supports all sizes |

## Parameter Details

### guidance_scale

Controls how closely the generation follows the prompt:
- **Lower values (1-5):** More creative freedom
- **Default (~7):** Balanced adherence
- **Higher values (10-20):** Strict prompt following, may reduce visual quality

### sequential_image_generation

For generating consistent multi-panel images:
- Use `--sequential` flag to enable
- Set `--num-images N` for number of panels
- Total reference images + generated images must not exceed 15

### optimize_prompt_options

Automatically enhances your prompt for better results:
- Use `--optimize-prompt` flag to enable
- Helps transform simple prompts into more detailed, effective ones

### response_format

- `url`: Returns URL to download image (default, recommended)
- `b64_json`: Returns base64-encoded image data (useful for direct processing)

## Programmatic Usage

```python
from generate import SeedreamConfig, generate_image

config = SeedreamConfig(
    prompt="A beautiful sunset over the ocean",
    model="seedream-4-5-251128",
    size="4K",
    guidance_scale=8.0,
    seed=42,
    watermark=False,
    optimize_prompt_options={"enabled": True}
)

result = generate_image(config, output_path="generated/sunset.png")
```

## Dependencies

```
requests
python-dotenv
tqdm
tos  # Only needed for reference images
```

Install:
```bash
pip install requests python-dotenv tqdm tos
```

## Troubleshooting

### "API_KEY is not set"
Set `BYTEPLUS_API_KEY` in `.env` file.

### "Seedream 4.5 doesn't support 1K"
Use `2K` or `4K` size for Seedream 4.5, or switch to Seedream 4.0.

### Reference image upload fails
Configure TOS credentials in `.env` file.

### High guidance_scale produces artifacts
Lower the value (try 5-10 range).

### Generation takes too long
- API timeout is 600 seconds
- 4K images take longer than 2K
- Sequential generation with many images takes longer
