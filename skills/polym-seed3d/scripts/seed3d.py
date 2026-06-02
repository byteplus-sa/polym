#!/usr/bin/env python3
"""CLI wrapper for Volcengine Ark Seed3D (doubao-seed3d) image/text -> 3D generation.

Seed3D is an ASYNC task API. This wrapper does the full round-trip:
  1. POST  /contents/generations/tasks         -> {"id": "cgt-..."}
  2. GET   /contents/generations/tasks/{id}     -> poll until status is terminal
  3. on "succeeded", content.file_url is a .zip containing pbr/mesh_textured_pbr.glb
     (optionally download + extract the .glb locally)

Verified working 2026-06-02 against the domestic Volcengine Ark endpoint
(https://ark.cn-beijing.volces.com/api/v3) with model doubao-seed3d-2-0-260328.

Endpoint note:
  - Domestic Volcengine (火山引擎):  https://ark.cn-beijing.volces.com/api/v3   <- default
  - As of 2026-06, Seed3D is domestic-only; BytePlus overseas ModelArk does NOT
    list a Seed3D model (it offers Hyper3D / Hitem3d instead).
"""

import argparse
import base64
import json
import mimetypes
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Optional

DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_MODEL = "doubao-seed3d-2-0-260328"
TASKS_PATH = "/contents/generations/tasks"
TERMINAL = {"succeeded", "failed", "cancelled", "canceled"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate a 3D model with Volcengine Ark Seed3D (async submit + poll).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = p.add_argument_group("input (provide --image and/or --prompt)")
    src.add_argument(
        "--image",
        help="Reference image: http(s) URL, data: URL, or local file path "
        "(local files are inlined as a base64 data URL).",
    )
    src.add_argument(
        "--prompt",
        help="Text prompt. Use alone for text-to-3D, or together with --image to steer the result.",
    )

    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model ID. Default: {DEFAULT_MODEL}")
    p.add_argument(
        "--base-url",
        default=os.getenv("ARK_BASE_URL", DEFAULT_BASE_URL),
        help=f"Ark base URL. Default: {DEFAULT_BASE_URL}",
    )

    # Optional generation params (echoed in the task object; best-effort, override with --extra).
    p.add_argument(
        "--subdivision-level",
        choices=("low", "medium", "high"),
        help="Mesh subdivision / detail level. Server default: medium.",
    )
    p.add_argument(
        "--file-format",
        choices=("glb", "obj", "fbx", "usdz", "ply", "stl"),
        help="Output 3D file format. Server default: glb.",
    )
    p.add_argument(
        "--draft",
        dest="draft",
        action="store_true",
        help="Request a faster draft-quality result.",
    )

    p.add_argument(
        "--extra",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra top-level request field. VALUE may be JSON. Repeatable.",
    )

    # Polling / output
    p.add_argument("--poll-interval", type=int, default=10, help="Seconds between polls (default 10).")
    p.add_argument("--max-wait", type=int, default=900, help="Max seconds to wait (default 900 = 15 min).")
    p.add_argument("--timeout", type=int, default=120, help="Per-request HTTP timeout in seconds (default 120).")
    p.add_argument(
        "--output-dir",
        help="Directory to write task.json, and (if --download) the .zip + extracted .glb.",
    )
    p.add_argument(
        "--download",
        action="store_true",
        help="Download the result .zip and extract its contents into --output-dir.",
    )
    p.add_argument(
        "--task-id",
        help="Skip submission and just poll/fetch an existing task id (cgt-...).",
    )
    p.add_argument("--dry-run", action="store_true", help="Print the request body and exit.")
    return p.parse_args()


def jsonish(value: str):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        low = value.lower()
        if low in ("true", "false"):
            return low == "true"
        if low == "null":
            return None
        return value


def file_to_data_url(path_str: str) -> str:
    path = pathlib.Path(path_str).expanduser().resolve()
    data = path.read_bytes()
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def normalize_image(value: str) -> str:
    scheme = urllib.parse.urlparse(value).scheme
    if scheme in {"http", "https", "data"}:
        return value
    return file_to_data_url(value)


def build_payload(args: argparse.Namespace) -> dict:
    content = []
    if args.image:
        content.append({"type": "image_url", "image_url": {"url": normalize_image(args.image)}})
    if args.prompt:
        content.append({"type": "text", "text": args.prompt})
    if not content:
        raise ValueError("Provide --image and/or --prompt.")

    payload = {"model": args.model, "content": content}
    if args.subdivision_level:
        payload["subdivisionlevel"] = args.subdivision_level
    if args.file_format:
        payload["fileformat"] = args.file_format
    if args.draft:
        payload["draft"] = True
    for item in args.extra:
        if "=" not in item:
            raise ValueError(f"Invalid --extra value: {item!r}. Expected KEY=VALUE.")
        k, v = item.split("=", 1)
        payload[k.strip()] = jsonish(v.strip())
    return payload


def http_json(method: str, url: str, api_key: str, timeout: int, body: Optional[dict] = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url=url,
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ark {method} {url} failed (HTTP {exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ark {method} {url} failed: {exc}") from exc


def submit(base_url: str, api_key: str, payload: dict, timeout: int) -> str:
    url = base_url.rstrip("/") + TASKS_PATH
    resp = http_json("POST", url, api_key, timeout, body=payload)
    task_id = resp.get("id")
    if not task_id:
        raise RuntimeError(f"No task id in submit response: {resp}")
    return task_id


def poll(base_url: str, api_key: str, task_id: str, interval: int, max_wait: int, timeout: int) -> dict:
    url = base_url.rstrip("/") + TASKS_PATH + "/" + task_id
    waited = 0
    while True:
        task = http_json("GET", url, api_key, timeout)
        status = task.get("status", "")
        print(f"  [{time.strftime('%H:%M:%S')}] status={status} (waited {waited}s)", file=sys.stderr)
        if status in TERMINAL:
            return task
        if waited >= max_wait:
            raise TimeoutError(f"Task {task_id} not finished after {max_wait}s (last status={status}).")
        time.sleep(interval)
        waited += interval


def download_and_extract(file_url: str, output_dir: pathlib.Path, timeout: int) -> list:
    zip_path = output_dir / "model.zip"
    req = urllib.request.Request(file_url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        zip_path.write_bytes(resp.read())
    extracted = []
    extract_dir = output_dir / "model"
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
        extracted = [str(extract_dir / n) for n in zf.namelist()]
    return [str(zip_path)] + extracted


def main() -> int:
    args = parse_args()

    if args.dry_run and not args.task_id:
        try:
            print(json.dumps(build_payload(args), indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"Failed to build request: {exc}", file=sys.stderr)
            return 2
        return 0

    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        print(
            'ARK_API_KEY is not set. Ask the user for the DOMESTIC Volcengine Ark key, '
            'run export ARK_API_KEY="..." in this shell, then rerun.',
            file=sys.stderr,
        )
        return 2

    output_dir = None
    if args.output_dir:
        output_dir = pathlib.Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.task_id:
            task_id = args.task_id
            print(f"Polling existing task {task_id} ...", file=sys.stderr)
        else:
            payload = build_payload(args)
            task_id = submit(args.base_url, api_key, payload, args.timeout)
            print(f"Submitted task: {task_id}", file=sys.stderr)

        task = poll(args.base_url, api_key, task_id, args.poll_interval, args.max_wait, args.timeout)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    status = task.get("status")
    if output_dir:
        (output_dir / "task.json").write_text(
            json.dumps(task, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    print(json.dumps(task, indent=2, ensure_ascii=False))

    if status != "succeeded":
        print(f"\nTask did not succeed (status={status}).", file=sys.stderr)
        return 1

    file_url = (task.get("content") or {}).get("file_url")
    if file_url:
        print(f"\nResult file_url:\n{file_url}", file=sys.stderr)

    if args.download and file_url and output_dir:
        try:
            files = download_and_extract(file_url, output_dir, args.timeout)
            print("\nDownloaded / extracted:", file=sys.stderr)
            for f in files:
                print(f"  {f}", file=sys.stderr)
        except Exception as exc:
            print(f"Task succeeded but download/extract failed: {exc}", file=sys.stderr)
            return 1
    elif args.download and not output_dir:
        print("--download requires --output-dir.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
