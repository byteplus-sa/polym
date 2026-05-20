#!/usr/bin/env python3
"""
Seedream Image Generation Script

Generate images using BytePlus Seedream 4.0/4.5 AI model via the Ark API.
Supports all API parameters including guidance_scale, sequential_image_generation,
optimize_prompt_options, etc.

API Reference: https://docs.byteplus.com/en/docs/ModelArk/1541523

Usage:
    python generate.py --prompt "your prompt here"
    python generate.py --prompt "your prompt" --output path/to/output.png
    python generate.py --prompt "your prompt" --ref-images ref1.png ref2.png
    python generate.py --prompt "your prompt" --guidance-scale 7.5 --optimize-prompt
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

import requests
import tqdm
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Load environment variables
SKILL_DIR = Path(__file__).resolve().parent.parent


def _get_env_path() -> Path:
    """Get path to .env file in skill directory."""
    return SKILL_DIR / ".env"


def load_env_file():
    """Load .env file from skill directory."""
    env_path = _get_env_path()
    
    if env_path.exists():
        load_dotenv(env_path, override=False)
        logger.debug(f"Loaded .env from: {env_path}")
    else:
        load_dotenv()
        logger.warning(f".env not found at {env_path}, using default load_dotenv()")


def _append_env_var(key: str, value: str) -> None:
    """Append an environment variable to the .env file and set it in os.environ."""
    env_path = _get_env_path()
    
    # Read existing content
    existing_content = ""
    if env_path.exists():
        existing_content = env_path.read_text()
    
    # Check if key already exists (replace it)
    lines = existing_content.splitlines()
    found = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f'{key}="'):
            lines[i] = f'{key}={value}'
            found = True
            break
    
    if found:
        env_path.write_text("\n".join(lines) + "\n")
    else:
        # Append to end
        with open(env_path, "a") as f:
            if existing_content and not existing_content.endswith("\n"):
                f.write("\n")
            f.write(f"{key}={value}\n")
    
    # Also set in current process
    os.environ[key] = value
    logger.info(f"✓ Set {key} in {env_path}")


def check_and_prompt_env_vars(need_tos: bool = False) -> bool:
    """
    Check required environment variables. If missing, prompt the user to provide them
    and auto-write to .env file.
    
    Args:
        need_tos: Whether TOS configuration is needed (for reference images)
    
    Returns:
        True if all required vars are set, False if user chose to abort
    """
    env_path = _get_env_path()
    
    # Create .env if it doesn't exist
    if not env_path.exists():
        print(f"\n⚠ .env file not found at {env_path}")
        print("Creating .env file...")
        env_path.touch()
    
    # Required variables
    required_vars = {
        "BYTEPLUS_API_KEY": {
            "description": "BytePlus Ark API Key",
            "help": "Get it from BytePlus Ark console: https://console.volcengine.com/ark",
        },
    }
    
    # Check BYTEPLUS_BASE_URL (has default, but still good to verify)
    if not os.getenv("BYTEPLUS_BASE_URL"):
        _append_env_var("BYTEPLUS_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3")
        print("✓ Set BYTEPLUS_BASE_URL to default: https://ark.ap-southeast.bytepluses.com/api/v3")
    
    # TOS variables (only if needed)
    if need_tos:
        required_vars.update({
            "TOS_BUCKET": {
                "description": "TOS Bucket Name",
                "help": "Your BytePlus TOS bucket for uploading reference images",
            },
            "TOS_ACCESS_KEY": {
                "description": "TOS Access Key",
                "help": "Your BytePlus TOS access key",
            },
            "TOS_SECRET_KEY": {
                "description": "TOS Secret Key",
                "help": "Your BytePlus TOS secret key",
            },
        })
    
    # Check each required variable
    missing_vars = []
    for var_name, var_info in required_vars.items():
        value = os.getenv(var_name, "").strip().strip('"').strip("'")
        if not value:
            missing_vars.append((var_name, var_info))
    
    if not missing_vars:
        return True  # All variables are set
    
    # Report missing variables and prompt user
    print("\n" + "=" * 60)
    print("⚠ Missing required environment variables:")
    print("=" * 60)
    for var_name, var_info in missing_vars:
        print(f"\n  • {var_name}: {var_info['description']}")
        print(f"    {var_info['help']}")
    print("\n" + "-" * 60)
    
    for var_name, var_info in missing_vars:
        while True:
            value = input(f"\nEnter {var_info['description']} ({var_name})\n  [or 'skip' to abort]: ").strip()
            
            if value.lower() == 'skip':
                print(f"\n✗ Aborted. Please set {var_name} manually in {env_path}")
                return False
            
            if value:
                _append_env_var(var_name, value)
                print(f"  ✓ {var_name} saved to .env")
                break
            else:
                print("  ✗ Value cannot be empty. Try again or type 'skip' to abort.")
    
    print("\n" + "=" * 60)
    print("✓ All required environment variables are configured!")
    print("=" * 60 + "\n")
    return True


load_env_file()

# API Configuration
API_KEY = os.getenv("BYTEPLUS_API_KEY")
BASE_URL = os.getenv("BYTEPLUS_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3")
DEFAULT_MODEL = os.getenv("SEEDREAM_MODEL", "seedream-4-5-251128")

# TOS Configuration (for reference images)
TOS_ENDPOINT = os.getenv("TOS_ENDPOINT", "tos-ap-southeast-1.bytepluses.com")
TOS_BUCKET = os.getenv("TOS_BUCKET", "")
TOS_ACCESS_KEY = os.getenv("TOS_ACCESS_KEY", "")
TOS_SECRET_KEY = os.getenv("TOS_SECRET_KEY", "")
TOS_REGION = os.getenv("TOS_REGION", "ap-southeast-1")

USE_TOS = bool(TOS_BUCKET and TOS_ACCESS_KEY and TOS_SECRET_KEY)


# ============================================
# TOS upload for network URL (presigned)
# ============================================
SKILL_TYPE = "seedream"

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

    env_path = _get_env_path()
    print(f"\n{'=' * 60}")
    print("TOS not configured — needed to return a network URL")
    print(f"(.env: {env_path})")
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
                print(f"  Saved {var} to .env")
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


@dataclass
class SeedreamConfig:
    """Configuration for Seedream image generation.
    
    All parameters based on BytePlus Seedream 4.0-4.5 API:
    https://docs.byteplus.com/en/docs/ModelArk/1541523
    """
    # Required
    prompt: str = ""
    
    # Model
    model: str = field(default_factory=lambda: DEFAULT_MODEL)
    
    # Image parameters
    size: str = "2K"  # Supported: "1K", "2K", "4K" (Note: 4.5 doesn't support 1K)
    seed: Optional[int] = None  # Random seed for reproducibility
    
    # Reference images
    image: Optional[List[str]] = None  # Array of reference image URLs
    
    # Sequential image generation (for multi-panel/consistent outputs)
    sequential_image_generation: str = "disabled"  # "enabled" or "disabled"
    sequential_image_generation_options: Optional[Dict[str, Any]] = None  # e.g., {"n": 2}
    
    # Generation control
    guidance_scale: Optional[float] = None  # Controls prompt adherence (1.0-20.0, default ~7.0)
    
    # Response options
    stream: bool = False  # Whether to stream response
    response_format: str = "url"  # "url" or "b64_json"
    
    # Watermark
    watermark: bool = False  # Whether to add watermark
    
    # Prompt optimization (new feature)
    optimize_prompt_options: Optional[Dict[str, Any]] = None  # e.g., {"enabled": true}
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to API payload, excluding None values."""
        payload = {
            "model": self.model,
            "prompt": self.prompt,
            "size": self.size,
            "stream": self.stream,
            "response_format": self.response_format,
            "watermark": self.watermark,
        }
        
        # Add optional parameters only if set
        if self.seed is not None:
            payload["seed"] = self.seed
            
        if self.image:
            payload["image"] = self.image
            payload["sequential_image_generation"] = self.sequential_image_generation
            
        if self.sequential_image_generation_options:
            payload["sequential_image_generation_options"] = self.sequential_image_generation_options
            
        if self.guidance_scale is not None:
            payload["guidance_scale"] = self.guidance_scale
            
        if self.optimize_prompt_options:
            payload["optimize_prompt_options"] = self.optimize_prompt_options
        
        return payload


def upload_to_tos(file_path: str) -> Optional[str]:
    """Upload a file to TOS and return the URL."""
    if not USE_TOS:
        logger.error("TOS not configured. Cannot upload reference images.")
        logger.error("Please set TOS_BUCKET, TOS_ACCESS_KEY, TOS_SECRET_KEY in .env")
        return None
    
    try:
        import tos
    except ImportError:
        logger.error("TOS SDK not installed. Run: pip install tos")
        return None
    
    try:
        import uuid
        import mimetypes
        
        # Check file exists
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # Detect content type
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = "application/octet-stream"
        
        # Generate object key
        ext = Path(file_path).suffix
        object_key = f"uploads/{uuid.uuid4().hex}{ext}"
        
        # Create TOS client
        client = tos.TosClientV2(
            ak=TOS_ACCESS_KEY,
            sk=TOS_SECRET_KEY,
            endpoint=TOS_ENDPOINT,
            region=TOS_REGION,
        )
        
        # Upload file
        with open(file_path, "rb") as f:
            client.put_object(
                bucket=TOS_BUCKET,
                key=object_key,
                content=f,
                content_type=content_type,
            )
        
        # Build URL
        url = f"https://{TOS_BUCKET}.{TOS_ENDPOINT.replace('https://', '').replace('http://', '')}/{object_key}"
        logger.info(f"Uploaded {file_path} to TOS: {url}")
        return url
        
    except Exception as e:
        logger.error(f"Failed to upload {file_path} to TOS: {e}")
        return None


def generate_image(
    config: SeedreamConfig,
    output_path: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Optional[str]:
    """
    Generate an image using Seedream model.
    
    Args:
        config: SeedreamConfig object with all generation parameters
        output_path: Path to save the generated image
        api_key: Optional API key (defaults to env)
        base_url: Optional base URL (defaults to env)
    
    Returns:
        Dict with gen_success, gen_image_path, gen_url
    """
    # Use provided or default API key/URL
    api_key = api_key or os.getenv("BYTEPLUS_API_KEY") or API_KEY
    base_url = base_url or os.getenv("BYTEPLUS_BASE_URL") or BASE_URL
    
    # Strip quotes that python-dotenv may leave for special var names
    if api_key:
        api_key = api_key.strip('"').strip("'")
    if base_url:
        base_url = base_url.strip('"').strip("'")
    
    # Validate API key
    if not api_key:
        logger.error("BYTEPLUS_API_KEY is not set. Please configure it in .env file.")
        logger.error("Run the script interactively to auto-configure, or set it manually.")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Build payload from config
    payload = config.to_payload()
    
    logger.info(f"Generating image with prompt: {config.prompt[:100]}...")
    logger.info(f"Model: {config.model}, Size: {config.size}")
    if config.guidance_scale:
        logger.info(f"Guidance scale: {config.guidance_scale}")
    if config.seed:
        logger.info(f"Seed: {config.seed}")
    if config.optimize_prompt_options:
        logger.info(f"Prompt optimization: enabled")
    
    try:
        # Make API request
        url = f"{base_url}/images/generations"
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
        
        if config.stream:
            # Streaming response
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=600,
                stream=True
            )
        else:
            # Standard response
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=600
            )
        
        logger.debug(f"Response status: {response.status_code}")
        
        # Handle errors
        if response.status_code != 200:
            try:
                error_detail = response.json()
                logger.error(f"API Error: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
            except:
                logger.error(f"API Error: {response.text[:500]}")
            return {"gen_success": False, "gen_image_path": None, "gen_url": None}
        
        # Parse response
        res = response.json()
        
        # Check for API errors
        if "error" in res:
            logger.error(f"API Error: {res['error'].get('message', 'Unknown error')}")
            return {"gen_success": False, "gen_image_path": None, "gen_url": None}
        
        api_url = None
        # Handle response format
        if config.response_format == "url":
            api_url = res['data'][0]['url']
            logger.info(f"Image generated successfully. Downloading...")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Download image
            resp = requests.get(api_url, stream=True, timeout=120)
            total = int(resp.headers.get("Content-Length") or 0)
            
            with tqdm.tqdm(total=total, unit="B", unit_scale=True, desc="Downloading") as pbar:
                with open(output_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        
        elif config.response_format == "b64_json":
            import base64
            b64_data = res['data'][0]['b64_json']
            
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(b64_data))
        
        logger.info(f"✓ Image saved to: {output_path}")
        
        if 'usage' in res:
            logger.info(f"Usage: {res['usage']}")
        
        gen_url = _get_network_url(output_path, api_url=api_url)
        if gen_url:
            logger.info(f"URL: {gen_url[:100]}...")
        
        return {"gen_success": True, "gen_image_path": output_path, "gen_url": gen_url}
        
    except requests.Timeout:
        logger.error("Request timed out. Try again later.")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}
    except requests.RequestException as e:
        logger.error(f"Request error: {e}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}
    except json.JSONDecodeError:
        logger.error("Invalid JSON response from API")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return {"gen_success": False, "gen_image_path": None, "gen_url": None}


def process_reference_images(ref_image_paths: List[str]) -> List[str]:
    """Process reference images, uploading local files to TOS if needed."""
    ref_images = []
    for path in ref_image_paths:
        # If already a URL, use directly
        if path.startswith('http://') or path.startswith('https://'):
            ref_images.append(path)
        else:
            # Upload to TOS
            url = upload_to_tos(path)
            if url is None:
                logger.error(f"Failed to upload reference image: {path}")
                return []
            ref_images.append(url)
    return ref_images


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using BytePlus Seedream 4.0/4.5 AI model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic generation
  %(prog)s --prompt "A serene mountain landscape at sunset"
  
  # With custom size and model
  %(prog)s --prompt "A futuristic city" --size 4K --model seedream-4-5-251128
  
  # With guidance scale for stronger prompt adherence
  %(prog)s --prompt "A photorealistic cat" --guidance-scale 10.0
  
  # With reference images
  %(prog)s --prompt "A cat in this style" --ref-images style.png
  
  # With seed for reproducibility
  %(prog)s --prompt "Abstract art" --seed 42
  
  # With prompt optimization
  %(prog)s --prompt "A simple mountain" --optimize-prompt
  
  # Sequential generation for multi-panel output
  %(prog)s --prompt "Comic strip panels" --sequential --num-images 4
  
  # Get base64 response instead of URL
  %(prog)s --prompt "A flower" --response-format b64_json

API Reference: https://docs.byteplus.com/en/docs/ModelArk/1541523
        """
    )
    
    # Required
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Text description for image generation"
    )
    
    # Output
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: generated/{timestamp}.png)"
    )
    
    # Model
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL,
        help=f"Model name (default: {DEFAULT_MODEL}). Options: seedream-4-0-250828, seedream-4-5-251128"
    )
    
    # Size
    parser.add_argument(
        "--size", "-s",
        default="2K",
        choices=["1K", "2K", "4K"],
        help="Image size (default: 2K). Note: Seedream 4.5 doesn't support 1K"
    )
    
    # Seed
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility"
    )
    
    # Reference images
    parser.add_argument(
        "--ref-images", "-r",
        nargs="+",
        help="Reference image paths or URLs (space-separated)"
    )
    
    # Guidance scale
    parser.add_argument(
        "--guidance-scale", "-g",
        type=float,
        help="Controls prompt adherence (1.0-20.0, higher = stricter)"
    )
    
    # Sequential generation
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Enable sequential image generation for consistent multi-panel outputs"
    )
    parser.add_argument(
        "--num-images", "-n",
        type=int,
        default=1,
        help="Number of images to generate in sequential mode (default: 1)"
    )
    
    # Response format
    parser.add_argument(
        "--response-format",
        choices=["url", "b64_json"],
        default="url",
        help="Response format (default: url)"
    )
    
    # Watermark
    parser.add_argument(
        "--watermark",
        action="store_true",
        help="Add watermark to generated image"
    )
    
    # Prompt optimization
    parser.add_argument(
        "--optimize-prompt",
        action="store_true",
        help="Enable prompt optimization for better results"
    )
    
    # Stream
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Enable streaming response"
    )
    
    # Verbose
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check required environment variables (interactive prompt if missing)
    need_tos = bool(args.ref_images)
    if not check_and_prompt_env_vars(need_tos=need_tos):
        print("\n✗ Required environment variables not configured. Exiting.")
        sys.exit(1)
    
    # Reload globals after potential .env updates
    global API_KEY, BASE_URL, TOS_BUCKET, TOS_ACCESS_KEY, TOS_SECRET_KEY, USE_TOS
    API_KEY = os.getenv("BYTEPLUS_API_KEY", "")
    BASE_URL = os.getenv("BYTEPLUS_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3")
    TOS_BUCKET = os.getenv("TOS_BUCKET", "")
    TOS_ACCESS_KEY = os.getenv("TOS_ACCESS_KEY", "")
    TOS_SECRET_KEY = os.getenv("TOS_SECRET_KEY", "")
    USE_TOS = bool(TOS_BUCKET and TOS_ACCESS_KEY and TOS_SECRET_KEY)
    
    # Generate output path if not specified
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"generated/{timestamp}.png"
    
    # Process reference images
    ref_images = None
    if args.ref_images:
        ref_images = process_reference_images(args.ref_images)
        if not ref_images and args.ref_images:
            print("\n✗ Failed to process reference images")
            sys.exit(1)
    
    # Build sequential generation options
    seq_options = None
    if args.sequential and args.num_images > 1:
        seq_options = {"n": args.num_images}
    
    # Build optimize prompt options
    optimize_options = None
    if args.optimize_prompt:
        optimize_options = {"enabled": True}
    
    # Create config
    config = SeedreamConfig(
        prompt=args.prompt,
        model=args.model,
        size=args.size,
        seed=args.seed,
        image=ref_images,
        sequential_image_generation="enabled" if args.sequential else "disabled",
        sequential_image_generation_options=seq_options,
        guidance_scale=args.guidance_scale,
        stream=args.stream,
        response_format=args.response_format,
        watermark=args.watermark,
        optimize_prompt_options=optimize_options,
    )
    
    # Generate the image
    result = generate_image(
        config=config,
        output_path=args.output,
    )
    
    if result and result.get("gen_success"):
        print(f"\n✓ Image generated successfully: {result['gen_image_path']}")
        if result.get("gen_url"):
            print(f"URL: {result['gen_url'][:100]}...")
    else:
        print("\n✗ Image generation failed")
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
