---
name: polym-eval-db
description: >
  SQLite eval database for image/video model comparisons. Use to import results,
  query win rates, dimensions, examples, and Elo rankings.
---

# Image & Video Eval DB

Persistent SQLite store for pairwise image generation evaluation results.
Covers two concerns:

- **Image data layer** — import HTML reports, query stats & examples (`query.py`)
- **Video data layer** — import from MySQL gsb_video, query stats (`query_video.py`)
- **Computation layer** — Elo ranking calculation with caching (both query scripts)

## Pre-flight Check

No API keys required. Python standard library only.

Default DB path: `skills/polym-eval-db/eval.db`
If the default DB is missing, query/reporting tools download it from `https://carey.tos-ap-southeast-1.bytepluses.com/xieyongliang/eval/eval.db` and use that local copy.
Override: set env var `EVAL_DB_PATH`

---

## Step 1a — Import Image Report (HTML)

```bash
python skills/polym-eval-db/scripts/import_report.py \
  https://carey.tos-ap-southeast-1.bytepluses.com/image-reports/20260322_134321_d8e98043.html
```

## Step 1b — Import Video Data (MySQL → SQLite)

```bash
# From a URL (any HTML eval report)
python skills/polym-eval-db/scripts/import_report.py \
  https://example.com/report.html

# Custom DB path
python skills/polym-eval-db/scripts/import_report.py \
  https://example.com/report.html --db /path/to/eval.db
```

Multiple reports can be imported; they land in the same DB and can be queried individually or combined.

```bash
# Import from MySQL (uses DB_HOST/DB_USER/DB_PASSWORD env vars or defaults)
python skills/polym-eval-db/scripts/import_mysql.py

# Custom MySQL connection
python skills/polym-eval-db/scripts/import_mysql.py \
  --mysql-host 127.0.0.1 --mysql-user root --mysql-password secret \
  --mysql-database usecase --table gsb_video
```

---

## Step 2a — Query Images (CLI)

```bash
python skills/polym-eval-db/scripts/query.py list
python skills/polym-eval-db/scripts/query.py stats
python skills/polym-eval-db/scripts/query.py stats --group-by category
python skills/polym-eval-db/scripts/query.py dims
python skills/polym-eval-db/scripts/query.py elo
python skills/polym-eval-db/scripts/query.py elo --dimension prompt_fidelity
python skills/polym-eval-db/scripts/query.py examples --winner A --limit 5
```

## Step 2b — Query Videos (CLI)

```bash
# List all video model pairs
python skills/polym-eval-db/scripts/query_video.py list

# Win/loss/tie stats per pair
python skills/polym-eval-db/scripts/query_video.py stats

# Per-dimension breakdown
python skills/polym-eval-db/scripts/query_video.py dims

# Multi-model Elo rankings
python skills/polym-eval-db/scripts/query_video.py elo
python skills/polym-eval-db/scripts/query_video.py elo --dimension instruction_following

# Search examples
python skills/polym-eval-db/scripts/query_video.py examples --winner B --limit 5
python skills/polym-eval-db/scripts/query_video.py examples \
  --comparison "seedance-1.0-pro vs veo-3.1" --winner A
```

---

## Image Query Reference

```bash
# List all imported reports
python skills/polym-eval-db/scripts/query.py list

# Overall win/loss/tie stats
python skills/polym-eval-db/scripts/query.py stats

# Stats for a specific report
python skills/polym-eval-db/scripts/query.py stats --report 20260322_134321_d8e98043

# Stats grouped by category / scenario / industry
python skills/polym-eval-db/scripts/query.py stats --group-by category
python skills/polym-eval-db/scripts/query.py stats --group-by scenario

# Per-dimension win-rate breakdown
python skills/polym-eval-db/scripts/query.py dims

# Elo rankings — overall
python skills/polym-eval-db/scripts/query.py elo

# Elo rankings — specific dimension
python skills/polym-eval-db/scripts/query.py elo --dimension prompt_fidelity

# Force recompute (ignore cache)
python skills/polym-eval-db/scripts/query.py elo --recompute

# Show 5 examples where Model A won
python skills/polym-eval-db/scripts/query.py examples --winner A --limit 5

# Search by category or scenario
python skills/polym-eval-db/scripts/query.py examples --category 模特 --winner B
python skills/polym-eval-db/scripts/query.py examples --scenario 电商 --limit 10
```

---

## Step 3 — Agent CLI Usage

Agents can use the CLI commands directly, for example:
```bash
python skills/polym-eval-db/scripts/query.py stats
python skills/polym-eval-db/scripts/query_video.py elo
```

The agent can answer questions like:
- "Seedream vs Gemini 的 Elo 排名是多少？"
- "在模特场景下哪个模型赢得更多？"
- "给我看几个 prompt_fidelity 维度 B 赢了的例子"
- "按 category 分组统计胜率"

---

## Evaluation Dimensions

| Key | Description |
|-----|-------------|
| `prompt_fidelity` | How well the image follows the prompt |
| `structure` | Structural accuracy and composition |
| `texture` | Material and texture quality |
| `lighting` | Lighting realism and consistency |
| `artifacts` | Absence of visual artifacts |
| `usefulness` | Practical usability of the output |
| `factual_consistency` | Factual correctness of depicted elements |
| `text_rendering` | Quality of text rendered in the image |
| `edit_consistency` | Consistency with reference/editing intent |

Each dimension: **A** (model_a wins) · **B** (model_b wins) · **tie**

---

## Adding Future Reports

Each new evaluation HTML report maps to a new `report_id` in the DB.
Re-run `import_report.py` with any new URL — existing rows are never overwritten.
Elo cache is automatically scoped per report set and invalidated when new
reports are added.
