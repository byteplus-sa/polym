#!/usr/bin/env python3
"""
Save a single pairwise evaluation result to eval.db.

Used as a standalone CLI after manual generation + scoring,
or called by the agent's polym-eval-run-evaluation workflow.

Usage:
    python3 save_to_db.py \
      --report-id seedream_vs_gemini_20260414 \
      --model-a "Seedream 5.0" --model-b "Gemini 3.1 Flash" \
      --prompt "A white sneaker on white background" \
      --winner A \
      --image-a https://... --image-b https://... \
      --dimensions '{"prompt_fidelity":"A","structure":"A"}' \
      --reason "Seedream shows better product detail"
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

EVAL_DB_PATH_CLI = Path(__file__).resolve().parents[2] / "polym-eval-db" / "scripts" / "db_path.py"


def resolve_db_path(db_path: str | Path | None = None, *, ensure: bool = False) -> Path:
    cmd = [sys.executable, str(EVAL_DB_PATH_CLI)]
    if db_path:
        cmd.extend(["--db", str(db_path)])
    if ensure:
        cmd.append("--ensure")
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        sys.exit(exc.returncode)
    return Path(result.stdout.strip())


DEFAULT_DB = resolve_db_path()

IMAGE_DIMENSIONS = [
    "prompt_fidelity", "structure", "texture", "lighting",
    "artifacts", "usefulness", "factual_consistency",
    "text_rendering", "edit_consistency",
]


def open_db(db_path: Path) -> sqlite3.Connection:
    db_path = resolve_db_path(db_path, ensure=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def ensure_report(conn: sqlite3.Connection, report_id: str, model_a: str, model_b: str,
                  title: str | None = None) -> None:
    existing = conn.execute(
        "SELECT report_id FROM reports WHERE report_id=?", (report_id,)
    ).fetchone()
    if not existing:
        t = title or f"{model_a} vs {model_b}"
        conn.execute(
            """INSERT INTO reports
               (report_id, report_title, model_a, model_b, model_a_key, model_b_key, total_rows)
               VALUES (?, ?, ?, ?, ?, ?, 0)""",
            (report_id, t, model_a, model_b,
             model_a.lower().replace(" ", "_"),
             model_b.lower().replace(" ", "_")),
        )
        print(f"  ✚ Created new report: {report_id}")
    else:
        print(f"  ✔ Using existing report: {report_id}")


def save_comparison(
    conn: sqlite3.Connection,
    report_id: str,
    model_a: str,
    model_b: str,
    prompt: str,
    winner: str,
    image_a_url: str | None,
    image_b_url: str | None,
    dimensions: dict,
    reason: str | None,
    category: str | None,
    scenario: str | None,
) -> int:
    # Row count for row_id
    count = conn.execute(
        "SELECT COUNT(*) FROM image_comparisons WHERE report_id=?", (report_id,)
    ).fetchone()[0]
    row_id = f"eval_{count + 1}"

    conn.execute(
        """INSERT INTO image_comparisons
           (report_id, row_id, prompt, winner,
            image_a_url, image_b_url,
            dim_prompt_fidelity, dim_structure, dim_texture, dim_lighting,
            dim_artifacts, dim_usefulness, dim_factual_consistency,
            dim_text_rendering, dim_edit_consistency,
            reason, category, scenario)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            report_id, row_id, prompt, winner,
            image_a_url, image_b_url,
            dimensions.get("prompt_fidelity"),
            dimensions.get("structure"),
            dimensions.get("texture"),
            dimensions.get("lighting"),
            dimensions.get("artifacts"),
            dimensions.get("usefulness"),
            dimensions.get("factual_consistency"),
            dimensions.get("text_rendering"),
            dimensions.get("edit_consistency"),
            reason, category, scenario,
        ),
    )

    # Update total_rows
    conn.execute(
        """UPDATE reports SET total_rows = (
               SELECT COUNT(*) FROM image_comparisons WHERE report_id=?
           ) WHERE report_id=?""",
        (report_id, report_id),
    )

    # Invalidate Elo cache
    cache_key = json.dumps([report_id])
    conn.execute("DELETE FROM elo_cache WHERE report_ids=?", (cache_key,))
    conn.commit()

    new_total = conn.execute(
        "SELECT total_rows FROM reports WHERE report_id=?", (report_id,)
    ).fetchone()[0]
    return new_total


def main() -> None:
    parser = argparse.ArgumentParser(description="Save evaluation result to eval.db")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to eval.db")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--report-title", default=None)
    parser.add_argument("--model-a", required=True)
    parser.add_argument("--model-b", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--winner", required=True, choices=["A", "B", "tie"])
    parser.add_argument("--image-a", default=None)
    parser.add_argument("--image-b", default=None)
    parser.add_argument("--dimensions", default="{}", help="JSON dict of dimension winners")
    parser.add_argument("--reason", default=None)
    parser.add_argument("--category", default=None)
    parser.add_argument("--scenario", default=None)
    args = parser.parse_args()

    try:
        dims = json.loads(args.dimensions)
    except json.JSONDecodeError:
        sys.exit("❌  --dimensions must be valid JSON, e.g. '{\"prompt_fidelity\":\"A\"}'")

    conn = open_db(Path(args.db))
    ensure_report(conn, args.report_id, args.model_a, args.model_b, args.report_title)

    total = save_comparison(
        conn=conn,
        report_id=args.report_id,
        model_a=args.model_a,
        model_b=args.model_b,
        prompt=args.prompt,
        winner=args.winner,
        image_a_url=args.image_a,
        image_b_url=args.image_b,
        dimensions=dims,
        reason=args.reason,
        category=args.category,
        scenario=args.scenario,
    )

    winner_label = args.model_a if args.winner == "A" else (args.model_b if args.winner == "B" else "Tie")
    print(f"\n✅  Saved comparison #{total}")
    print(f"   Report  : {args.report_id}")
    print(f"   Winner  : {winner_label} ({args.winner})")
    if dims:
        print(f"   Dims    : {dims}")
    print(f"   Total rows in report: {total}\n")
    conn.close()


if __name__ == "__main__":
    main()
