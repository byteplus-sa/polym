#!/usr/bin/env python3
"""
Gemini Image Generation Script

Supports two backends:
  - google (default): Vertex AI + Google AI Studio with automatic fallback
  - aidp: ByteDance AIDP model hub (multimodal/crawl endpoint)

Usage:
    # Google backend (default)
    python generate.py --prompt "A cute cat"

    # AIDP backend
    python generate.py --prompt "A cute cat" --backend aidp
"""

import base64

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

from PIL import Image
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False
import argparse
import json
import logging
import os
import sys
import time
import requests
from io import BytesIO
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ============================================
# .env management
# ============================================
SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_DIR / ".env"

REQUIRED_ENV_VARS = {
    "GOOGLE_AI_STUDIO_API_KEY": {
        "description": "Google AI Studio API Key",
        "help": "Get it from https://aistudio.google.com/apikey",
    },
}

AIDP_REQUIRED_ENV_VARS = {
    "AIDP_API_KEY": {
        "description": "AIDP API Key",
        "help": "ByteDance AIDP platform API key",
    },
}

OPTIONAL_ENV_VARS = {
    "GEMINI_IMAGE_API_KEY": "Vertex AI API Key (optional, for Vertex AI client)",
    "GEMINI_IMAGE_MODEL": "Model ID (default: gemini-2.0-flash-preview-image-generation)",
}

# AIDP defaults
AIDP_ENDPOINT = os.getenv("AIDP_ENDPOINT", "https://aidp.bytedance.net/api/modelhub/online/multimodal/crawl")
AIDP_DEFAULT_MODEL = "gemini-3.1-fi"  # Gemini-3.1-flash-image-preview (Nano Banana 2, ~35s)


def _load_env():
    """Load .env from skill directory."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)
    else:
        load_dotenv()


def _append_env_var(key: str, value: str):
    """Write an env var to the skill's .env file."""
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


def check_env(backend: str = "google"):
    """Check required env vars, prompt user interactively if missing."""
    required = REQUIRED_ENV_VARS if backend == "google" else AIDP_REQUIRED_ENV_VARS
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

DEFAULT_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation")


# ============================================
# TOS upload for network URL
# ============================================
SKILL_TYPE = "gemini"

TOS_ENV_VARS = {
    "TOS_BUCKET": {
        "description": "TOS Bucket Name",
        "help": "BytePlus TOS bucket for uploading generated files",
    },
    "TOS_ACCESS_KEY": {
        "description": "TOS Access Key",
        "help": "BytePlus TOS access key",
    },
    "TOS_SECRET_KEY": {
        "description": "TOS Secret Key",
        "help": "BytePlus TOS secret key",
    },
}


def _ensure_tos_env():
    """Prompt user for TOS vars if missing. Returns True when configured."""
    missing = []
    for var, info in TOS_ENV_VARS.items():
        if not os.getenv(var, "").strip():
            missing.append((var, info))
    if not missing:
        return True

    print(f"\n{'=' * 60}")
    print("TOS not configured — needed to return a network URL")
    print(f"(.env: {ENV_PATH})")
    print(f"{'=' * 60}")
    for var, info in missing:
        print(f"\n  {var}: {info['description']}")
        print(f"    {info['help']}")

    for var, info in missing:
        while True:
            value = input(f"\nEnter {info['description']} ({var})\n  [or 'skip' to skip TOS upload]: ").strip()
            if value.lower() == "skip":
                logger.info("TOS configuration skipped — gen_url will be None")
                return False
            if value:
                _append_env_var(var, value)
                print(f"  Saved {var} to {ENV_PATH}")
                break
            print("  Value cannot be empty.")
    return True


def _tos_upload_and_presign(local_path, expires=3600):
    """Upload a local file to TOS and return a presigned GET URL."""
    bucket = os.getenv("TOS_BUCKET", "")
    ak = os.getenv("TOS_ACCESS_KEY", "")
    sk = os.getenv("TOS_SECRET_KEY", "")
    endpoint = os.getenv("TOS_ENDPOINT", "tos-ap-southeast-1.bytepluses.com")
    region = os.getenv("TOS_REGION", "ap-southeast-1")
    prefix = os.getenv("TOS_PREFIX", "generated").strip("/")

    if not all([bucket, ak, sk]):
        return None

    try:
        import tos as tos_sdk
        from tos.enum import HttpMethodType
        import mimetypes

        content_type, _ = mimetypes.guess_type(local_path)
        if content_type is None:
            content_type = "application/octet-stream"

        from datetime import datetime as _dt
        ext = os.path.splitext(local_path)[1] or ".png"
        filename = _dt.now().strftime("%Y%m%d_%H%M%S") + ext
        object_key = f"{prefix}/{SKILL_TYPE}/{filename}"

        client = tos_sdk.TosClientV2(ak=ak, sk=sk, endpoint=endpoint, region=region)
        with open(local_path, "rb") as f:
            client.put_object(bucket=bucket, key=object_key, content=f, content_type=content_type)

        out = client.pre_signed_url(HttpMethodType.Http_Method_Get, bucket=bucket, key=object_key, expires=expires)
        logger.info(f"Uploaded to TOS: {object_key}")
        return out.signed_url
    except ImportError:
        logger.warning("TOS SDK not installed (pip install tos), cannot generate network URL")
        return None
    except Exception as e:
        logger.warning(f"TOS upload failed: {e}")
        return None


def _get_network_url(local_path, api_url=None):
    """Return a network-accessible URL for the generated file.

    Uses api_url directly if accessible, otherwise uploads to TOS.
    """
    if api_url and api_url.startswith(("http://", "https://")):
        return api_url

    if not os.getenv("TOS_BUCKET"):
        _ensure_tos_env()

    return _tos_upload_and_presign(local_path)


def _create_clients():
    """Create Vertex AI and AI Studio clients."""
    vertex_client = None
    ai_studio_client = None

    try:
        api_key = os.environ.get("GEMINI_IMAGE_API_KEY")
        if api_key:
            vertex_client = genai.Client(vertexai=True, api_key=api_key)
        else:
            vertex_client = genai.Client(vertexai=True)
    except Exception as e:
        logger.warning(f"Vertex AI client init failed: {e}")

    ai_studio_key = os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
    if ai_studio_key:
        try:
            ai_studio_client = genai.Client(api_key=ai_studio_key)
        except Exception as e:
            logger.warning(f"AI Studio client init failed: {e}")

    return vertex_client, ai_studio_client


def generate_image(
    id: str,
    prompt: str,
    ref_image_paths: list = None,
    path: str = "generated",
    size: str = "1K",
    model: str = None,
    use_ai_studio: bool = False,
    retry_with_ai_studio: bool = True,
) -> str:
    """
    Generate an image using Gemini.

    Returns:
        Dict with gen_success, gen_image_path, gen_url
    """
    if model is None:
        model = DEFAULT_MODEL
    if ref_image_paths is None:
        ref_image_paths = []

    vertex_client, ai_studio_client = _create_clients()

    content = []
    for ref_path in ref_image_paths:
        try:
            if ref_path.startswith("http://") or ref_path.startswith("https://"):
                response = requests.get(ref_path, timeout=30)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
            else:
                img = Image.open(ref_path)
            content.append(img)
            logger.info(f"  Loaded reference image: {ref_path}")
        except Exception as e:
            logger.error(f"  Failed to load reference image {ref_path}: {e}")
            return {"gen_success": False, "gen_image_path": None, "gen_url": None}
    content.append(prompt)

    os.makedirs(path, exist_ok=True)
    output_file = os.path.join(path, f"{id}.png")

    clients_to_try = []
    if use_ai_studio and ai_studio_client:
        clients_to_try = [("AI Studio", ai_studio_client)]
    elif retry_with_ai_studio and ai_studio_client:
        clients_to_try = [("Vertex AI", vertex_client), ("AI Studio", ai_studio_client)]
    elif vertex_client:
        clients_to_try = [("Vertex AI", vertex_client)]
    else:
        logger.error("No valid client available. Check API keys.")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    last_error = None
    for client_name, client in clients_to_try:
        if client is None:
            continue
        try:
            logger.info(f"  Using {client_name} for generation...")
            t0 = time.time()
            response = client.models.generate_content(
                model=model,
                contents=content,
                config=types.GenerateContentConfig(
                    image_config=types.ImageConfig(image_size=size)
                ),
            )
            elapsed = time.time() - t0

            if response.parts:
                image_parts = [part for part in response.parts if part.inline_data]
                if image_parts:
                    image = image_parts[0].as_image()
                    image.save(output_file)
                    gen_url = _get_network_url(output_file)
                    logger.info(f"  Generated with {client_name} in {elapsed:.1f}s: {output_file}")
                    return {"gen_success": True, "gen_image_path": output_file, "gen_url": gen_url}
                else:
                    logger.warning(f"  {client_name}: No image in response parts")
                    if response.text:
                        logger.info(f"  Response text: {response.text[:200]}")
                    continue
            else:
                if response.prompt_feedback:
                    logger.error(f"  Prompt feedback: {response.prompt_feedback}")
                if response.candidates:
                    logger.error(f"  Finish reason: {response.candidates[0].finish_reason}")
                continue

        except Exception as e:
            error_str = str(e)
            last_error = e
            logger.warning(f"  {client_name} failed: {error_str[:150]}")

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                logger.info(f"  Rate limited on {client_name}, trying next...")
                time.sleep(2)
                continue
            else:
                continue

    logger.error(f"Image generation failed after all attempts: {last_error}")
    return {"gen_success": False, "gen_image_path": None, "gen_url": None}


def _image_to_base64(source: str) -> tuple:
    """Return (base64_string, mime_type) for image at path or URL."""
    if source.startswith(("http://", "https://")):
        resp = requests.get(source, timeout=60)
        resp.raise_for_status()
        raw = resp.content
        ct = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        mime = ct if ct.startswith("image/") else "image/jpeg"
    else:
        with open(source, "rb") as f:
            raw = f.read()
        ext = Path(source).suffix.lower().lstrip(".")
        mime = {"png": "image/png", "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/jpeg")
    return base64.b64encode(raw).decode("utf-8"), mime


def aidp_generate_image(
    prompt: str,
    ref_image_paths: list = None,
    output_file: str = "generated/output.png",
    model: str = None,
) -> dict:
    """Generate image via AIDP multimodal/crawl endpoint.

    Response format:
        choices[0].message.multimodal_contents -> list of items
        Image items: {"type": "inline_data", "inline_data": {"mime_type": "image/png", "data": "<base64>"}}
    """
    if model is None:
        model = os.getenv("GEMINI_AIDP_MODEL", AIDP_DEFAULT_MODEL)
    if ref_image_paths is None:
        ref_image_paths = []

    api_key = os.getenv("AIDP_API_KEY", "")
    endpoint = AIDP_ENDPOINT

    # Build message content
    content = []
    for ref_path in ref_image_paths:
        try:
            b64, mime = _image_to_base64(ref_path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })
            logger.info(f"  Loaded reference image: {ref_path}")
        except Exception as e:
            logger.error(f"  Failed to load reference image {ref_path}: {e}")
            return {"gen_success": False, "gen_image_path": None, "gen_url": None}
    content.append({"type": "text", "text": prompt})

    body = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 8192,
    }

    logger.info(f"  Using AIDP ({model}) for generation...")
    t0 = time.time()
    try:
        resp = requests.post(
            endpoint,
            json=body,
            headers={"Content-Type": "application/json", "api-key": api_key},
            timeout=120,
        )
    except Exception as e:
        logger.error(f"  AIDP request failed: {e}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    elapsed = time.time() - t0

    if resp.status_code != 200:
        logger.error(f"  AIDP error {resp.status_code}: {resp.text[:200]}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        logger.error(f"  AIDP: no choices in response")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    message = choices[0].get("message", {})
    multimodal_contents = message.get("multimodal_contents", [])

    # Find first inline_data (image) item
    image_item = None
    for item in multimodal_contents:
        if item.get("type") == "inline_data" and item.get("inline_data"):
            image_item = item["inline_data"]
            break

    if not image_item:
        logger.error("  AIDP: no image found in multimodal_contents")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    # Decode and save
    image_bytes = base64.b64decode(image_item["data"])
    mime_type = image_item.get("mime_type", "image/png")
    ext = mime_type.split("/")[-1].replace("jpeg", "jpg")
    if not output_file.endswith(f".{ext}"):
        output_file = os.path.splitext(output_file)[0] + f".{ext}"

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(image_bytes)

    gen_url = _get_network_url(output_file)
    logger.info(f"  Generated with AIDP in {elapsed:.1f}s: {output_file}")
    return {"gen_success": True, "gen_image_path": output_file, "gen_url": gen_url}


def main():
    parser = argparse.ArgumentParser(description="Generate images with Gemini")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--model", "-m", default=None, help=f"Model ID (default: google={DEFAULT_MODEL}, aidp={AIDP_DEFAULT_MODEL})")
    parser.add_argument("--size", "-s", default="1K", choices=["1K", "2K", "4K"], help="Image size (google backend only)")
    parser.add_argument("--ref-images", "-r", nargs="*", default=[], help="Reference image paths/URLs")
    parser.add_argument("--output", "-o", default=None, help="Output file path")
    parser.add_argument("--use-ai-studio", action="store_true", help="Force AI Studio (google backend only)")
    parser.add_argument("--no-retry", action="store_true", help="Don't fallback to AI Studio on 429 (google backend only)")
    parser.add_argument("--backend", "-b", default="google", choices=["google", "aidp"],
                        help="Backend to use: google (Vertex AI + AI Studio) or aidp (ByteDance AIDP)")

    args = parser.parse_args()

    if not check_env(args.backend):
        sys.exit(1)

    if args.output:
        output_dir = os.path.dirname(args.output) or "generated"
        file_id = os.path.splitext(os.path.basename(args.output))[0]
        output_file = args.output
    else:
        output_dir = "generated"
        file_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"{file_id}.png")

    logger.info(f"Backend: {args.backend}")
    logger.info(f"Prompt: {args.prompt[:80]}...")
    if args.ref_images:
        logger.info(f"Reference images: {len(args.ref_images)}")

    if args.backend == "aidp":
        model = args.model or AIDP_DEFAULT_MODEL
        logger.info(f"Model: {model}")
        result = aidp_generate_image(
            prompt=args.prompt,
            ref_image_paths=args.ref_images,
            output_file=output_file,
            model=model,
        )
    else:
        model = args.model or DEFAULT_MODEL
        logger.info(f"Model: {model}")
        logger.info(f"Size: {args.size}")
        result = generate_image(
            id=file_id,
            prompt=args.prompt,
            ref_image_paths=args.ref_images,
            path=output_dir,
            size=args.size,
            model=model,
            use_ai_studio=args.use_ai_studio,
            retry_with_ai_studio=not args.no_retry,
        )

    if result and result.get("gen_success"):
        logger.info(f"\nSuccess: {result['gen_image_path']}")
        if result.get("gen_url"):
            logger.info(f"URL: {result['gen_url'][:100]}...")
    else:
        logger.error("\nFailed to generate image")
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
