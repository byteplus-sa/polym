---
name: polym-eval-report-generator
description: >
  Generate Markdown reports from polym-eval-db. Use for eval summaries, model
  comparison reports, Elo reports, and exported evaluation findings.
---

# Report Generator

Generate structured evaluation reports from polym-eval-db data.

## Quick Usage

```
生成 Seedream vs Gemini 的评测报告
给我一份视频模型的 Elo 排名报告
生成所有图片评测的综合报告，中文，保存到 report.md
generate a full report for report ID: seedream_vs_gemini_20260414
```

## Report Types

| Type | Flag | Content |
|------|------|---------|
| **image** | `--type image` | Image comparisons: Elo, win-rate, dimensions, examples |
| **video** | `--type video` | Video comparisons: Elo, multi-model rankings |
| **full** | `--type full` | All data sources combined |
| **elo-only** | `--type elo` | Elo rankings table only (quick view) |

---

## Agent Instructions

When the user asks for a report:

1. **Determine scope**: which report_id(s), model(s), or "all"
2. **Run the generator script** with appropriate flags
3. **Display the report content** inline in chat (Markdown renders well)
4. **Optionally save** to a file if user requests

---

## Standalone CLI Usage

```bash
# Full image + video report (all data), Chinese
python3 skills/polym-eval-report-generator/scripts/generate_report.py

# Image report only
python3 skills/polym-eval-report-generator/scripts/generate_report.py --type image

# Video report only
python3 skills/polym-eval-report-generator/scripts/generate_report.py --type video

# Filter by specific report ID
python3 skills/polym-eval-report-generator/scripts/generate_report.py \
  --report-id seedream_vs_gemini_20260414

# Filter by model name (partial match)
python3 skills/polym-eval-report-generator/scripts/generate_report.py \
  --model Seedream

# English report
python3 skills/polym-eval-report-generator/scripts/generate_report.py --lang en

# Save to file
python3 skills/polym-eval-report-generator/scripts/generate_report.py \
  --output benchmark/image/reports/my_report.md

# Elo only, top 5 models
python3 skills/polym-eval-report-generator/scripts/generate_report.py \
  --type elo --top-n 5

# Custom DB path
EVAL_DB_PATH=/root/eval.db python3 skills/polym-eval-report-generator/scripts/generate_report.py
```

## Parameters

| Parameter | Flag | Default | Description |
|-----------|------|---------|-------------|
| `type` | `--type` | `full` | `image`, `video`, `full`, `elo` |
| `report_id` | `--report-id` | all | Filter to one report |
| `model` | `--model` | all | Filter by model name (partial) |
| `lang` | `--lang` | `zh` | `zh` (Chinese) or `en` (English) |
| `top_n` | `--top-n` | 10 | Max models in Elo table |
| `output` | `--output` | stdout | Save to file path |
| `no_examples` | `--no-examples` | False | Skip example rows section |

## Report Structure

```
# [Model A] vs [Model B] 评测报告

## 概览
- 数据规模 / 报告来源 / 评测日期

## Elo 排名
(table of models ranked by Elo score, with per-dimension scores)

## 胜率统计
(overall win/loss/tie counts and percentages)

## 维度分析
(per-dimension breakdown table with win rates and leading model)

## 场景分析
(grouped by category/scenario if available)

## 典型案例
(sample comparisons — A wins, B wins, tie)

## 结论与建议
(auto-generated summary based on the data)
```

## Environment Variables

```bash
EVAL_DB_PATH=...   # Path to SQLite DB (default: skills/polym-eval-db/eval.db, auto-downloaded if missing)
```
