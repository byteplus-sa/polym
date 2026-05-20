---
name: polym-eval-generate-veo
description: Generate videos with Google Veo via Vertex AI or AIDP. Use for Veo text-to-video, image-to-video, and first-frame workflows.
---

# Generate Veo Videos

Generate videos using Google Veo models. Supports **two backends**:
- `vertexai` (default): Google Cloud Vertex AI (google-genai SDK)
- `aidp`: ByteDance AIDP model hub (requests + JSON)

Both T2V (text-to-video) and I2V (image-to-video, first-frame reference) are supported.

---

## Pre-flight Check

### Vertex AI backend (default)

```bash
export VERTEX_PROJECT="your-gcp-project-id"
export VERTEX_LOCATION="us-central1"
```

### AIDP backend

```bash
export AIDP_AK="your-aidp-ak"
```

---

## Quick Start

```bash
cd skills/polym-eval-generate-veo
pip install -r requirements.txt
```

### Vertex AI backend (default)

```bash
# T2V
python scripts/generate.py \
  --prompt "A golden retriever running through a meadow at sunset"

# I2V (first-frame reference)
python scripts/generate.py \
  --prompt "The scene gently comes alive" \
  --first-frame /path/to/photo.jpg
```

### AIDP backend

```bash
# T2V
python scripts/generate.py \
  --backend aidp \
  --prompt "A golden retriever running through a meadow at sunset"

# I2V
python scripts/generate.py \
  --backend aidp \
  --prompt "The scene gently comes alive" \
  --first-frame /path/to/photo.jpg

# Use fast model
python scripts/generate.py \
  --backend aidp --model veo-3.0-fast-generate-001 \
  --prompt "A golden retriever running"
```

---

## Parameter Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt / -p` | required | Text prompt |
| `--backend` | `vertexai` | `vertexai` or `aidp` |
| `--model / -m` | `veo-3.0-generate-preview` (vertexai) / `veo-3.0-generate-001` (aidp) | Model override |
| `--first-frame` | `None` | Reference image path or URL (I2V) |
| `--seconds / -d` | `8` | Duration: `4`, `6`, or `8` |
| `--aspect-ratio` | auto-detected | `16:9` or `9:16` |
| `--output / -o` | `generated/<id>.mp4` | Output path |

---

## Available Models

| Backend | Model | Mode | Notes |
|---------|-------|------|-------|
| vertexai | `veo-3.0-generate-preview` | T2V, I2V | Default Vertex AI model |
| aidp | `veo-3.0-generate-001` | T2V, I2V | **Default AIDP model**, confirmed working |
| aidp | `veo-3.0-fast-generate-001` | T2V, I2V | Faster variant, confirmed working |

---

## Environment Variables

### Vertex AI backend
| Variable | Required | Description |
|----------|----------|-------------|
| `VERTEX_PROJECT` | Yes | GCP project ID |
| `VERTEX_LOCATION` | Yes | Vertex AI location (e.g. `us-central1`) |
| `VEO_MODEL` | No | Default model |
| `TOS_BUCKET` | No | TOS bucket for network URL |
| `TOS_ACCESS_KEY` | No | TOS access key |
| `TOS_SECRET_KEY` | No | TOS secret key |

### AIDP backend
| Variable | Required | Description |
|----------|----------|-------------|
| `AIDP_AK` | Yes | AIDP API Key (ak) |
| `AIDP_HOST` | No | AIDP host (default: `aidp.bytedance.net`) |
| `VEO_AIDP_MODEL` | No | Default AIDP model (default: `veo-3.0-generate-001`) |

---

## Output

```json
{
  "gen_success": true,
  "gen_video_path": "generated/abc12345.mp4",
  "gen_url": "https://tosv.byted.org/obj/gpt-openapi-public-cn/xxx_0.mp4",
  "gen_elapsed": 90,
  "gen_failed_reason": null
}
```

---

## AIDP API Details

### Submit task
`POST /veo/v1/generate?ak={ak}`
```json
{
  "model": "veo-3.0-generate-001",
  "instances": [{"prompt": "...", "image": {"bytesBase64Encoded": "...", "mimeType": "image/jpeg"}}],
  "parameters": {"aspectRatio": "16:9", "durationSeconds": 8}
}
```

### Get status
`POST /veo/v1/fetch?ak={ak}&product={product_name}`
```json
{"model": "veo-3.0-generate-001", "operationName": "projects/.../operations/<id>"}
```
Response: `{"done": true, "response": {"videos": [{"gcsUri": "gpt-openapi-public-cn/xxx_0.mp4"}]}}`

### Download
`https://tosv.byted.org/obj/{gcsUri}` (CN internal network)

### Model → product name mapping
| Model | Product name (for fetch) |
|-------|--------------------------|
| `veo-3.0-generate-001` | `google_veo_3.0_generate_001` |
| `veo-3.0-fast-generate-001` | `google_veo_3.0_fast_generate_001` |

---

## Dependencies

```
requests
Pillow
python-dotenv
google-genai    # vertexai backend only
```

Optional (for TOS upload / network URL with Vertex AI backend):
```
tos
```

---

## Troubleshooting

- **`VERTEX_PROJECT`/`VERTEX_LOCATION` not set**: Script will prompt for input (vertexai backend only).
- **`AIDP_AK` not set**: Script will prompt for input (aidp backend only).
- **TOS download fails**: `tosv.byted.org` requires ByteDance internal network access (VPN or office network).
- **`google-genai` import error**: Only needed for `vertexai` backend — `pip install google-genai`.
- **Unknown product name warning**: Model not in mapping; product name auto-derived from model name.
