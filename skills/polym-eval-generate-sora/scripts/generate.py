#!/usr/bin/env python3
"""
Sora Video Generation Skill Script

Generate videos using Sora models. Supports two backends:
  - openai (default): OpenAI public API (sora-2, sora-2-pro)
  - aidp: ByteDance AIDP model hub (azure-sora2, azure-sora)

Supports T2V and I2V (first frame reference), auto aspect ratio detection,
automatic image resizing for I2V.

Usage:
    # T2V via OpenAI (default)
    python generate.py --prompt "A serene lake reflecting autumn trees"

    # I2V via OpenAI
    python generate.py --prompt "The scene gently animates" --first-frame photo.jpg

    # T2V via AIDP (azure-sora2)
    python generate.py --prompt "A serene lake" --backend aidp

    # I2V via AIDP (azure-sora2)
    python generate.py --prompt "The scene animates" --first-frame photo.jpg --backend aidp
"""

import os
import sys
import time
import json
import io
import uuid
import argparse
import tempfile
import logging
from pathlib import Path

import requests
from PIL import Image, ImageOps
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============================================
# .env management
# ============================================
SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_DIR / ".env"

REQUIRED_ENV_VARS = {
    "OPENAI_API_KEY": {
        "description": "OpenAI API Key",
        "help": "Get it from https://platform.openai.com/api-keys",
    },
}

AIDP_REQUIRED_ENV_VARS = {
    "AIDP_AK": {
        "description": "AIDP API Key (ak)",
        "help": "ByteDance AIDP platform AK for Sora",
    },
}

# AIDP defaults
AIDP_HOST = "aidp.bytedance.net"
AIDP_BASE_TMPL = "https://{host}/api/modelhub/online/multimodal/crawl"
AIDP_DEFAULT_MODEL = "azure-sora2"

# TOS download base (CN office/prod network)
TOS_CN_PREFIX = "https://tosv.byted.org/obj"


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


def check_env(backend: str = "openai"):
    """Check required env vars for the given backend. Default: openai."""
    required = REQUIRED_ENV_VARS if backend == "openai" else AIDP_REQUIRED_ENV_VARS
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
# Config (loaded after env)
# ============================================
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = "https://api.openai.com/v1/videos"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# ============================================
# TOS upload for network URL
# ============================================
SKILL_TYPE = "sora"

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
        ext = os.path.splitext(local_path)[1] or ".mp4"
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


# ============================================
# Image helpers
# ============================================
def load_image(source: str) -> Image.Image:
    if source.startswith(("http://", "https://")):
        logger.info(f"Downloading image from URL: {source[:80]}...")
        resp = requests.get(source, timeout=60)
        resp.raise_for_status()
        return Image.open(io.BytesIO(resp.content))
    return Image.open(source)


def detect_aspect_ratio(image_source: str) -> str:
    try:
        img = load_image(image_source)
        w, h = img.size
        if w / h >= 1.0:
            logger.info(f"Landscape image ({w}x{h}) -> 16:9")
            return "16:9"
        else:
            logger.info(f"Portrait image ({w}x{h}) -> 9:16")
            return "9:16"
    except Exception as e:
        logger.warning(f"Failed to detect aspect ratio: {e}, defaulting to 16:9")
        return "16:9"


def get_sora_size(aspect_ratio: str, resolution: str = "720p") -> str:
    size_map = {
        ("720p", "16:9"): "1280x720",
        ("720p", "9:16"): "720x1280",
        ("1080p", "16:9"): "1920x1080",
        ("1080p", "9:16"): "1080x1920",
    }
    return size_map.get((resolution, aspect_ratio), "1280x720")


# ============================================
# OpenAI Core API (original, unchanged)
# ============================================
def _get_headers():
    """Build headers with current API key (may have been set interactively)."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def create_video(prompt, first_frame=None, seconds=8, size=None, resolution="720p", model=None):
    if model is None:
        model = os.getenv("SORA_MODEL", "sora-2")
    headers = _get_headers()

    if first_frame:
        h_no_ct = {k: v for k, v in headers.items() if k.lower() != "content-type"}

        if size is None:
            aspect_ratio = detect_aspect_ratio(first_frame)
            size = get_sora_size(aspect_ratio, resolution)
            logger.info(f"Auto-detected size: {size}")

        w, h = map(int, size.lower().split("x"))

        img = load_image(first_frame).convert("RGB")
        img = ImageOps.exif_transpose(img)
        img.thumbnail((w, h), Image.LANCZOS)

        canvas = Image.new("RGB", (w, h), 0)
        x = (w - img.width) // 2
        y = (h - img.height) // 2
        canvas.paste(img, (x, y))

        scaled_file = tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False)
        canvas.save(scaled_file.name, format="JPEG", quality=95)
        scaled_file.close()

        payload = {"prompt": prompt, "seconds": seconds, "size": size, "model": model}

        logger.info(f"Creating I2V task | Model: {model} | Size: {size} | Duration: {seconds}s")

        with open(scaled_file.name, "rb") as f:
            files = [("input_reference", (scaled_file.name, f, "image/jpeg"))]
            resp = requests.post(BASE_URL, headers=h_no_ct, data=payload, files=files)

        os.unlink(scaled_file.name)
    else:
        if size is None:
            size = get_sora_size("16:9", resolution)
            logger.info(f"No reference, using default size: {size}")

        payload = {"prompt": prompt, "seconds": str(seconds), "size": str(size), "model": model}

        logger.info(f"Creating T2V task | Model: {model} | Size: {size} | Duration: {seconds}s")
        resp = requests.post(BASE_URL, headers=headers, json=payload)

    if resp.status_code == 200:
        data = resp.json()
        logger.info(f"Task created: {data['id']} (status: {data['status']})")
        return data
    else:
        logger.error(f"Failed to create task: {resp.status_code} - {resp.text}")
        return None


def check_video_status(video_id):
    url = f"{BASE_URL}/{video_id}"
    resp = requests.get(url, headers=_get_headers())
    if resp.status_code == 200:
        return resp.json()
    else:
        logger.error(f"Failed to check status: {resp.status_code} - {resp.text}")
        return None


def wait_for_completion(video_id, poll_interval=10, max_wait=600):
    logger.info("Waiting for video generation...")
    elapsed = 0

    while elapsed < max_wait:
        data = check_video_status(video_id)
        if not data:
            time.sleep(poll_interval)
            elapsed += poll_interval
            continue

        status = data["status"]
        progress = data.get("progress", 0)
        logger.info(f"  Status: {status} | Progress: {progress}% | Elapsed: {elapsed}s")

        if status == "completed":
            data["elapsed"] = elapsed
            return data
        elif status == "failed":
            error = data.get("error", "Unknown error")
            raise RuntimeError(f"Video generation failed: {error}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise RuntimeError(f"Timeout: Video did not complete within {max_wait}s")


def download_video(video_id, output_path):
    url = f"{BASE_URL}/{video_id}/content"
    logger.info(f"Downloading video to {output_path}...")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    resp = requests.get(url, headers=_get_headers(), stream=True)

    if resp.status_code == 200:
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
        logger.info(f"Video saved: {output_path} ({downloaded} bytes)")
        return True
    else:
        logger.error(f"Failed to download: {resp.status_code} - {resp.text}")
        return False


# ============================================
# AIDP backend
# ============================================
def _aidp_base():
    host = os.getenv("AIDP_HOST", AIDP_HOST)
    return AIDP_BASE_TMPL.format(host=host)


def _aidp_ak():
    return os.getenv("AIDP_AK", "")


AIDP_SORA2_VALID_SECONDS = {4, 8, 12}


def _snap_seconds_sora2(seconds: int) -> int:
    """Round seconds to nearest supported value (4, 8, 12)."""
    valid = sorted(AIDP_SORA2_VALID_SECONDS)
    nearest = min(valid, key=lambda v: abs(v - seconds))
    if nearest != seconds:
        logger.warning(f"azure-sora2 only supports seconds={valid}; rounding {seconds} -> {nearest}")
    return nearest


def aidp_create_video_sora2(prompt, first_frame=None, seconds=8, size=None, resolution="720p"):
    """Submit generation task for azure-sora2 via AIDP /v1/videos (multipart form-data).

    azure-sora2 API:  POST /sora/v1/videos?ak={ak}
    Params: prompt, size (e.g. 1280x720), seconds (4/8/12), model=azure-sora2
    I2V: add input_reference (image file)
    Must use multipart/form-data (never application/x-www-form-urlencoded).
    """
    ak = _aidp_ak()
    url = f"{_aidp_base()}/sora/v1/videos?ak={ak}"

    if size is None:
        if first_frame:
            aspect_ratio = detect_aspect_ratio(first_frame)
            size = get_sora_size(aspect_ratio, resolution)
            logger.info(f"Auto-detected size: {size}")
        else:
            size = get_sora_size("16:9", resolution)
            logger.info(f"Default size: {size}")

    seconds = _snap_seconds_sora2(seconds)

    # Build as multipart even for T2V (API requires multipart/form-data).
    # Use files-style tuples so requests always sends multipart.
    parts = [
        ("prompt", (None, prompt)),
        ("size", (None, size)),
        ("seconds", (None, str(seconds))),
        ("model", (None, "azure-sora2")),
    ]

    if first_frame:
        w, h = map(int, size.lower().split("x"))
        img = load_image(first_frame).convert("RGB")
        img = ImageOps.exif_transpose(img)
        img.thumbnail((w, h), Image.LANCZOS)
        canvas = Image.new("RGB", (w, h), 0)
        canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2))

        tmp_file = tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False)
        canvas.save(tmp_file.name, format="JPEG", quality=95)
        tmp_file.close()

        logger.info(f"AIDP azure-sora2 I2V | Size: {size} | Duration: {seconds}s")
        with open(tmp_file.name, "rb") as f:
            img_bytes = f.read()
        os.unlink(tmp_file.name)
        parts.append(("input_reference", ("reference.jpg", img_bytes, "image/jpeg")))
    else:
        logger.info(f"AIDP azure-sora2 T2V | Size: {size} | Duration: {seconds}s")

    resp = requests.post(url, files=parts)
    if resp.status_code == 200:
        result = resp.json()
        logger.info(f"Task created: {result['id']} (status: {result['status']})")
        return result
    else:
        logger.error(f"Failed to create task: {resp.status_code} - {resp.text}")
        return None


def aidp_create_video_sora1(prompt, seconds=5, size=None, resolution="720p"):
    """Submit generation task for azure-sora (legacy T2V only) via AIDP /v2/generate.

    azure-sora API:  POST /sora/v2/generate?ak={ak}
    Params: prompt, height, width, n_seconds, n_variants, model=azure-sora
    """
    ak = _aidp_ak()
    url = f"{_aidp_base()}/sora/v2/generate?ak={ak}"

    if size is None:
        size = get_sora_size("16:9", resolution)

    width, height = map(int, size.lower().split("x"))
    data = {
        "prompt": prompt,
        "height": str(height),
        "width": str(width),
        "n_seconds": str(seconds),
        "n_variants": "1",
        "model": "azure-sora",
    }

    logger.info(f"AIDP azure-sora T2V | Size: {size} | Duration: {seconds}s")
    resp = requests.post(url, data=data)
    if resp.status_code == 200:
        result = resp.json()
        logger.info(f"Task created: {result['id']} (status: {result['status']})")
        return result
    else:
        logger.error(f"Failed to create task: {resp.status_code} - {resp.text}")
        return None


def aidp_check_status(task_id, model):
    """Poll generation status for AIDP Sora (routes by model)."""
    ak = _aidp_ak()
    if model == "azure-sora2":
        url = f"{_aidp_base()}/sora/v1/videos/{task_id}?ak={ak}&product=azure_sora2"
        resp = requests.get(url)
    else:
        url = f"{_aidp_base()}/sora/v2/fetch?ak={ak}"
        resp = requests.post(url, json={"model": "azure-sora", "taskid": task_id})

    if resp.status_code == 200:
        return resp.json()
    logger.error(f"Failed to check status: {resp.status_code} - {resp.text}")
    return None


def aidp_download_from_tos(file_tos_url: str, output_path: str) -> bool:
    """Download video from AIDP TOS result URL.

    file_tos_url is a path like 'gpt-openapi-public-cn/video_xxx.mp4'.
    CN download: https://tosv.byted.org/obj/{file_tos_url}
    If file_tos_url is already a full URL (nontt pre-signed), use it directly.
    """
    if file_tos_url.startswith(("http://", "https://")):
        download_url = file_tos_url
    else:
        download_url = f"{TOS_CN_PREFIX}/{file_tos_url}"

    logger.info(f"Downloading from TOS: {download_url}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    resp = requests.get(download_url, stream=True, timeout=300)
    if resp.status_code == 200:
        downloaded = 0
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
        logger.info(f"Video saved: {output_path} ({downloaded} bytes)")
        return True
    else:
        logger.error(f"TOS download failed: {resp.status_code} - {resp.text[:200]}")
        return False


def aidp_wait_for_completion(task_id, model, poll_interval=10, max_wait=600):
    """Poll AIDP until completed; returns final status dict with 'elapsed' key."""
    elapsed = 0
    logger.info(f"Waiting for video generation (AIDP {model})...")

    while elapsed < max_wait:
        data = aidp_check_status(task_id, model)
        if not data:
            time.sleep(poll_interval)
            elapsed += poll_interval
            continue

        status = data.get("status", "unknown")
        progress = data.get("progress", "")
        progress_str = f" | Progress: {progress}%" if progress != "" else ""
        logger.info(f"  Status: {status}{progress_str} | Elapsed: {elapsed}s")

        if status in ("completed", "succeeded"):
            data["elapsed"] = elapsed
            return data
        elif status in ("failed", "error"):
            raise RuntimeError(f"Video generation failed: {data}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise RuntimeError(f"Timeout: Video did not complete within {max_wait}s")


# ============================================
# Main workflow
# ============================================
def generate_video(prompt, first_frame=None, output=None, seconds=8,
                   size=None, resolution="720p", model=None, backend="openai"):
    # azure-sora2 only supports 4/8/12s; snap happens inside aidp_create_video_sora2
    """Generate a video. backend='openai' uses OpenAI API; backend='aidp' uses ByteDance AIDP."""

    video_id = uuid.uuid4().hex[:8]
    if output is None:
        os.makedirs("generated", exist_ok=True)
        output = f"generated/{video_id}.mp4"

    # ── AIDP path ──────────────────────────────────────────────────────────
    if backend == "aidp":
        if model is None:
            model = os.getenv("SORA_AIDP_MODEL", AIDP_DEFAULT_MODEL)

        try:
            if model == "azure-sora2":
                task_data = aidp_create_video_sora2(prompt, first_frame, seconds, size, resolution)
            elif model == "azure-sora":
                if first_frame:
                    logger.warning("azure-sora does not support I2V; ignoring --first-frame")
                task_data = aidp_create_video_sora1(prompt, seconds, size, resolution)
            else:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": None, "gen_failed_reason": f"Unknown AIDP model: {model}"}

            if not task_data:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": None, "gen_failed_reason": "Task creation failed"}

            task_id = task_data["id"]
            final_status = aidp_wait_for_completion(task_id, model, poll_interval=10)

            file_tos_url = final_status.get("file_tos_url", "")
            if not file_tos_url:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": final_status.get("elapsed"), "gen_failed_reason": "file_tos_url empty"}

            success = aidp_download_from_tos(file_tos_url, output)
            if not success:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": final_status.get("elapsed"), "gen_failed_reason": "TOS download failed"}

            # Build public TOS URL (accessible within ByteDance network)
            if file_tos_url.startswith(("http://", "https://")):
                gen_url = file_tos_url
            else:
                gen_url = f"{TOS_CN_PREFIX}/{file_tos_url}"

            elapsed = final_status.get("elapsed")
            logger.info("=" * 60)
            logger.info(f"Generation complete! Output: {output}")
            logger.info(f"Elapsed: {elapsed}s | Model: {model}")
            logger.info(f"TOS URL: {gen_url}")
            logger.info("=" * 60)

            return {"gen_success": True, "gen_video_path": output, "gen_url": gen_url,
                    "gen_elapsed": elapsed, "gen_failed_reason": None}

        except Exception as e:
            logger.error(f"AIDP generation failed: {e}")
            return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                    "gen_elapsed": None, "gen_failed_reason": str(e)}

    # ── OpenAI path (original, unchanged) ─────────────────────────────────
    if model is None:
        model = os.getenv("SORA_MODEL", "sora-2")

    video_data = create_video(prompt, first_frame, seconds, size, resolution, model)
    if not video_data:
        return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                "gen_elapsed": None, "gen_failed_reason": "Task creation failed"}

    task_id = video_data["id"]
    final_status = wait_for_completion(task_id, poll_interval=10)
    success = download_video(task_id, output)

    if success:
        gen_url = _get_network_url(output)
        logger.info("=" * 60)
        logger.info(f"Generation complete! Output: {output}")
        logger.info(f"Elapsed: {final_status.get('elapsed', '?')}s")
        if gen_url:
            logger.info(f"URL: {gen_url[:100]}...")
        logger.info("=" * 60)
        return {"gen_success": True, "gen_video_path": output, "gen_url": gen_url,
                "gen_elapsed": final_status.get("elapsed"), "gen_failed_reason": None}
    else:
        return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                "gen_elapsed": None, "gen_failed_reason": "Failed to download video"}


def main():
    parser = argparse.ArgumentParser(description="Generate video with Sora")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--model", "-m", default=None,
                        help="Model: sora-2/sora-2-pro (openai) | azure-sora2/azure-sora (aidp)")
    parser.add_argument(
        "--backend",
        default="openai",
        choices=["openai", "aidp"],
        help="Backend: 'openai' (default, OpenAI public API) or 'aidp' (ByteDance AIDP)",
    )
    parser.add_argument("--first-frame", default=None, help="Reference image path/URL (for I2V)")
    parser.add_argument("--seconds", "-d", type=int, default=8, help="Duration in seconds (default: 8)")
    parser.add_argument("--size", "-s", default=None, help="Size like 1280x720 (auto-detected from image)")
    parser.add_argument("--resolution", default="720p", choices=["720p", "1080p"], help="Resolution tier")
    parser.add_argument("--output", "-o", default=None, help="Output file path")

    args = parser.parse_args()

    if not check_env(backend=args.backend):
        sys.exit(1)

    result = generate_video(
        prompt=args.prompt,
        first_frame=args.first_frame,
        output=args.output,
        seconds=args.seconds,
        size=args.size,
        resolution=args.resolution,
        model=args.model,
        backend=args.backend,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
