---
name: "polym-sdr-leads-qualification"
description: "Score and qualify Trigify leads using LLM-powered evidence extraction and deterministic routing. Supports Anthropic, OpenAI, Gemini, BytePlus Ark, and any LiteLLM-compatible provider."
---

# SDR Leads Qualification

Score Trigify lead exports with a single LLM call per lead: evidence extraction, sub-score assignment, and deterministic Python routing into qualified / review / disqualified queues.

**Runbook:** `docs/RUNBOOK.md` · **Examples:** `docs/EXAMPLES.md`

---

## Invocation Protocol

When this skill is triggered, follow the steps below in order. Do not skip steps.

### Step 1 — Locate the skill directory

The skill lives at `~/.claude/skills/polym-sdr-leads-qualification/` when installed, or at the repo path if running from source. Resolve the correct path before proceeding.

```bash
SKILL_DIR=~/.claude/skills/polym-sdr-leads-qualification
# fallback for repo-local runs:
# SKILL_DIR=<repo-root>/skills/polym-sdr-leads-qualification
```

### Step 2 — Ask for the CSV file

If the user has not already provided a CSV path, ask:

> "What is the path to your Trigify CSV file?"

### Step 3 — Campaign selection

List available campaigns by scanning `$SKILL_DIR/campaigns/` for subdirectories that contain a `config.json` file (this naturally excludes `common/` and any other utility directories). Then ask the user:

> "Which campaign should I use to score these leads?
>
> Available campaigns:
> 1. **seedance** — ByteDance Seedance AI video (default)
> 2. **kling** — Kuaishou Kling AI video
> [… any other detected campaign folders …]
> 3. **Create a new campaign**
>
> Press Enter to use seedance, or type a number / campaign name."

- If the user picks an existing campaign → skip to **Step 5**.
- If the user picks "Create a new campaign" → proceed to **Step 4**.

### Step 4 — New campaign creation

#### 4a. Gather minimal inputs

Ask the user these questions (can be in one message):

```
1. Product name  (e.g. "Runway", "Adobe Firefly", "HeyGen")
2. One-line tagline  (e.g. "AI video creation for creative teams")
3. What does the product do?  (2–4 sentences — key capabilities, differentiators)
4. Target customer types  (which industries / company types are ideal buyers?)
5. Target buyer personas  (job titles most likely to buy — list them)
6. What pain does the product solve?  (speed, cost, scale, quality — be specific)
7. Hard disqualifiers  (industries or roles that should NEVER qualify)
8. Campaign ID (slug, lowercase, no spaces — e.g. "runway", "heygen")
   Leave blank to auto-generate from product name.
```

Tell the user: _"You don't need to be exhaustive — I'll fill in the details using the Seedance campaign as a structural template."_

#### 4b. Generate campaign files

Using the user's answers plus the seedance campaign files as structural references, generate all six files. Write them to `$SKILL_DIR/campaigns/<campaign-id>/`.

**`config.json`**
```json
{
    "name": "<Product Name>",
    "tagline": "<tagline>",
    "score_weights": {
        "segment_fit": 20,
        "buyer_fit": 20,
        "pain_fit": 25,
        "workflow_fit": 20,
        "commercial_fit": 15
    },
    "qualified_threshold": 70,
    "disqualified_threshold": 60
}
```

**`product.md`** — Describe the product: key capabilities, differentiators, primary use cases by segment. Model the structure on `campaigns/seedance/product.md`.

**`icp.md`** — Define the ICP: primary target verticals (table with segment ID, description, why-fit), target personas (Tier 1 decision makers, Tier 2 influencers, Tier 3 low priority), anti-ICP list, segment → use case mapping. Model on `campaigns/seedance/icp.md`. Derive segment IDs and verticals from the user's stated target customer types — adapt, do not copy Seedance segments verbatim.

**`signals.md`** — Define what constitutes a high-intent, medium-intent signal for this product. A POST about the product's problem space = high intent. A LIKE = low signal. List product-specific buying signals. Model on `campaigns/seedance/signals.md`.

**`qualification.md`** — Full 100-point scoring rubric using the same five sub-scores (segment_fit 20, buyer_fit 20, pain_fit 25, workflow_fit 20, commercial_fit 15). Adapt score bands to match the product's ICP. Model on `campaigns/seedance/qualification.md`.

**`disqualification.md`** — Hard disqualifiers: wrong industry, junior roles, irrelevant functions, confirmed competitors. Pull from the user's stated hard disqualifiers plus infer obvious ones from the product description. Model on `campaigns/seedance/disqualification.md`. Follow the same IMPORTANT rule: only confirmed negatives belong in `hard_disqualifiers`; uncertain cases go in `unknowns`.

#### 4c. Show a confirmation summary

After generating the files, show the user a structured summary:

```
Campaign: <id>
Product: <name> — <tagline>

Target segments: <list the top 4-5 segment IDs>
Tier 1 buyers: <list top 3-4 job titles>
Hard disqualifiers: <list top 3-4>
Scoring thresholds: qualified ≥ 70 | review 60–69 | disqualified < 60

Files written:
  campaigns/<id>/config.json
  campaigns/<id>/product.md
  campaigns/<id>/icp.md
  campaigns/<id>/signals.md
  campaigns/<id>/qualification.md
  campaigns/<id>/disqualification.md
```

Then ask:

> "Does this look right? Type **yes** to score the leads with this campaign, **edit** to change anything, or **cancel** to stop."

- If "yes" → proceed to Step 5 with `--campaign <id>`.
- If "edit" → ask which file or field to change, apply the edit, re-show the summary.
- If "cancel" → stop.

### Step 5 — Confirm env vars

Check that `LLM_API_KEY` and `LLM_MODEL` are set. If not, prompt:

> "Please set LLM_API_KEY and LLM_MODEL (and optionally LLM_PROVIDER / LLM_API_BASE) before scoring."

### Step 6 — Run the scorer

```bash
python3 $SKILL_DIR/scripts/score_csv.py \
  --input <csv_path> \
  --output-dir ./output \
  --campaign <campaign_id>
```

Add `--limit N` if the user asked to process only a subset. Add `--disable-web-enrichment` if they asked to skip website fetches.

After the run, report:
- Total leads processed
- Qualified / Review / Disqualified counts from `output/summary.json`
- Path to output directory

---

## Pre-flight Check

Set in `.env` or as environment variables:

| Variable | Required | Example |
|---|---|---|
| `LLM_API_KEY` | Yes | `sk-ant-...` / `sk-...` / `AIza...` |
| `LLM_MODEL` | Yes | `claude-sonnet-4-6`, `gpt-4o`, `gemini-2.0-flash`, `ep-xxxx` |
| `LLM_PROVIDER` | No | `anthropic`, `openai`, `gemini` — auto-detected if omitted |
| `LLM_API_BASE` | No | BytePlus Ark URL or any custom endpoint |

## Quick Start (manual CLI)

```bash
# Anthropic
LLM_API_KEY=sk-ant-... LLM_MODEL=claude-sonnet-4-6 LLM_PROVIDER=anthropic \
python3 ~/.claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input leads.csv --output-dir ./output --campaign seedance

# BytePlus Ark
LLM_API_KEY=<ark-key> LLM_MODEL=ep-xxxx LLM_PROVIDER=openai \
LLM_API_BASE=https://ark.ap-southeast.bytepluses.com/api/v3 \
python3 ~/.claude/skills/polym-sdr-leads-qualification/scripts/score_csv.py \
  --input leads.csv --output-dir ./output --campaign seedance
```

## Parameter Reference

| Flag | Description | Default |
|---|---|---|
| `--input` | Path to Trigify CSV | **Required** |
| `--output-dir` | Output directory | **Required** |
| `--campaign` | Campaign pack: `seedance`, `kling`, or any custom id | `seedance` |
| `--limit N` | Process only first N rows | all |
| `--disable-web-enrichment` | Skip website fetch per lead | off |
| `--sleep-ms N` | Pause between leads (rate limit control) | 0 |
| `--provider` | Override `LLM_PROVIDER` | env |
| `--api-base` | Override `LLM_API_BASE` | env |
| `--model` | Override `LLM_MODEL` | env |
| `--api-key` | Override `LLM_API_KEY` | env |

## Output Files

```
output/
  all_scored_leads.csv
  qualified_leads.csv
  review_leads.csv
  disqualified_leads.csv
  summary.json
  artifacts/{lead_id}_input.json
  artifacts/{lead_id}_enrichment.json
  artifacts/{lead_id}_evidence.json
  artifacts/{lead_id}_decision.json
```

## Available Campaigns

| Campaign | Product | Qualified ≥ | Review band |
|---|---|---|---|
| `seedance` | ByteDance Seedance (AI video) | 70 | 60–69 |
| `kling` | Kuaishou Kling (AI video) | 70 | 60–69 |

Custom campaigns created via the interactive flow are stored in `campaigns/<id>/` and are immediately available via `--campaign <id>`.

## Scoring Logic

Each lead goes through: normalize → parallel web enrichment → single LLM call (evidence + 5 sub-scores) → Python clamping + routing. Hard disqualifiers and `signal_strength=low` override the score regardless of total. See `docs/RUNBOOK.md` for the full decision protocol.

## When To Invoke

- Process or inspect a Trigify lead export
- Score a single company or person for campaign fit
- Explain why a lead was routed to review or disqualified
- Work with or extend campaign prompts under `campaigns/`
- Create a new campaign for a product not yet in the library
- Prepare outreach output from scored leads
