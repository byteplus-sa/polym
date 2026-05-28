#!/usr/bin/env python3
"""
Upload final MP4 to Lark Drive via lark-cli, return shareable URL.

Usage:
    python3 upload_to_lark.py dist/main.mp4
    python3 upload_to_lark.py dist/main.mp4 --folder-token fldcnXXX
    python3 upload_to_lark.py dist/main.mp4 --send-to-self
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_cli(args):
    """Run lark-cli with structured args, return parsed JSON."""
    cmd = ["lark-cli"] + args + ["--output", "json"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip()
    try:
        return json.loads(r.stdout), None
    except json.JSONDecodeError as e:
        return None, f"JSON parse failed: {e}; raw: {r.stdout[:200]}"


def check_lark_cli():
    if not shutil.which("lark-cli"):
        print("ERROR: lark-cli not found. Install: npm install -g @larksuite/cli", file=sys.stderr)
        sys.exit(1)


def check_auth():
    """Verify user is authenticated."""
    r = subprocess.run(["lark-cli", "auth", "status"], capture_output=True, text=True)
    if r.returncode != 0 or "authenticated" not in r.stdout.lower():
        print("Not authenticated to Lark. Run: lark-cli auth login --recommend", file=sys.stderr)
        sys.exit(1)


def upload(file_path, folder_token=None):
    args = ["drive", "+upload", "--file", str(file_path)]
    if folder_token:
        args += ["--folder-token", folder_token]
    return run_cli(args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="Path to MP4 to upload")
    ap.add_argument("--folder-token", default=None,
                    help="Lark folder token (extract from folder URL after /folder/)")
    ap.add_argument("--send-to-self", action="store_true",
                    help="After upload, DM yourself the link")
    ap.add_argument("--chat-id", default=None,
                    help="If provided, send the URL to this Lark chat")
    args = ap.parse_args()

    file_path = Path(args.file).resolve()
    if not file_path.exists():
        print(f"ERROR: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    check_lark_cli()
    check_auth()

    print(f"Uploading {file_path.name} ({file_path.stat().st_size // 1024 // 1024} MB) to Lark...",
          file=sys.stderr)

    result, err = upload(file_path, args.folder_token)
    if err:
        print(f"Upload failed: {err}", file=sys.stderr)
        sys.exit(1)

    data = result.get("data", {})
    file_token = data.get("file_token")
    url = data.get("url")

    if not file_token:
        print(f"Unexpected response (no file_token): {result}", file=sys.stderr)
        sys.exit(1)

    print(f"\n✓ Uploaded successfully")
    print(f"  file_token: {file_token}")
    print(f"  url: {url}")

    summary = {
        "file_token": file_token,
        "url": url,
        "file_name": data.get("file_name", file_path.name),
        "size_bytes": data.get("size", file_path.stat().st_size),
    }

    if args.send_to_self:
        print("\nSending link to self...", file=sys.stderr)
        msg = f"📹 Video uploaded: {url}"
        send_args = ["im", "+messages-send", "--as", "user", "--to-self", "--text", msg]
        sr, sr_err = run_cli(send_args)
        if sr_err:
            print(f"Send-to-self failed: {sr_err}", file=sys.stderr)
        else:
            print("✓ Sent to self DM")

    if args.chat_id:
        print(f"\nSending link to chat {args.chat_id}...", file=sys.stderr)
        msg = f"📹 Video ready: {url}"
        send_args = ["im", "+messages-send", "--as", "user",
                     "--chat-id", args.chat_id, "--text", msg]
        sr, sr_err = run_cli(send_args)
        if sr_err:
            print(f"Send to chat failed: {sr_err}", file=sys.stderr)
        else:
            print("✓ Sent to chat")

    print(f"\n{json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
