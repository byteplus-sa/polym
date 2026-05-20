---
name: polym-eval-score-video-gemini
description: Score generated videos with Gemini via Vertex AI or AIDP. Use for pointwise video grading and pairwise video comparisons.
---

# Score Video with Gemini

Evaluate AI-generated video quality using Google Gemini models.

**Two backends:**
- **vertexai** (default) — Google Cloud Vertex AI via `google-genai` SDK
- **aidp** — ByteDance AIDP model hub via OpenAI-compatible API (model: `gemini-3.1-p`)

**Two evaluation modes:**
- **Pointwise** — Score a single video on 5 instruction-following dimensions (0-2 scale)
- **Pairwise** — Compare two videos across 4 visual dimensions (+ 2 audio dimensions if audio present), scoring 1/0/-1

## Pre-flight Check

**Vertex AI backend** — verify in `.env`:
- `GOOGLE_CLOUD_PROJECT` (Required — GCP project ID)
- `GOOGLE_CLOUD_LOCATION` (Required — e.g. `us-central1`)
- `GOOGLE_CLOUD_MODEL` (optional, default: `gemini-2.5-flash-preview-05-20`)

Ensure:
- Google Cloud authentication is configured (ADC or service account)
- `ffprobe` is available on PATH (for audio detection in pairwise mode)
- OpenCV (`cv2`) is installed (for frame extraction fallback)

**AIDP backend** — verify in `.env`:
- `AIDP_API_KEY` (Required — ByteDance AIDP API key)
- `AIDP_ENDPOINT` (optional, default: `https://aidp.bytedance.net/api/modelhub/online/v2/crawl`)
- `AIDP_MODEL` (optional, default: `gemini-3.1-p`)

Also install: `pip install openai`

AIDP video input: `gemini-3.1-p` supports direct video upload via base64. Falls back to frame extraction automatically if direct upload fails.

## Quick Start

```bash
# Pointwise via Vertex AI (default)
python skills/polym-eval-score-video-gemini/scripts/evaluate.py \
  --mode pointwise \
  --prompt "A cat jumps onto a table and knocks over a cup" \
  --video generated.mp4

# Pointwise via AIDP (gemini-3.1-p)
python skills/polym-eval-score-video-gemini/scripts/evaluate.py \
  --mode pointwise \
  --prompt "A cat jumps onto a table and knocks over a cup" \
  --video generated.mp4 \
  --backend aidp

# Pointwise with reference images
python skills/polym-eval-score-video-gemini/scripts/evaluate.py \
  --mode pointwise \
  --prompt "The character walks forward slowly" \
  --video generated.mp4 \
  --ref-images character_ref.jpg

# Pairwise via AIDP: compare two videos
python skills/polym-eval-score-video-gemini/scripts/evaluate.py \
  --mode pairwise \
  --prompt "A drone shot rising over a coastal city at sunset" \
  --video-a modelA.mp4 \
  --video-b modelB.mp4 \
  --backend aidp

# Pairwise with forced audio evaluation
python skills/polym-eval-score-video-gemini/scripts/evaluate.py \
  --mode pairwise \
  --prompt "A person singing in a park" \
  --video-a modelA.mp4 \
  --video-b modelB.mp4 \
  --has-audio
```

## Parameter Reference

| Parameter | CLI Flag | Type | Description | Default |
|-----------|----------|------|-------------|---------|
| `mode` | `--mode` | string | `pointwise` or `pairwise` | **Required** |
| `prompt` | `--prompt, -p` | string | Text prompt used to generate the video | **Required** |
| `backend` | `--backend` | string | `vertexai` or `aidp` | `vertexai` |
| `video` | `--video` | string | Video path (pointwise mode) | Required for pointwise |
| `video_a` | `--video-a` | string | Video A path (pairwise mode) | Required for pairwise |
| `video_b` | `--video-b` | string | Video B path (pairwise mode) | Required for pairwise |
| `ref_images` | `--ref-images` | string[] | Reference image paths | None |
| `model` | `--model, -m` | string | Gemini model ID | env `GOOGLE_CLOUD_MODEL` / `AIDP_MODEL` |
| `max_frames` | `--max-frames` | int | Max frames to extract | 12 |
| `temperature` | `--temperature` | float | Sampling temperature | 0.2 |
| `has_audio` | `--has-audio` | flag | Force audio evaluation (pairwise) | auto-detect |

## Pointwise Scoring Dimensions (0-2)

Evaluates instruction-following only. Scale: 0 = no/wrong response, 1 = partial, 2 = fully correct.

| Dimension | Description |
|-----------|-------------|
| `subject_action` | Whether the specified subject performs the required action correctly |
| `camera_motion` | Whether camera movements match the prompt (pan/zoom/dolly/etc.) |
| `degree_adverb` | Whether intensity/speed/quantity adverbs are respected (slowly, rapidly, etc.) |
| `environment_scene` | Whether scene/environment description is consistent across the video |
| `temporal_order` | Whether multi-step instructions execute in correct temporal order |

If the prompt does not specify a requirement for a given dimension, score defaults to 2 (no violation).

## Pairwise Comparison — Visual Dimensions (1/0/-1)

| Dimension | Sub-dimensions |
|-----------|---------------|
| `structure_preservation` | subject_consistency, text_consistency, structure_reasonability |
| `visual_quality` | sharpness, style_consistency, interframe_consistency, aesthetics |
| `motion_performance` | motion_amplitude, motion_physical, motion_liveliness |
| `instruction_following` | subject_action, camera_motion, degree_adverb, environment_scene, temporal_order |

## Pairwise Comparison — Audio Dimensions (only when audio detected)

| Dimension | Sub-dimensions |
|-----------|---------------|
| `audio_quality` | clarity, naturalness, speech_intelligibility, sound_realism |
| `av_alignment` | lip_sync_accuracy, action_sound_sync, rhythm_alignment, emotion_alignment |

## Video Input Modes

- **Direct video input** — For Gemini 2.5 Pro / 3 Pro (Vertex AI) and `gemini-3.1-p` (AIDP), the full video file is sent directly (base64 via AIDP `file_url`, native bytes via Vertex AI)
- **Frame extraction** — For other models, intelligent frame sampling using scene detection + optical flow analysis (up to `--max-frames` frames). AIDP also falls back to frame extraction if direct video upload fails.

## Dependencies

```
# Vertex AI backend
google-genai
Pillow
opencv-python
numpy
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

### Frame extraction returns empty
Ensure OpenCV is installed (`pip install opencv-python`) and the video file is valid.

### Audio detection fails
Ensure `ffprobe` (from ffmpeg) is on your PATH. Install: `brew install ffmpeg` or `apt install ffmpeg`.
