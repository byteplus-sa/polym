#!/usr/bin/env python3
"""
Categorize user input files for Phase 1.

Walks a directory of mixed inputs and produces a structured manifest.

Usage:
    python3 parse_inputs.py path/to/inputs/
    python3 parse_inputs.py file1.md file2.png ref.mp4
"""
import argparse
import json
import sys
from pathlib import Path

EXTENSIONS = {
    "text_doc": {".md", ".txt", ".rst"},
    "screenshot": {".png", ".jpg", ".jpeg", ".webp", ".gif"},
    "pdf": {".pdf"},
    "reference_video": {".mp4", ".mov", ".webm", ".m4v"},
    "audio": {".mp3", ".wav", ".m4a", ".aac"},
}


def categorize(path: Path):
    suffix = path.suffix.lower()
    for kind, exts in EXTENSIONS.items():
        if suffix in exts:
            return kind
    return "unknown"


def is_github_url(s):
    return "github.com" in s and "/" in s.split("github.com/", 1)[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+",
                    help="Files or directories or URLs (mix freely)")
    ap.add_argument("--out", default="inputs-manifest.json")
    args = ap.parse_args()

    manifest = {
        "text_docs": [],
        "screenshots": [],
        "pdfs": [],
        "reference_videos": [],
        "audio_files": [],
        "github_urls": [],
        "other_urls": [],
        "unknown": [],
    }

    for raw in args.inputs:
        # URL?
        if raw.startswith("http://") or raw.startswith("https://"):
            if is_github_url(raw):
                manifest["github_urls"].append(raw)
            else:
                manifest["other_urls"].append(raw)
            continue

        p = Path(raw)
        if not p.exists():
            print(f"WARN: not found: {raw}", file=sys.stderr)
            manifest["unknown"].append(raw)
            continue

        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    cat = categorize(f)
                    if cat == "text_doc":
                        manifest["text_docs"].append(str(f))
                    elif cat == "screenshot":
                        manifest["screenshots"].append(str(f))
                    elif cat == "pdf":
                        manifest["pdfs"].append(str(f))
                    elif cat == "reference_video":
                        manifest["reference_videos"].append(str(f))
                    elif cat == "audio":
                        manifest["audio_files"].append(str(f))
                    else:
                        manifest["unknown"].append(str(f))
        else:
            cat = categorize(p)
            target = {
                "text_doc": "text_docs",
                "screenshot": "screenshots",
                "pdf": "pdfs",
                "reference_video": "reference_videos",
                "audio": "audio_files",
                "unknown": "unknown",
            }[cat]
            manifest[target].append(str(p))

    Path(args.out).write_text(json.dumps(manifest, indent=2))

    # Print human summary
    print("Input manifest:")
    for k, v in manifest.items():
        if v:
            print(f"  {k}: {len(v)}")
            for item in v[:3]:
                print(f"    - {item}")
            if len(v) > 3:
                print(f"    ... and {len(v) - 3} more")
    print(f"\nWritten to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
