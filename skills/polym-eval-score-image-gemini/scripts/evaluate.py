#!/usr/bin/env python3
"""
Gemini Image Evaluation Skill Script

Evaluate AI-generated images using Google Gemini models.
Supports two backends:
  - vertexai (default): Google Cloud Vertex AI via google-genai SDK
  - aidp: ByteDance AIDP model hub via OpenAI-compatible API

Supports two evaluation modes:
  - Pointwise: Score a single image on 6 dimensions (0-5) + overall
  - Pairwise:  Compare two images across 9 dimensions (A/B/tie)

Usage:
    # Pointwise via Vertex AI (default)
    python evaluate.py --mode pointwise --prompt "A cat on a sofa" --image gen.png

    # Pointwise via AIDP
    python evaluate.py --mode pointwise --prompt "A cat on a sofa" --image gen.png --backend aidp

    # Pairwise via AIDP
    python evaluate.py --mode pairwise --prompt "A cat on a sofa" --image-a a.png --image-b b.png --backend aidp
"""

import os
import sys
import io
import json
import time
import base64
import argparse
import logging
from pathlib import Path

from PIL import Image
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

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
# Evaluation prompts (English)
# ============================================

IMAGE_POINTWISE_PROMPT = """
You are a professional high-fidelity image generation quality evaluation system. Your task is to perform multi-dimensional objective scoring of a single generated image (GEN).

You will be provided with:

1. A text prompt describing the intended generation
2. Zero or more optional reference images (REF_1, REF_2, ...) for visual context
3. One generated image (GEN) to evaluate

Your evaluation should:
- Comprehensively understand the intent conveyed by the text prompt (subject, structure, action, scene, style, text elements, etc.)
- Understand the visual context provided by reference images (if any), including subject appearance, brand characteristics, composition, lighting, materials, colors, and style examples
- Consider the model's advanced capabilities (e.g., high-resolution text rendering, fact checking, grounded generation, visual context preservation, conversational editing)
- Score based ONLY on "the quality of GEN itself" and "GEN's consistency with the text prompt + reference images"
- Do NOT speculate on hidden requirements the user did not express

================================================================
INPUT DESCRIPTION
================================================================
- The text prompt defines the core semantics: subject, attributes, action, scene, lighting, style, text content, etc.
- Reference images (if present) provide:
  - Subject or product appearance and structure (e.g., SKU, person, logo)
  - Composition, color, lighting, surface material, brand guidelines, and other visual constraints
  - Scene examples or style examples
- The generated image GEN is the sole object to be scored.

When reference images are present:
- Pixel-level match between GEN and reference is NOT required, but key appearance and semantic consistency must be maintained.
- If GEN significantly deviates from reference images in subject category, structural features, color, or brand elements, deduct points in reference_consistency.
- If the prompt is an editing instruction (e.g., "change the top to green", "only modify the background"), focus on edit_consistency.

================================================================
SCORING DIMENSIONS (0-5 integer scale)
================================================================
Score each of the following 6 core dimensions (0 = very poor, 5 = excellent):

1. instruction_follow (Instruction Following)
   - Whether the text prompt's key requirements are faithfully executed
     (e.g., subject type, count, action, scene, aspect ratio, canvas requirements, local-only modifications)
   - Whether explicit constraints are correctly obeyed (e.g., "do not change background", "must preserve logo", "generate 3 images/3 characters")
   - Severe deviation or ignoring core instructions → low score

2. structure_accuracy (Structural Accuracy)
   - Whether human/object proportions, poses, and perspective are natural and reasonable
   - Whether products are complete, without obvious distortion, severed limbs, misalignment, or physically impossible structures
   - Whether spatial relationships in the scene are correct (foreground/background, ground contact, shadow placement)
   - Obvious structural errors (e.g., wrong finger count, floating objects, misaligned composites) → significant deduction

3. content_correctness (Content Correctness)
   - Whether image content matches the text description (semantic match: category, attributes, action, quantity, relationships)
   - If the prompt involves real-world information (weather, geography, brands, category knowledge), whether the image is reasonable within common knowledge
   - If the image contains key text/numerical information (prices, dates, brand names), whether it is semantically correct with no obvious typos or logical errors
   - Severe hallucinations (content seriously contradicts text/reality) → low score

4. aesthetics (Aesthetics)
   - Whether composition is balanced, subject is prominent, whitespace is reasonable
   - Whether lighting, color palette, style consistency, and overall visual impression are professional
   - Whether it meets mainstream aesthetic standards for e-commerce/advertising/content creation (not overly cluttered or amateurish)
   - Very amateurish, chaotic composition, or garish colors → deduction

5. edit_consistency (Edit Consistency)
   - Primarily evaluated when the prompt is an "edit/modify existing image" instruction:
     - Whether the original subject, composition, and style are preserved while correctly applying local modifications
     - Whether only the specified region was modified, without unintended changes to other parts
   - If this is a "from-scratch generation" (not an editing task):
     - Give a neutral-to-high score (e.g., 3) and note in reason: "Not an editing task, scored as no obvious violation"

6. reference_consistency (Reference Consistency)
   - If reference images exist:
     - Whether key ID/appearance features are correctly preserved (e.g., same person/model/product overall identity consistency)
     - Whether clothing, logo, packaging, materials, etc. maintain consistency with reference examples on key information
     - If only "style borrowing" is required, evaluate correspondence in style/composition/color tone rather than pixel reproduction
   - If no reference images are provided, give a neutral score (e.g., 3) and note in reason: "No reference images, scored as neutral"

================================================================
OUTPUT REQUIREMENTS
================================================================
Output STRICTLY one JSON object only, with no extra text or explanation:

{{
  "instruction_follow": 0-5,
  "structure_accuracy": 0-5,
  "content_correctness": 0-5,
  "aesthetics": 0-5,
  "edit_consistency": 0-5,
  "reference_consistency": 0-5,
  "reason": "1-3 sentences summarizing key scoring rationale, focusing on instruction following, structural reasonableness, content correctness, and edit/reference consistency."
}}

================================================================
Please evaluate based on the text prompt, optional reference images, and generated image provided below. Output JSON now.
Text prompt: \"\"\"{prompt}\"\"\"
"""

IMAGE_POINTWISE_SUFFIX = """Image order (strictly follow):
1) Generated image: GEN
2) Reference images REF_1..REF_K (may be 0)
Please evaluate GEN and output JSON only. Reference image count: REF={n_refs}."""


IMAGE_PAIRWISE_PROMPT = """
You are a professional image generation quality comparison system.
Compare two generated images (A and B) and provide dimension-wise preference judgments.

Compare across **9 dimensions**:
- "A" = Image A is clearly better than Image B
- "B" = Image B is clearly better than Image A
- "tie" = Both images are comparable (no meaningful difference)

**IMPORTANT: Use "tie" as the default when there is no clear evidence of difference.**
Only judge A or B when you can identify a specific, observable difference.

---

## Dimension Definitions

### 1. Prompt Fidelity (prompt_fidelity)
Evaluate how well each image follows the text prompt instructions.

- Does the image correctly implement the subject, attributes, actions, and scene requirements?
- If the prompt contains text to render, is it correctly displayed?
- If the prompt contains editing instructions, are they correctly executed?
- **Only judge A/B if one image clearly fails to follow an instruction that the other succeeds at.**

---

### 2. Structure (structure)
Evaluate structural accuracy and physical plausibility.

- Human/object proportions, perspective, and composition
- No structural collapse, misalignment, distortion, or anatomical errors
- **Only judge A/B if one image has visible structural defects the other doesn't.**

---

### 3. Texture (texture)
Evaluate detail and material quality.

- Fine details, textures, materials, edge sharpness
- 2K/4K fidelity when zoomed
- **Only judge A/B if texture quality difference is clearly visible.**

---

### 4. Lighting (lighting)
Evaluate lighting and material realism.

- Natural and consistent lighting direction
- Believable shadows, reflections, transparent materials (glass, water, metal)
- **Only judge A/B if lighting quality difference is clearly visible.**

---

### 5. Artifacts (artifacts)
Evaluate AI-generated defects.

- Fewer AI artifacts (repeated textures, incomplete elements, ghosting, incorrect text)
- **Only judge A/B if one image has visible artifacts the other doesn't.**

---

### 6. Usefulness (usefulness)
Evaluate practical usability for real-world applications.

- Suitability for e-commerce, advertising, creative design
- Subject clarity, composition, whitespace, readability, professionalism
- **Only judge A/B if one image is clearly more usable than the other.**

---

### 7. Factual Consistency (factual_consistency)
Evaluate alignment with real-world knowledge.

- If the prompt involves real-world facts (weather, locations, brands, object properties)
- Penalize images with factually incorrect content
- Do not penalize fantasy scenes if the prompt allows them
- **Only judge A/B if one image has factual errors the other doesn't.**

---

### 8. Text Rendering (text_rendering)
Evaluate text quality in the generated image.

- If the image contains text (posters, packaging, UI, mixed languages)
- Readability, font quality, edge sharpness, spelling accuracy
- **Only judge A/B if text quality difference is clearly visible, or if one image renders required text correctly while the other doesn't.**

---

### 9. Edit Consistency (edit_consistency)
Evaluate consistency in editing tasks.

- If this is an editing task, does the image preserve the original subject and context?
- Are only the specified areas modified?
- If not an editing task, default to "tie"
- **Only judge A/B if one image correctly performs the edit while the other doesn't.**

---

## Judgment Guidelines

**Key Principles:**
1. **"tie" is the expected default outcome for most comparisons**
2. Most image pairs from good models will have similar quality — judge them as "tie"
3. Only judge A or B when you can point to a SPECIFIC, OBJECTIVE difference
4. Do not invent differences that don't exist
5. Minor, subjective, or aesthetic preferences should NOT determine a winner

**CRITICAL: When to judge "tie":**
- Both images successfully follow the prompt (even if in slightly different ways)
- Both images have similar visual quality
- Differences are minor, subjective, or aesthetic preferences
- You cannot articulate a clear, specific flaw in one image that the other avoids
- **When in doubt, choose "tie"**

**When to judge A or B:**
- One image CLEARLY fails to follow a critical prompt instruction while the other succeeds
- One image has OBVIOUS defects (severe artifacts, structural errors, wrong text) that the other avoids
- One image has FACTUALLY incorrect content while the other is correct
- The difference is so clear that any viewer would agree

---

## Output Format (Strict JSON only)

{{
  "reason": "Brief explanation of why one image is better (or why they are tied)",
  "dimensions": {{
    "prompt_fidelity": "A" | "B" | "tie",
    "structure": "A" | "B" | "tie",
    "texture": "A" | "B" | "tie",
    "lighting": "A" | "B" | "tie",
    "artifacts": "A" | "B" | "tie",
    "usefulness": "A" | "B" | "tie",
    "factual_consistency": "A" | "B" | "tie",
    "text_rendering": "A" | "B" | "tie",
    "edit_consistency": "A" | "B" | "tie"
  }}
}}

---

You will receive two generated images (GEN_A and GEN_B) and a text prompt:
Text prompt: \"\"\"{prompt}\"\"\"
"""

IMAGE_PAIRWISE_SUFFIX = """
Image order (strictly follow):
1) Image A: GEN_A
2) Image B: GEN_B
3) (Optional) Reference images REF_1..REF_K (K may be 0)

Compare A and B, output JSON only. Reference images are for semantic/style understanding only.
Reference image count: REF={n_refs}."""


# ============================================
# Prompt builders
# ============================================
def build_pointwise_prompt(prompt: str, n_refs: int) -> str:
    return IMAGE_POINTWISE_PROMPT.format(prompt=prompt) + "\n" + IMAGE_POINTWISE_SUFFIX.format(n_refs=n_refs)


def build_pairwise_prompt(prompt: str, n_refs: int) -> str:
    return IMAGE_PAIRWISE_PROMPT.format(prompt=prompt) + "\n" + IMAGE_PAIRWISE_SUFFIX.format(n_refs=n_refs)


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
# Image handling — Vertex AI (google-genai Parts)
# ============================================
def pil_to_part(img_file, fmt="jpeg", quality=85, max_size=2048):
    """Convert image to Gemini Part (Vertex AI), auto-resize large images."""
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    if isinstance(img_file, str):
        img = Image.open(img_file)
    else:
        img = img_file

    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        logger.debug(f"Resized image from {w}x{h} to {new_w}x{new_h}")

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format=fmt, quality=quality)
    return types.Part(
        inline_data=types.Blob(
            mime_type=f"image/{fmt}",
            data=buf.getvalue(),
        )
    )


def text_to_part(text):
    if not GENAI_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    return types.Part(text=text)


# ============================================
# Image handling — AIDP (base64 data URLs)
# ============================================
def pil_to_base64(img_file, fmt="jpeg", quality=85, max_size=2048) -> str:
    """Convert image to base64 data URL for AIDP OpenAI-compatible API."""
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


# ============================================
# OpenAI message builders for AIDP
# ============================================
def build_openai_messages_pointwise(prompt_text: str, gen_image_path, ref_images=None,
                                     max_image_size: int = 2048) -> list:
    user_text = build_pointwise_prompt(prompt=prompt_text, n_refs=len(ref_images or []))
    content = [{"type": "text", "text": user_text}]
    content.append({
        "type": "image_url",
        "image_url": {"url": pil_to_base64(gen_image_path, max_size=max_image_size)},
    })
    for ref in (ref_images or []):
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(ref, max_size=max_image_size)},
        })
    return [{"role": "user", "content": content}]


def build_openai_messages_pairwise(prompt_text: str, gen_image_path_a, gen_image_path_b,
                                    ref_images=None, max_image_size: int = 2048,
                                    quality: int = 85) -> list:
    user_text = build_pairwise_prompt(prompt=prompt_text, n_refs=len(ref_images or []))
    content = [{"type": "text", "text": user_text}]
    content.append({
        "type": "image_url",
        "image_url": {"url": pil_to_base64(gen_image_path_a, max_size=max_image_size, quality=quality)},
    })
    content.append({
        "type": "image_url",
        "image_url": {"url": pil_to_base64(gen_image_path_b, max_size=max_image_size, quality=quality)},
    })
    for ref in (ref_images or []):
        content.append({
            "type": "image_url",
            "image_url": {"url": pil_to_base64(ref, max_size=max_image_size, quality=quality)},
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
def eval_pointwise(client, model_name, prompt_text, gen_image_path, ref_images=None,
                   temperature=0.2, max_image_size=2048, backend="vertexai",
                   session_id: str = None):
    """
    Pointwise evaluation: score a single generated image.

    Returns:
        Parsed JSON dict with scores, or raw text if JSON parsing fails.
    """
    if backend == "aidp":
        messages = build_openai_messages_pointwise(
            prompt_text, gen_image_path, ref_images=ref_images, max_image_size=max_image_size
        )
        result = aidp_call_with_retry(client, model_name, messages, temperature=temperature,
                                      session_id=session_id)
    else:
        user_text = build_pointwise_prompt(prompt=prompt_text, n_refs=len(ref_images or []))
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
            top_p=1,
            max_output_tokens=16384,
        )
        contents = []
        contents.append(text_to_part(user_text))
        contents.append(pil_to_part(gen_image_path, max_size=max_image_size))
        for ref in (ref_images or []):
            contents.append(pil_to_part(ref, max_size=max_image_size))
        result = gemini_call_with_retry(client, model_name, contents, config)

    if result:
        try:
            return json.loads(extract_json(result))
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON, returning raw text")
            return {"raw_response": result}
    return None


def eval_pairwise(client, model_name, prompt_text, gen_image_path_a, gen_image_path_b,
                  ref_images=None, temperature=0.2, max_image_size=2048, backend="vertexai",
                  session_id: str = None):
    """
    Pairwise evaluation: compare two generated images.

    Returns:
        Parsed JSON dict with dimension judgments, or raw text if JSON parsing fails.
    """
    if backend == "aidp":
        # Try progressively smaller image sizes if needed
        size_strategies = [
            {"max_size": max_image_size, "quality": 85, "name": "normal"},
            {"max_size": int(max_image_size * 0.75), "quality": 80, "name": "medium"},
            {"max_size": int(max_image_size * 0.5), "quality": 75, "name": "small"},
        ]
        for strategy in size_strategies:
            messages = build_openai_messages_pairwise(
                prompt_text, gen_image_path_a, gen_image_path_b,
                ref_images=ref_images,
                max_image_size=strategy["max_size"],
                quality=strategy["quality"],
            )
            result = aidp_call_with_retry(client, model_name, messages, temperature=temperature,
                                          max_retries=2, session_id=session_id)
            if result:
                try:
                    return json.loads(extract_json(result))
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON, returning raw text")
                    return {"raw_response": result}
            logger.warning(f"Strategy '{strategy['name']}' returned empty, trying smaller images...")
        logger.error("All image size strategies failed")
        return None
    else:
        user_text = build_pairwise_prompt(prompt=prompt_text, n_refs=len(ref_images or []))
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
            top_p=1,
            max_output_tokens=16384,
        )
        size_strategies = [
            {"max_size": max_image_size, "quality": 85, "name": "normal"},
            {"max_size": int(max_image_size * 0.75), "quality": 80, "name": "medium"},
            {"max_size": int(max_image_size * 0.5), "quality": 75, "name": "small"},
        ]
        for strategy in size_strategies:
            try:
                contents = []
                contents.append(text_to_part(user_text))
                contents.append(pil_to_part(gen_image_path_a, max_size=strategy["max_size"], quality=strategy["quality"]))
                contents.append(pil_to_part(gen_image_path_b, max_size=strategy["max_size"], quality=strategy["quality"]))
                for ref in (ref_images or []):
                    contents.append(pil_to_part(ref, max_size=strategy["max_size"], quality=strategy["quality"]))

                result = gemini_call_with_retry(client, model_name, contents, config, max_retries=2)

                if result:
                    try:
                        return json.loads(extract_json(result))
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON, returning raw text")
                        return {"raw_response": result}

                logger.warning(f"Strategy '{strategy['name']}' returned empty, trying smaller images...")

            except Exception as e:
                if "MAX_TOKENS" in str(e) or "token" in str(e).lower():
                    logger.warning(f"Strategy '{strategy['name']}' hit token limit, trying smaller images...")
                    continue
                raise

        logger.error("All image size strategies failed")
        return None


# ============================================
# Main
# ============================================
def main():
    parser = argparse.ArgumentParser(description="Evaluate images with Gemini")
    parser.add_argument("--mode", required=True, choices=["pointwise", "pairwise"], help="Evaluation mode")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt used to generate the image(s)")
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

    # Pointwise args
    parser.add_argument("--image", default=None, help="Generated image path (pointwise mode)")

    # Pairwise args
    parser.add_argument("--image-a", default=None, help="Image A path (pairwise mode)")
    parser.add_argument("--image-b", default=None, help="Image B path (pairwise mode)")

    # Shared optional args
    parser.add_argument("--ref-images", nargs="*", default=None, help="Reference image paths")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature (default: 0.2)")
    parser.add_argument("--max-image-size", type=int, default=2048, help="Max image dimension (default: 2048)")

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
        if not args.image:
            parser.error("--image is required for pointwise mode")

        logger.info(f"Pointwise evaluation | Model: {model}")
        logger.info(f"  Image: {args.image}")
        logger.info(f"  Prompt: {args.prompt[:80]}...")
        logger.info(f"  Refs: {len(args.ref_images or [])}")

        result = eval_pointwise(
            client, model, args.prompt, args.image,
            ref_images=args.ref_images,
            temperature=args.temperature,
            max_image_size=args.max_image_size,
            backend=args.backend,
            session_id=session_id,
        )

    elif args.mode == "pairwise":
        if not args.image_a or not args.image_b:
            parser.error("--image-a and --image-b are required for pairwise mode")

        logger.info(f"Pairwise evaluation | Model: {model}")
        logger.info(f"  Image A: {args.image_a}")
        logger.info(f"  Image B: {args.image_b}")
        logger.info(f"  Prompt: {args.prompt[:80]}...")
        logger.info(f"  Refs: {len(args.ref_images or [])}")

        result = eval_pairwise(
            client, model, args.prompt, args.image_a, args.image_b,
            ref_images=args.ref_images,
            temperature=args.temperature,
            max_image_size=args.max_image_size,
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
