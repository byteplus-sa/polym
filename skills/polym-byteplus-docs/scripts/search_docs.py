#!/usr/bin/env python3
"""Rank official links from the polym-byteplus-docs llms.txt index."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
from pathlib import Path


HEADING_RE = re.compile(r"^## (?P<section>\S.*)$")
LINK_RE = re.compile(
    r"^- \[(?P<title>(?:\\.|[^\]])+)\]"
    r"\((?P<url>https://docs\.byteplus\.com/en/docs/[^\s)]+)\)$"
)
TOKEN_RE = re.compile(r"[a-z0-9]+")
LIBRARY_ALIASES = {
    "cdn": "byteplus cdn",
    "ecs": "elastic compute service",
    "iam": "— iam",
    "rtc": "byteplus rtc",
    "tos": "torch object storage",
    "vod": "video on demand",
    "vpc": "virtual private cloud",
    "waf": "web application firewall",
}


@dataclasses.dataclass(frozen=True)
class Entry:
    section: str
    title: str
    url: str


def find_index(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit.expanduser())
    env_path = os.environ.get("BYTEPLUS_LLMS_TXT")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.append(Path(__file__).resolve().parents[1] / "llms.txt")
    for origin in (Path.cwd().resolve(), Path(__file__).resolve()):
        candidates.extend(parent / "llms.txt" for parent in (origin, *origin.parents))

    seen: set[Path] = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Could not find llms.txt. Ensure it is bundled beside SKILL.md, pass "
        "--index PATH, or set BYTEPLUS_LLMS_TXT."
    )


def unescape_label(value: str) -> str:
    return re.sub(r"\\([\\\[\]])", r"\1", value)


def load_entries(path: Path) -> tuple[list[str], list[Entry]]:
    sections: list[str] = []
    entries: list[Entry] = []
    current_section = "Uncategorized"
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            heading = HEADING_RE.fullmatch(line)
            if heading:
                current_section = heading.group("section")
                sections.append(current_section)
                continue
            link = LINK_RE.fullmatch(line)
            if link:
                entries.append(
                    Entry(
                        section=current_section,
                        title=unescape_label(link.group("title")),
                        url=link.group("url"),
                    )
                )
    if not entries:
        raise ValueError(f"No BytePlus documentation links found in {path}")
    return sections, entries


def tokens(value: str) -> list[str]:
    return TOKEN_RE.findall(value.casefold())


def score_entry(entry: Entry, query: str, query_tokens: list[str]) -> int:
    title = entry.title.casefold()
    section = entry.section.casefold()
    url = entry.url.casefold()
    phrase = " ".join(query.casefold().split())
    score = 0
    if phrase and phrase in title:
        score += 120
    if phrase and phrase in section:
        score += 70
    if phrase and phrase in url:
        score += 30
    title_tokens = set(tokens(title))
    section_tokens = set(tokens(section))
    url_tokens = set(tokens(url))
    for token in query_tokens:
        if token in title_tokens:
            score += 24
        elif token in title:
            score += 12
        if token in section_tokens:
            score += 12
        elif token in section:
            score += 6
        if token in url_tokens:
            score += 5
        elif token in url:
            score += 2
    matched = sum(
        token in title or token in section or token in url for token in set(query_tokens)
    )
    if query_tokens and matched == len(set(query_tokens)):
        score += 35
    return score


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="*", help="Feature, product, API, or task terms")
    parser.add_argument("--index", type=Path, help="Path to the BytePlus llms.txt")
    parser.add_argument("--library", help="Case-insensitive product/library filter")
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--list-libraries", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise ValueError("--limit must be positive")
    index = find_index(args.index)
    sections, entries = load_entries(index)

    if args.list_libraries:
        for section in sections:
            print(section)
        return 0

    query = " ".join(args.query).strip()
    if not query:
        raise ValueError("Provide a query or use --list-libraries")
    query_tokens = tokens(query)
    if not query_tokens:
        raise ValueError("Query must contain at least one letter or number")

    library_filter = args.library.casefold() if args.library else None
    if library_filter is None:
        library_filter = next(
            (
                LIBRARY_ALIASES[token]
                for token in query_tokens
                if token in LIBRARY_ALIASES
            ),
            None,
        )
    ranked: list[tuple[int, Entry]] = []
    for entry in entries:
        if library_filter and library_filter not in entry.section.casefold():
            continue
        score = score_entry(entry, query, query_tokens)
        if score:
            ranked.append((score, entry))
    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1].section.casefold(),
            item[1].title.casefold(),
            item[1].url,
        )
    )
    ranked = ranked[: args.limit]

    if args.as_json:
        print(
            json.dumps(
                [
                    {"score": score, **dataclasses.asdict(entry)}
                    for score, entry in ranked
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        for score, entry in ranked:
            print(f"[{score:>3}] {entry.section} :: {entry.title}")
            print(f"      {entry.url}")

    if not ranked:
        print("No matching BytePlus documentation links found.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
