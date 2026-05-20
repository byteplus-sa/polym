#!/usr/bin/env python3
"""
Generate comprehensive evaluation reports from polym-eval-db SQLite data.
Mirrors the style of benchmark/image/reports/*.md and benchmark/video/reports/*.md.

Usage:
  python3 generate_report.py                          # full report, all data
  python3 generate_report.py --type image             # image comparisons only
  python3 generate_report.py --type video             # video comparisons only
  python3 generate_report.py --type elo               # Elo rankings only
  python3 generate_report.py --report-id my_report    # filter by report ID
  python3 generate_report.py --model Seedream         # filter by model name
  python3 generate_report.py --lang en --output out.md
"""

import argparse
import datetime
import json
import os
import sqlite3
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

EVAL_DB_PATH_CLI = Path(__file__).resolve().parents[2] / "polym-eval-db" / "scripts" / "db_path.py"

# ---------------------------------------------------------------------------
# DB path
# ---------------------------------------------------------------------------

def resolve_default_db_path() -> Path:
    try:
        result = subprocess.run(
            [sys.executable, str(EVAL_DB_PATH_CLI)],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        sys.exit(exc.returncode)
    return Path(result.stdout.strip())


def ensure_db_path(db_path: Path) -> Path:
    try:
        result = subprocess.run(
            [sys.executable, str(EVAL_DB_PATH_CLI), "--db", str(db_path), "--ensure"],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr)
        sys.exit(exc.returncode)
    return Path(result.stdout.strip())


def find_db() -> Path:
    env = os.environ.get("EVAL_DB_PATH", "")
    if env:
        p = Path(env).expanduser()
        if p.exists():
            return p
    candidates = [
        resolve_default_db_path(),
        Path(__file__).parent.parent.parent.parent / "eval.db",
    ]
    for c in candidates:
        if c.exists():
            return c
    return resolve_default_db_path()


def get_conn(db_path: Path) -> sqlite3.Connection:
    db_path = ensure_db_path(db_path)
    uri = "file:" + urllib.parse.quote(str(db_path)) + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Elo calculation (simple Bradley-Terry / iterative)
# ---------------------------------------------------------------------------

def compute_elo(comparisons: list, k: int = 32, base: float = 1500.0) -> dict:
    """Compute Elo scores from a list of (model_a, model_b, winner) tuples."""
    ratings = defaultdict(lambda: base)
    for model_a, model_b, winner in comparisons:
        ra, rb = ratings[model_a], ratings[model_b]
        ea = 1 / (1 + 10 ** ((rb - ra) / 400))
        eb = 1 - ea
        if winner == "A":
            sa, sb = 1.0, 0.0
        elif winner == "B":
            sa, sb = 0.0, 1.0
        else:
            sa, sb = 0.5, 0.5
        ratings[model_a] = ra + k * (sa - ea)
        ratings[model_b] = rb + k * (sb - eb)
    return dict(ratings)


# ---------------------------------------------------------------------------
# Image report data
# ---------------------------------------------------------------------------

IMAGE_DIMENSIONS = [
    "prompt_fidelity", "structure", "texture", "lighting",
    "artifacts", "usefulness", "factual_consistency", "text_rendering", "edit_consistency",
]

DIM_LABELS_ZH = {
    "prompt_fidelity": "指令遵循",
    "structure": "结构准确性",
    "texture": "纹理质量",
    "lighting": "光照效果",
    "artifacts": "瑕疵控制",
    "usefulness": "实用性",
    "factual_consistency": "事实一致性",
    "text_rendering": "文字渲染",
    "edit_consistency": "编辑一致性",
}

DIM_LABELS_EN = {d: d.replace("_", " ").title() for d in IMAGE_DIMENSIONS}


def fetch_image_data(conn: sqlite3.Connection, report_id: str = None, model: str = None) -> dict:
    """Fetch image comparison data from SQLite."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    if "image_comparisons" not in tables:
        return {}

    where_clauses = []
    params = []
    if report_id:
        where_clauses.append("report_id = ?")
        params.append(report_id)
    if model:
        where_clauses.append("(model_a LIKE ? OR model_b LIKE ?)")
        params += [f"%{model}%", f"%{model}%"]

    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    rows = conn.execute(
        f"SELECT * FROM image_comparisons {where} ORDER BY report_id, id",
        params
    ).fetchall()

    if not rows:
        return {}

    rows = [dict(r) for r in rows]

    # Stats
    total = len(rows)
    wins_a = sum(1 for r in rows if r.get("winner") == "A")
    wins_b = sum(1 for r in rows if r.get("winner") == "B")
    ties   = sum(1 for r in rows if r.get("winner") == "tie")

    # Per-dimension stats
    dim_stats = {}
    for dim in IMAGE_DIMENSIONS:
        da = sum(1 for r in rows if r.get(dim) == "A")
        db = sum(1 for r in rows if r.get(dim) == "B")
        dt = sum(1 for r in rows if r.get(dim) == "tie")
        n  = da + db + dt
        if n > 0:
            dim_stats[dim] = {"A": da, "B": db, "tie": dt, "n": n,
                               "pct_A": da/n*100, "pct_B": db/n*100, "pct_tie": dt/n*100}

    # Model pairs
    pairs = defaultdict(lambda: {"A": 0, "B": 0, "tie": 0})
    for r in rows:
        key = (r.get("model_a", "?"), r.get("model_b", "?"))
        w   = r.get("winner", "tie")
        pairs[key][w if w in ("A", "B", "tie") else "tie"] += 1

    # Elo
    elo_input = [(r.get("model_a","?"), r.get("model_b","?"), r.get("winner","tie")) for r in rows]
    elo_scores = compute_elo(elo_input)

    # Category/scenario breakdown
    cat_stats = defaultdict(lambda: {"A": 0, "B": 0, "tie": 0})
    for r in rows:
        cat = r.get("category") or r.get("scenario") or "—"
        w   = r.get("winner", "tie")
        cat_stats[cat][w if w in ("A","B","tie") else "tie"] += 1

    # Get model names for the primary pair
    model_a_name = rows[0].get("model_a", "Model A") if rows else "Model A"
    model_b_name = rows[0].get("model_b", "Model B") if rows else "Model B"
    if len(pairs) == 1:
        (model_a_name, model_b_name) = list(pairs.keys())[0]

    # Sample examples (top 3 per side)
    examples_a = [r for r in rows if r.get("winner") == "A" and r.get("prompt")][:3]
    examples_b = [r for r in rows if r.get("winner") == "B" and r.get("prompt")][:3]

    # Reports list
    report_ids = sorted(set(r.get("report_id", "") for r in rows))

    return {
        "total": total, "wins_a": wins_a, "wins_b": wins_b, "ties": ties,
        "model_a": model_a_name, "model_b": model_b_name,
        "pairs": dict(pairs), "dim_stats": dim_stats,
        "elo_scores": elo_scores, "cat_stats": dict(cat_stats),
        "examples_a": examples_a, "examples_b": examples_b,
        "report_ids": report_ids,
    }


# ---------------------------------------------------------------------------
# Video report data
# ---------------------------------------------------------------------------

VIDEO_DIMENSIONS = ["structure", "visual_quality", "motion_quality",
                    "instruction_following", "audio_quality", "av_alignment"]

VIDEO_DIM_LABELS_ZH = {
    "structure": "构图结构",
    "visual_quality": "视觉质量",
    "motion_quality": "运动质量",
    "instruction_following": "指令遵循",
    "audio_quality": "音频质量",
    "av_alignment": "音画同步",
}
VIDEO_DIM_LABELS_EN = {d: d.replace("_", " ").title() for d in VIDEO_DIMENSIONS}


def fetch_video_data(conn: sqlite3.Connection, model: str = None) -> dict:
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    if "video_comparisons" not in tables:
        return {}

    where = ""
    params = []
    if model:
        where = "WHERE model_a LIKE ? OR model_b LIKE ?"
        params = [f"%{model}%", f"%{model}%"]

    rows = conn.execute(
        f"SELECT * FROM video_comparisons {where} ORDER BY id",
        params
    ).fetchall()

    if not rows:
        return {}

    rows = [dict(r) for r in rows]
    total = len(rows)
    wins_a = sum(1 for r in rows if r.get("winner") == "A")
    wins_b = sum(1 for r in rows if r.get("winner") == "B")
    ties   = sum(1 for r in rows if r.get("winner") == "tie")

    dim_stats = {}
    for dim in VIDEO_DIMENSIONS:
        col_a = f"{dim}_a"
        col_b = f"{dim}_b"
        if col_a not in rows[0]:
            continue
        scores_a = [r.get(col_a, 0) or 0 for r in rows]
        scores_b = [r.get(col_b, 0) or 0 for r in rows]
        n = len(rows)
        avg_a = sum(scores_a) / n if n else 0
        avg_b = sum(scores_b) / n if n else 0
        dim_stats[dim] = {"avg_a": round(avg_a, 2), "avg_b": round(avg_b, 2),
                          "n": n, "leader": "A" if avg_a > avg_b else ("B" if avg_b > avg_a else "tie")}

    # All models in the data
    all_models = set()
    for r in rows:
        all_models.add(r.get("model_a", ""))
        all_models.add(r.get("model_b", ""))
    all_models.discard("")

    # Elo
    elo_input = [(r.get("model_a","?"), r.get("model_b","?"), r.get("winner","tie")) for r in rows]
    elo_scores = compute_elo(elo_input)

    return {
        "total": total, "wins_a": wins_a, "wins_b": wins_b, "ties": ties,
        "all_models": sorted(all_models),
        "dim_stats": dim_stats, "elo_scores": elo_scores,
    }


def fetch_extra_tables(conn: sqlite3.Connection) -> dict:
    """Fetch seedance_ad and seedream_ecom summary counts."""
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    out = {}
    for t in ("seedance_ad_usecases", "seedream_ecom_usecases", "youtube_videos"):
        if t in tables:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            out[t] = n
    return out


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def rating(pct_a: float, pct_b: float) -> str:
    diff = pct_a - pct_b
    if diff > 5:   return "✅"
    if diff > 0:   return "⚠️"
    if diff > -5:  return "⚠️"
    return "❌"


def build_image_section(data: dict, lang: str, no_examples: bool) -> list:
    lines = []
    is_zh = lang == "zh"
    model_a = data["model_a"]
    model_b = data["model_b"]
    total   = data["total"]
    dim_labels = DIM_LABELS_ZH if is_zh else DIM_LABELS_EN

    h2 = "##"

    if is_zh:
        lines += [f"{h2} 图片评测", ""]
        lines += [f"- **总评测对数**: {total}"]
        lines += [f"- **模型 A**: {model_a}  |  **模型 B**: {model_b}"]
        if len(data["report_ids"]) > 1:
            lines += [f"- **报告来源**: {', '.join(data['report_ids'])}"]
        lines += [""]
    else:
        lines += [f"{h2} Image Evaluation", ""]
        lines += [f"- **Total pairs**: {total}"]
        lines += [f"- **Model A**: {model_a}  |  **Model B**: {model_b}"]
        lines += [""]

    # Win rate overview
    wa, wb, wt = data["wins_a"], data["wins_b"], data["ties"]
    pa, pb, pt = wa/total*100, wb/total*100, wt/total*100
    if is_zh:
        lines += [f"### 胜率总览", ""]
        lines += [f"| 模型 | 胜局 | 负局 | 平局 | 胜率 |",
                  f"|------|:----:|:----:|:----:|:----:|",
                  f"| {model_a} | {wa} | {wb} | {wt} | **{pa:.1f}%** |",
                  f"| {model_b} | {wb} | {wa} | {wt} | **{pb:.1f}%** |", ""]
    else:
        lines += [f"### Win Rate Overview", ""]
        lines += [f"| Model | Wins | Losses | Ties | Win Rate |",
                  f"|-------|:----:|:------:|:----:|:--------:|",
                  f"| {model_a} | {wa} | {wb} | {wt} | **{pa:.1f}%** |",
                  f"| {model_b} | {wb} | {wa} | {wt} | **{pb:.1f}%** |", ""]

    # Elo
    elo = data["elo_scores"]
    if elo:
        sorted_elo = sorted(elo.items(), key=lambda x: x[1], reverse=True)
        if is_zh:
            lines += [f"### Elo 排名", ""]
            lines += ["| 排名 | 模型 | Elo 分数 |",
                      "|:----:|------|:--------:|"]
        else:
            lines += [f"### Elo Rankings", ""]
            lines += ["| Rank | Model | Elo Score |",
                      "|:----:|-------|:---------:|"]
        for i, (m, s) in enumerate(sorted_elo, 1):
            lines.append(f"| {i} | {m} | **{s:.0f}** |")
        lines.append("")

    # Dimension breakdown
    if data["dim_stats"]:
        if is_zh:
            lines += ["### 维度分析", ""]
            lines += [f"| 维度 | {model_a} 胜率 | {model_b} 胜率 | 平局 | 领先方 | 评级 |",
                      f"|------|:-----------:|:-----------:|:----:|--------|:----:|"]
        else:
            lines += ["### Dimension Analysis", ""]
            lines += [f"| Dimension | {model_a} Win% | {model_b} Win% | Tie% | Leader | Rating |",
                      f"|-----------|:------------:|:------------:|:----:|--------|:------:|"]
        for dim, s in sorted(data["dim_stats"].items(), key=lambda x: x[1]["pct_A"] - x[1]["pct_B"], reverse=True):
            label = dim_labels.get(dim, dim)
            leader = model_a if s["pct_A"] > s["pct_B"] else (model_b if s["pct_B"] > s["pct_A"] else ("平局" if is_zh else "Tie"))
            r = rating(s["pct_A"], s["pct_B"])
            lines.append(f"| {label} | {s['pct_A']:.1f}% | {s['pct_B']:.1f}% | {s['pct_tie']:.1f}% | {leader} | {r} |")
        lines.append("")

    # Category breakdown
    if data["cat_stats"] and len(data["cat_stats"]) > 1:
        title = "### 场景分析" if is_zh else "### Scenario Analysis"
        lines += [title, ""]
        hdr = f"| {'场景' if is_zh else 'Scenario'} | {model_a} | {model_b} | {'平局' if is_zh else 'Tie'} | {'领先' if is_zh else 'Leader'} |"
        lines += [hdr, "|---|:---:|:---:|:---:|---|"]
        for cat, s in sorted(data["cat_stats"].items(), key=lambda x: x[1]["A"] + x[1]["B"] + x[1]["tie"], reverse=True):
            n = s["A"] + s["B"] + s["tie"]
            if n == 0:
                continue
            leader = model_a if s["A"] > s["B"] else (model_b if s["B"] > s["A"] else ("—"))
            lines.append(f"| {cat} | {s['A']} ({s['A']/n*100:.0f}%) | {s['B']} ({s['B']/n*100:.0f}%) | {s['tie']} | {leader} |")
        lines.append("")

    # Examples
    if not no_examples and (data["examples_a"] or data["examples_b"]):
        title = "### 典型案例" if is_zh else "### Sample Cases"
        lines += [title, ""]
        if data["examples_a"]:
            hdr = f"**{model_a} 获胜案例:**" if is_zh else f"**{model_a} wins:**"
            lines += [hdr, ""]
            for ex in data["examples_a"]:
                prompt = (ex.get("prompt") or "")[:100]
                reason = (ex.get("reason") or "")[:120]
                lines.append(f"- `{prompt}` — {reason}")
            lines.append("")
        if data["examples_b"]:
            hdr = f"**{model_b} 获胜案例:**" if is_zh else f"**{model_b} wins:**"
            lines += [hdr, ""]
            for ex in data["examples_b"]:
                prompt = (ex.get("prompt") or "")[:100]
                reason = (ex.get("reason") or "")[:120]
                lines.append(f"- `{prompt}` — {reason}")
            lines.append("")

    return lines


def build_video_section(data: dict, lang: str) -> list:
    lines = []
    is_zh = lang == "zh"
    dim_labels = VIDEO_DIM_LABELS_ZH if is_zh else VIDEO_DIM_LABELS_EN
    models = data["all_models"]

    if is_zh:
        lines += ["## 视频评测", ""]
        lines += [f"- **总评测对数**: {data['total']}"]
        lines += [f"- **参与模型**: {', '.join(models)}", ""]
    else:
        lines += ["## Video Evaluation", ""]
        lines += [f"- **Total pairs**: {data['total']}"]
        lines += [f"- **Models**: {', '.join(models)}", ""]

    # Elo
    elo = data["elo_scores"]
    if elo:
        sorted_elo = sorted(elo.items(), key=lambda x: x[1], reverse=True)
        if is_zh:
            lines += ["### Elo 排名", ""]
            lines += ["| 排名 | 模型 | Elo 分数 |", "|:----:|------|:--------:|"]
        else:
            lines += ["### Elo Rankings", ""]
            lines += ["| Rank | Model | Elo Score |", "|:----:|-------|:---------:|"]
        for i, (m, s) in enumerate(sorted_elo, 1):
            lines.append(f"| {i} | {m} | **{s:.0f}** |")
        lines.append("")

    # Dimension scores
    if data["dim_stats"]:
        if is_zh:
            lines += ["### 维度平均分", ""]
            lines += ["| 维度 | 模型 A 均分 | 模型 B 均分 | 领先方 |", "|------|:---------:|:---------:|--------|"]
        else:
            lines += ["### Dimension Scores", ""]
            lines += ["| Dimension | Model A Avg | Model B Avg | Leader |", "|-----------|:-----------:|:-----------:|--------|"]
        for dim, s in data["dim_stats"].items():
            label = dim_labels.get(dim, dim)
            leader = "A" if s["leader"] == "A" else ("B" if s["leader"] == "B" else ("平局" if is_zh else "Tie"))
            lines.append(f"| {label} | {s['avg_a']} | {s['avg_b']} | {leader} |")
        lines.append("")

    return lines


def build_conclusions(image_data: dict, video_data: dict, extra: dict, lang: str) -> list:
    is_zh = lang == "zh"
    lines = []
    title = "## 结论与建议" if is_zh else "## Conclusions & Recommendations"
    lines += [title, ""]

    if image_data:
        wa, wb = image_data["wins_a"], image_data["wins_b"]
        ma, mb = image_data["model_a"], image_data["model_b"]
        winner = ma if wa > wb else (mb if wb > wa else None)
        if is_zh:
            if winner:
                lines.append(f"- **图片生成**: {winner} 在综合胜率上领先（{max(wa,wb)}/{image_data['total']} = {max(wa,wb)/image_data['total']*100:.1f}%）")
            # Strong dims for A
            strong_a = [d for d, s in image_data["dim_stats"].items() if s["pct_A"] - s["pct_B"] > 3]
            strong_b = [d for d, s in image_data["dim_stats"].items() if s["pct_B"] - s["pct_A"] > 3]
            if strong_a:
                labels = [DIM_LABELS_ZH.get(d, d) for d in strong_a]
                lines.append(f"- {ma} 在以下维度领先：{', '.join(labels)}")
            if strong_b:
                labels = [DIM_LABELS_ZH.get(d, d) for d in strong_b]
                lines.append(f"- {mb} 在以下维度领先：{', '.join(labels)}")
        else:
            if winner:
                lines.append(f"- **Image generation**: {winner} leads in overall win rate ({max(wa,wb)}/{image_data['total']} = {max(wa,wb)/image_data['total']*100:.1f}%)")
            strong_a = [d for d, s in image_data["dim_stats"].items() if s["pct_A"] - s["pct_B"] > 3]
            strong_b = [d for d, s in image_data["dim_stats"].items() if s["pct_B"] - s["pct_A"] > 3]
            if strong_a:
                labels = [DIM_LABELS_EN.get(d, d) for d in strong_a]
                lines.append(f"- {ma} leads in: {', '.join(labels)}")
            if strong_b:
                labels = [DIM_LABELS_EN.get(d, d) for d in strong_b]
                lines.append(f"- {mb} leads in: {', '.join(labels)}")

    if video_data:
        sorted_elo = sorted(video_data["elo_scores"].items(), key=lambda x: x[1], reverse=True)
        top = sorted_elo[0][0] if sorted_elo else "?"
        if is_zh:
            lines.append(f"- **视频生成**: {top} 获得最高 Elo 评分")
        else:
            lines.append(f"- **Video generation**: {top} achieves highest Elo score")

    if extra:
        for t, n in extra.items():
            if is_zh:
                lines.append(f"- **{t}**: {n} 条用例数据已入库")
            else:
                lines.append(f"- **{t}**: {n} use case records available")

    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def generate_report(args) -> str:
    db_path = find_db()
    conn = get_conn(db_path)

    is_zh = args.lang == "zh"
    date  = datetime.datetime.now().strftime("%Y-%m-%d")
    lines = []

    # Title
    title_parts = []
    if args.report_id:
        title_parts.append(args.report_id)
    if args.model:
        title_parts.append(args.model)
    scope = " · ".join(title_parts) if title_parts else ("全量数据" if is_zh else "All Data")

    if is_zh:
        lines += [f"# 模型评测报告 — {scope}", ""]
        lines += [f"> 生成日期: {date}  "]
        lines += [f"> 数据库: `{db_path}`  ", ""]
    else:
        lines += [f"# Model Evaluation Report — {scope}", ""]
        lines += [f"> Generated: {date}  "]
        lines += [f"> Database: `{db_path}`  ", ""]

    # Elo-only mode
    if args.type == "elo":
        image_data = fetch_image_data(conn, args.report_id, args.model)
        video_data = fetch_video_data(conn, args.model)
        if image_data and image_data.get("elo_scores"):
            if is_zh:
                lines += ["## 图片模型 Elo 排名", ""]
                lines += ["| 排名 | 模型 | Elo 分数 |", "|:----:|------|:--------:|"]
            else:
                lines += ["## Image Model Elo Rankings", ""]
                lines += ["| Rank | Model | Elo Score |", "|:----:|-------|:---------:|"]
            for i, (m, s) in enumerate(sorted(image_data["elo_scores"].items(), key=lambda x: x[1], reverse=True)[:args.top_n], 1):
                lines.append(f"| {i} | {m} | **{s:.0f}** |")
            lines.append("")
        if video_data and video_data.get("elo_scores"):
            if is_zh:
                lines += ["## 视频模型 Elo 排名", ""]
                lines += ["| 排名 | 模型 | Elo 分数 |", "|:----:|------|:--------:|"]
            else:
                lines += ["## Video Model Elo Rankings", ""]
                lines += ["| Rank | Model | Elo Score |", "|:----:|-------|:---------:|"]
            for i, (m, s) in enumerate(sorted(video_data["elo_scores"].items(), key=lambda x: x[1], reverse=True)[:args.top_n], 1):
                lines.append(f"| {i} | {m} | **{s:.0f}** |")
            lines.append("")
        return "\n".join(lines)

    # Full / image / video reports
    image_data = {}
    video_data = {}
    extra = {}

    if args.type in ("full", "image"):
        image_data = fetch_image_data(conn, args.report_id, args.model)
        if image_data:
            lines += build_image_section(image_data, args.lang, args.no_examples)
            lines += ["---", ""]

    if args.type in ("full", "video"):
        video_data = fetch_video_data(conn, args.model)
        if video_data:
            lines += build_video_section(video_data, args.lang)
            lines += ["---", ""]

    if args.type == "full":
        extra = fetch_extra_tables(conn)

    if not image_data and not video_data:
        msg = "未找到数据。请先使用 polym-eval-db import 工具导入数据。" if is_zh else \
              "No data found. Please import data first using polym-eval-db import tools."
        lines.append(msg)
    else:
        lines += build_conclusions(image_data, video_data, extra, args.lang)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate eval report from polym-eval-db SQLite")
    parser.add_argument("--type", default="full",
                        choices=["full", "image", "video", "elo"],
                        help="Report type (default: full)")
    parser.add_argument("--report-id", default="",
                        help="Filter to a specific report ID")
    parser.add_argument("--model", default="",
                        help="Filter by model name (partial match)")
    parser.add_argument("--lang", default="zh", choices=["zh", "en"],
                        help="Report language (default: zh)")
    parser.add_argument("--top-n", type=int, default=10,
                        help="Max models in Elo table (default: 10)")
    parser.add_argument("--output", default="",
                        help="Save to file (default: print to stdout)")
    parser.add_argument("--no-examples", action="store_true",
                        help="Skip example rows section")

    args = parser.parse_args()
    report = generate_report(args)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report saved to: {out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
