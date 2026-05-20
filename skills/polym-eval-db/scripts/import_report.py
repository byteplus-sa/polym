#!/usr/bin/env python3
"""
Import an image evaluation HTML report into SQLite.

The report is a self-contained HTML page with an embedded `reportData` JSON
object produced by the eval-llm-webui pipeline.

Usage:
    python import_report.py <url_or_file> [--db PATH]

Examples:
    python import_report.py https://example.com/report.html
    python import_report.py /path/to/report.html --db /path/to/eval.db
"""

import argparse
import json
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

from db_utils import default_db_path

# ─── Default DB path ────────────────────────────────────────────────────────
DEFAULT_DB = default_db_path()

DIMENSIONS = [
    "prompt_fidelity",
    "structure",
    "texture",
    "lighting",
    "artifacts",
    "usefulness",
    "factual_consistency",
    "text_rendering",
    "edit_consistency",
]


# ─── DB init ─────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS reports (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id    TEXT    UNIQUE NOT NULL,
            source_url   TEXT,
            report_title TEXT,
            report_date  TEXT,
            model_a      TEXT    NOT NULL,
            model_b      TEXT    NOT NULL,
            model_a_key  TEXT    NOT NULL,
            model_b_key  TEXT    NOT NULL,
            total_rows   INTEGER,
            imported_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS image_comparisons (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id               TEXT    NOT NULL REFERENCES reports(report_id),
            row_id                  TEXT    NOT NULL,
            excel_id                INTEGER,
            prompt                  TEXT,
            reference_image         TEXT,
            category                TEXT,
            industry                TEXT,
            scenario                TEXT,
            image_a_url             TEXT,
            image_b_url             TEXT,
            ref_images_count        INTEGER,
            winner                  TEXT,   -- A | B | tie  (A=model_a, B=model_b)
            dim_prompt_fidelity     TEXT,
            dim_structure           TEXT,
            dim_texture             TEXT,
            dim_lighting            TEXT,
            dim_artifacts           TEXT,
            dim_usefulness          TEXT,
            dim_factual_consistency TEXT,
            dim_text_rendering      TEXT,
            dim_edit_consistency    TEXT,
            reason                  TEXT,
            UNIQUE(report_id, row_id)
        );

        CREATE TABLE IF NOT EXISTS elo_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            report_ids  TEXT    NOT NULL,   -- JSON array of report_ids used
            dimension   TEXT    NOT NULL,
            model       TEXT    NOT NULL,
            elo_score   REAL,
            wins        INTEGER,
            losses      INTEGER,
            ties        INTEGER,
            total       INTEGER,
            win_rate    REAL,
            computed_at TEXT    DEFAULT (datetime('now')),
            UNIQUE(report_ids, dimension, model)
        );

        CREATE INDEX IF NOT EXISTS idx_cmp_report   ON image_comparisons(report_id);
        CREATE INDEX IF NOT EXISTS idx_cmp_winner   ON image_comparisons(winner);
        CREATE INDEX IF NOT EXISTS idx_cmp_category ON image_comparisons(category);
        CREATE INDEX IF NOT EXISTS idx_cmp_scenario ON image_comparisons(scenario);
        CREATE INDEX IF NOT EXISTS idx_elo_key      ON elo_cache(report_ids, dimension);
    """)


# ─── HTML fetch & JSON extraction ────────────────────────────────────────────

def fetch_html(source: str) -> str:
    """Fetch HTML from a URL or local file path."""
    if source.startswith("http://") or source.startswith("https://"):
        import ssl
        # Some internal / staging hosts use non-standard CA chains;
        # create an unverified context as a fallback.
        ctx = ssl.create_default_context()
        try:
            req = urllib.request.Request(source, headers={"User-Agent": "eval-llm-bot/1.0"})
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            # Retry without cert verification (internal / self-signed certs)
            ctx_noverify = ssl._create_unverified_context()
            req = urllib.request.Request(source, headers={"User-Agent": "eval-llm-bot/1.0"})
            with urllib.request.urlopen(req, timeout=60, context=ctx_noverify) as resp:
                return resp.read().decode("utf-8")
    else:
        return Path(source).read_text(encoding="utf-8")


def extract_report_data(html: str) -> dict:
    """Extract the `reportData` JSON object embedded in the HTML."""
    match = re.search(r"const\s+reportData\s*=\s*(\{)", html)
    if not match:
        raise ValueError(
            "Could not find `const reportData = {...}` in the HTML. "
            "Is this a valid eval report page?"
        )
    start = match.start(1)
    decoder = json.JSONDecoder()
    data, _ = decoder.raw_decode(html, start)
    return data


# ─── Normalization ────────────────────────────────────────────────────────────

def detect_models(rows: list[dict]) -> tuple[str, str]:
    """Return (model_a_key, model_b_key) from the first row's generated_images."""
    for row in rows:
        keys = list(row.get("generated_images", {}).keys())
        if len(keys) >= 2:
            return keys[0], keys[1]
    raise ValueError("Could not detect model keys from generated_images")


def normalize_winner(raw: str, model_a_key: str, model_b_key: str) -> str:
    """Map report winner value → A / B / tie."""
    if not raw or raw == "tie":
        return "tie"
    # Already normalized
    if raw in ("A", "B"):
        return raw
    # Match by model key substring (e.g. "seedream" in "seedream_5_0")
    raw_l = raw.lower()
    if any(p in raw_l for p in model_a_key.lower().split("_")):
        return "A"
    if any(p in raw_l for p in model_b_key.lower().split("_")):
        return "B"
    return raw  # fallback: keep as-is


def normalize_dim(val: str) -> str:
    """Ensure dimension values are A / B / tie."""
    if val in ("A", "B", "tie"):
        return val
    return val or ""


# ─── Import logic ─────────────────────────────────────────────────────────────

def import_report(source: str, db_path: Path) -> None:
    print(f"📥  Fetching report …  {source}")
    html = fetch_html(source)

    print("🔍  Extracting reportData …")
    data = extract_report_data(html)

    rows_raw = data.get("rows", [])
    # rows may be a dict keyed by row_id or a plain list
    if isinstance(rows_raw, dict):
        rows = list(rows_raw.values())
    else:
        rows = list(rows_raw)
    if not rows:
        raise ValueError("Report contains no rows.")

    # Detect report_id from URL filename or generate one
    report_id = re.sub(r"\.html$", "", Path(source.rstrip("/")).name)
    if not report_id or report_id == source:
        import hashlib, time
        report_id = hashlib.md5(source.encode()).hexdigest()[:12]

    model_a_key, model_b_key = detect_models(rows)

    summary = data.get("summary", {})
    models = summary.get("models", [])
    model_a = models[0] if len(models) > 0 else model_a_key
    model_b = models[1] if len(models) > 1 else model_b_key

    print(f"📊  Report  : {report_id}")
    print(f"    Model A : {model_a}  ({model_a_key})")
    print(f"    Model B : {model_b}  ({model_b_key})")
    print(f"    Rows    : {len(rows)}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))

    try:
        init_db(conn)

        conn.execute(
            """
            INSERT OR REPLACE INTO reports
                (report_id, source_url, report_title, report_date,
                 model_a, model_b, model_a_key, model_b_key, total_rows)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                source,
                data.get("report_title", ""),
                data.get("report_date", ""),
                model_a, model_b,
                model_a_key, model_b_key,
                summary.get("total_rows", len(rows)),
            ),
        )

        inserted = skipped = 0
        for row in rows:
            meta  = row.get("metadata", {})
            gen   = row.get("generated_images", {})
            evl   = row.get("evaluation", {})
            dims  = evl.get("dimensions", {})

            winner = normalize_winner(evl.get("winner", ""), model_a_key, model_b_key)

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO image_comparisons (
                        report_id, row_id, excel_id,
                        prompt, reference_image, category, industry, scenario,
                        image_a_url, image_b_url, ref_images_count,
                        winner,
                        dim_prompt_fidelity, dim_structure, dim_texture,
                        dim_lighting, dim_artifacts, dim_usefulness,
                        dim_factual_consistency, dim_text_rendering, dim_edit_consistency,
                        reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_id,
                        row.get("row_id", ""),
                        row.get("excel_id"),
                        meta.get("prompt", ""),
                        meta.get("reference_image", ""),
                        meta.get("category", ""),
                        meta.get("industry", ""),
                        meta.get("scenario", ""),
                        gen.get(model_a_key, {}).get("download_url", ""),
                        gen.get(model_b_key, {}).get("download_url", ""),
                        evl.get("ref_images_count"),
                        winner,
                        normalize_dim(dims.get("prompt_fidelity", "")),
                        normalize_dim(dims.get("structure", "")),
                        normalize_dim(dims.get("texture", "")),
                        normalize_dim(dims.get("lighting", "")),
                        normalize_dim(dims.get("artifacts", "")),
                        normalize_dim(dims.get("usefulness", "")),
                        normalize_dim(dims.get("factual_consistency", "")),
                        normalize_dim(dims.get("text_rendering", "")),
                        normalize_dim(dims.get("edit_consistency", "")),
                        evl.get("reason", ""),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1

        conn.commit()
        print(f"\n✅  Done — {inserted} rows inserted, {skipped} already existed")
        print(f"    DB: {db_path}")

    finally:
        conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import an image eval HTML report into SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("source", help="URL or local file path of the HTML report")
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help=f"SQLite database path (default: {DEFAULT_DB})",
    )
    args = parser.parse_args()
    import_report(args.source, Path(args.db))


if __name__ == "__main__":
    main()
