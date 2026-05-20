#!/usr/bin/env python3
"""
Query video evaluation results from SQLite.

Subcommands:
    list        Show all model pairs and comparison counts
    stats       Win/loss/tie breakdown (overall or by model pair)
    dims        Per-dimension breakdown table
    elo         Compute multi-model Elo rankings
    examples    Show individual comparison rows

Usage:
    python query_video.py list
    python query_video.py stats  [--comparison "seedance-1.0-pro vs sora-2-pro"]
    python query_video.py dims   [--comparison PAIR]
    python query_video.py elo    [--dimension overall|structure_preservation|...]
                                 [--recompute]
    python query_video.py examples [--winner A|B|tie] [--comparison PAIR] [--limit N]

Dimensions: overall | structure_preservation | visual_quality |
            motion_performance | instruction_following
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.parse
from pathlib import Path
from textwrap import shorten
from typing import Any

from db_utils import default_db_path, ensure_db

DEFAULT_DB = default_db_path()

VIDEO_DIMENSIONS = [
    "structure_preservation",
    "visual_quality",
    "motion_performance",
    "instruction_following",
]
DIM_COL = {d: f"dim_{d}" for d in VIDEO_DIMENSIONS}

ELO_K    = 32.0
ELO_BASE = 1500.0


# ─── DB helpers ──────────────────────────────────────────────────────────────

def open_db(db_path: Path) -> sqlite3.Connection:
    db_path = ensure_db(db_path)
    uri = "file:" + urllib.parse.quote(str(db_path)) + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_rows(conn: sqlite3.Connection, comparison: str | None) -> list[sqlite3.Row]:
    if comparison:
        return conn.execute(
            "SELECT * FROM video_comparisons WHERE comparison=? ORDER BY pk_id",
            (comparison,),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM video_comparisons ORDER BY pk_id"
    ).fetchall()


# ─── Formatting ───────────────────────────────────────────────────────────────

def bar(n: int, total: int, width: int = 18) -> str:
    filled = round(width * n / total) if total else 0
    return "█" * filled + "░" * (width - filled)


def pct(n: int, total: int) -> str:
    return f"{100*n/total:.1f}%" if total else "—"


def print_table(headers: list[str], rows: list[list[Any]], sep: str = "  ") -> None:
    if not rows:
        print("  (no data)")
        return
    cols = list(zip(headers, *rows))
    widths = [max(len(str(v)) for v in col) for col in cols]
    fmt = sep.join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(sep.join("─" * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))


# ─── Subcommand: list ─────────────────────────────────────────────────────────

def cmd_list(conn: sqlite3.Connection, _args: argparse.Namespace) -> None:
    rows = conn.execute(
        """SELECT comparison, model_a, model_b, COUNT(*) total,
                  SUM(winner='A') wins_a, SUM(winner='B') wins_b,
                  SUM(winner='tie') ties, resolution
           FROM video_comparisons
           GROUP BY comparison ORDER BY comparison"""
    ).fetchall()
    if not rows:
        print("No video comparison data found. Run import_mysql.py first.")
        return
    print(f"\n📹  Video Comparisons in DB\n")
    hdrs = ["Comparison", "Total", "A-wins", "B-wins", "Ties", "Res"]
    tbl = [[r["comparison"], r["total"], r["wins_a"], r["wins_b"], r["ties"], r["resolution"] or "—"]
           for r in rows]
    print_table(hdrs, tbl)
    print()


# ─── Subcommand: stats ────────────────────────────────────────────────────────

def cmd_stats(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    rows = get_rows(conn, args.comparison)
    total = len(rows)

    # Group by comparison pair for display
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r["comparison"], []).append(r)

    print(f"\n📊  Video Stats  (n={total})\n")
    for comp, grp in sorted(groups.items()):
        # Extract model names from first row
        model_a = grp[0]["model_a"]
        model_b = grp[0]["model_b"]
        n = len(grp)
        a = sum(1 for r in grp if r["winner"] == "A")
        b = sum(1 for r in grp if r["winner"] == "B")
        t = sum(1 for r in grp if r["winner"] == "tie")
        print(f"  ── {comp}  (n={n}) ──")
        print(f"  {model_a:<28} : {a:>3}  {bar(a,n)}  {pct(a,n)}")
        print(f"  {model_b:<28} : {b:>3}  {bar(b,n)}  {pct(b,n)}")
        print(f"  {'tie':<28} : {t:>3}  {bar(t,n)}  {pct(t,n)}")
        print()


# ─── Subcommand: dims ─────────────────────────────────────────────────────────

def cmd_dims(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    rows = get_rows(conn, args.comparison)
    total = len(rows)

    # Collect all unique model pairs
    pairs = sorted({r["comparison"] for r in rows})

    for pair in pairs:
        grp = [r for r in rows if r["comparison"] == pair]
        n = len(grp)
        model_a = grp[0]["model_a"]
        model_b = grp[0]["model_b"]

        print(f"\n📐  Dimensions — {pair}  (n={n})\n")
        hdrs = ["Dimension", f"A ({model_a[:16]})", f"B ({model_b[:16]})", "Tie"]
        tbl = []
        for dim in VIDEO_DIMENSIONS:
            col = DIM_COL[dim]
            a = sum(1 for r in grp if r[col] == 1)
            b = sum(1 for r in grp if r[col] == -1)
            t = sum(1 for r in grp if r[col] == 0)
            tbl.append([dim, f"{a} ({pct(a,n)})", f"{b} ({pct(b,n)})", f"{t} ({pct(t,n)})"])
        print_table(hdrs, tbl)
    print()


# ─── Subcommand: elo ─────────────────────────────────────────────────────────

def compute_multi_elo(
    rows: list[sqlite3.Row],
    dimension: str,
) -> dict[str, dict]:
    """
    Compute Elo for all models from a set of pairwise comparisons.
    Handles multi-model scenario (A vs B, A vs C, B vs C).
    """
    ratings: dict[str, float] = {}
    counts:  dict[str, dict]  = {}

    def ensure(model: str) -> None:
        if model not in ratings:
            ratings[model] = ELO_BASE
            counts[model]  = {"wins": 0, "losses": 0, "ties": 0}

    col = "winner" if dimension == "overall" else DIM_COL[dimension]

    for row in rows:
        model_a = row["model_a"]
        model_b = row["model_b"]
        ensure(model_a)
        ensure(model_b)

        val = row[col]

        # For dimension cols, val is -1/0/+1; for winner col, it's A/B/tie
        if dimension == "overall":
            result = val   # "A" | "B" | "tie"
        else:
            result = "A" if val == 1 else ("B" if val == -1 else "tie")

        if result not in ("A", "B", "tie"):
            continue

        ra, rb = ratings[model_a], ratings[model_b]
        exp_a  = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
        exp_b  = 1.0 - exp_a

        if result == "A":
            sa, sb = 1.0, 0.0
            counts[model_a]["wins"]   += 1
            counts[model_b]["losses"] += 1
        elif result == "B":
            sa, sb = 0.0, 1.0
            counts[model_b]["wins"]   += 1
            counts[model_a]["losses"] += 1
        else:
            sa = sb = 0.5
            counts[model_a]["ties"] += 1
            counts[model_b]["ties"] += 1

        ratings[model_a] = ra + ELO_K * (sa - exp_a)
        ratings[model_b] = rb + ELO_K * (sb - exp_b)

    out = {}
    for model, c in counts.items():
        total = c["wins"] + c["losses"] + c["ties"]
        out[model] = {
            "elo":      round(ratings[model], 1),
            "wins":     c["wins"],
            "losses":   c["losses"],
            "ties":     c["ties"],
            "total":    total,
            "win_rate": round(100 * c["wins"] / total, 1) if total else 0.0,
        }
    return out


def cmd_elo(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    dimension = args.dimension or "overall"
    if dimension not in ("overall", *VIDEO_DIMENSIONS):
        sys.exit(f"❌  Unknown dimension. Choose: overall, {', '.join(VIDEO_DIMENSIONS)}")

    # Check cache
    cache_key = "video_all"
    if not args.recompute:
        cached = conn.execute(
            "SELECT * FROM elo_cache WHERE report_ids=? AND dimension=?",
            (cache_key, f"video_{dimension}"),
        ).fetchall()
        if cached:
            ranked = sorted([dict(r) for r in cached], key=lambda x: x["elo_score"], reverse=True)
            _print_elo(ranked, dimension, cached=True)
            return

    rows   = get_rows(conn, None)
    result = compute_multi_elo(rows, dimension)

    # Cache
    try:
        for model, s in result.items():
            conn.execute(
                """INSERT OR REPLACE INTO elo_cache
                   (report_ids, dimension, model, elo_score, wins, losses, ties, total, win_rate)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cache_key, f"video_{dimension}", model,
                 s["elo"], s["wins"], s["losses"], s["ties"], s["total"], s["win_rate"]),
            )
        conn.commit()
    except sqlite3.OperationalError:
        pass

    ranked = sorted(
        [{"model": m, "elo_score": s["elo"], **s} for m, s in result.items()],
        key=lambda x: x["elo_score"],
        reverse=True,
    )
    _print_elo(ranked, dimension, cached=False)


def _print_elo(ranked: list[dict], dimension: str, *, cached: bool) -> None:
    note = " (cached)" if cached else ""
    print(f"\n🏆  Video Elo Rankings — {dimension}{note}\n")
    hdrs = ["Rank", "Model", "Elo", "Wins", "Losses", "Ties", "Win Rate"]
    tbl  = []
    for i, s in enumerate(ranked, 1):
        tbl.append([
            i,
            s.get("model", ""),
            f"{s.get('elo_score') or s.get('elo', 0):.1f}",
            s["wins"], s["losses"], s["ties"],
            f"{s['win_rate']:.1f}%",
        ])
    print_table(hdrs, tbl)
    print()


# ─── Subcommand: examples ────────────────────────────────────────────────────

def cmd_examples(conn: sqlite3.Connection, args: argparse.Namespace) -> None:
    clauses = ["1=1"]
    params:  list[Any] = []

    if args.comparison:
        clauses.append("comparison = ?")
        params.append(args.comparison)

    if args.winner:
        w = args.winner.upper()
        clauses.append("winner = ?")
        params.append(w if w in ("A", "B") else "tie")

    limit = min(args.limit or 5, 50)
    params.append(limit)

    rows = conn.execute(
        f"SELECT * FROM video_comparisons WHERE {' AND '.join(clauses)} ORDER BY pk_id LIMIT ?",
        params,
    ).fetchall()

    if not rows:
        print("No matching examples.")
        return

    print(f"\n🔍  {len(rows)} example(s)\n")
    dim_sym = {1: "✓", -1: "✗", 0: "="}
    for r in rows:
        winner_str = (
            f"✅ {r['model_a']}" if r["winner"] == "A"
            else f"✅ {r['model_b']}" if r["winner"] == "B"
            else "🤝 Tie"
        )
        print(f"  ── pk#{r['pk_id']}  {winner_str} ──")
        print(f"  Pair   : {r['comparison']}")
        print(f"  Prompt : {shorten(r['prompt'] or '', 110)}")
        dims = "  ".join(
            f"{d[:4]}={dim_sym.get(r[DIM_COL[d]], '?')}"
            for d in VIDEO_DIMENSIONS
        )
        print(f"  Dims   : {dims}  (sum={r['dim_sum']})")
        if r["video_a_url"]:
            print(f"  Video A: {r['video_a_url'][:80]}…")
        if r["video_b_url"]:
            print(f"  Video B: {r['video_b_url'][:80]}…")
        print()


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="query_video.py",
        description="Query video evaluation results from SQLite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--db", default=str(DEFAULT_DB))
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Show all model pairs")

    p_st = sub.add_parser("stats", help="Win/loss/tie breakdown")
    p_st.add_argument("--comparison", metavar="PAIR")

    p_di = sub.add_parser("dims", help="Per-dimension breakdown")
    p_di.add_argument("--comparison", metavar="PAIR")

    p_el = sub.add_parser("elo", help="Multi-model Elo rankings")
    p_el.add_argument("--dimension", metavar="DIM",
                      help="overall | " + " | ".join(VIDEO_DIMENSIONS))
    p_el.add_argument("--recompute", action="store_true")

    p_ex = sub.add_parser("examples", help="Show individual rows")
    p_ex.add_argument("--comparison", metavar="PAIR")
    p_ex.add_argument("--winner", choices=["A", "B", "tie", "a", "b"])
    p_ex.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()
    conn = open_db(Path(args.db))
    cmds = {"list": cmd_list, "stats": cmd_stats, "dims": cmd_dims,
            "elo": cmd_elo, "examples": cmd_examples}
    try:
        cmds[args.cmd](conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
