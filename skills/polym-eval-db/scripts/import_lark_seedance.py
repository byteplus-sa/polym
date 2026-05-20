#!/usr/bin/env python3
"""
Import Seedance 2.0 Marketing & Advertising use-case evaluation data
from the internal Lark document into SQLite.

The Lark doc has a summary table with columns:
    Use Case & Workflow | Modal | GSB | Absolute Score | Remarks

Sectors: Branding/Awareness Ads · Performance/Paid Ads · E-commerce Product Videos
         Local Services/O2O Ads · UGC/Creator-Style Native Ads ·
         Global/Multi-language Ads · Technology/SaaS/AI-native GTM

GSB values: Good / Same / Bad / N/A
Absolute Score: 1–5 or N/A (some rows without competitor comparison)
Modalities: T2V · I2V · R2V · V2V

Usage:
    python import_lark_seedance.py [--db PATH]

Requires lark-cli to be installed and authenticated (`lark-cli auth login`).
"""

from __future__ import annotations

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from db_utils import default_db_path

# ─── Config ──────────────────────────────────────────────────────────────────

DOC_ID      = "HEqSdx3qhoOpXIx6EtnlLftFgwb"
SOURCE_NAME = "seedance_2_ad_usecases"

DEFAULT_DB = default_db_path()

DDL = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS seedance_ad_usecases (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source         TEXT    DEFAULT 'lark_seedance_doc',
    sector         TEXT    NOT NULL,
    use_case       TEXT    NOT NULL,
    workflow       TEXT,
    modality       TEXT,              -- T2V | I2V | R2V | V2V
    gsb            TEXT,              -- Good | Same | Bad | N/A
    gsb_normalized TEXT,              -- good | same | bad | na
    absolute_score TEXT,              -- 1-5 or N/A
    absolute_num   REAL,              -- numeric version, NULL if N/A
    remarks        TEXT,
    competitor     TEXT,              -- extracted competitor name if mentioned
    imported_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(sector, use_case)
);

CREATE INDEX IF NOT EXISTS idx_uc_sector   ON seedance_ad_usecases(sector);
CREATE INDEX IF NOT EXISTS idx_uc_modality ON seedance_ad_usecases(modality);
CREATE INDEX IF NOT EXISTS idx_uc_gsb      ON seedance_ad_usecases(gsb_normalized);
CREATE INDEX IF NOT EXISTS idx_uc_score    ON seedance_ad_usecases(absolute_num);
"""

# ─── Fetch document ───────────────────────────────────────────────────────────

def fetch_doc() -> str:
    print(f"📄  Fetching Lark doc {DOC_ID} …")
    result = subprocess.run(
        ["lark-cli", "docs", "+fetch", "--doc", DOC_ID, "--as", "user", "--format", "pretty"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        err = result.stderr or result.stdout
        if "auth" in err.lower() or "login" in err.lower():
            sys.exit("❌  Lark auth required — run: lark-cli auth login")
        sys.exit(f"❌  lark-cli failed:\n{err}")
    return result.stdout


# ─── Table parser ─────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Strip HTML tags, align markers, excess whitespace."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\{align="[^"]+"\}', '', text)
    text = re.sub(r'\*+', '', text)          # bold markers
    return re.sub(r'\s+', ' ', text).strip()


def parse_table(html: str) -> list[dict]:
    """
    Parse the 52-row summary table from the pretty-formatted Lark output.

    Handles:
    - Sector header rows (colspan=5)
    - Sub-section header rows (colspan=5, "Additional Use-cases")
    - rowspan on cells (e.g. N/A spanning 5 rows)
    - Normal 5-column data rows
    """
    # Grab the first big table (rows=52)
    m = re.search(r'<lark-table rows="52"[^>]*>(.*?)</lark-table>', html, re.DOTALL)
    if not m:
        raise ValueError("Could not find the 52-row summary table in the document.")
    table = m.group(1)

    raw_rows = re.findall(r'<lark-tr>(.*?)</lark-tr>', table, re.DOTALL)

    records = []
    current_sector = None
    # rowspan carry-forward: index → (value, remaining_rows)
    carried: dict[int, tuple[str, int]] = {}

    MODALITIES = {"T2V", "I2V", "R2V", "V2V"}
    GSB_VALUES = {"Good", "Same", "Bad", "N/A"}
    SECTOR_KEYWORDS = (
        "Branding", "Performance", "E-commerce", "Local Services",
        "UGC", "Global", "Technology", "Social Media", "Locali", "Real Est",
    )

    for raw_row in raw_rows:
        # Find all <lark-td> with optional rowspan
        td_matches = list(re.finditer(
            r'<lark-td(?P<attrs>[^>]*)>(?P<body>.*?)</lark-td>', raw_row, re.DOTALL
        ))

        if not td_matches:
            continue

        # Check for sector header (colspan=5 single cell)
        if len(td_matches) == 1:
            attrs = td_matches[0].group("attrs")
            body  = clean(td_matches[0].group("body"))
            if 'colspan="5"' in attrs and any(kw in body for kw in SECTOR_KEYWORDS):
                current_sector = body
                carried.clear()   # reset carry-forward for new sector
                continue
            # sub-section header (Additional Use-cases etc.) — skip
            continue

        # Build cell list, injecting carried values at correct positions
        # First, decrement carry counts and collect still-active values
        new_carried = {}
        for idx, (val, remaining) in carried.items():
            if remaining > 1:
                new_carried[idx] = (val, remaining - 1)
        carried = new_carried

        # Reconstruct the "virtual" 5-cell row by inserting carried values
        cells_raw: list[tuple[str, int]] = []   # (text, col_index_in_virtual_row)
        virtual_col = 0

        for tdm in td_matches:
            # Skip columns already filled by carried rowspan
            while virtual_col in carried:
                cells_raw.append((carried[virtual_col][0], virtual_col))
                virtual_col += 1

            attrs  = tdm.group("attrs")
            body   = clean(tdm.group("body"))
            rs_m   = re.search(r'rowspan="(\d+)"', attrs)
            rowspan = int(rs_m.group(1)) if rs_m else 1

            cells_raw.append((body, virtual_col))
            if rowspan > 1:
                carried[virtual_col] = (body, rowspan)
            virtual_col += 1

        # Fill trailing carried
        while virtual_col in carried:
            cells_raw.append((carried[virtual_col][0], virtual_col))
            virtual_col += 1

        cells = [v for v, _ in cells_raw]

        if len(cells) < 4:
            continue
        if not current_sector:
            continue

        # Skip sub-header rows that sneak through
        if any(kw in cells[0] for kw in ("Additional", "Without comparison")):
            continue

        use_case_full = cells[0]
        modal         = cells[1] if len(cells) > 1 else ""
        gsb           = cells[2] if len(cells) > 2 else ""
        score_raw     = cells[3] if len(cells) > 3 else ""
        remarks       = cells[4] if len(cells) > 4 else ""

        # Validate modality
        if modal not in MODALITIES:
            continue

        # Split use_case into name + workflow (separated by newline or →)
        uc_parts = re.split(r'\n', use_case_full, maxsplit=1)
        use_case_name = uc_parts[0].strip()
        workflow      = uc_parts[1].strip() if len(uc_parts) > 1 else ""

        # Normalize GSB
        gsb_clean = gsb.strip()
        # Sometimes "Same (as Kling3.0)", "Same (with Veo3.1)" etc.
        gsb_base = re.split(r'[\s(]', gsb_clean)[0]   # first word
        if gsb_base not in GSB_VALUES:
            gsb_base = gsb_clean  # keep as-is

        gsb_norm = {"Good": "good", "Same": "same", "Bad": "bad", "N/A": "na"}.get(gsb_base, "na")

        # Numeric score
        score_str = score_raw.strip()
        try:
            score_num = float(score_str)
        except ValueError:
            score_num = None

        # Extract competitor name from GSB or remarks
        competitor = None
        for text in (gsb_clean, remarks):
            m = re.search(
                r'\b(Kling[\s\d.]*|Veo[\s\d.]*|Sora[\s\d.]*|Higgsfield|Runway|Pika|CogVideo)\b',
                text, re.IGNORECASE
            )
            if m:
                competitor = m.group(1).strip()
                break

        records.append({
            "sector":         current_sector,
            "use_case":       use_case_name,
            "workflow":       workflow,
            "modality":       modal,
            "gsb":            gsb_base,
            "gsb_normalized": gsb_norm,
            "absolute_score": score_str or "N/A",
            "absolute_num":   score_num,
            "remarks":        remarks,
            "competitor":     competitor,
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
                """INSERT OR REPLACE INTO seedance_ad_usecases
                   (sector, use_case, workflow, modality, gsb, gsb_normalized,
                    absolute_score, absolute_num, remarks, competitor)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (r["sector"], r["use_case"], r["workflow"], r["modality"],
                 r["gsb"], r["gsb_normalized"], r["absolute_score"],
                 r["absolute_num"], r["remarks"], r["competitor"]),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()

    # Summary print
    print(f"\n✅  Done — {inserted} rows inserted, {skipped} already existed")
    print(f"    DB: {db_path}\n")

    rows = conn.execute(
        """SELECT sector,
                  COUNT(*) total,
                  SUM(gsb_normalized='good') good,
                  SUM(gsb_normalized='same') same,
                  SUM(gsb_normalized='bad')  bad,
                  SUM(gsb_normalized='na')   na,
                  ROUND(AVG(absolute_num),1) avg_score
           FROM seedance_ad_usecases
           GROUP BY sector ORDER BY id"""
    ).fetchall()

    print(f"  {'Sector':<38} {'Total':>5}  {'Good':>4}  {'Same':>4}  {'Bad':>3}  {'N/A':>3}  {'AvgScore':>8}")
    print("  " + "─" * 72)
    for r in rows:
        print(f"  {r[0]:<38} {r[1]:>5}  {r[2]:>4}  {r[3]:>4}  {r[4]:>3}  {r[5]:>3}  {str(r[6]):>8}")
    print()
    conn.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Import Seedance ad use-case doc into SQLite")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()

    html    = fetch_doc()
    records = parse_table(html)

    if not records:
        sys.exit("❌  No records parsed — check document format or lark-cli output.")

    print(f"🔍  Parsed {len(records)} use-case rows across sectors")
    import_to_db(records, Path(args.db))


if __name__ == "__main__":
    main()
