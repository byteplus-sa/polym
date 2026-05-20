---
name: polym-eval-score-image-gemini
description: Score generated images with Gemini via Vertex AI or AIDP. Use for pointwise image grading and pairwise A/B/tie image comparisons.
---

# Score Image with Gemini

Evaluate AI-generated image quality using Google Gemini models.

**Two backends:**
- **vertexai** (default) — Google Cloud Vertex AI via `google-genai` SDK
- **aidp** — ByteDance AIDP model hub via OpenAI-compatible API (model: `gemini-3.1-p`)

**Two evaluation modes:**
- **Pointwise** — Score a single generated image on 6 dimensions (0-5 scale) + overall
- **Pairwise** — Compare two generated images across 9 dimensions (A/B/tie)

## Pre-flight Check

**Vertex AI backend** — verify in `.env`:
- `GOOGLE_CLOUD_PROJECT` (Required — GCP project ID)
- `GOOGLE_CLOUD_LOCATION` (Required — e.g. `us-central1`)
- `GOOGLE_CLOUD_MODEL` (optional, default: `gemini-2.5-flash-preview-05-20`)

Ensure Google Cloud authentication is configured (ADC or service account).

**AIDP backend** — verify in `.env`:
- `AIDP_API_KEY` (Required — ByteDance AIDP API key)
- `AIDP_ENDPOINT` (optional, default: `https://aidp.bytedance.net/api/modelhub/online/v2/crawl`)
- `AIDP_MODEL` (optional, default: `gemini-3.1-p`)

Also install: `pip install openai`

## Quick Start

```bash
# Pointwise via Vertex AI (default)
python skills/polym-eval-score-image-gemini/scripts/evaluate.py \
  --mode pointwise \
  --prompt "A golden retriever sitting in a garden" \
  --image generated.png

# Pointwise via AIDP (gemini-3.1-p)
python skills/polym-eval-score-image-gemini/scripts/evaluate.py \
  --mode pointwise \
  --prompt "A golden retriever sitting in a garden" \
  --image generated.png \
  --backend aidp

# Pointwise with reference images
python skills/polym-eval-score-image-gemini/scripts/evaluate.py \
  --mode pointwise \
  --prompt "Product photo of a red sneaker" \
  --image generated.png \
  --ref-images ref1.jpg ref2.jpg

# Pairwise via AIDP: compare two images
python skills/polym-eval-score-image-gemini/scripts/evaluate.py \
  --mode pairwise \
  --prompt "A futuristic city skyline at sunset" \
  --image-a modelA_output.png \
  --image-b modelB_output.png \
  --backend aidp

# Pairwise with reference images
python skills/polym-eval-score-image-gemini/scripts/evaluate.py \
  --mode pairwise \
  --prompt "Edit: change the dress color to blue" \
  --image-a editA.png \
  --image-b editB.png \
  --ref-images original.jpg
```

## Parameter Reference

| Parameter | CLI Flag | Type | Description | Default |
|-----------|----------|------|-------------|---------|
| `mode` | `--mode` | string | `pointwise` or `pairwise` | **Required** |
| `prompt` | `--prompt, -p` | string | The text prompt used to generate the image | **Required** |
| `backend` | `--backend` | string | `vertexai` or `aidp` | `vertexai` |
| `image` | `--image` | string | Image path (pointwise mode) | Required for pointwise |
| `image_a` | `--image-a` | string | Image A path (pairwise mode) | Required for pairwise |
| `image_b` | `--image-b` | string | Image B path (pairwise mode) | Required for pairwise |
| `ref_images` | `--ref-images` | string[] | Reference image paths (optional) | None |
| `model` | `--model, -m` | string | Gemini model ID | env `GOOGLE_CLOUD_MODEL` / `AIDP_MODEL` |
| `temperature` | `--temperature` | float | Sampling temperature | 0.2 |
| `max_image_size` | `--max-image-size` | int | Max image dimension (auto-resize) | 2048 |

## Pointwise Scoring Dimensions (0-5)

| Dimension | Description |
|-----------|-------------|
| `instruction_follow` | Faithfulness to prompt instructions (subject, count, action, scene, constraints) |
| `structure_accuracy` | Anatomical/structural correctness (proportions, perspective, physics) |
| `content_correctness` | Semantic correctness (attributes, quantities, text content, factual accuracy) |
| `aesthetics` | Composition, color harmony, lighting, overall visual appeal |
| `edit_consistency` | For editing tasks: preserving unmodified regions while applying edits |
| `reference_consistency` | Alignment with reference images (identity, brand, style preservation) |
| `reason` | 1-3 sentence summary of key scoring rationale |

## Pairwise Comparison Dimensions (A/B/tie)

| Dimension | Description |
|-----------|-------------|
| `prompt_fidelity` | Which image better follows the text prompt |
| `structure` | Structural accuracy and physical plausibility |
| `texture` | Detail and material quality |
| `lighting` | Lighting and material realism |
| `artifacts` | Fewer AI-generated defects |
| `usefulness` | Practical usability for real-world applications |
| `factual_consistency` | Alignment with real-world knowledge |
| `text_rendering` | Quality of rendered text in image |
| `edit_consistency` | Correctness of editing operations |

## Features

- **Auto image resizing** — Large images are automatically downscaled to reduce token usage
- **Retry with backoff** — Handles rate limits (429) and empty responses with exponential backoff
- **Fallback image sizes** — Pairwise mode tries progressively smaller images if token limits are hit
- **JSON output** — Structured, machine-readable scoring results
- **Reference images** — Optional context for identity/brand/style consistency evaluation

## Dependencies

```
# Vertex AI backend
google-genai
Pillow
requests
python-dotenv

# AIDP backend (additional)
openai
```

## Troubleshooting

### "GOOGLE_CLOUD_PROJECT is not set" (Vertex AI)
Set `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` in `.env`.

### "AIDP_API_KEY must be set" (AIDP)
Set `AIDP_API_KEY` in `.env`.

### Authentication error (Vertex AI)
Run `gcloud auth application-default login` or configure a service account.

### Empty response / MAX_TOKENS
The script automatically retries with smaller image sizes. If it persists, try `--max-image-size 1024`.

### Rate limit (429)
The script uses exponential backoff. If persistent, reduce request frequency or increase quota.
