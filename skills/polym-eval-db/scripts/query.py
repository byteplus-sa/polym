#!/usr/bin/env python3
"""
Query image evaluation results from SQLite — data layer + Elo computation.

Subcommands:
    list                    List all imported reports
    stats                   Win / loss / tie breakdown
    elo                     Compute Elo rankings (cached after first run)
    examples                Show individual comparison rows
    dims                    Per-dimension win-rate table across all dimensions

Usage:
    python query.py list
    python query.py stats  [--report ID] [--group-by category|scenario|industry]
    python query.py elo    [--report ID [ID…]] [--dimension DIM] [--recompute]
    python query.py examples [--report ID] [--winner A|B|tie]
                             [--category TEXT] [--scenario TEXT] [--limit N]
    python query.py dims   [--report ID]

Environment:
    EVAL_DB_PATH   override the default SQLite path

Dimensions: overall | prompt_fidelity | structure | texture | lighting |
            artifacts | usefulness | factual_consistency | text_rendering |
            edit_consistency
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import urllib.parse
from pathlib import Path
from textwrap import shorten
from typing import Any

from db_utils import default_db_path, ensure_db

# ─── Config ──────────────────────────────────────────────────────────────────

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

DIM_COL = {d: f"dim_{d}" for d in DIMENSIONS}   # dim name → DB column
ELO_K   = 32.0
ELO_BASE = 1500.0


# ─── DB helpers ──────────────────────────────────────────────────────────────

def open_db(db_path: Path) -> sqlite3.Connection:
    db_path = ensure_db(db_path)
    uri = "file:" + urllib.parse.quote(str(db_path)) + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_report_ids(conn: sqlite3.Connection, requested: list[str] | None) -> list[str]:
    """Return the list of report IDs to operate on."""
    rows = conn.execute("SELECT report_id FROM reports ORDER BY imported_at").fetchall()
    available = [r["report_id"] for r in rows]
    if not available:
        sys.exit("❌  No reports in database. Run import_report.py first.")
    if not requested:
        return available          # default: all reports
    missing = [r for r in requested if r not in available]
    if missing:
        sys.exit(f"❌  Unknown report IDs: {missing}\n    Available: {available}")
    return requested


def fetch_comparisons(conn: sqlite3.Connection, report_ids: list[str]) -> list[sqlite3.Row]:
    ph = ",".join("?" * len(report_ids))
    return conn.execute(
        f"SELECT * FROM image_comparisons WHERE report_id IN ({ph}) ORDER BY report_id, excel_id",
        report_ids,
    ).fetchall()


# ─── Formatting helpers ───────────────────────────────────────────────────────

def bar(n: int, total: int, width: int = 20) -> str:
    filled = round(width * n / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:.1f}%" if total else "—"


def print_table(headers: list[str], rows: list[list[Any]], *, sep: str = "  ") -> None:
    cols = list(zip(headers, *rows)) if rows else [(h,) for h in headers]
    widths = [max(len(str(v)) for v in col) for col in cols]
    fmt = sep.join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(sep.join("─" * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))


# ─── Subcommand: list ─────────────────────────────────────────────────────────

def cmd_list(conn: sqlite3.Connection, _args: argparse.Namespace) -> None:
    rows = conn.execute(
        "SELECT report_id, report_title, model_a, model_b, total_rows, imported_at FROM reports ORDER BY imported_at"
    ).fetchall()
    if not rows:
        print("No reports imported yet.")
        return
    print(f"\n{'Reports in database':}\n{'─'*60}")
    for r in rows:
        print(f"  ID      : {r['report_id']}")
        print(f"  Title   : {r['report_title'] or '(untitled)'}")
        print(f"  Models  : {r['model_a']}  vs  {r['model_b']}")
        print(f"  Rows    : {r['total_rows']}")
        print(f"  Imported: {r['imported_at']}")
        print()


# ─── Subcommand: stats ────────────────────────────────────────────────────────

def cmd_stats(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    report_ids = get_report_ids(conn, args.report)
    rows = fetch_comparisons(conn, report_ids)

    # Resolve model labels
    rpt_rows = conn.execute(
        "SELECT report_id, model_a, model_b FROM reports WHERE report_id IN ({})".format(
            ",".join("?" * len(report_ids))
        ),
        report_ids,
    ).fetchall()
    # For simplicity, use the first report's model names as labels
    model_a_label = rpt_rows[0]["model_a"] if rpt_rows else "Model A"
    model_b_label = rpt_rows[0]["model_b"] if rpt_rows else "Model B"

    group_by = args.group_by  # None | "category" | "scenario" | "industry"

    def tally(subset):
        a = sum(1 for r in subset if r["winner"] == "A")
        b = sum(1 for r in subset if r["winner"] == "B")
        t = sum(1 for r in subset if r["winner"] == "tie")
        return a, b, t

    if group_by:
        groups: dict[str, list] = {}
        for r in rows:
            key = r[group_by] or "(blank)"
            groups.setdefault(key, []).append(r)

        print(f"\n📊  Stats by {group_by}  ({', '.join(report_ids)})\n")
        hdrs = [group_by.capitalize(), f"A ({model_a_label[:12]})", f"B ({model_b_label[:12]})", "Tie", "Total"]
        tbl = []
        for grp, grp_rows in sorted(groups.items()):
            a, b, t = tally(grp_rows)
            total = len(grp_rows)
            tbl.append([shorten(grp, 35), f"{a} ({pct(a,total)})", f"{b} ({pct(b,total)})", f"{t} ({pct(t,total)})", total])
        print_table(hdrs, tbl)
    else:
        a, b, t = tally(rows)
        total = len(rows)
        print(f"\n📊  Overall Stats  ({', '.join(report_ids)})\n")
        print(f"  Total comparisons : {total}")
        print(f"  {model_a_label:<30} wins : {a:>4}  {bar(a,total)}  {pct(a,total)}")
        print(f"  {model_b_label:<30} wins : {b:>4}  {bar(b,total)}  {pct(b,total)}")
        print(f"  {'Tie':<30}      : {t:>4}  {bar(t,total)}  {pct(t,total)}")
        print()


# ─── Subcommand: dims ─────────────────────────────────────────────────────────

def cmd_dims(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    report_ids = get_report_ids(conn, args.report)
    rows = fetch_comparisons(conn, report_ids)

    rpt_rows = conn.execute(
        "SELECT model_a, model_b FROM reports WHERE report_id IN ({})".format(
            ",".join("?" * len(report_ids))
        ),
        report_ids,
    ).fetchall()
    model_a_label = rpt_rows[0]["model_a"][:14] if rpt_rows else "Model A"
    model_b_label = rpt_rows[0]["model_b"][:14] if rpt_rows else "Model B"

    total = len(rows)
    print(f"\n📐  Per-Dimension Breakdown  ({', '.join(report_ids)})  n={total}\n")
    hdrs = ["Dimension", f"A ({model_a_label})", f"B ({model_b_label})", "Tie"]
    tbl = []
    for dim in DIMENSIONS:
        col = DIM_COL[dim]
        a = sum(1 for r in rows if r[col] == "A")
        b = sum(1 for r in rows if r[col] == "B")
        t = sum(1 for r in rows if r[col] == "tie")
        tbl.append([dim, f"{a} ({pct(a,total)})", f"{b} ({pct(b,total)})", f"{t} ({pct(t,total)})"])
    print_table(hdrs, tbl)
    print()


# ─── Subcommand: elo ─────────────────────────────────────────────────────────

def compute_elo(
    rows: list[sqlite3.Row],
    dimension: str,          # "overall" or one of DIMENSIONS
    model_a: str,
    model_b: str,
) -> dict[str, dict]:
    """
    Compute Elo ratings for model_a and model_b from pairwise comparisons.

    winner column (or dim column) uses A/B/tie.
    Returns {model_name: {elo, wins, losses, ties, total, win_rate}}.
    """
    ratings = {model_a: ELO_BASE, model_b: ELO_BASE}
    counts  = {model_a: {"wins": 0, "losses": 0, "ties": 0},
               model_b: {"wins": 0, "losses": 0, "ties": 0}}

    col = "winner" if dimension == "overall" else DIM_COL[dimension]

    for row in rows:
        result = row[col]
        if result not in ("A", "B", "tie"):
            continue

        ra, rb = ratings[model_a], ratings[model_b]
        exp_a = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
        exp_b = 1.0 - exp_a

        if result == "A":
            sa, sb = 1.0, 0.0
            counts[model_a]["wins"]   += 1
            counts[model_b]["losses"] += 1
        elif result == "B":
            sa, sb = 0.0, 1.0
            counts[model_b]["wins"]   += 1
            counts[model_a]["losses"] += 1
        else:  # tie
            sa = sb = 0.5
            counts[model_a]["ties"] += 1
            counts[model_b]["ties"] += 1

        ratings[model_a] = ra + ELO_K * (sa - exp_a)
        ratings[model_b] = rb + ELO_K * (sb - exp_b)

    result_map = {}
    for model in (model_a, model_b):
        c = counts[model]
        total = c["wins"] + c["losses"] + c["ties"]
        result_map[model] = {
            "elo":      round(ratings[model], 1),
            "wins":     c["wins"],
            "losses":   c["losses"],
            "ties":     c["ties"],
            "total":    total,
            "win_rate": round(100 * c["wins"] / total, 1) if total else 0.0,
        }
    return result_map


def cmd_elo(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    report_ids = get_report_ids(conn, args.report)
    dimension  = args.dimension or "overall"

    if dimension not in ("overall", *DIMENSIONS):
        sys.exit(f"❌  Unknown dimension '{dimension}'. Choose: overall, {', '.join(DIMENSIONS)}")

    # Check cache
    cache_key = json.dumps(sorted(report_ids))
    if not args.recompute:
        cached = conn.execute(
            "SELECT * FROM elo_cache WHERE report_ids=? AND dimension=?",
            (cache_key, dimension),
        ).fetchall()
        if cached:
            rpt = conn.execute(
                "SELECT model_a, model_b FROM reports WHERE report_id=?", (report_ids[0],)
            ).fetchone()
            model_a_label = rpt["model_a"] if rpt else "Model A"
            model_b_label = rpt["model_b"] if rpt else "Model B"
            label_map = {}
            for row in cached:
                label_map[row["model"]] = row
            _print_elo_table(label_map, model_a_label, model_b_label, dimension, report_ids, cached=True)
            return

    rows = fetch_comparisons(conn, report_ids)
    rpt  = conn.execute(
        "SELECT model_a, model_b FROM reports WHERE report_id=?", (report_ids[0],)
    ).fetchone()
    model_a = rpt["model_a"]
    model_b = rpt["model_b"]

    result = compute_elo(rows, dimension, model_a, model_b)

    # Cache results
    try:
        for model, stats in result.items():
            conn.execute(
                """
                INSERT OR REPLACE INTO elo_cache
                    (report_ids, dimension, model, elo_score, wins, losses, ties, total, win_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (cache_key, dimension, model,
                 stats["elo"], stats["wins"], stats["losses"], stats["ties"],
                 stats["total"], stats["win_rate"]),
            )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    _print_elo_table(result, model_a, model_b, dimension, report_ids, cached=False)


def _print_elo_table(
    result: dict,
    model_a: str,
    model_b: str,
    dimension: str,
    report_ids: list[str],
    *,
    cached: bool,
) -> None:
    cache_note = " (cached)" if cached else ""
    print(f"\n🏆  Elo Rankings — {dimension}{cache_note}  ({', '.join(report_ids)})\n")
    hdrs = ["Rank", "Model", "Elo", "Wins", "Losses", "Ties", "Win Rate"]
    ranked = sorted(result.items(), key=lambda x: x[1]["elo"] if isinstance(x[1], dict) else x[1]["elo_score"], reverse=True)
    tbl = []
    for i, (model, s) in enumerate(ranked, 1):
        if isinstance(s, sqlite3.Row):
            s = dict(s)
        tbl.append([
            i,
            model,
            f"{s.get('elo') or s.get('elo_score'):.1f}",
            s["wins"], s["losses"], s["ties"],
            f"{s['win_rate']:.1f}%",
        ])
    print_table(hdrs, tbl)
    print()


# ─── Subcommand: examples ────────────────────────────────────────────────────

def cmd_examples(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    report_ids = get_report_ids(conn, args.report)

    clauses = ["report_id IN ({})".format(",".join("?" * len(report_ids)))]
    params: list[Any] = list(report_ids)

    if args.winner:
        clauses.append("winner = ?")
        params.append(args.winner.upper() if args.winner.upper() in ("A", "B") else args.winner.lower())

    if args.category:
        clauses.append("category LIKE ?")
        params.append(f"%{args.category}%")

    if args.scenario:
        clauses.append("scenario LIKE ?")
        params.append(f"%{args.scenario}%")

    limit = args.limit or 5
    params.append(limit)

    sql = (
        f"SELECT * FROM image_comparisons WHERE {' AND '.join(clauses)} "
        f"ORDER BY excel_id LIMIT ?"
    )
    rows = conn.execute(sql, params).fetchall()

    # Fetch model labels
    rpt = conn.execute(
        "SELECT model_a, model_b FROM reports WHERE report_id=?", (report_ids[0],)
    ).fetchone()
    model_a = rpt["model_a"] if rpt else "Model A"
    model_b = rpt["model_b"] if rpt else "Model B"

    winner_label = {"A": f"✅ {model_a}", "B": f"✅ {model_b}", "tie": "🤝 Tie"}

    if not rows:
        print("No matching examples found.")
        return

    print(f"\n🔍  {len(rows)} example(s)  ({', '.join(report_ids)})\n")
    for r in rows:
        print(f"  ── #{r['excel_id']}  {winner_label.get(r['winner'], r['winner'])} ──")
        print(f"  Prompt   : {shorten(r['prompt'], 120)}")
        print(f"  Category : {r['category']}  |  Scenario: {r['scenario']}")
        dims_str = "  ".join(
            f"{d[:4]}={'✓' if r[DIM_COL[d]]=='A' else ('✗' if r[DIM_COL[d]]=='B' else '=')}"
            for d in DIMENSIONS
        )
        print(f"  Dims     : {dims_str}")
        if r["reason"]:
            print(f"  Reason   : {shorten(r['reason'], 200)}")
        if r["image_a_url"]:
            print(f"  Image A  : {r['image_a_url'][:80]}…")
        if r["image_b_url"]:
            print(f"  Image B  : {r['image_b_url'][:80]}…")
        print()


# ─── CLI dispatch ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="query.py",
        description="Query image evaluation results from SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite database path")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # list
    sub.add_parser("list", help="List all imported reports")

    # stats
    p_stats = sub.add_parser("stats", help="Win/loss/tie breakdown")
    p_stats.add_argument("--report", nargs="+", metavar="ID", help="Report ID(s) — default: all")
    p_stats.add_argument("--group-by", choices=["category", "scenario", "industry"], dest="group_by")

    # elo
    p_elo = sub.add_parser("elo", help="Compute Elo rankings")
    p_elo.add_argument("--report", nargs="+", metavar="ID", help="Report ID(s) — default: all")
    p_elo.add_argument(
        "--dimension", metavar="DIM",
        help="overall (default) or: " + " | ".join(DIMENSIONS),
    )
    p_elo.add_argument("--recompute", action="store_true", help="Ignore cached results")

    # dims
    p_dims = sub.add_parser("dims", help="Per-dimension win-rate table")
    p_dims.add_argument("--report", nargs="+", metavar="ID")

    # examples
    p_ex = sub.add_parser("examples", help="Show individual comparison rows")
    p_ex.add_argument("--report", nargs="+", metavar="ID")
    p_ex.add_argument("--winner", choices=["A", "B", "tie", "a", "b"])
    p_ex.add_argument("--category", metavar="TEXT")
    p_ex.add_argument("--scenario", metavar="TEXT")
    p_ex.add_argument("--limit", type=int, default=5)

    args   = parser.parse_args()
    db     = open_db(Path(args.db))
    cmds   = {"list": cmd_list, "stats": cmd_stats, "elo": cmd_elo,
               "dims": cmd_dims, "examples": cmd_examples}
    try:
        cmds[args.cmd](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    main()
