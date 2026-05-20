---
name: polym-eval-generate-gemini
description: Generate Gemini/Imagen images via Vertex AI, AI Studio, or AIDP. Use for Gemini image generation, editing, and reference-image workflows.
---

# Generate Gemini Images

Generate images using Google Gemini (nano banana / nano banana 2) via two backends:
- **google** (default): Vertex AI + Google AI Studio with automatic fallback
- **aidp**: ByteDance AIDP model hub (internal, fastest for ByteDance users)

## Two Backends

| Backend | Models | Endpoint | Auth |
|---------|--------|----------|------|
| `google` | `gemini-2.0-flash-preview-image-generation` | Vertex AI / AI Studio | `GOOGLE_AI_STUDIO_API_KEY` |
| `aidp` | `gemini-3.1-fi` (Nano Banana 2, default), `gemini-2.5-flash-image` (Nano Banana), `gemini_nbp` (Nano Banana Pro (Gemini 3.0 Image)) | `aidp.bytedance.net/.../multimodal/crawl` | `AIDP_API_KEY` |

## Pre-flight Check (IMPORTANT - Do this BEFORE generating)

Before running any generation command, the Agent MUST check that required environment variables are configured:

1. **Read the `.env` file** at the project root and verify:
   - **google backend**: `GOOGLE_AI_STUDIO_API_KEY` (required), optional: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GEMINI_IMAGE_API_KEY`
   - **aidp backend**: `AIDP_API_KEY`

2. **If any required variable is missing**, tell the user which variables are needed and ask for values before proceeding.

## Quick Start

```bash
# Google backend (default)
python skills/polym-eval-generate-gemini/scripts/generate.py --prompt "A serene mountain landscape at sunset"

# AIDP backend (ByteDance internal)
python skills/polym-eval-generate-gemini/scripts/generate.py --prompt "A serene mountain landscape at sunset" --backend aidp
```

## Required Configuration

Set in your `.env` file:

```bash
# Google backend
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
GEMINI_IMAGE_API_KEY=your_vertex_api_key  # or use ADC
GOOGLE_AI_STUDIO_API_KEY=your_ai_studio_key

# AIDP backend
AIDP_API_KEY=your_aidp_key

# Optional: Model overrides
GEMINI_IMAGE_MODEL=gemini-2.0-flash-preview-image-generation  # google backend default
GEMINI_AIDP_MODEL=gemini-3.1-fi                               # aidp backend default
```

## Usage Examples

### AIDP: Basic text-to-image

```bash
python skills/polym-eval-generate-gemini/scripts/generate.py \
  --prompt "A photorealistic cat sitting on a windowsill" \
  --backend aidp \
  --output generated/cat.png
```

### AIDP: Image editing with reference

```bash
python skills/polym-eval-generate-gemini/scripts/generate.py \
  --prompt "Make this image look like a watercolor painting" \
  --backend aidp \
  --ref-images path/to/photo.jpg \
  --output generated/watercolor.png
```

### AIDP: Use nano banana pro model

```bash
python skills/polym-eval-generate-gemini/scripts/generate.py \
  --prompt "A product photo on white background" \
  --backend aidp \
  --model gemini_nbp \
  --output generated/product.png
```

### Google: Basic text-to-image

```bash
python skills/polym-eval-generate-gemini/scripts/generate.py \
  --prompt "A photorealistic cat sitting on a windowsill" \
  --output generated/cat.png
```

### Google: Specify size

```bash
python skills/polym-eval-generate-gemini/scripts/generate.py \
  --prompt "Abstract geometric art" \
  --size 2K \
  --output generated/abstract.png
```

### Google: Force AI Studio instead of Vertex AI

```bash
python skills/polym-eval-generate-gemini/scripts/generate.py \
  --prompt "A sunset over the ocean" \
  --use-ai-studio
```

## Complete Parameter Reference

| Parameter | CLI Flag | Type | Description | Default |
|-----------|----------|------|-------------|---------|
| `prompt` | `--prompt, -p` | string | Text description | **Required** |
| `backend` | `--backend, -b` | string | `google` or `aidp` | `google` |
| `model` | `--model, -m` | string | Model ID | see below |
| `size` | `--size, -s` | string | `1K`, `2K`, `4K` (google only) | `1K` |
| `ref_images` | `--ref-images, -r` | list | Reference image paths/URLs | None |
| `use_ai_studio` | `--use-ai-studio` | flag | Force AI Studio (google only) | False |
| `no_retry` | `--no-retry` | flag | Don't fallback to AI Studio (google only) | False |
| `output` | `--output, -o` | string | Output file path | `generated/{timestamp}.png` |

## Available Models

### AIDP Backend

| AIDP Model ID | Google Model Name | Alias | Speed | Notes |
|---------------|-------------------|-------|-------|-------|
| `gemini-3.1-fi` | Gemini 3.1 Flash Image Preview | **Nano Banana 2 (Gemini 3.1 Flash Image Preview)** | ~35s | **Default**; has internal thinking |
| `gemini-2.5-flash-image` | Gemini 2.5 Flash Image | **Nano Banana (Gemini 2.5 Flash Image)** | ~8s | Faster, no thinking |
| `gemini_nbp` | Gemini 3.0 Image | **Nano Banana Pro (Gemini 3.0 Image)** | unknown | Previous generation |

### Google Backend

| Model ID | Notes |
|----------|-------|
| `gemini-2.0-flash-preview-image-generation` | Default |

## AIDP API Details

- **Endpoint**: `https://aidp.bytedance.net/api/modelhub/online/multimodal/crawl`
- **Auth header**: `api-key: <AIDP_API_KEY>`
- **Request format**: OpenAI chat completions JSON
- **Response**: `choices[0].message.multimodal_contents` — array with items of type `inline_data` containing base64-encoded image

Response image extraction:
```python
multimodal_contents = response["choices"][0]["message"]["multimodal_contents"]
image_item = next(i["inline_data"] for i in multimodal_contents if i["type"] == "inline_data")
image_bytes = base64.b64decode(image_item["data"])
```

## Programmatic Usage

```python
# Google backend
from generate import generate_image

result = generate_image(
    id="my_image",
    prompt="A beautiful sunset over the ocean",
    ref_image_paths=[],
    path="generated",
    size="1K",
    model="gemini-2.0-flash-preview-image-generation",
)

# AIDP backend
from generate import aidp_generate_image

result = aidp_generate_image(
    prompt="A beautiful sunset over the ocean",
    ref_image_paths=[],
    output_file="generated/output.png",
    model="gemini-3.1-fi",
)

# Returns: {"gen_success": bool, "gen_image_path": str, "gen_url": str}
```

## Dependencies

```
google-genai
Pillow
requests
python-dotenv
```

Install:
```bash
pip install google-genai Pillow requests python-dotenv
```

## Troubleshooting

### "No image in response"
The model may have filtered the prompt. Try rephrasing or check `prompt_feedback` in logs.

### 429 Rate Limit (Google backend)
Configure both Vertex AI and AI Studio keys for automatic fallback.

### AIDP timeout
`gemini-3.1-fi` (default) takes 30–60 seconds due to internal thinking/reasoning. Use `gemini-2.5-flash-image` for faster generation (~8s) without thinking.

### "product[gemini_3.1_fi] request should be process by cluster[multimodal...]"
Using wrong endpoint — must use `multimodal/crawl`, not `v2/crawl`.
