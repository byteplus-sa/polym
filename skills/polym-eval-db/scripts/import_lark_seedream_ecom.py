#!/usr/bin/env python3
"""
Import Seedream 5.0 E-commerce use-case evaluation data from Lark wiki into SQLite.

Doc: [Internal] Seedream 5.0 Use cases for specific E-commerce sectors
Wiki: https://bytedance.larkoffice.com/wiki/N6dcwcXaqie1Y9kOQMuc7mKGnOd

Compares Seedream 5.0 vs Nanobanana across 5 e-commerce sectors:
  Clothing & Fashion · Accessories & Jewelry · Furniture · Electronics ·
  General Accessories (Bags, Belts, Hats, Watches)

Table columns: Use-case | Reference | Prompt | Nanobanana notes | Seedream 5.0 notes | GSB
GSB values (from Seedream's perspective): Good | Same | Bad

Usage:
    python import_lark_seedream_ecom.py [--db PATH]
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from db_utils import default_db_path

DOC_ID      = "N6dcwcXaqie1Y9kOQMuc7mKGnOd"
MODEL_A     = "Seedream 5.0"
MODEL_B     = "Nanobanana"

DEFAULT_DB = default_db_path()

DDL = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS seedream_ecom_usecases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT    DEFAULT 'lark_seedream_ecom_doc',
    sector          TEXT    NOT NULL,
    use_case        TEXT    NOT NULL,
    prompt          TEXT,
    gsb             TEXT,              -- Good | Same | Bad
    gsb_normalized  TEXT,              -- good | same | bad
    seedream_notes  TEXT,              -- ✔️/✖️ observations for Seedream 5.0
    nanobanana_notes TEXT,             -- ✔️/✖️ observations for Nanobanana
    imported_at     TEXT    DEFAULT (datetime('now')),
    UNIQUE(sector, use_case)
);

CREATE INDEX IF NOT EXISTS idx_secom_sector ON seedream_ecom_usecases(sector);
CREATE INDEX IF NOT EXISTS idx_secom_gsb    ON seedream_ecom_usecases(gsb_normalized);
"""


# ─── Fetch ────────────────────────────────────────────────────────────────────

def fetch_doc() -> str:
    print(f"📄  Fetching Lark doc {DOC_ID} …")
    result = subprocess.run(
        ["lark-cli", "docs", "+fetch", "--doc", DOC_ID, "--as", "user", "--format", "pretty"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        err = result.stderr or result.stdout
        if "auth" in err.lower():
            sys.exit("❌  Run: lark-cli auth login")
        sys.exit(f"❌  lark-cli failed:\n{err}")
    return result.stdout


# ─── Parse ────────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Strip HTML/Lark tags and normalise whitespace."""
    # Remove image/grid/column tags and their content markers
    text = re.sub(r'<image[^/]*/>', '', text)
    text = re.sub(r'<grid[^>]*>|</grid>|<column[^>]*>|</column>', '', text)
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove markdown bold markers
    text = re.sub(r'\*+', '', text)
    # Remove backtick code fences
    text = re.sub(r'```\w*', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_doc(content: str) -> list[dict]:
    """
    Parse all 5 sector tables.
    Each table has a # Section header immediately before it.
    Columns: Use-case | Reference | Prompt | Nanobanana | Seedream 5.0 | GSB
    """
    records = []

    # Find sector sections: "# SectorName\n...<lark-table ...>...</lark-table>"
    # The main title "# [Internal] Seedream…" is also a # header — skip it
    sector_blocks = re.split(r'^# ', content, flags=re.MULTILINE)

    for block in sector_blocks[1:]:          # skip preamble
        # First line is the sector name
        lines = block.split('\n', 1)
        sector_name = lines[0].strip().strip('*').strip()

        # Skip the preamble / executive-summary block
        if 'Internal' in sector_name or 'Main use' in sector_name:
            continue

        # Find the lark-table in this block
        table_m = re.search(r'<lark-table[^>]*>(.*?)</lark-table>', block, re.DOTALL)
        if not table_m:
            continue

        rows = re.findall(r'<lark-tr>(.*?)</lark-tr>', table_m.group(1), re.DOTALL)

        for row in rows:
            cells_raw = re.findall(r'<lark-td[^>]*>(.*?)</lark-td>', row, re.DOTALL)
            cells = [clean(c) for c in cells_raw]

            # Skip header row and empty rows
            if not cells or cells[0] in ('Use-case', 'Use Case', ''):
                continue
            if len(cells) < 3:
                continue

            use_case        = cells[0]
            # cells[1] is the Reference column (image tokens) — skip
            prompt          = cells[2] if len(cells) > 2 else ''
            nanobanana_notes = cells[3] if len(cells) > 3 else ''
            seedream_notes  = cells[4] if len(cells) > 4 else ''
            gsb_raw         = cells[5] if len(cells) > 5 else ''

            # Validate GSB
            gsb = gsb_raw.strip().title()
            if gsb not in ('Good', 'Same', 'Bad'):
                # sometimes GSB appears in col 4 if reference was merged
                for c in cells:
                    if c.strip().title() in ('Good', 'Same', 'Bad'):
                        gsb = c.strip().title()
                        break

            gsb_norm = {'Good': 'good', 'Same': 'same', 'Bad': 'bad'}.get(gsb, 'unknown')

            records.append({
                'sector':           sector_name,
                'use_case':         use_case,
                'prompt':           prompt,
                'gsb':              gsb,
                'gsb_normalized':   gsb_norm,
                'seedream_notes':   seedream_notes,
                'nanobanana_notes': nanobanana_notes,
            })

    return records


# ─── Import ───────────────────────────────────────────────────────────────────

def import_to_db(records: list[dict], db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(DDL)

    inserted = skipped = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO seedream_ecom_usecases
                   (sector, use_case, prompt, gsb, gsb_normalized,
                    seedream_notes, nanobanana_notes)
                   VALUES (?,?,?,?,?,?,?)""",
                (r['sector'], r['use_case'], r['prompt'], r['gsb'],
                 r['gsb_normalized'], r['seedream_notes'], r['nanobanana_notes']),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    print(f"\n✅  Done — {inserted} rows inserted, {skipped} already existed")
    print(f"    DB: {db_path}\n")

    # Summary table
    rows = conn.execute(
        """SELECT sector,
                  COUNT(*) total,
                  SUM(gsb_normalized='good') good,
                  SUM(gsb_normalized='same') same,
                  SUM(gsb_normalized='bad')  bad
           FROM seedream_ecom_usecases
           GROUP BY sector ORDER BY rowid"""
    ).fetchall()

    print(f"  {'Sector':<42} {'Total':>5}  {'Good':>4}  {'Same':>4}  {'Bad':>3}")
    print("  " + "─" * 62)
    total_good = total_same = total_bad = 0
    for r in rows:
        print(f"  {r[0]:<42} {r[1]:>5}  {r[2]:>4}  {r[3]:>4}  {r[4]:>3}")
        total_good += r[2]; total_same += r[3]; total_bad += r[4]
    total = total_good + total_same + total_bad
    print("  " + "─" * 62)
    print(f"  {'TOTAL':<42} {total:>5}  {total_good:>4}  {total_same:>4}  {total_bad:>3}")
    print(f"\n  Seedream vs Nanobanana — Good rate: {100*total_good//total}%  "
          f"Same rate: {100*total_same//total}%  Bad rate: {100*total_bad//total}%")
    conn.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Import Seedream e-com use-case doc into SQLite")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    content = fetch_doc()
    records = parse_doc(content)

    if not records:
        sys.exit("❌  No records parsed.")

    print(f"🔍  Parsed {len(records)} use-case rows across "
          f"{len(set(r['sector'] for r in records))} sectors")
    import_to_db(records, Path(args.db))


if __name__ == "__main__":
    main()
