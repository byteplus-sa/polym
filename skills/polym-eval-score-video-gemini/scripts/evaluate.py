#!/usr/bin/env python3
"""
Gemini Video Evaluation Skill Script

Evaluate AI-generated videos using Google Gemini models.
Supports two backends:
  - vertexai (default): Google Cloud Vertex AI via google-genai SDK
  - aidp: ByteDance AIDP model hub via OpenAI-compatible API

Supports two evaluation modes:
  - Pointwise: Score a single video on 5 instruction-following dimensions (0-2)
  - Pairwise:  Compare two videos across 4-6 dimensions (1/0/-1)

Supports direct video input (Gemini 2.5/3 Pro on Vertex AI, or gemini-3.1-p on AIDP),
with frame extraction fallback for other models.

Usage:
    # Pointwise via Vertex AI (default)
    python evaluate.py --mode pointwise --prompt "A cat jumps" --video gen.mp4

    # Pointwise via AIDP
    python evaluate.py --mode pointwise --prompt "A cat jumps" --video gen.mp4 --backend aidp

    # Pairwise via AIDP
    python evaluate.py --mode pairwise --prompt "A cat jumps" --video-a a.mp4 --video-b b.mp4 --backend aidp
"""

import os
import sys
import io
import json
import time
import base64
import subprocess
import argparse
import logging
from typing import List, Tuple, Optional
from pathlib import Path

import numpy as np
from PIL import Image
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

try:
    import cv2
except ImportError:
    print("WARNING: opencv-python not installed. Frame extraction will not work.")
    print("Install with: pip install opencv-python")
    cv2 = None

# Vertex AI backend
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# AIDP backend (OpenAI-compatible)
try:
    from openai import AzureOpenAI as AzureOpenAIClient
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============================================
# .env management
# ============================================
SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_DIR / ".env"

VERTEXAI_REQUIRED_ENV_VARS = {
    "GOOGLE_CLOUD_PROJECT": {
        "description": "Google Cloud Project ID",
        "help": "Your GCP project ID for Vertex AI",
    },
    "GOOGLE_CLOUD_LOCATION": {
        "description": "Vertex AI Location",
        "help": "e.g. us-central1",
    },
}

AIDP_REQUIRED_ENV_VARS = {
    "AIDP_API_KEY": {
        "description": "AIDP API Key",
        "help": "API key for ByteDance AIDP model hub",
    },
}

# AIDP defaults
AIDP_ENDPOINT = "https://aidp.bytedance.net/api/modelhub/online/v2/crawl"
AIDP_API_VERSION = "2024-03-01-preview"
AIDP_DEFAULT_MODEL = "gemini-3.1-p"


def _load_env():
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)
    else:
        load_dotenv()


def _append_env_var(key: str, value: str):
    lines = []
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    os.environ[key] = value


def check_env(backend: str = "vertexai"):
    required = VERTEXAI_REQUIRED_ENV_VARS if backend == "vertexai" else AIDP_REQUIRED_ENV_VARS
    missing = []
    for var, info in required.items():
        if not os.getenv(var, "").strip():
            missing.append((var, info))
    if not missing:
        return True

    print(f"\n{'=' * 60}")
    print(f"Missing required environment variables (.env: {ENV_PATH})")
    print(f"{'=' * 60}")
    for var, info in missing:
        print(f"\n  {var}: {info['description']}")
        print(f"    {info['help']}")

    for var, info in missing:
        while True:
            value = input(f"\nEnter {info['description']} ({var})\n  [or 'skip' to abort]: ").strip()
            if value.lower() == "skip":
                print(f"\nAborted. Set {var} manually in {ENV_PATH}")
                return False
            if value:
                _append_env_var(var, value)
                print(f"  Saved {var} to {ENV_PATH}")
                break
            print("  Value cannot be empty.")

    print(f"\n{'=' * 60}")
    print("All required environment variables configured!")
    print(f"{'=' * 60}\n")
    return True


_load_env()

# ============================================
# Retry config
# ============================================
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2

# ============================================
# Evaluation Prompts (English)
# ============================================

VIDEO_POINTWISE_PROMPT = """You are a professional video evaluation system. You excel at rigorously scoring generated videos based on their actual visual performance. Only evaluate the "generated content" itself — do not reference a target/ground-truth video, and do not penalize based on reference frames (they are only for understanding semantic style).

Given a generated video (as a sequence of frames in temporal order), optional reference images, and a text prompt, evaluate ONLY the "Instruction Following" dimension across the following 5 sub-dimensions, scoring each 0/1/2:

Scoring scale (must be strictly followed):
- 0: No response or clearly wrong response
- 1: Partial response (some response but incomplete, or with obvious deviations)
- 2: Full response (clear, stable, fully consistent with the instruction)

If the prompt does NOT explicitly require something for a given sub-dimension, score it as 2 (treated as no violation).

The 5 sub-dimensions to score (against the prompt):
1) Subject Action Consistency (subject_action)
   - Whether the specified subject's action is correctly driven; focus on whether the subject is correctly identified and action elements match.
2) Camera Motion Consistency (camera_motion)
   - Whether required camera movements are executed (push/pull/pan/dolly/zoom/etc.); if the prompt does not specify camera motion, score 2.
3) Degree Adverb Consistency (degree_adverb)
   - Whether intensity/speed/quantity degree adverbs are correctly reflected (e.g., slowly/rapidly, slightly/dramatically, few/many).
4) Environment/Scene Description Consistency (environment_scene)
   - Whether the scene/environment description is matched, especially maintaining consistency during camera transitions or background changes.
5) Temporal Order Consistency (temporal_order)
   - Whether multi-step instructions are executed in the correct temporal order (sequence, stages, steps).

Strict output requirements (output ONLY this JSON, keys and types must match exactly, no explanations or extra fields):
{{
  "subject_action": 0|1|2,
  "camera_motion": 0|1|2,
  "degree_adverb": 0|1|2,
  "environment_scene": 0|1|2,
  "temporal_order": 0|1|2
}}

You will now receive the video frames (GEN) and the text prompt. Evaluate based solely on visual and semantic content, ignoring audio. Output JSON now.
Text prompt: \"\"\"{prompt}\"\"\"
"""

VIDEO_POINTWISE_SUFFIX = """Task and order (strictly follow):
1) Generated video frames GEN_F1..GEN_Fn (in temporal order)
2) Reference images REF_1..REF_K (may be 0)
Evaluate GEN and output JSON only. Frame info: GEN={n_gen}; REF={n_refs}."""


VIDEO_PAIRWISE_PROMPT_VIDEO_ONLY = """
You are a professional video generation quality comparison system.
Compare two generated videos (A and B) and provide dimension-wise preference judgments.

**Note: These videos contain NO audio. Evaluate ONLY visual aspects.**

Compare across **4 main dimensions**:
- "1" = Video A is better than Video B
- "0" = Both videos are comparable (no meaningful difference)
- "-1" = Video B is better than Video A

For each main dimension:
1. Output an overall judgment (1, 0, or -1)
2. Output specific reasons for each sub-dimension
3. If the main dimension score is 1 or -1, mark the differing sub-dimensions accordingly

---

## Dimension Definitions

### 1. Structure Preservation (structure_preservation)
Evaluate whether the video preserves subject identity and structural integrity.

1. subject_consistency
   - Subject appearance, texture, logo, and identity remain consistent
   - No deformation, melting, abnormal changes, or identity drift

2. text_consistency
   - Text on subject (logos, product text) remains clear and stable
   - No sudden disappearance or distortion

3. structure_reasonability
   - Human/object proportions follow visual norms and physics
   - No collapse, distortion, penetration, or abnormal deformation

---

### 2. Visual Quality (visual_quality)
Evaluate overall image quality.

1. sharpness
   - Clear, detailed frames
   - No resolution degradation relative to first frame

2. style_consistency
   - Color tone, brightness, contrast remain stable
   - No style or color grading shifts

3. interframe_consistency
   - Smooth frame transitions
   - No flicker, black frames, scaling jumps, or corruption

4. aesthetics
   - Overall visual appeal
   - Composition, color harmony, and rhythm

---

### 3. Motion Performance (motion_performance)
Evaluate motion quality itself (NOT whether it follows the prompt).

1. motion_amplitude
   - Motion scale is appropriate for the scene
   - Static != disadvantage, motion != advantage

2. motion_physical
   - Motion follows physics and context
   - No floating, teleportation, clipping, or sudden disappearance

3. motion_liveliness
   - Motion is smooth and natural
   - No stiff, robotic, or mechanical movement

---

### 4. Instruction Following (instruction_following)
Evaluate how well the video follows the text prompt instructions.

1. subject_action_consistency
   - Correct subject performs the required actions
   - No wrong subject moving while intended subject stays static

2. camera_motion_consistency
   - Camera movements (pan, zoom, tracking, dolly, rotation) match the prompt
   - No missing or contradictory camera motion

3. degree_adverb_consistency
   - Degree adverbs (slowly, rapidly, slightly, dramatically) are respected
   - Motion speed and intensity match the description

4. environment_scene_consistency
   - Scene, background, lighting, and atmosphere match the prompt
   - Scene changes and transitions are correctly reflected

5. temporal_order_consistency
   - Multi-step instructions are executed in the correct temporal order
   - No step skipping, reversal, or merging

---

## Judgment Guidelines

**Key Principles:**
1. Identify meaningful differences — do not default to Same
2. High visual quality does NOT compensate for poor instruction following
3. Static vs motion is not inherently better or worse
4. When differences exist, make a clear decision (1 or -1)
5. Use 0 only when videos are truly comparable

**Critical Issues (Must Penalize):**
- Subject identity change
- Object disappearance or sudden appearance
- Physics violations
- Structure collapse or distortion
- Clear instruction-following failures

---

## Output Format (Strict JSON only)

{{
  "structure_preservation": {{
    "score": 1|0|-1,
    "reason": {{
      "subject_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "text_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "structure_reasonability": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "visual_quality": {{
    "score": 1|0|-1,
    "reason": {{
      "sharpness": {{"score": 1|0|-1, "reason": "brief reason"}},
      "style_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "interframe_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "aesthetics": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "motion_performance": {{
    "score": 1|0|-1,
    "reason": {{
      "motion_amplitude": {{"score": 1|0|-1, "reason": "brief reason"}},
      "motion_physical": {{"score": 1|0|-1, "reason": "brief reason"}},
      "motion_liveliness": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "instruction_following": {{
    "score": 1|0|-1,
    "reason": {{
      "subject_action_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "camera_motion_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "degree_adverb_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "environment_scene_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "temporal_order_consistency": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }}
}}

---

You will receive two video frame sequences (Video A and Video B) and a text prompt:
Text prompt: \"\"\"{prompt}\"\"\"
"""

VIDEO_PAIRWISE_PROMPT_WITH_AUDIO = """
You are a professional video generation quality comparison system.
Compare two generated videos (A and B) with audio and provide dimension-wise preference judgments.

**Note: These videos CONTAIN audio. Evaluate visual quality, audio quality, and audio-visual alignment.**

Compare across **6 main dimensions**:
- "1" = Video A is better than Video B
- "0" = Both videos are comparable (no meaningful difference)
- "-1" = Video B is better than Video A

---

## Visual Dimensions

### 1. Structure Preservation (structure_preservation)
Evaluate whether the video preserves subject identity and structural integrity.

1. subject_consistency
   - Subject appearance, texture, logo, and identity remain consistent
   - No deformation, melting, abnormal changes, or identity drift

2. text_consistency
   - Text on subject (logos, product text) remains clear and stable
   - No sudden disappearance or distortion

3. structure_reasonability
   - Human/object proportions follow visual norms and physics
   - No collapse, distortion, penetration, or abnormal deformation

---

### 2. Visual Quality (visual_quality)
Evaluate overall image quality.

1. sharpness
   - Clear, detailed frames
   - No resolution degradation relative to first frame

2. style_consistency
   - Color tone, brightness, contrast remain stable
   - No style or color grading shifts

3. interframe_consistency
   - Smooth frame transitions
   - No flicker, black frames, scaling jumps, or corruption

4. aesthetics
   - Overall visual appeal
   - Composition, color harmony, and rhythm

---

### 3. Motion Performance (motion_performance)
Evaluate motion quality itself (NOT whether it follows the prompt).

1. motion_amplitude
   - Motion scale is appropriate for the scene
   - Static != disadvantage, motion != advantage

2. motion_physical
   - Motion follows physics and context
   - No floating, teleportation, clipping, or sudden disappearance

3. motion_liveliness
   - Motion is smooth and natural
   - No stiff, robotic, or mechanical movement

---

### 4. Instruction Following (instruction_following)
Evaluate how well the video follows the text prompt instructions.

1. subject_action_consistency
   - Correct subject performs the required actions
   - No wrong subject moving while intended subject stays static

2. camera_motion_consistency
   - Camera movements (pan, zoom, tracking, dolly, rotation) match the prompt
   - No missing or contradictory camera motion

3. degree_adverb_consistency
   - Degree adverbs (slowly, rapidly, slightly, dramatically) are respected
   - Motion speed and intensity match the description

4. environment_scene_consistency
   - Scene, background, lighting, and atmosphere match the prompt
   - Scene changes and transitions are correctly reflected

5. temporal_order_consistency
   - Multi-step instructions are executed in the correct temporal order
   - No step skipping, reversal, or merging

---

## Audio Dimensions

### 5. Audio Quality (audio_quality)

1. clarity
   - Clear audio without distortion or noise

2. naturalness
   - Natural timbre and dynamics

3. speech_intelligibility
   - Speech is clear and understandable (if present)

4. sound_realism
   - Sounds match the scene context

---

### 6. AV Alignment (av_alignment)

1. lip_sync_accuracy
   - Lip movements match speech (if applicable)

2. action_sound_sync
   - Visual actions align with sound effects

3. rhythm_alignment
   - Audio rhythm matches visual pacing

4. emotion_alignment
   - Emotional tone of audio matches visuals

---

## Judgment Guidelines

1. Instruction-following failures must be penalized even if audio is good
2. Audio quality does not compensate for visual or instruction errors
3. When differences exist, make a clear decision (1 or -1)

---

## Output Format (Strict JSON only)

{{
  "structure_preservation": {{
    "score": 1|0|-1,
    "reason": {{
      "subject_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "text_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "structure_reasonability": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "visual_quality": {{
    "score": 1|0|-1,
    "reason": {{
      "sharpness": {{"score": 1|0|-1, "reason": "brief reason"}},
      "style_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "interframe_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "aesthetics": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "motion_performance": {{
    "score": 1|0|-1,
    "reason": {{
      "motion_amplitude": {{"score": 1|0|-1, "reason": "brief reason"}},
      "motion_physical": {{"score": 1|0|-1, "reason": "brief reason"}},
      "motion_liveliness": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "instruction_following": {{
    "score": 1|0|-1,
    "reason": {{
      "subject_action_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "camera_motion_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "degree_adverb_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "environment_scene_consistency": {{"score": 1|0|-1, "reason": "brief reason"}},
      "temporal_order_consistency": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "audio_quality": {{
    "score": 1|0|-1,
    "reason": {{
      "clarity": {{"score": 1|0|-1, "reason": "brief reason"}},
      "naturalness": {{"score": 1|0|-1, "reason": "brief reason"}},
      "speech_intelligibility": {{"score": 1|0|-1, "reason": "brief reason"}},
      "sound_realism": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }},
  "av_alignment": {{
    "score": 1|0|-1,
    "reason": {{
      "lip_sync_accuracy": {{"score": 1|0|-1, "reason": "brief reason"}},
      "action_sound_sync": {{"score": 1|0|-1, "reason": "brief reason"}},
      "rhythm_alignment": {{"score": 1|0|-1, "reason": "brief reason"}},
      "emotion_alignment": {{"score": 1|0|-1, "reason": "brief reason"}}
    }}
  }}
}}

---

You will receive two videos (A and B) with audio tracks and a text prompt:
Text prompt: \"\"\"{prompt}\"\"\"
"""

VIDEO_PAIRWISE_SUFFIX = """Task and order (strictly follow):
1) Video A frames: A_F1..A_Fn (in temporal order)
2) Video B frames: B_F1..B_Fn (in temporal order)
3) (Optional) Reference images REF_1..REF_K (K may be 0, for semantic/style context only, not for ranking)
Compare A and B, output JSON only. Frame info: A={n_gen_a}; B={n_gen_b}; REF={n_refs}."""


# ============================================
# Prompt builders
# ============================================
def build_pointwise_prompt(prompt: str, n_gen: int, n_refs: int) -> str:
    return VIDEO_POINTWISE_PROMPT.format(prompt=prompt) + "\n" + VIDEO_POINTWISE_SUFFIX.format(n_gen=n_gen, n_refs=n_refs)


def build_pairwise_prompt(prompt: str, n_gen_a: int, n_gen_b: int, n_refs: int = 0,
                          has_audio: bool = False) -> str:
    if has_audio:
        base = VIDEO_PAIRWISE_PROMPT_WITH_AUDIO.format(prompt=prompt)
    else:
        base = VIDEO_PAIRWISE_PROMPT_VIDEO_ONLY.format(prompt=prompt)
    return base + "\n" + VIDEO_PAIRWISE_SUFFIX.format(n_gen_a=n_gen_a, n_gen_b=n_gen_b, n_refs=n_refs)


# ============================================
# JSON extraction helper
# ============================================
def extract_json(text: str) -> str:
    """Strip markdown code fences if present, returning clean JSON."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


# ============================================
# Audio detection
# ============================================
def has_audio_stream(video_path: str) -> bool:
    """Detect whether a video file contains an audio stream using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0 and result.stdout.strip() == "audio"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning(f"Cannot detect audio stream for {video_path}: {e}")
        return False


# ============================================
# Video frame extraction
# ============================================
def video_to_frames(
    video_path: str,
    max_frames: int = 12,
    target_size: Optional[Tuple[int, int]] = None,
) -> List[Image.Image]:
    """
    Extract representative frames from a video using scene detection + optical flow + uniform sampling.
    Returns a list of PIL Images.
    """
    if cv2 is None:
        logger.error("OpenCV not available. Cannot extract frames.")
        return []

    scene_thresh = 0.28
    motion_percentile = 85.0
    analyze_stride = 3
    max_analyze_frames = 600
    time_budget_sec = 8.0

    t0 = time.time()
    cap = cv2.VideoCapture(video_path)
    sel_frame_indices: List[int] = []

    if not cap.isOpened():
        logger.error(f"Cannot open video file: {video_path}")
        return []

    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = cap.get(cv2.CAP_PROP_FPS)
        logger.debug(f"Video info: {video_path}, total_frames={total}, FPS={fps}")

        if total <= 0:
            total = 10 ** 9

        ret, prev = cap.read()
        if not ret:
            logger.error(f"Cannot read first frame: {video_path}")
            return []

        prev_hsv = cv2.cvtColor(prev, cv2.COLOR_BGR2HSV)
        prev_hist = cv2.calcHist([prev_hsv], [0, 1], None, [50, 50], [0, 180, 0, 256])
        cv2.normalize(prev_hist, prev_hist)
        prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY)

        scores = []
        frame_idx = 1
        analyzed = 0

        while True:
            if time.time() - t0 > time_budget_sec:
                break
            if analyzed >= max_analyze_frames:
                break

            for _ in range(analyze_stride):
                ret, frame = cap.read()
                frame_idx += 1
                if not ret:
                    break
            if not ret:
                break

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 50], [0, 180, 0, 256])
            cv2.normalize(hist, hist)
            hist_diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
            )
            mag = float(np.linalg.norm(flow, axis=2).mean())

            score = hist_diff * 10.0 + mag
            scores.append((frame_idx, score))
            analyzed += 1

            prev_gray = gray
            prev_hist = hist

            if frame_idx >= total:
                break

        if not scores:
            pil_img = Image.fromarray(cv2.cvtColor(prev, cv2.COLOR_BGR2RGB))
            if target_size:
                pil_img = pil_img.resize(target_size, Image.LANCZOS)
            return [pil_img]

        scores_arr = np.array(scores, dtype=np.float32)
        scene_thr_abs = scene_thresh * 10.0
        scene_changes = np.where(scores_arr[:, 1] > scene_thr_abs)[0].tolist()

        perc = float(np.clip(motion_percentile, 50.0, 99.9))
        motion_thr = np.percentile(scores_arr[:, 1], perc)
        motion_peaks = np.where(scores_arr[:, 1] >= motion_thr)[0].tolist()

        uniform_points = np.linspace(0, len(scores_arr) - 1, max_frames, dtype=int).tolist()
        sel_rows = sorted(set(scene_changes + motion_peaks + uniform_points))[:max_frames]
        sel_frame_indices = [int(scores_arr[r, 0]) for r in sel_rows]

    finally:
        cap.release()

    cap2 = cv2.VideoCapture(video_path)
    pil_frames: List[Image.Image] = []
    try:
        for idx in sel_frame_indices:
            cap2.set(cv2.CAP_PROP_POS_FRAMES, max(idx - 1, 0))
            ret, frame = cap2.read()
            if not ret:
                continue
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            if target_size:
                img = img.resize(target_size, Image.LANCZOS)
            pil_frames.append(img)
    finally:
        cap2.release()

    return pil_frames


# ============================================
# Image/video part helpers — Vertex AI
# ============================================
def text_to_part(text: str):
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    return types.Part(text=text)


def pil_to_part(img_file, fmt="png", quality=90):
    """Convert PIL image or image path to Gemini Part (Vertex AI)."""
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    if isinstance(img_file, str):
        img = Image.open(img_file)
    else:
        img = img_file
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format=fmt, quality=quality)
    return types.Part(
        inline_data=types.Blob(
            mime_type=f"image/{fmt}",
            data=buf.getvalue(),
        )
    )


def video_to_part(video_path: str):
    """Convert a video file to a Gemini Part for direct video input (Vertex AI)."""
    with open(video_path, "rb") as f:
        video_bytes = f.read()

    ext = video_path.lower()
    if ext.endswith(".mp4"):
        mime = "video/mp4"
    elif ext.endswith(".mov"):
        mime = "video/quicktime"
    elif ext.endswith(".avi"):
        mime = "video/x-msvideo"
    elif ext.endswith(".webm"):
        mime = "video/webm"
    else:
        mime = "video/mp4"

    return types.Part.from_bytes(data=video_bytes, mime_type=mime)


def supports_direct_video_vertexai(model_name: str) -> bool:
    """Check if model supports direct video input on Vertex AI."""
    name = model_name.lower()
    return "gemini-2.5-pro" in name or "gemini-3-pro" in name


# ============================================
# Image/video helpers — AIDP (base64)
# ============================================
def pil_to_base64(img_file, fmt="jpeg", quality=85, max_size: int = 1024) -> str:
    """Convert PIL image or path to base64 data URL for AIDP."""
    if isinstance(img_file, str):
        img = Image.open(img_file)
    else:
        img = img_file
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format=fmt, quality=quality)
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/{fmt};base64,{b64}"


def video_to_base64_content(video_path: str) -> dict:
    """Convert a video file to an AIDP file_url content item (base64)."""
    ext = video_path.lower()
    if ext.endswith(".mp4"):
        mime = "video/mp4"
    elif ext.endswith(".mov"):
        mime = "video/quicktime"
    elif ext.endswith(".webm"):
        mime = "video/webm"
    else:
        mime = "video/mp4"

    with open(video_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return {
        "type": "file_url",
        "file_url": {
            "mime_type": mime,
            "url": f"data:{mime};base64,{b64}",
        },
    }


def supports_direct_video_aidp(model_name: str) -> bool:
    """Check if model supports direct video input on AIDP."""
    name = model_name.lower()
    # gemini-3.1-p and other Pro-class models support direct video
    return "gemini-3" in name or "gemini-2.5-pro" in name


# ============================================
# OpenAI message builders for AIDP (video)
# ============================================
def build_openai_messages_pointwise_frames(prompt_text: str, gen_frames: List[Image.Image],
                                            ref_images=None, frame_size: int = 768) -> list:
    """Build AIDP messages for pointwise evaluation using extracted frames."""
    user_text = build_pointwise_prompt(
        prompt=prompt_text, n_gen=len(gen_frames), n_refs=len(ref_images or [])
    )
    content = [{"type": "text", "text": user_text}]
    for fr in gen_frames:
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(fr, max_size=frame_size)},
        })
    for ref in (ref_images or []):
        if isinstance(ref, str):
            ref = Image.open(ref)
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(ref, max_size=frame_size)},
        })
    return [{"role": "user", "content": content}]


def build_openai_messages_pointwise_direct(prompt_text: str, gen_video_path: str,
                                            ref_images=None) -> list:
    """Build AIDP messages for pointwise evaluation using direct video input."""
    user_text = build_pointwise_prompt(prompt=prompt_text, n_gen=0, n_refs=len(ref_images or []))
    content = [{"type": "text", "text": user_text}]
    content.append(video_to_base64_content(gen_video_path))
    for ref in (ref_images or []):
        if isinstance(ref, str):
            ref = Image.open(ref)
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(ref)},
        })
    return [{"role": "user", "content": content}]


def build_openai_messages_pairwise_frames(prompt_text: str,
                                           gen_frames_a: List[Image.Image],
                                           gen_frames_b: List[Image.Image],
                                           ref_images=None, has_audio: bool = False,
                                           frame_size: int = 768) -> list:
    """Build AIDP messages for pairwise evaluation using extracted frames."""
    user_text = build_pairwise_prompt(
        prompt=prompt_text,
        n_gen_a=len(gen_frames_a), n_gen_b=len(gen_frames_b),
        n_refs=len(ref_images or []), has_audio=has_audio,
    )
    content = [{"type": "text", "text": user_text}]
    for fr in gen_frames_a:
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(fr, max_size=frame_size)},
        })
    for fr in gen_frames_b:
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(fr, max_size=frame_size)},
        })
    for ref in (ref_images or []):
        if isinstance(ref, str):
            ref = Image.open(ref)
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(ref, max_size=frame_size)},
        })
    return [{"role": "user", "content": content}]


def build_openai_messages_pairwise_direct(prompt_text: str, gen_video_path_a: str,
                                           gen_video_path_b: str, ref_images=None,
                                           has_audio: bool = False) -> list:
    """Build AIDP messages for pairwise evaluation using direct video input."""
    user_text = build_pairwise_prompt(
        prompt=prompt_text, n_gen_a=0, n_gen_b=0,
        n_refs=len(ref_images or []), has_audio=has_audio,
    )
    content = [{"type": "text", "text": user_text}]
    content.append(video_to_base64_content(gen_video_path_a))
    content.append(video_to_base64_content(gen_video_path_b))
    for ref in (ref_images or []):
        if isinstance(ref, str):
            ref = Image.open(ref)
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(ref)},
        })
    return [{"role": "user", "content": content}]


# ============================================
# Vertex AI client & call
# ============================================
def get_vertexai_client():
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    if not project or not location:
        raise ValueError("GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set in .env")
    return genai.Client(vertexai=True, project=project, location=location)


# Keep alias for backwards compatibility
get_client = get_vertexai_client


def gemini_call_with_retry(client, model_name, contents, config, max_retries=MAX_RETRIES):
    """Vertex AI Gemini API call with retry and exponential backoff."""
    last_error = None

    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )

            if not resp or not resp.text or not resp.text.strip():
                error_detail = "Empty response"
                if hasattr(resp, "candidates") and resp.candidates:
                    for candidate in resp.candidates:
                        if hasattr(candidate, "finish_reason"):
                            error_detail += f" | finish_reason: {candidate.finish_reason}"

                logger.warning(f"Gemini returned empty: {error_detail} (attempt {attempt + 1}/{max_retries})")
                last_error = error_detail
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))
                continue

            return resp.text

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Gemini API error: {error_msg} (attempt {attempt + 1}/{max_retries})")
            last_error = error_msg

            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                time.sleep(RETRY_DELAY_BASE * (2 ** attempt))
            else:
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))

    logger.error(f"Gemini API call failed after {max_retries} retries. Last error: {last_error}")
    return None


# ============================================
# AIDP client & call
# ============================================
def get_aidp_client():
    if not OPENAI_AVAILABLE:
        raise ImportError("openai not installed. Run: pip install openai")
    api_key = os.environ.get("AIDP_API_KEY")
    if not api_key:
        raise ValueError("AIDP_API_KEY must be set in .env")
    endpoint = os.environ.get("AIDP_ENDPOINT", AIDP_ENDPOINT)
    return AzureOpenAIClient(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=AIDP_API_VERSION,
    )


def aidp_call_with_retry(client, model_name: str, messages: list, temperature: float = 0.2,
                          max_tokens: int = 16384, max_retries: int = MAX_RETRIES,
                          session_id: str = None):
    """AIDP OpenAI-compatible API call with retry and exponential backoff.

    session_id: when set, adds the AIDP sticky-session header so all requests with the
    same session_id route to the same underlying GCP account, enabling Gemini implicit
    prompt cache (GCP Gemini caches automatically; requires >2048 prompt tokens, TTL 5min).
    The header value must be a JSON *string*: extra: {"session_id": "<id>"}
    """
    extra_headers = {}
    if session_id:
        extra_headers["extra"] = json.dumps({"session_id": session_id})

    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=False,
                max_tokens=max_tokens,
                temperature=temperature,
                extra_headers=extra_headers if extra_headers else None,
            )
            text = response.choices[0].message.content
            if not text or not text.strip():
                logger.warning(f"AIDP returned empty response (attempt {attempt + 1}/{max_retries})")
                last_error = "Empty response"
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))
                continue
            return text

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"AIDP API error: {error_msg} (attempt {attempt + 1}/{max_retries})")
            last_error = error_msg

            if "429" in error_msg or "rate" in error_msg.lower() or "quota" in error_msg.lower():
                time.sleep(RETRY_DELAY_BASE * (2 ** attempt))
            else:
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))

    logger.error(f"AIDP API call failed after {max_retries} retries. Last error: {last_error}")
    return None


# ============================================
# Evaluation functions
# ============================================
def eval_pointwise(client, model_name, prompt_text, gen_video_path, ref_images=None,
                   max_frames=12, temperature=0.2, backend="vertexai", session_id: str = None):
    """
    Pointwise video evaluation: score a single video on 5 instruction-following dimensions.

    Returns:
        Parsed JSON dict with scores, or None on failure.
    """
    try:
        if backend == "aidp":
            use_direct = supports_direct_video_aidp(model_name) and os.path.exists(gen_video_path)

            if use_direct:
                logger.info(f"AIDP: using direct video input (model: {model_name})")
                messages = build_openai_messages_pointwise_direct(
                    prompt_text, gen_video_path, ref_images=ref_images
                )
                result = aidp_call_with_retry(client, model_name, messages, temperature=temperature,
                                              session_id=session_id)

                if result is None:
                    logger.warning("AIDP direct video failed, falling back to frame extraction")
                    use_direct = False

            if not use_direct:
                logger.info(f"AIDP: using frame extraction (model: {model_name})")
                gen_frames = video_to_frames(gen_video_path, max_frames=max_frames)
                if not gen_frames:
                    logger.error(f"Frame extraction failed: {gen_video_path}")
                    return None
                logger.info(f"Extracted {len(gen_frames)} frames")
                messages = build_openai_messages_pointwise_frames(
                    prompt_text, gen_frames, ref_images=ref_images
                )
                result = aidp_call_with_retry(client, model_name, messages, temperature=temperature,
                                              session_id=session_id)

        else:
            use_direct = supports_direct_video_vertexai(model_name) and os.path.exists(gen_video_path)

            if use_direct:
                logger.info(f"Vertex AI: using direct video input (model: {model_name})")
                user_text = build_pointwise_prompt(prompt=prompt_text, n_gen=0, n_refs=len(ref_images or []))
                contents = [text_to_part(user_text), video_to_part(gen_video_path)]
                for ref in (ref_images or []):
                    contents.append(pil_to_part(ref))
            else:
                logger.info(f"Vertex AI: using frame extraction (model: {model_name})")
                gen_frames = video_to_frames(gen_video_path, max_frames=max_frames)
                if not gen_frames:
                    logger.error(f"Frame extraction failed: {gen_video_path}")
                    return None

                frame_size = gen_frames[0].size
                logger.info(f"Extracted {len(gen_frames)} frames ({frame_size[0]}x{frame_size[1]})")

                user_text = build_pointwise_prompt(
                    prompt=prompt_text, n_gen=len(gen_frames), n_refs=len(ref_images or [])
                )
                contents = [text_to_part(user_text)]
                for fr in gen_frames:
                    contents.append(pil_to_part(fr))
                for ref in (ref_images or []):
                    if isinstance(ref, str):
                        ref = Image.open(ref)
                    if ref.size != frame_size:
                        ref = ref.resize(frame_size, Image.LANCZOS)
                    contents.append(pil_to_part(ref))

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=temperature,
                max_output_tokens=8192,
            )
            result = gemini_call_with_retry(client, model_name, contents, config)

        if result:
            try:
                return json.loads(extract_json(result))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON, returning raw text")
                return {"raw_response": result}
        return None

    except Exception as e:
        logger.error(f"Pointwise evaluation failed: {e}")
        return None


def eval_pairwise(client, model_name, prompt_text, gen_video_path_a, gen_video_path_b,
                  ref_images=None, max_frames=12, temperature=0.2, has_audio=None,
                  backend="vertexai", session_id: str = None):
    """
    Pairwise video evaluation: compare two videos.

    Returns:
        Parsed JSON dict with dimension judgments, or None on failure.
    """
    try:
        # Auto-detect audio
        if has_audio is None:
            audio_a = has_audio_stream(gen_video_path_a) if gen_video_path_a else False
            audio_b = has_audio_stream(gen_video_path_b) if gen_video_path_b else False
            has_audio = audio_a and audio_b
            if has_audio:
                logger.info("Audio detected in both videos, using audio evaluation prompt")

        if backend == "aidp":
            use_direct = (
                supports_direct_video_aidp(model_name)
                and os.path.exists(gen_video_path_a)
                and os.path.exists(gen_video_path_b)
            )

            if use_direct:
                logger.info(f"AIDP: using direct video input (model: {model_name})")
                messages = build_openai_messages_pairwise_direct(
                    prompt_text, gen_video_path_a, gen_video_path_b,
                    ref_images=ref_images, has_audio=has_audio,
                )
                result = aidp_call_with_retry(client, model_name, messages, temperature=temperature,
                                              session_id=session_id)

                if result is None:
                    logger.warning("AIDP direct video failed, falling back to frame extraction")
                    use_direct = False

            if not use_direct:
                logger.info(f"AIDP: using frame extraction (model: {model_name})")
                gen_frames_a = video_to_frames(gen_video_path_a, max_frames=max_frames)
                gen_frames_b = video_to_frames(gen_video_path_b, max_frames=max_frames)
                if not gen_frames_a:
                    logger.error(f"Frame extraction failed for video A: {gen_video_path_a}")
                    return None
                if not gen_frames_b:
                    logger.error(f"Frame extraction failed for video B: {gen_video_path_b}")
                    return None
                logger.info(f"Extracted A={len(gen_frames_a)} frames, B={len(gen_frames_b)} frames")
                messages = build_openai_messages_pairwise_frames(
                    prompt_text, gen_frames_a, gen_frames_b,
                    ref_images=ref_images, has_audio=has_audio,
                )
                result = aidp_call_with_retry(client, model_name, messages, temperature=temperature,
                                              session_id=session_id)

        else:
            use_direct = (
                supports_direct_video_vertexai(model_name)
                and os.path.exists(gen_video_path_a)
                and os.path.exists(gen_video_path_b)
            )

            if use_direct:
                logger.info(f"Vertex AI: using direct video input (model: {model_name})")
                user_text = build_pairwise_prompt(
                    prompt=prompt_text, n_gen_a=0, n_gen_b=0,
                    n_refs=len(ref_images or []), has_audio=has_audio,
                )
                contents = [text_to_part(user_text)]
                contents.append(video_to_part(gen_video_path_a))
                contents.append(video_to_part(gen_video_path_b))
                for ref in (ref_images or []):
                    if isinstance(ref, str):
                        ref = Image.open(ref)
                    contents.append(pil_to_part(ref))
            else:
                logger.info(f"Vertex AI: using frame extraction (model: {model_name})")
                gen_frames_a = video_to_frames(gen_video_path_a, max_frames=max_frames)
                gen_frames_b = video_to_frames(gen_video_path_b, max_frames=max_frames)

                if not gen_frames_a:
                    logger.error(f"Frame extraction failed for video A: {gen_video_path_a}")
                    return None
                if not gen_frames_b:
                    logger.error(f"Frame extraction failed for video B: {gen_video_path_b}")
                    return None

                frame_size_a = gen_frames_a[0].size
                logger.info(f"Extracted A={len(gen_frames_a)} frames, B={len(gen_frames_b)} frames")

                user_text = build_pairwise_prompt(
                    prompt=prompt_text,
                    n_gen_a=len(gen_frames_a), n_gen_b=len(gen_frames_b),
                    n_refs=len(ref_images or []), has_audio=has_audio,
                )
                contents = [text_to_part(user_text)]
                for fr in gen_frames_a:
                    contents.append(pil_to_part(fr))
                for fr in gen_frames_b:
                    contents.append(pil_to_part(fr))
                for ref in (ref_images or []):
                    if isinstance(ref, str):
                        ref = Image.open(ref)
                    if ref.size != frame_size_a:
                        ref = ref.resize(frame_size_a, Image.LANCZOS)
                    contents.append(pil_to_part(ref))

            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=temperature,
                top_p=1,
                max_output_tokens=16384,
            )
            result = gemini_call_with_retry(client, model_name, contents, config)

        if result:
            try:
                return json.loads(extract_json(result))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON, returning raw text")
                return {"raw_response": result}
        return None

    except Exception as e:
        logger.error(f"Pairwise evaluation failed: {e}")
        return None


# ============================================
# Main
# ============================================
def main():
    parser = argparse.ArgumentParser(description="Evaluate videos with Gemini")
    parser.add_argument("--mode", required=True, choices=["pointwise", "pairwise"], help="Evaluation mode")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt used to generate the video(s)")
    parser.add_argument("--model", "-m", default=None, help="Gemini model ID (default: env GOOGLE_CLOUD_MODEL or AIDP_MODEL)")
    parser.add_argument(
        "--backend",
        default="vertexai",
        choices=["vertexai", "aidp"],
        help="Backend to use: 'vertexai' (default, Vertex AI via google-genai) or 'aidp' (ByteDance AIDP)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help=(
            "AIDP session ID for prompt cache (--backend aidp only). "
            "Routes requests to the same underlying GCP account so Gemini implicit cache kicks in. "
            "Use a stable ID across a batch run to maximize cache hits (TTL 5 min, requires >2048 prompt tokens). "
            "Falls back to env AIDP_SESSION_ID if not set."
        ),
    )

    # Pointwise
    parser.add_argument("--video", default=None, help="Video path (pointwise mode)")

    # Pairwise
    parser.add_argument("--video-a", default=None, help="Video A path (pairwise mode)")
    parser.add_argument("--video-b", default=None, help="Video B path (pairwise mode)")

    # Shared
    parser.add_argument("--ref-images", nargs="*", default=None, help="Reference image paths")
    parser.add_argument("--max-frames", type=int, default=12, help="Max frames to extract (default: 12)")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature (default: 0.2)")
    parser.add_argument("--has-audio", action="store_true", default=None, help="Force audio evaluation (pairwise)")

    args = parser.parse_args()

    if not check_env(backend=args.backend):
        sys.exit(1)

    session_id = args.session_id or os.getenv("AIDP_SESSION_ID")

    if args.backend == "aidp":
        if not OPENAI_AVAILABLE:
            print("ERROR: openai not installed. Run: pip install openai")
            sys.exit(1)
        model = args.model or os.getenv("AIDP_MODEL", AIDP_DEFAULT_MODEL)
        client = get_aidp_client()
        logger.info(f"Backend: AIDP | Endpoint: {os.getenv('AIDP_ENDPOINT', AIDP_ENDPOINT)} | Model: {model}")
        if session_id:
            logger.info(f"  Prompt cache: enabled (session_id={session_id})")
        else:
            logger.info("  Prompt cache: disabled (pass --session-id or set AIDP_SESSION_ID to enable)")
    else:
        if not GENAI_AVAILABLE:
            print("ERROR: google-genai not installed. Run: pip install google-genai")
            sys.exit(1)
        model = args.model or os.getenv("GOOGLE_CLOUD_MODEL", "gemini-2.5-flash-preview-05-20")
        client = get_vertexai_client()
        logger.info(f"Backend: Vertex AI | Model: {model}")

    if args.mode == "pointwise":
        if not args.video:
            parser.error("--video is required for pointwise mode")

        logger.info(f"Pointwise evaluation | Model: {model}")
        logger.info(f"  Video: {args.video}")
        logger.info(f"  Prompt: {args.prompt[:80]}...")

        result = eval_pointwise(
            client, model, args.prompt, args.video,
            ref_images=args.ref_images,
            max_frames=args.max_frames,
            temperature=args.temperature,
            backend=args.backend,
            session_id=session_id,
        )

    elif args.mode == "pairwise":
        if not args.video_a or not args.video_b:
            parser.error("--video-a and --video-b are required for pairwise mode")

        logger.info(f"Pairwise evaluation | Model: {model}")
        logger.info(f"  Video A: {args.video_a}")
        logger.info(f"  Video B: {args.video_b}")
        logger.info(f"  Prompt: {args.prompt[:80]}...")

        result = eval_pairwise(
            client, model, args.prompt, args.video_a, args.video_b,
            ref_images=args.ref_images,
            max_frames=args.max_frames,
            temperature=args.temperature,
            has_audio=args.has_audio,
            backend=args.backend,
            session_id=session_id,
        )

    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps({"error": "Evaluation failed"}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
