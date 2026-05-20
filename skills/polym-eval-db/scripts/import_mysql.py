#!/usr/bin/env python3
"""
Import gsb_video rows from MySQL into the local SQLite eval DB.

The MySQL `usecase.gsb_video` table stores multi-model pairwise video
generation comparisons (seedance, sora, veo, …).  Each row holds a `gsb`
JSON column with 4 dimension scores (−1/0/+1) where:
    +1  → model_a wins that dimension
     0  → tie
    −1  → model_b wins that dimension

Overall winner is derived as sign(sum of dimension scores).

Usage:
    python import_mysql.py [--db PATH] [--mysql-host H] [--mysql-port P]
                           [--mysql-user U] [--mysql-password PW]
                           [--mysql-database DB] [--table TABLE]

Defaults come from env vars DB_HOST / DB_PORT / DB_USER / DB_PASSWORD /
DB_DATABASE (same vars used by the FastAPI backend).
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from db_utils import default_db_path

# ─── Config ──────────────────────────────────────────────────────────────────

DEFAULT_SQLITE = default_db_path()

MYSQL_DEFAULTS = {
    "host":     os.environ.get("DB_HOST",     "127.0.0.1"),
    "port":     int(os.environ.get("DB_PORT", 3306)),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "NewRootPass123!"),
    "database": os.environ.get("DB_DATABASE", "usecase"),
}

VIDEO_DIMENSIONS = [
    "structure_preservation",
    "visual_quality",
    "motion_performance",
    "instruction_following",
]

# ─── SQLite schema ────────────────────────────────────────────────────────────

DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS video_comparisons (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    source                      TEXT    DEFAULT 'mysql_gsb_video',
    pk_id                       INTEGER UNIQUE,          -- MySQL auto-increment pk
    row_id                      INTEGER,                 -- prompt group id
    prompt                      TEXT,
    model_a                     TEXT    NOT NULL,
    model_b                     TEXT    NOT NULL,
    comparison                  TEXT,                    -- "modelA vs modelB"
    ref_image                   TEXT,
    video_a_url                 TEXT,
    video_b_url                 TEXT,
    resolution                  TEXT,
    industry                    INTEGER,
    scene                       INTEGER,
    -- Dimension scores: +1 (A wins) | 0 (tie) | -1 (B wins)
    dim_structure_preservation  INTEGER,
    dim_visual_quality          INTEGER,
    dim_motion_performance      INTEGER,
    dim_instruction_following   INTEGER,
    -- Derived overall winner
    dim_sum                     INTEGER,   -- sum of 4 dimension scores
    winner                      TEXT,      -- A | B | tie
    -- Raw fields
    gsb_json                    TEXT,
    reason                      TEXT,
    confidence                  REAL,
    imported_at                 TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_vcmp_models      ON video_comparisons(model_a, model_b);
CREATE INDEX IF NOT EXISTS idx_vcmp_winner      ON video_comparisons(winner);
CREATE INDEX IF NOT EXISTS idx_vcmp_comparison  ON video_comparisons(comparison);
CREATE INDEX IF NOT EXISTS idx_vcmp_resolution  ON video_comparisons(resolution);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(DDL)


# ─── Score → winner mapping ───────────────────────────────────────────────────

def score_to_winner(score: int) -> str:
    if score > 0:
        return "A"
    if score < 0:
        return "B"
    return "tie"


def parse_gsb(gsb_str: str | None) -> dict:
    """
    Parse the gsb JSON and return per-dimension scores + derived overall winner.
    Returns {"dim_*": int, "dim_sum": int, "winner": str}.
    """
    if not gsb_str:
        return {f"dim_{d}": None for d in VIDEO_DIMENSIONS} | {"dim_sum": None, "winner": "tie"}

    try:
        gsb = json.loads(gsb_str)
    except json.JSONDecodeError:
        return {f"dim_{d}": None for d in VIDEO_DIMENSIONS} | {"dim_sum": None, "winner": "tie"}

    scores = {}
    total = 0
    for dim in VIDEO_DIMENSIONS:
        s = gsb.get(dim, {}).get("score")
        if s is None:
            # fallback: check top-level numeric
            s = gsb.get(dim) if isinstance(gsb.get(dim), (int, float)) else 0
        s = int(s) if s is not None else 0
        scores[f"dim_{dim}"] = s
        total += s

    scores["dim_sum"] = total
    scores["winner"] = score_to_winner(total)
    return scores


# ─── Import logic ─────────────────────────────────────────────────────────────

def import_gsb_video(
    sqlite_path: Path,
    mysql_cfg: dict,
    table: str = "gsb_video",
) -> None:
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError:
        sys.exit("❌  pymysql is required: pip install pymysql")

    print(f"🔌  Connecting to MySQL {mysql_cfg['host']}:{mysql_cfg['port']} "
          f"db={mysql_cfg['database']} …")

    mysql_conn = pymysql.connect(**mysql_cfg, cursorclass=DictCursor)
    try:
        with mysql_conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as n FROM `{table}`")
            total_mysql = cur.fetchone()["n"]
            print(f"    Found {total_mysql} rows in {table}")

            cur.execute(f"SELECT * FROM `{table}` ORDER BY pk_id")
            mysql_rows = cur.fetchall()
    finally:
        mysql_conn.close()

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(sqlite_path))

    try:
        init_db(conn)

        inserted = skipped = 0
        for row in mysql_rows:
            gsb_str  = row.get("gsb") or ""
            dim_data = parse_gsb(gsb_str)

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO video_comparisons (
                        pk_id, row_id, prompt,
                        model_a, model_b, comparison,
                        ref_image, video_a_url, video_b_url,
                        resolution, industry, scene,
                        dim_structure_preservation, dim_visual_quality,
                        dim_motion_performance, dim_instruction_following,
                        dim_sum, winner,
                        gsb_json, reason, confidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["pk_id"],
                        row.get("id"),
                        row.get("prompt", ""),
                        row.get("model_a", ""),
                        row.get("model_b", ""),
                        row.get("comparison", ""),
                        row.get("ref_image", ""),
                        row.get("gen_video_path_a", ""),
                        row.get("gen_video_path_b", ""),
                        row.get("resolution", ""),
                        row.get("industry"),
                        row.get("scene"),
                        dim_data.get("dim_structure_preservation"),
                        dim_data.get("dim_visual_quality"),
                        dim_data.get("dim_motion_performance"),
                        dim_data.get("dim_instruction_following"),
                        dim_data.get("dim_sum"),
                        dim_data.get("winner"),
                        gsb_str,
                        row.get("reason", ""),
                        row.get("confidence"),
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1

        conn.commit()

        # Quick summary
        pairs = conn.execute(
            "SELECT comparison, COUNT(*) n, "
            "SUM(winner='A') wins_a, SUM(winner='B') wins_b, SUM(winner='tie') ties "
            "FROM video_comparisons GROUP BY comparison"
        ).fetchall()

        print(f"\n✅  Done — {inserted} rows inserted, {skipped} already existed")
        print(f"    DB: {sqlite_path}\n")
        print("  Comparison                              total   A-wins  B-wins  ties")
        print("  " + "─" * 68)
        for p in pairs:
            print(
                f"  {p[0]:<38}  {p[1]:>5}   {p[2]:>5}   {p[3]:>5}  {p[4]:>4}"
            )
        print()

    finally:
        conn.close()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import MySQL gsb_video into SQLite eval DB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--db",             default=str(DEFAULT_SQLITE), help="SQLite path")
    parser.add_argument("--mysql-host",     default=MYSQL_DEFAULTS["host"])
    parser.add_argument("--mysql-port",     default=MYSQL_DEFAULTS["port"], type=int)
    parser.add_argument("--mysql-user",     default=MYSQL_DEFAULTS["user"])
    parser.add_argument("--mysql-password", default=MYSQL_DEFAULTS["password"])
    parser.add_argument("--mysql-database", default=MYSQL_DEFAULTS["database"])
    parser.add_argument("--table",          default="gsb_video")
    args = parser.parse_args()

    mysql_cfg = {
        "host":     args.mysql_host,
        "port":     args.mysql_port,
        "user":     args.mysql_user,
        "password": args.mysql_password,
        "database": args.mysql_database,
        "unix_socket": "/tmp/mysql.sock" if args.mysql_host == "127.0.0.1" else None,
    }
    # Remove None values
    mysql_cfg = {k: v for k, v in mysql_cfg.items() if v is not None}

    import_gsb_video(Path(args.db), mysql_cfg, args.table)


if __name__ == "__main__":
    main()
