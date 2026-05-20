#!/usr/bin/env python3
"""
GPT Image Generation & Editing Script

Supports two modes via ByteDance AIDP:
  - generate (default): text-to-image or image-to-image via /images/generations
  - edit:               image editing with reference images via /images/edits

Usage:
    # Text-to-image (generate)
    python generate.py --prompt "A cute cat"

    # Image editing (edit mode)
    python generate.py --mode edit --prompt "给猫咪穿衣服" --images cat.jpg

    # Image editing with mask
    python generate.py --mode edit --prompt "Replace background with beach" \
        --images photo.jpg --mask mask.png
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
import requests
from datetime import datetime
from io import BytesIO
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# ============================================
# .env management
# ============================================
SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_DIR / ".env"

REQUIRED_ENV_VARS = {
    "AIDP_API_KEY": {
        "description": "AIDP API Key",
        "help": "ByteDance AIDP platform API key",
    },
}


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


def check_env():
    missing = []
    for var, info in REQUIRED_ENV_VARS.items():
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
    return True


_load_env()

# ============================================
# AIDP endpoints
# ============================================
AIDP_BASE_GENERATE = "https://aidp.bytedance.net/api/modelhub/online/v2/crawl/openai"
AIDP_BASE_EDIT = "https://aidp.bytedance.net/gpt/openapi/online/v2/crawl/openai"
DEFAULT_MODEL = "gpt-image-1"

SKILL_TYPE = "gpt-image"

# ============================================
# TOS upload
# ============================================
TOS_ENV_VARS = {
    "TOS_BUCKET": {"description": "TOS Bucket Name", "help": "BytePlus TOS bucket"},
    "TOS_ACCESS_KEY": {"description": "TOS Access Key", "help": "BytePlus TOS access key"},
    "TOS_SECRET_KEY": {"description": "TOS Secret Key", "help": "BytePlus TOS secret key"},
}


def _ensure_tos_env():
    missing = [
        (var, info)
        for var, info in TOS_ENV_VARS.items()
        if not os.getenv(var, "").strip()
    ]
    if not missing:
        return True

    print(f"\n{'=' * 60}")
    print("TOS not configured — needed to return a network URL")
    print(f"{'=' * 60}")
    for var, info in missing:
        while True:
            value = input(f"\nEnter {info['description']} ({var})\n  [or 'skip' to skip TOS upload]: ").strip()
            if value.lower() == "skip":
                return False
            if value:
                _append_env_var(var, value)
                break
            print("  Value cannot be empty.")
    return True


def _tos_upload_and_presign(local_path, expires=3600):
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
        content_type = content_type or "application/octet-stream"
        ext = os.path.splitext(local_path)[1] or ".png"
        filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ext
        object_key = f"{prefix}/{SKILL_TYPE}/{filename}"

        client = tos_sdk.TosClientV2(ak=ak, sk=sk, endpoint=endpoint, region=region)
        with open(local_path, "rb") as f:
            client.put_object(bucket=bucket, key=object_key, content=f, content_type=content_type)
        out = client.pre_signed_url(HttpMethodType.Http_Method_Get, bucket=bucket, key=object_key, expires=expires)
        logger.info(f"Uploaded to TOS: {object_key}")
        return out.signed_url
    except ImportError:
        logger.warning("TOS SDK not installed (pip install tos)")
        return None
    except Exception as e:
        logger.warning(f"TOS upload failed: {e}")
        return None


def _get_network_url(local_path):
    if not os.getenv("TOS_BUCKET"):
        _ensure_tos_env()
    return _tos_upload_and_presign(local_path)


# ============================================
# Core generation
# ============================================

def _aidp_headers():
    ak = os.getenv("AIDP_API_KEY", "")
    return {"Content-Type": "application/json", "api-key": ak}


def _save_b64_image(b64_data: str, output_file: str) -> str:
    """Decode base64 image and save to file. Returns actual output path."""
    img_bytes = base64.b64decode(b64_data)
    # Detect format from bytes
    if img_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        ext = ".png"
    elif img_bytes[:2] == b'\xff\xd8':
        ext = ".jpg"
    elif img_bytes[:4] == b'RIFF' and img_bytes[8:12] == b'WEBP':
        ext = ".webp"
    else:
        ext = ".png"

    base, _ = os.path.splitext(output_file)
    output_file = base + ext
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(img_bytes)
    return output_file


def generate_image(
    prompt: str,
    output_file: str = "generated/output.png",
    model: str = None,
    size: str = "1024x1024",
    quality: str = "low",
    n: int = 1,
) -> dict:
    """Generate image via AIDP /images/generations endpoint."""
    if model is None:
        model = os.getenv("GPT_IMAGE_MODEL", DEFAULT_MODEL)

    ak = os.getenv("AIDP_API_KEY", "")
    url = f"{AIDP_BASE_GENERATE}/images/generations?ak={ak}"

    body = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "quality": quality,
    }

    logger.info(f"  Generating with {model} | size={size} quality={quality}...")
    t0 = time.time()
    try:
        resp = requests.post(url, json=body, headers=_aidp_headers(), timeout=120)
    except Exception as e:
        logger.error(f"  Request failed: {e}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    elapsed = time.time() - t0

    if resp.status_code != 200:
        logger.error(f"  HTTP {resp.status_code}: {resp.text[:200]}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    data = resp.json()
    if "error" in data:
        logger.error(f"  API error: {data['error']}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    items = data.get("data", [])
    if not items or not items[0].get("b64_json"):
        logger.error(f"  No image data in response")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    actual_path = _save_b64_image(items[0]["b64_json"], output_file)
    gen_url = _get_network_url(actual_path)
    logger.info(f"  Done in {elapsed:.1f}s: {actual_path}")
    if data.get("usage"):
        logger.info(f"  Tokens: {data['usage']}")

    return {"gen_success": True, "gen_image_path": actual_path, "gen_url": gen_url}


def edit_image(
    prompt: str,
    image_paths: list,
    output_file: str = "generated/output.png",
    model: str = None,
    size: str = "1024x1024",
    quality: str = "low",
    mask_path: str = None,
    n: int = 1,
) -> dict:
    """Edit images via AIDP /images/edits endpoint (multipart/form-data)."""
    if model is None:
        model = os.getenv("GPT_IMAGE_MODEL", DEFAULT_MODEL)
    if not image_paths:
        logger.error("  At least one image is required for edit mode")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    ak = os.getenv("AIDP_API_KEY", "")
    url = f"{AIDP_BASE_EDIT}/images/edits?ak={ak}"

    # Build multipart form data
    files = []
    opened = []
    try:
        for img_path in image_paths:
            if img_path.startswith(("http://", "https://")):
                r = requests.get(img_path, timeout=60)
                r.raise_for_status()
                buf = BytesIO(r.content)
                fname = img_path.split("/")[-1].split("?")[0] or "image.jpg"
                files.append(("image[]", (fname, buf, "image/jpeg")))
                opened.append(buf)
            else:
                f = open(img_path, "rb")
                opened.append(f)
                fname = os.path.basename(img_path)
                files.append(("image[]", (fname, f, "image/jpeg")))

        if mask_path:
            f = open(mask_path, "rb")
            opened.append(f)
            files.append(("mask", (os.path.basename(mask_path), f, "image/png")))

        data = {
            "prompt": prompt,
            "model": model,
            "quality": quality,
            "size": size,
            "n": str(n),
        }

        headers = {"api-key": ak}  # No Content-Type; let requests set multipart boundary

        logger.info(f"  Editing {len(image_paths)} image(s) with {model} | size={size} quality={quality}...")
        t0 = time.time()
        resp = requests.post(url, data=data, files=files, headers=headers, timeout=120)
    except Exception as e:
        logger.error(f"  Request failed: {e}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}
    finally:
        for f in opened:
            f.close()

    elapsed = time.time() - t0

    if resp.status_code != 200:
        logger.error(f"  HTTP {resp.status_code}: {resp.text[:200]}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    result = resp.json()
    if "error" in result:
        logger.error(f"  API error: {result['error']}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    items = result.get("data", [])
    if not items or not items[0].get("b64_json"):
        logger.error("  No image data in response")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}

    actual_path = _save_b64_image(items[0]["b64_json"], output_file)
    gen_url = _get_network_url(actual_path)
    logger.info(f"  Done in {elapsed:.1f}s: {actual_path}")
    if result.get("usage"):
        logger.info(f"  Tokens: {result['usage']}")

    return {"gen_success": True, "gen_image_path": actual_path, "gen_url": gen_url}


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(description="GPT Image generation/editing via AIDP")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--mode", default="generate", choices=["generate", "edit"],
                        help="Mode: generate (T2I) or edit (image editing)")
    parser.add_argument("--model", "-m", default=None,
                        help=f"Model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--size", "-s", default="1024x1024",
                        choices=["1024x1024", "1536x1024", "1024x1536", "auto"],
                        help="Image size")
    parser.add_argument("--quality", "-q", default="low",
                        choices=["low", "medium", "high", "auto"],
                        help="Image quality")
    parser.add_argument("--images", "-i", nargs="+", default=[],
                        help="Reference image paths/URLs (edit mode)")
    parser.add_argument("--mask", default=None,
                        help="Mask image path (edit mode, optional)")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file path")
    parser.add_argument("--n", type=int, default=1,
                        help="Number of images to generate")

    args = parser.parse_args()

    if not check_env():
        sys.exit(1)

    if args.output:
        output_file = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"generated/{ts}.png"

    logger.info(f"Mode: {args.mode}")
    logger.info(f"Prompt: {args.prompt[:80]}...")
    logger.info(f"Model: {args.model or DEFAULT_MODEL}")

    if args.mode == "edit":
        if not args.images:
            logger.error("--images is required for edit mode")
            sys.exit(1)
        result = edit_image(
            prompt=args.prompt,
            image_paths=args.images,
            output_file=output_file,
            model=args.model,
            size=args.size,
            quality=args.quality,
            mask_path=args.mask,
            n=args.n,
        )
    else:
        result = generate_image(
            prompt=args.prompt,
            output_file=output_file,
            model=args.model,
            size=args.size,
            quality=args.quality,
            n=args.n,
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
