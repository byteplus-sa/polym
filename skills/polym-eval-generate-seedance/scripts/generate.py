#!/usr/bin/env python3
"""
Seedance Video Generation Skill Script

Generate videos using BytePlus Seedance models via Ark SDK.
Supports T2V, I2V (first frame / last frame / both), auto aspect ratio detection,
camera control, draft mode, and per-model parameter validation.

API Reference: https://docs.byteplus.com/en/docs/ModelArk/1366799

Usage:
    # T2V
    python generate.py --prompt "A cat playing" --model seedance-1-5-pro-251215

    # I2V (first frame)
    python generate.py --prompt "Scene animates" --first-frame photo.jpg

    # First & last frame control
    python generate.py --prompt "Transition" --first-frame a.jpg --last-frame b.jpg
"""

import os
import sys
import time
import json
import io
import re
import uuid
import argparse
import logging
from pathlib import Path

import requests
import tqdm
from PIL import Image
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _inject_system_truststore() -> None:
    """Use the OS trust store when truststore is available."""
    try:
        import truststore
        truststore.inject_into_ssl()
        logger.debug("Injected system trust store for TLS verification")
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"Failed to inject system trust store: {e}")


def _is_ssl_certificate_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    return (
        isinstance(exc, requests.exceptions.SSLError)
        or "certificate_verify_failed" in message
        or "unable to get local issuer certificate" in message
    )


def _log_request_error(exc: BaseException) -> None:
    if _is_ssl_certificate_error(exc):
        logger.error(f"TLS certificate verification failed: {exc}")
        logger.error(
            "Install the optional 'truststore' dependency so Python uses the OS "
            "certificate verifier, or check that the server is sending a complete "
            "certificate chain."
        )
    else:
        logger.error(f"Request error: {exc}")


_inject_system_truststore()

# ============================================
# .env management
# ============================================
SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_DIR / ".env"

REQUIRED_ENV_VARS = {
    "BYTEPLUS_API_KEY": {
        "description": "BytePlus Ark API Key",
        "help": "Get it from https://console.volcengine.com/ark",
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

    print(f"\n{'=' * 60}")
    print("All required environment variables configured!")
    print(f"{'=' * 60}\n")
    return True


_load_env()

# ============================================
# Config (loaded after env)
# ============================================
API_KEY = os.getenv("BYTEPLUS_API_KEY")
BASE_URL = os.getenv("BYTEPLUS_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3")


# ============================================
# TOS upload for network URL
# ============================================
SKILL_TYPE = "seedance"

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
# Model capabilities
# ============================================
MODEL_CAPABILITIES = {
    "seedance-1-5-pro": {
        "resolutions": ["480p", "720p", "1080p"],
        "ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "duration_range": (4, 12),
        "supports_first_frame": True,
        "supports_last_frame": True,
        "supports_camerafixed": True,
    },
    "seedance-1-0-pro-fast": {
        "resolutions": ["480p", "720p", "1080p"],
        "ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "duration_range": (2, 12),
        "supports_first_frame": True,
        "supports_last_frame": True,
        "supports_camerafixed": True,
        "t2v_ratio_restrictions": ["adaptive"],
        "i2v_camerafixed_not_supported": True,
    },
    "seedance-1-0-pro": {
        "resolutions": ["480p", "720p", "1080p"],
        "ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "duration_range": (2, 12),
        "supports_first_frame": True,
        "supports_last_frame": True,
        "supports_camerafixed": True,
        "t2v_ratio_restrictions": ["adaptive"],
        "i2v_camerafixed_not_supported": True,
    },
    "seedance-1-0-lite": {
        "resolutions": ["480p", "720p", "1080p"],
        "ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        "duration_range": (2, 12),
        "supports_first_frame": True,
        "supports_last_frame": True,
        "supports_camerafixed": True,
        "t2v_ratio_restrictions": ["adaptive"],
        "i2v_ratio_restrictions": ["adaptive"],
        "i2v_resolution_restrictions": ["1080p"],
        "i2v_camerafixed_not_supported": True,
    },
}

DEFAULT_CAPABILITIES = {
    "resolutions": ["480p", "720p", "1080p"],
    "ratios": ["16:9", "4:3", "1:1", "3:4", "9:16", "21:9"],
    "duration_range": (2, 12),
    "supports_first_frame": True,
    "supports_last_frame": True,
    "supports_camerafixed": True,
}


def get_model_capabilities(model: str) -> dict:
    normalized_model = model.lower().replace(".", "-")
    for key in MODEL_CAPABILITIES:
        if key in normalized_model:
            return MODEL_CAPABILITIES[key]
    logger.warning(f"Unknown model {model}, using default capabilities")
    return DEFAULT_CAPABILITIES


def validate_and_adjust_params(model, resolution, aspect_ratio, duration, has_first_frame, camerafixed):
    caps = get_model_capabilities(model)

    if resolution not in caps["resolutions"]:
        logger.warning(f"Model {model} doesn't support {resolution}, falling back to 720p")
        resolution = "720p"

    if has_first_frame and resolution in caps.get("i2v_resolution_restrictions", []):
        logger.warning(f"Model {model} I2V doesn't support {resolution}, falling back to 720p")
        resolution = "720p"

    if aspect_ratio not in caps["ratios"]:
        logger.warning(f"Model {model} doesn't support ratio {aspect_ratio}, falling back to 16:9")
        aspect_ratio = "16:9"

    if not has_first_frame and aspect_ratio in caps.get("t2v_ratio_restrictions", []):
        logger.warning(f"Model {model} T2V doesn't support ratio {aspect_ratio}, falling back to 16:9")
        aspect_ratio = "16:9"

    if has_first_frame and aspect_ratio in caps.get("i2v_ratio_restrictions", []):
        logger.warning(f"Model {model} I2V doesn't support ratio {aspect_ratio}, falling back to 16:9")
        aspect_ratio = "16:9"

    min_dur, max_dur = caps["duration_range"]
    duration = max(min_dur, min(max_dur, duration))

    if has_first_frame and caps.get("i2v_camerafixed_not_supported") and camerafixed:
        logger.warning(f"Model {model} I2V doesn't support camerafixed, disabling")
        camerafixed = False

    return resolution, aspect_ratio, duration, camerafixed


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


def upload_image_to_url(image_source: str) -> str:
    """Upload local image to TOS or return URL directly.
    
    Self-contained TOS upload — no external project dependencies required.
    Falls back to base64 data URL if TOS is not configured.
    """
    if not image_source:
        return None
    if image_source.startswith(("http://", "https://")):
        return image_source

    # Try TOS upload (self-contained)
    tos_bucket = os.getenv("TOS_BUCKET", "")
    tos_ak = os.getenv("TOS_ACCESS_KEY", "")
    tos_sk = os.getenv("TOS_SECRET_KEY", "")
    tos_endpoint = os.getenv("TOS_ENDPOINT", "tos-ap-southeast-1.bytepluses.com")
    tos_region = os.getenv("TOS_REGION", "ap-southeast-1")

    if tos_bucket and tos_ak and tos_sk:
        try:
            import tos
            import uuid
            import mimetypes
            from pathlib import Path

            content_type, _ = mimetypes.guess_type(image_source)
            if content_type is None:
                content_type = "application/octet-stream"

            ext = Path(image_source).suffix
            object_key = f"uploads/{uuid.uuid4().hex}{ext}"

            client = tos.TosClientV2(
                ak=tos_ak, sk=tos_sk,
                endpoint=tos_endpoint, region=tos_region,
            )
            with open(image_source, "rb") as f:
                client.put_object(bucket=tos_bucket, key=object_key, content=f, content_type=content_type)

            url = f"https://{tos_bucket}.{tos_endpoint.replace('https://', '').replace('http://', '')}/{object_key}"
            logger.info(f"Uploaded to TOS: {url[:80]}...")
            return url
        except ImportError:
            logger.warning("TOS SDK not installed (pip install tos), falling back to base64")
        except Exception as e:
            logger.warning(f"TOS upload failed: {e}, falling back to base64")

    # Fallback: encode as base64 data URL
    import base64
    with open(image_source, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = os.path.splitext(image_source)[1].lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime = mime_map.get(ext, "image/jpeg")
    logger.warning("TOS not configured or unavailable, using base64 data URL (may not work for all API endpoints)")
    return f"data:{mime};base64,{data}"


# ============================================
# Core API
# ============================================
def get_client():
    if not API_KEY:
        raise ValueError("BYTEPLUS_API_KEY is not set. Please configure it in .env file.")
    try:
        from byteplussdkarkruntime import Ark
    except ImportError:
        raise RuntimeError("byteplussdkarkruntime not installed. Run: pip install byteplussdkarkruntime")
    return Ark(api_key=API_KEY, base_url=BASE_URL)


def create_video(client, prompt, first_frame=None, last_frame=None, seconds=8,
                 size="720p", aspect_ratio=None, model=None, watermark=False,
                 camerafixed=False, draft=False, seed=None):
    has_ref = bool(first_frame or last_frame)

    if aspect_ratio is None or aspect_ratio == "auto":
        if first_frame:
            aspect_ratio = detect_aspect_ratio(first_frame)
        elif last_frame:
            aspect_ratio = detect_aspect_ratio(last_frame)
        else:
            aspect_ratio = "16:9"

    if draft and size != "480p":
        logger.warning(f"Draft mode forces 480p (was {size})")
        size = "480p"

    size, aspect_ratio, seconds, camerafixed = validate_and_adjust_params(
        model, size, aspect_ratio, seconds, has_ref, camerafixed
    )

    content = [{"type": "text", "text": prompt}]

    if first_frame:
        url = upload_image_to_url(first_frame)
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "first_frame"})

    if last_frame:
        url = upload_image_to_url(last_frame)
        content.append({"type": "image_url", "image_url": {"url": url}, "role": "last_frame"})

    mode = "T2V"
    if first_frame and last_frame:
        mode = "First&Last Frame"
    elif first_frame:
        mode = "I2V (First Frame)"
    elif last_frame:
        mode = "I2V (Last Frame)"

    logger.info(f"Creating {mode} task | Model: {model} | {size} {aspect_ratio} {seconds}s")

    extra_params = {"resolution": size, "ratio": aspect_ratio, "duration": seconds, "watermark": watermark}
    if camerafixed is not None:
        extra_params["camerafixed"] = camerafixed
    if draft:
        extra_params["draft"] = draft
    if seed is not None:
        extra_params["seed"] = seed

    task = client.content_generation.tasks.create(model=model, content=content, extra_body=extra_params)
    logger.info(f"Task created: {task.id}")
    return task.id


def wait_for_completion(client, task_id, poll_interval=3, max_wait=600):
    elapsed = 0
    last_status = None
    while elapsed < max_wait:
        task = client.content_generation.tasks.get(task_id=task_id)
        status = task.status
        if status != last_status:
            logger.info(f"[{task_id}] status = {status} ({elapsed}s)")
            last_status = status

        if status in ("succeeded", "completed", "done"):
            video_url = task.content.video_url if task.content else None
            return {"status": status, "video_url": video_url, "elapsed": elapsed}

        if status in ("failed", "error", "canceled"):
            error_msg = str(task.error) if task.error else "Unknown error"
            raise RuntimeError(f"Video generation failed: {error_msg}")

        time.sleep(poll_interval)
        elapsed += poll_interval

    raise RuntimeError(f"Timeout: Video did not complete within {max_wait}s")


def download_video(url, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    resp = requests.get(url, stream=True, timeout=120)
    total = int(resp.headers.get("Content-Length", 0))
    pbar = tqdm.tqdm(total=total, unit="B", unit_scale=True, desc="Downloading")
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))
    pbar.close()
    logger.info(f"Video saved: {output_path}")
    return True


# ============================================
# Main workflow
# ============================================
def generate_video(prompt, first_frame=None, last_frame=None, output=None,
                   seconds=8, size="720p", aspect_ratio=None, model=None,
                   watermark=False, camerafixed=False, draft=False, seed=None):
    if model is None:
        model = os.getenv("SEEDANCE_MODEL")
    if not model:
        raise ValueError("No model specified. Use --model or set SEEDANCE_MODEL in .env")

    video_id = uuid.uuid4().hex[:8]
    if output is None:
        os.makedirs("generated", exist_ok=True)
        output = f"generated/{video_id}.mp4"

    client = get_client()

    task_id = create_video(
        client, prompt,
        first_frame=first_frame, last_frame=last_frame,
        seconds=seconds, size=size, aspect_ratio=aspect_ratio,
        model=model, watermark=watermark, camerafixed=camerafixed,
        draft=draft, seed=seed,
    )

    result = wait_for_completion(client, task_id)
    video_url = result.get("video_url")
    if not video_url:
        raise RuntimeError("No video URL in response")

    download_video(video_url, output)
    gen_url = _get_network_url(output, api_url=video_url)

    logger.info("=" * 60)
    logger.info(f"Generation complete! Output: {output}")
    logger.info(f"Elapsed: {result.get('elapsed', '?')}s")
    if gen_url:
        logger.info(f"URL: {gen_url[:100]}...")
    logger.info("=" * 60)

    return {
        "gen_success": True,
        "gen_video_path": output,
        "gen_url": gen_url,
        "gen_elapsed": result.get("elapsed"),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate video with Seedance")
    parser.add_argument("--prompt", "-p", required=True, help="Text prompt")
    parser.add_argument("--model", "-m", default=None, help="Model ID (default: env SEEDANCE_MODEL)")
    parser.add_argument("--first-frame", default=None, help="First frame image path/URL")
    parser.add_argument("--last-frame", default=None, help="Last frame image path/URL")
    parser.add_argument("--seconds", "-d", type=int, default=8, help="Duration in seconds (default: 8)")
    parser.add_argument("--size", "-s", default="720p", choices=["480p", "720p", "1080p"], help="Resolution")
    parser.add_argument("--aspect-ratio", default=None, help="Aspect ratio (auto-detected from image)")
    parser.add_argument("--watermark", action="store_true", help="Add watermark")
    parser.add_argument("--camerafixed", action="store_true", help="Fix camera position")
    parser.add_argument("--draft", action="store_true", help="Draft mode (480p, faster)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--output", "-o", default=None, help="Output file path")

    args = parser.parse_args()

    if not check_env():
        sys.exit(1)

    try:
        result = generate_video(
            prompt=args.prompt,
            first_frame=args.first_frame,
            last_frame=args.last_frame,
            output=args.output,
            seconds=args.seconds,
            size=args.size,
            aspect_ratio=args.aspect_ratio,
            model=args.model,
            watermark=args.watermark,
            camerafixed=args.camerafixed,
            draft=args.draft,
            seed=args.seed,
        )
    except requests.RequestException as e:
        _log_request_error(e)
        sys.exit(1)
    except Exception as e:
        if _is_ssl_certificate_error(e):
            _log_request_error(e)
            sys.exit(1)
        raise

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
