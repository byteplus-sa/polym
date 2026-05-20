#!/usr/bin/env python3
"""
Veo Video Generation Skill Script

Generate videos using Google Veo models. Supports two backends:
  - vertexai (default): Google Cloud Vertex AI (google-genai SDK)
  - aidp: ByteDance AIDP model hub (requests + JSON)

Supports T2V and I2V (first frame reference), auto aspect ratio detection.

Usage:
    # T2V via Vertex AI (default)
    python generate.py --prompt "A golden retriever running through a meadow"

    # I2V via Vertex AI
    python generate.py --prompt "The scene comes alive" --first-frame photo.jpg

    # T2V via AIDP
    python generate.py --prompt "A golden retriever running" --backend aidp

    # I2V via AIDP
    python generate.py --prompt "The scene animates" --first-frame photo.jpg --backend aidp
"""

import os
import sys
import time
import json
import io
import uuid
import base64
import tempfile
import argparse
import logging
from pathlib import Path

import requests
from PIL import Image
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

# Try to import Google GenAI (only needed for vertexai backend)
try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ============================================
# .env management
# ============================================
SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_DIR / ".env"

REQUIRED_ENV_VARS = {
    "VERTEX_PROJECT": {
        "description": "Google Cloud Project ID",
        "help": "Your GCP project ID for Vertex AI",
    },
    "VERTEX_LOCATION": {
        "description": "Vertex AI Location",
        "help": "e.g. us-central1",
    },
}

AIDP_REQUIRED_ENV_VARS = {
    "AIDP_AK": {
        "description": "AIDP API Key (ak)",
        "help": "ByteDance AIDP platform AK",
    },
}

# AIDP defaults
AIDP_HOST = "aidp.bytedance.net"
AIDP_BASE_TMPL = "https://{host}/api/modelhub/online/multimodal/crawl"
AIDP_DEFAULT_MODEL = "veo-3.0-generate-001"

# TOS download base (CN)
TOS_CN_PREFIX = "https://tosv.byted.org/obj"

# Model name -> product name mapping for AIDP fetch endpoint.
# The product name is used as ?product= in the fetch request.
AIDP_VEO_PRODUCT_MAP = {
    "veo-3.0-generate-001": "google_veo_3.0_generate_001",
    "veo-3.0-fast-generate-001": "google_veo_3.0_fast_generate_001",
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


def check_env(backend: str = "vertexai"):
    required = REQUIRED_ENV_VARS if backend == "vertexai" else AIDP_REQUIRED_ENV_VARS
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
# TOS upload for network URL (Vertex AI path)
# ============================================
SKILL_TYPE = "veo"

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


def download_image_to_temp(url: str) -> str:
    logger.info(f"Downloading image from URL: {url[:80]}...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    ext = ".jpg"
    content_type = resp.headers.get("Content-Type", "").lower()
    if "png" in content_type:
        ext = ".png"
    elif "webp" in content_type:
        ext = ".webp"

    temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    temp_file.write(resp.content)
    temp_file.close()
    logger.info(f"Image saved to temp: {temp_file.name}")
    return temp_file.name


def image_to_base64(source: str) -> tuple[str, str]:
    """Return (base64_string, mime_type) for the image at source path or URL."""
    if source.startswith(("http://", "https://")):
        resp = requests.get(source, timeout=60)
        resp.raise_for_status()
        raw = resp.content
        ct = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        mime = ct if ct.startswith("image/") else "image/jpeg"
    else:
        with open(source, "rb") as f:
            raw = f.read()
        ext = Path(source).suffix.lower()
        mime = {"png": "image/png", "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")

    return base64.b64encode(raw).decode("utf-8"), mime


# ============================================
# Vertex AI Core API (original, unchanged)
# ============================================
def get_client():
    if not _GENAI_AVAILABLE:
        raise ImportError("google-genai not installed. Run: pip install google-genai")
    project = os.environ.get("VERTEX_PROJECT")
    location = os.environ.get("VERTEX_LOCATION")
    if not project or not location:
        raise ValueError("VERTEX_PROJECT and VERTEX_LOCATION must be set in .env")
    return genai.Client(vertexai=True, project=project, location=location)


def create_video(client, prompt, first_frame=None, seconds=8, aspect_ratio=None, model=None):
    if model is None:
        model = os.getenv("VEO_MODEL", "veo-3.0-generate-preview")

    if first_frame:
        if aspect_ratio is None:
            aspect_ratio = detect_aspect_ratio(first_frame)
            logger.info(f"Auto-detected aspect_ratio: {aspect_ratio}")

        local_path = first_frame
        if first_frame.startswith(("http://", "https://")):
            local_path = download_image_to_temp(first_frame)

        image = types.Image.from_file(location=local_path)
        logger.info(f"Creating I2V task | Model: {model} | {aspect_ratio} | {seconds}s")

        op = client.models.generate_videos(
            model=model,
            prompt=prompt,
            image=image,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=seconds,
                aspect_ratio=aspect_ratio,
            ),
        )
    else:
        if aspect_ratio is None:
            aspect_ratio = "16:9"
            logger.info(f"No reference, using default aspect_ratio: {aspect_ratio}")

        logger.info(f"Creating T2V task | Model: {model} | {aspect_ratio} | {seconds}s")

        op = client.models.generate_videos(
            model=model,
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                duration_seconds=seconds,
                enhance_prompt=True,
                aspect_ratio=aspect_ratio,
            ),
        )

    return op


def wait_for_completion(client, op, poll_interval=10, max_wait=600):
    logger.info("Waiting for video generation...")
    elapsed = 0

    while elapsed < max_wait:
        op = client.operations.get(op)

        if op.done:
            status = "Completed"
        elif op.error:
            status = "Failed"
        else:
            status = "In Progress"

        logger.info(f"  Status: {status} | Elapsed: {elapsed}s")

        if op.error:
            raise RuntimeError(f"Video generation failed: {op.error}")

        if op.done:
            if op.response and op.response.generated_videos:
                return op
            else:
                raise RuntimeError(f"Completed but no videos in response: {op.response}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise RuntimeError(f"Timeout: Video did not complete within {max_wait}s")


def download_video(op, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    try:
        generated_video = op.response.generated_videos[0]
        generated_video.video.save(output_path)
        logger.info(f"Video saved: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download video: {e}")
        return False


# ============================================
# AIDP backend
# ============================================
def _aidp_base():
    host = os.getenv("AIDP_HOST", AIDP_HOST)
    return AIDP_BASE_TMPL.format(host=host)


def _aidp_ak():
    return os.getenv("AIDP_AK", "")


def _aidp_product(model: str) -> str:
    """Return AIDP product name for status fetch endpoint."""
    product = AIDP_VEO_PRODUCT_MAP.get(model)
    if not product:
        logger.warning(f"Unknown AIDP product for model '{model}', using model name as fallback")
        return model.replace("-", "_").replace(".", "_")
    return product


def aidp_create_video(prompt, first_frame=None, seconds=8, aspect_ratio=None, model=None):
    """Submit Veo generation task via AIDP /veo/v1/generate.

    POST /veo/v1/generate?ak={ak}
    Body: {"model": "...", "instances": [{...}], "parameters": {"aspectRatio": "16:9"}}
    I2V: add "image": {"bytesBase64Encoded": "...", "mimeType": "image/jpeg"} in instance
    """
    if model is None:
        model = os.getenv("VEO_AIDP_MODEL", AIDP_DEFAULT_MODEL)

    ak = _aidp_ak()
    url = f"{_aidp_base()}/veo/v1/generate?ak={ak}"

    if aspect_ratio is None:
        if first_frame:
            aspect_ratio = detect_aspect_ratio(first_frame)
            logger.info(f"Auto-detected aspect_ratio: {aspect_ratio}")
        else:
            aspect_ratio = "16:9"
            logger.info(f"Default aspect_ratio: {aspect_ratio}")

    instance = {"prompt": prompt}

    if first_frame:
        b64, mime = image_to_base64(first_frame)
        instance["image"] = {"bytesBase64Encoded": b64, "mimeType": mime}
        logger.info(f"AIDP Veo I2V | Model: {model} | {aspect_ratio} | {seconds}s")
    else:
        logger.info(f"AIDP Veo T2V | Model: {model} | {aspect_ratio} | {seconds}s")

    body = {
        "model": model,
        "instances": [instance],
        "parameters": {
            "aspectRatio": aspect_ratio,
            "durationSeconds": seconds,
        },
    }

    resp = requests.post(url, json=body, headers={"Content-Type": "application/json"})
    if resp.status_code == 200:
        result = resp.json()
        operation_name = result.get("name", "")
        logger.info(f"Task created: {operation_name}")
        return result
    else:
        logger.error(f"Failed to create task: {resp.status_code} - {resp.text}")
        return None


def aidp_check_status(operation_name: str, model: str):
    """Poll Veo generation status via AIDP /veo/v1/fetch.

    POST /veo/v1/fetch?ak={ak}&product={product_name}
    Body: {"model": "...", "operationName": "..."}
    """
    ak = _aidp_ak()
    product = _aidp_product(model)
    url = f"{_aidp_base()}/veo/v1/fetch?ak={ak}&product={product}"

    resp = requests.post(
        url,
        json={"model": model, "operationName": operation_name},
        headers={"Content-Type": "application/json"},
    )
    if resp.status_code == 200:
        return resp.json()
    logger.error(f"Failed to check status: {resp.status_code} - {resp.text}")
    return None


def aidp_download_from_tos(gcs_uri: str, output_path: str) -> bool:
    """Download video from AIDP TOS result.

    gcs_uri is like 'gpt-openapi-public-cn/xxx_0.mp4'.
    Download URL: https://tosv.byted.org/obj/{gcs_uri}
    If gcs_uri is already a full URL (nontt pre-signed), use it directly.
    """
    if gcs_uri.startswith(("http://", "https://")):
        download_url = gcs_uri
    else:
        download_url = f"{TOS_CN_PREFIX}/{gcs_uri}"

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


def aidp_wait_for_completion(operation_name: str, model: str, poll_interval=10, max_wait=600):
    """Poll AIDP until done; returns final status dict with 'elapsed' key."""
    elapsed = 0
    logger.info(f"Waiting for video generation (AIDP {model})...")

    while elapsed < max_wait:
        data = aidp_check_status(operation_name, model)
        if not data:
            time.sleep(poll_interval)
            elapsed += poll_interval
            continue

        done = data.get("done", False)
        error = data.get("error", {})
        logger.info(f"  done={done} | Elapsed: {elapsed}s")

        if error and error.get("code") not in (None, 0, ""):
            raise RuntimeError(f"Video generation failed: {error}")

        if done:
            data["elapsed"] = elapsed
            return data

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise RuntimeError(f"Timeout: Video did not complete within {max_wait}s")


# ============================================
# Main workflow
# ============================================
def generate_video(prompt, first_frame=None, output=None, seconds=8,
                   aspect_ratio=None, model=None, backend="vertexai"):
    """Generate a video. backend='vertexai' uses Vertex AI; backend='aidp' uses ByteDance AIDP."""

    video_id = uuid.uuid4().hex[:8]
    if output is None:
        os.makedirs("generated", exist_ok=True)
        output = f"generated/{video_id}.mp4"

    # ── AIDP path ──────────────────────────────────────────────────────────
    if backend == "aidp":
        if model is None:
            model = os.getenv("VEO_AIDP_MODEL", AIDP_DEFAULT_MODEL)

        try:
            task_data = aidp_create_video(prompt, first_frame, seconds, aspect_ratio, model)
            if not task_data:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": None, "gen_failed_reason": "Task creation failed"}

            operation_name = task_data.get("name", "")
            if not operation_name:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": None, "gen_failed_reason": "No operation name in response"}

            final_status = aidp_wait_for_completion(operation_name, model, poll_interval=10)

            # Extract gcsUri from response.videos[0].gcsUri
            videos = (final_status.get("response") or {}).get("videos", [])
            if not videos:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": final_status.get("elapsed"),
                        "gen_failed_reason": "No videos in response"}

            gcs_uri = videos[0].get("gcsUri", "")
            if not gcs_uri:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": final_status.get("elapsed"),
                        "gen_failed_reason": "gcsUri is empty"}

            success = aidp_download_from_tos(gcs_uri, output)
            if not success:
                return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                        "gen_elapsed": final_status.get("elapsed"),
                        "gen_failed_reason": "TOS download failed"}

            # Build public URL
            if gcs_uri.startswith(("http://", "https://")):
                gen_url = gcs_uri
            else:
                gen_url = f"{TOS_CN_PREFIX}/{gcs_uri}"

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

    # ── Vertex AI path (original, unchanged) ──────────────────────────────
    if model is None:
        model = os.getenv("VEO_MODEL", "veo-3.0-generate-preview")

    client = get_client()
    operation = create_video(client, prompt, first_frame, seconds, aspect_ratio, model)

    if operation.error:
        return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                "gen_elapsed": None, "gen_failed_reason": str(operation.error)}

    operation = wait_for_completion(client, operation, poll_interval=10)
    success = download_video(operation, output)

    if success:
        gen_url = _get_network_url(output)
        logger.info("=" * 60)
        logger.info(f"Generation complete! Output: {output}")
        if gen_url:
            logger.info(f"URL: {gen_url[:100]}...")
        logger.info("=" * 60)
        return {"gen_success": True, "gen_video_path": output, "gen_url": gen_url,
                "gen_elapsed": None, "gen_failed_reason": None}
    else:
        return {"gen_success": False, "gen_video_path": None, "gen_url": None,
                "gen_elapsed": None, "gen_failed_reason": "Failed to download video"}


def main():
    parser = argparse.ArgumentParser(description="Generate video with Veo")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--model", "-m", default=None,
                        help="Model: veo-3.0-generate-preview (vertexai) | veo-3.1-generate-preview (aidp)")
    parser.add_argument(
        "--backend",
        default="vertexai",
        choices=["vertexai", "aidp"],
        help="Backend: 'vertexai' (default, Google Vertex AI) or 'aidp' (ByteDance AIDP)",
    )
    parser.add_argument("--first-frame", default=None, help="Reference image path/URL (for I2V)")
    parser.add_argument("--seconds", "-d", type=int, default=8, choices=[4, 6, 8],
                        help="Duration: 4, 6, or 8 seconds")
    parser.add_argument("--aspect-ratio", default=None, choices=["16:9", "9:16"],
                        help="Aspect ratio (auto-detected from image if not set)")
    parser.add_argument("--output", "-o", default=None, help="Output file path")

    args = parser.parse_args()

    if not check_env(backend=args.backend):
        sys.exit(1)

    result = generate_video(
        prompt=args.prompt,
        first_frame=args.first_frame,
        output=args.output,
        seconds=args.seconds,
        aspect_ratio=args.aspect_ratio,
        model=args.model,
        backend=args.backend,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
