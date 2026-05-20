#!/usr/bin/env python3
"""
Import a static-HTML GSB video evaluation report into SQLite.

This handles reports like GSB_Video_Analysis_Report_English.html, which compare
4 video models (Kling 3.0, Seedance 2, Sora 2, Veo 3.1) across 18 prompts
with 6 pairwise comparison rows per prompt (all C(4,2) pairs).

Dimensions per comparison row (scores: +1 / 0 / -1):
    Struct · Visual · Motion · Instruct · Audio · AV Align

Winner column: model short-name or "Tie"

Usage:
    python import_gsb_video_html.py <url_or_file> [--db PATH]

Example:
    python import_gsb_video_html.py \\
      https://carey.tos-ap-southeast-1.bytepluses.com/.../GSB_Video_Analysis_Report_English.html
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import ssl
import sys
import urllib.request
from pathlib import Path

from db_utils import default_db_path

DEFAULT_DB = default_db_path()

# Short name → canonical full name
MODEL_NAMES = {
    "Kling":     "Kling 3.0",
    "Seedance":  "Seedance 2",
    "Sora":      "Sora 2",
    "Veo":       "Veo 3.1",
}

DDL = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS youtube_videos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id    TEXT    NOT NULL,
    source_url   TEXT,
    prompt_num   INTEGER NOT NULL,
    prompt_text  TEXT,
    model_a      TEXT    NOT NULL,   -- full name, first in "X vs Y"
    model_b      TEXT    NOT NULL,   -- full name, second
    comparison   TEXT    NOT NULL,   -- e.g. "Kling vs Seedance"
    winner_name  TEXT,               -- full model name, or "Tie"
    winner       TEXT,               -- A | B | tie  (relative)
    dim_struct   INTEGER,            -- +1 / 0 / -1
    dim_visual   INTEGER,
    dim_motion   INTEGER,
    dim_instruct INTEGER,
    dim_audio    INTEGER,
    dim_av_align INTEGER,
    dim_sum      INTEGER,            -- sum of all 6 dimension scores
    has_audio    INTEGER DEFAULT 1,  -- 0/1
    video_a_url  TEXT,
    video_b_url  TEXT,
    imported_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(report_id, prompt_num, comparison)
);

CREATE INDEX IF NOT EXISTS idx_gsb4_report   ON youtube_videos(report_id);
CREATE INDEX IF NOT EXISTS idx_gsb4_models   ON youtube_videos(model_a, model_b);
CREATE INDEX IF NOT EXISTS idx_gsb4_winner   ON youtube_videos(winner);
CREATE INDEX IF NOT EXISTS idx_gsb4_prompt   ON youtube_videos(prompt_num);
"""


# ─── Fetch HTML ──────────────────────────────────────────────────────────────

def fetch_html(source: str) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        ctx = ssl.create_default_context()
        try:
            req = urllib.request.Request(source, headers={"User-Agent": "eval-bot/1.0"})
            with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
                return r.read().decode("utf-8")
        except Exception:
            ctx2 = ssl._create_unverified_context()
            req = urllib.request.Request(source, headers={"User-Agent": "eval-bot/1.0"})
            with urllib.request.urlopen(req, timeout=60, context=ctx2) as r:
                return r.read().decode("utf-8")
    return Path(source).read_text(encoding="utf-8")


# ─── Parsing helpers ─────────────────────────────────────────────────────────

def strip_tags(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def parse_score(val: str) -> int | None:
    v = val.strip()
    if v in ('+1', '1'):  return  1
    if v in ('-1',):      return -1
    if v == '0':          return  0
    return None


def resolve_winner(winner_raw: str, model_a: str, model_b: str) -> str:
    """Map winner model name → A | B | tie."""
    w = winner_raw.strip()
    if w.lower() in ('tie', 'draw', ''):
        return 'tie'
    full = MODEL_NAMES.get(w, w)
    if full == model_a:  return 'A'
    if full == model_b:  return 'B'
    return 'tie'


# ─── Main parser ─────────────────────────────────────────────────────────────

def parse_report(html: str, source_url: str) -> list[dict]:
    # Derive report_id from URL filename
    report_id = re.sub(r'\.html?$', '', Path(source_url.rstrip('/').split('?')[0]).name)
    if not report_id or len(report_id) < 4:
        import hashlib
        report_id = hashlib.md5(source_url.encode()).hexdigest()[:12]

    body_start = html.find('<body')
    body = html[body_start:]

    # Split into per-prompt blocks on <*  class="prompt-id">
    blocks = re.split(r'(?=<[^>]+ class="prompt-id")', body)

    records = []

    for block in blocks[1:]:   # skip preamble
        # ── prompt number & text ──────────────────────────────────────────
        pid_m = re.search(r'class="prompt-id"[^>]*>Prompt #(\d+)', block)
        if not pid_m:
            continue
        prompt_num = int(pid_m.group(1))

        text_m = re.search(r'class="prompt-content"[^>]*>(.*?)</\w+>', block, re.DOTALL)
        prompt_text = strip_tags(text_m.group(1)) if text_m else ""

        # ── video URLs per model ──────────────────────────────────────────
        video_urls: dict[str, str] = {}   # short_name → url
        for vm in re.finditer(
            r'href="([^"]+\.mp4[^"]*)"[^>]*>.*?<div class="model-name">([^<]+)</div>',
            block, re.DOTALL
        ):
            url, name = vm.group(1).strip(), vm.group(2).strip()
            video_urls[name] = url

        # ── comparison table ──────────────────────────────────────────────
        table_m = re.search(r'<table[^>]*>(.*?)</table>', block, re.DOTALL)
        if not table_m:
            continue

        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_m.group(1), re.DOTALL)
        for row in rows:
            tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(tds) < 7:
                continue
            cells = [strip_tags(c) for c in tds]

            comparison = cells[0]  # "Kling vs Seedance"
            parts = re.split(r'\s+vs\s+', comparison, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) != 2:
                continue

            a_short, b_short = parts[0].strip(), parts[1].strip()
            model_a = MODEL_NAMES.get(a_short, a_short)
            model_b = MODEL_NAMES.get(b_short, b_short)

            dim_struct   = parse_score(cells[1])
            dim_visual   = parse_score(cells[2])
            dim_motion   = parse_score(cells[3])
            dim_instruct = parse_score(cells[4])
            dim_audio    = parse_score(cells[5]) if len(cells) > 5 else None
            dim_av_align = parse_score(cells[6]) if len(cells) > 6 else None
            winner_raw   = cells[7] if len(cells) > 7 else cells[-1]

            has_audio = dim_audio is not None
            scores = [s for s in [dim_struct, dim_visual, dim_motion,
                                   dim_instruct, dim_audio, dim_av_align]
                      if s is not None]
            dim_sum = sum(scores)

            winner = resolve_winner(winner_raw, model_a, model_b)

            records.append({
                "report_id":   report_id,
                "source_url":  source_url,
                "prompt_num":  prompt_num,
                "prompt_text": prompt_text,
                "model_a":     model_a,
                "model_b":     model_b,
                "comparison":  comparison,
                "winner_name": MODEL_NAMES.get(winner_raw.strip(), winner_raw.strip()),
                "winner":      winner,
                "dim_struct":  dim_struct,
                "dim_visual":  dim_visual,
                "dim_motion":  dim_motion,
                "dim_instruct":dim_instruct,
                "dim_audio":   dim_audio,
                "dim_av_align":dim_av_align,
                "dim_sum":     dim_sum,
                "has_audio":   int(has_audio),
                "video_a_url": video_urls.get(a_short, ""),
                "video_b_url": video_urls.get(b_short, ""),
            })

    return records


# ─── Import ──────────────────────────────────────────────────────────────────

def import_to_db(records: list[dict], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(DDL)

    inserted = skipped = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO youtube_videos
                   (report_id, source_url, prompt_num, prompt_text,
                    model_a, model_b, comparison,
                    winner_name, winner,
                    dim_struct, dim_visual, dim_motion, dim_instruct,
                    dim_audio, dim_av_align, dim_sum, has_audio,
                    video_a_url, video_b_url)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (r["report_id"], r["source_url"], r["prompt_num"], r["prompt_text"],
                 r["model_a"], r["model_b"], r["comparison"],
                 r["winner_name"], r["winner"],
                 r["dim_struct"], r["dim_visual"], r["dim_motion"], r["dim_instruct"],
                 r["dim_audio"], r["dim_av_align"], r["dim_sum"], r["has_audio"],
                 r["video_a_url"], r["video_b_url"]),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    print(f"✅  Done — {inserted} rows inserted, {skipped} already existed")
    print(f"    DB: {db_path}\n")

    # Per-model summary (win rates across all comparisons)
    models = conn.execute(
        "SELECT DISTINCT model_a FROM youtube_videos WHERE report_id=? "
        "UNION SELECT DISTINCT model_b FROM youtube_videos WHERE report_id=?",
        (records[0]["report_id"], records[0]["report_id"])
    ).fetchall()
    models = [m[0] for m in models]

    print(f"  {'Model':<18} {'As A':>6} {'A-win':>6} {'As B':>6} {'B-win':>6} {'Total':>6} {'Wins':>6} {'WinRate':>8}")
    print("  " + "─" * 65)
    rid = records[0]["report_id"]
    for m in sorted(models):
        as_a  = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE report_id=? AND model_a=?", (rid,m)).fetchone()[0]
        a_win = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE report_id=? AND model_a=? AND winner='A'", (rid,m)).fetchone()[0]
        as_b  = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE report_id=? AND model_b=?", (rid,m)).fetchone()[0]
        b_win = conn.execute("SELECT COUNT(*) FROM youtube_videos WHERE report_id=? AND model_b=? AND winner='B'", (rid,m)).fetchone()[0]
        total = as_a + as_b
        wins  = a_win + b_win
        wr    = f"{100*wins/total:.1f}%" if total else "—"
        print(f"  {m:<18} {as_a:>6} {a_win:>6} {as_b:>6} {b_win:>6} {total:>6} {wins:>6} {wr:>8}")
    print()
    conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import GSB video HTML report into SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("source", help="URL or local file path of the HTML report")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    print(f"📥  Fetching {args.source} …")
    html    = fetch_html(args.source)
    records = parse_report(html, args.source)

    if not records:
        sys.exit("❌  No records parsed — check the HTML structure.")

    print(f"🔍  Parsed {len(records)} pairwise comparison rows "
          f"({len(set(r['prompt_num'] for r in records))} prompts × "
          f"{len(set(r['comparison'] for r in records))} pairs)")
    import_to_db(records, Path(args.db))


if __name__ == "__main__":
    main()
