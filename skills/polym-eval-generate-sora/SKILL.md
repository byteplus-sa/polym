---
name: polym-eval-generate-sora
description: Generate videos with Sora via OpenAI or ByteDance AIDP. Use for Sora 2/Pro text-to-video and image-to-video workflows.
---

# polym-eval-generate-sora

Generate videos using Sora models.

Supports **two backends**:
- `openai` (default): OpenAI public API — `sora-2`, `sora-2-pro`
- `aidp`: ByteDance AIDP model hub — `azure-sora2` (recommended), `azure-sora` (legacy T2V only)

Both T2V (text-to-video) and I2V (image-to-video, first-frame reference) are supported.
Auto aspect ratio detection from the reference image.

---

## Pre-flight Check

### OpenAI backend (default)

```bash
# Required
export OPENAI_API_KEY="sk-..."
```

If `OPENAI_API_KEY` is not set, the script will prompt you to enter it and save it to `.env`.

### AIDP backend

```bash
# Required
export AIDP_AK="your-aidp-ak"
```

> **Note for `azure-sora2`**: The "账号粘性功能开关" must be enabled in your AIDP platform account
> for `azure-sora2` to work correctly. Contact the AIDP platform team if unsure.

---

## Quick Start

```bash
cd skills/polym-eval-generate-sora
pip install -r requirements.txt
```

### OpenAI backend (default)

```bash
# T2V
python scripts/generate.py \
  --prompt "A serene lake reflecting autumn trees at sunset" \
  --seconds 8

# I2V (first-frame reference)
python scripts/generate.py \
  --prompt "The scene gently animates" \
  --first-frame /path/to/photo.jpg \
  --seconds 8
```

### AIDP backend (azure-sora2, recommended)

```bash
# T2V
python scripts/generate.py \
  --backend aidp \
  --prompt "A serene lake reflecting autumn trees at sunset" \
  --seconds 5

# I2V
python scripts/generate.py \
  --backend aidp \
  --prompt "The scene gently animates" \
  --first-frame /path/to/photo.jpg \
  --seconds 5

# Use legacy azure-sora (T2V only)
python scripts/generate.py \
  --backend aidp --model azure-sora \
  --prompt "A serene lake" \
  --seconds 5
```

---

## Parameter Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt / -p` | required | Text prompt |
| `--backend` | `openai` | `openai` or `aidp` |
| `--model / -m` | `sora-2` (openai) / `azure-sora2` (aidp) | Model override |
| `--first-frame` | `None` | Reference image path or URL (I2V) |
| `--seconds / -d` | `8` | Duration in seconds |
| `--size / -s` | auto-detected | Explicit size e.g. `1280x720` |
| `--resolution` | `720p` | Resolution tier: `720p` or `1080p` |
| `--output / -o` | `generated/<id>.mp4` | Output path |

---

## Available Models

| Backend | Model | Mode | Notes |
|---------|-------|------|-------|
| openai | `sora-2` | T2V, I2V | Default OpenAI model |
| openai | `sora-2-pro` | T2V, I2V | Higher quality |
| aidp | `azure-sora2` | T2V, I2V | Recommended AIDP model |
| aidp | `azure-sora` | T2V only | Legacy; no I2V support |

---

## Environment Variables

### OpenAI backend
| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `SORA_MODEL` | No | Default model (default: `sora-2`) |
| `TOS_BUCKET` | No | TOS bucket for network URL |
| `TOS_ACCESS_KEY` | No | TOS access key |
| `TOS_SECRET_KEY` | No | TOS secret key |

### AIDP backend
| Variable | Required | Description |
|----------|----------|-------------|
| `AIDP_AK` | Yes | AIDP API Key (ak) |
| `AIDP_HOST` | No | AIDP host (default: `aidp.bytedance.net`) |
| `SORA_AIDP_MODEL` | No | Default AIDP model (default: `azure-sora2`) |

---

## Output

```json
{
  "gen_success": true,
  "gen_video_path": "generated/abc12345.mp4",
  "gen_url": "https://...",
  "gen_elapsed": 120,
  "gen_failed_reason": null
}
```

---

## AIDP API Details

### azure-sora2
- Submit: `POST /sora/v1/videos?ak={ak}` (multipart form-data)
- Status: `GET /sora/v1/videos/{id}?ak={ak}&product=azure_sora2`
- Result: `file_tos_url` field in response, downloaded from `https://tosv.byted.org/obj/{file_tos_url}`
- Supports: T2V and I2V (`input_reference` field)

### azure-sora (legacy)
- Submit: `POST /sora/v2/generate?ak={ak}` (form-data: `height`, `width`, `n_seconds`)
- Status: `POST /sora/v2/fetch?ak={ak}` (body: `{"model":"azure-sora","taskid":"..."}`)
- Supports: T2V only

---

## Dependencies

```
requests
Pillow
python-dotenv
```

Optional (for TOS upload / network URL with OpenAI backend):
```
tos
```

---

## Troubleshooting

- **`OPENAI_API_KEY` not set**: Script will prompt for input and save to `.env`.
- **`AIDP_AK` not set**: Script will prompt for input and save to `.env`.
- **I2V fails with azure-sora**: Not supported; use `azure-sora2` for I2V.
- **azure-sora2 fails**: Ensure "账号粘性功能开关" is enabled in AIDP platform account.
- **TOS download fails**: Check network access to `tosv.byted.org` (ByteDance internal network required).
- **Timeout**: Increase `max_wait` in `aidp_wait_for_completion` / `wait_for_completion`.
