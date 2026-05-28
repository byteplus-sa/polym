#!/usr/bin/env python3
"""
HyperFrames registry cache + browser — PR #4.

Fetches the upstream registry manifest, caches it locally with a 24h TTL,
and provides simple filtering by type / tag / name. Use this when discovering
new blocks/components without manually browsing the GitHub repo.

The fetched cache lives at `~/.explainer-video/registry-cache.json` so other
scripts (compose_and_render.py) can read it without re-fetching.

Usage:
    python3 fetch_registry.py                 # list everything (refreshed if stale)
    python3 fetch_registry.py --type block    # only blocks
    python3 fetch_registry.py --tag captions  # only items tagged "captions"
    python3 fetch_registry.py --json          # machine-readable output
    python3 fetch_registry.py --refresh       # force refresh ignoring TTL
    python3 fetch_registry.py --get vfx-iphone-device  # detail for one item
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REGISTRY_URL = "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry/registry.json"
ITEM_URL_TMPL = "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry/{kind_plural}/{name}/registry-item.json"
CACHE_PATH = Path.home() / ".explainer-video" / "registry-cache.json"
TTL_SECONDS = 86400  # 24 hours

KIND_TO_PLURAL = {
    "hyperframes:block": "blocks",
    "hyperframes:component": "components",
    "hyperframes:example": "examples",
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "explainer-video-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def load_cache(refresh: bool = False) -> dict:
    """Returns parsed cache; refreshes if missing or stale."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CACHE_PATH.exists() and not refresh:
        age = time.time() - CACHE_PATH.stat().st_mtime
        if age < TTL_SECONDS:
            return json.loads(CACHE_PATH.read_text())
    print(f"Fetching {REGISTRY_URL}…", file=sys.stderr)
    data = fetch_json(REGISTRY_URL)
    payload = {"fetched_at": int(time.time()), "registry": data}
    CACHE_PATH.write_text(json.dumps(payload, indent=2))
    return payload


def fetch_item_detail(name: str, kind: str) -> dict:
    """Fetch the registry-item.json for one item. Not cached (rare lookup)."""
    plural = KIND_TO_PLURAL.get(kind)
    if not plural:
        raise ValueError(f"unknown kind {kind!r}")
    url = ITEM_URL_TMPL.format(kind_plural=plural, name=name)
    return fetch_json(url)


def filter_items(items, kind_filter=None, tag_filter=None, name_filter=None):
    out = []
    for it in items:
        if kind_filter and it.get("type") != kind_filter:
            continue
        if name_filter and name_filter.lower() not in it["name"].lower():
            continue
        out.append(it)
    if tag_filter:
        # tag filter requires fetching detail; do it for the filtered subset only
        detailed = []
        for it in out:
            try:
                detail = fetch_item_detail(it["name"], it["type"])
                if tag_filter.lower() in [t.lower() for t in detail.get("tags", [])]:
                    detailed.append({**it, **{"tags": detail.get("tags", [])}})
            except Exception:
                pass
        out = detailed
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--type",
        dest="kind",
        choices=["block", "component", "example"],
        help="Filter by item type",
    )
    ap.add_argument("--tag", help="Filter by tag (requires per-item fetch)")
    ap.add_argument("--name", help="Substring match on name")
    ap.add_argument("--refresh", action="store_true", help="Force refresh ignoring TTL")
    ap.add_argument("--json", action="store_true", help="Emit JSON output")
    ap.add_argument("--get", help="Fetch and print detail for one item by name")
    args = ap.parse_args()

    if args.get:
        cache = load_cache(refresh=args.refresh)
        items = cache["registry"].get("items", [])
        match = next((it for it in items if it["name"] == args.get), None)
        if not match:
            print(f"error: {args.get!r} not in registry", file=sys.stderr)
            sys.exit(2)
        detail = fetch_item_detail(args.get, match["type"])
        print(json.dumps(detail, indent=2))
        return

    cache = load_cache(refresh=args.refresh)
    items = cache["registry"].get("items", [])
    kind_full = {
        "block": "hyperframes:block",
        "component": "hyperframes:component",
        "example": "hyperframes:example",
    }.get(args.kind)
    filtered = filter_items(items, kind_filter=kind_full, tag_filter=args.tag, name_filter=args.name)

    if args.json:
        print(json.dumps(filtered, indent=2))
        return

    age_min = int((time.time() - cache["fetched_at"]) / 60)
    print(f"# Registry · {len(items)} items total · cache {age_min}min old\n")
    if not filtered:
        print("(no items match filters)")
        return
    by_type = {}
    for it in filtered:
        by_type.setdefault(it.get("type", "?"), []).append(it)
    for kind in ("hyperframes:block", "hyperframes:component", "hyperframes:example"):
        if kind not in by_type:
            continue
        print(f"## {kind} ({len(by_type[kind])})")
        for it in by_type[kind]:
            tags = ", ".join(it.get("tags", []))
            extra = f"  [{tags}]" if tags else ""
            print(f"  - {it['name']}{extra}")
        print()


if __name__ == "__main__":
    main()
