---
name: polym-eval-run-evaluation
description: >
  Run model generation, pairwise Gemini scoring, and eval-db persistence. Use for
  new image/video benchmarks, GSB runs, and model comparisons.
---

# Run Evaluation

Orchestrate the full evaluation pipeline:
**Generate → Score → Save to polym-eval-db**

## Quick Usage

```
用 Seedream 和 Gemini 生成这张图并评测：<prompt>
对比 Seedance 和 Sora 在以下提示词上的表现：<prompt>
运行一次完整评测，prompt: "..."，模型A: Seedream，模型B: Gemini
```

## Pipeline Overview

```
[User prompt]
     │
     ├─► polym-eval-generate-seedream / polym-eval-generate-gemini / polym-eval-generate-seedance / ...
     │        (produces image_a_url / video_a_url)
     │
     ├─► generate-[model_b]
     │        (produces image_b_url / video_b_url)
     │
     ├─► polym-eval-score-image-gemini (pairwise) / polym-eval-score-video-gemini (pairwise)
     │        (produces winner + dimensions + reason)
     │
     └─► polym-eval-db: save_evaluation_result
              (persists to SQLite for future querying)
```

---

## Agent Instructions

When the user asks to run an evaluation or compare models, follow these steps:

### Step 1 — Optimize Prompt (optional but recommended)
If the user's prompt is vague, use the `polym-eval-prompt-optimizer` skill to improve it first.

### Step 2 — Generate with Model A
Call the appropriate generation skill:
- Image: `polym-eval-generate-seedream` or `polym-eval-generate-gemini`
- Video: `polym-eval-generate-seedance`, `polym-eval-generate-sora`, or `polym-eval-generate-veo`

Record the output URL as `image_a_url` or `video_a_url`.

### Step 3 — Generate with Model B
Same as Step 2 for the second model. Record as `image_b_url` or `video_b_url`.

### Step 4 — Score Pairwise
- Images: use `polym-eval-score-image-gemini` in **pairwise** mode
  - Pass `image_a_url`, `image_b_url`, and `prompt`
  - Returns: `winner` (A/B/tie), `dimensions` dict, `reason`
- Videos: use `polym-eval-score-video-gemini` in **pairwise** mode
  - Pass `video_a_url`, `video_b_url`, and `prompt`
  - Returns: `winner`, `dimensions` dict

### Step 5 — Save to polym-eval-db
Call the local save script with the same fields:
```json
{
  "report_id": "<model_a>_vs_<model_b>_<YYYYMMDD>",
  "report_title": "<model_a> vs <model_b> — <date>",
  "model_a": "<model_a_name>",
  "model_b": "<model_b_name>",
  "prompt": "<the prompt used>",
  "winner": "A|B|tie",
  "image_a_url": "<url>",
  "image_b_url": "<url>",
  "dimensions": {
    "prompt_fidelity": "A|B|tie",
    "structure": "A|B|tie",
    "texture": "A|B|tie",
    "lighting": "A|B|tie",
    "artifacts": "A|B|tie",
    "usefulness": "A|B|tie"
  },
  "reason": "<scoring rationale>",
  "category": "<optional tag>",
  "scenario": "<optional tag>"
}
```

Example:

```bash
python3 skills/polym-eval-run-evaluation/scripts/save_to_db.py \
  --report-id seedream_vs_gemini_20260414 \
  --model-a "Seedream 5.0" \
  --model-b "Gemini 3.1 Flash" \
  --prompt "A pair of white sneakers..." \
  --winner A \
  --image-a "https://..." \
  --image-b "https://..." \
  --dimensions '{"prompt_fidelity":"A","structure":"A"}' \
  --reason "Seedream preserves more product detail"
```

### Step 6 — Report Results
Show the user:
- Which model won and by how much
- Per-dimension breakdown table
- The generated images/videos (as links or attachments)
- Confirmation that results were saved (report_id, total rows)

---

## Example Workflow

**User:** 用 Seedream 和 Gemini 对比这个电商场景：一双白色运动鞋，白色背景，专业产品摄影

**Agent steps:**
1. (Optional) Optimize prompt via `polym-eval-prompt-optimizer --model seedream --scenario ecommerce`
2. Generate with Seedream → `image_a_url = "https://...seedream_result.png"`
3. Generate with Gemini → `image_b_url = "https://...gemini_result.png"`
4. Score pairwise with `polym-eval-score-image-gemini`
5. Save via `scripts/save_to_db.py`:
   ```json
   {
     "report_id": "seedream_vs_gemini_20260414",
     "model_a": "Seedream 5.0",
     "model_b": "Gemini 3.1 Flash",
     "prompt": "A pair of white sneakers...",
     "winner": "A",
     "dimensions": {"prompt_fidelity": "A", "structure": "A", "texture": "tie", ...}
   }
   ```
6. Show summary table + image links

---

## Batch Evaluation

For multiple prompts, repeat Steps 2-5 for each prompt under the same `report_id`.
After all prompts, run `query_elo` to see aggregate Elo rankings.

```
批量评测 5 个电商提示词，模型：Seedream vs Gemini
```

---

## Standalone Script

```bash
# Save a single result from command line
python3 skills/polym-eval-run-evaluation/scripts/save_to_db.py \
  --report-id seedream_vs_gemini_20260414 \
  --model-a "Seedream 5.0" \
  --model-b "Gemini 3.1 Flash" \
  --prompt "A pair of white sneakers on white background" \
  --winner A \
  --image-a https://... \
  --image-b https://... \
  --dimensions '{"prompt_fidelity":"A","structure":"A","texture":"tie"}' \
  --reason "Seedream shows better product detail and lighting"
```
