---
name: polym-eval-seedream-aigc-gtm
description: |
  GTM positioning, competitive analysis, strengths/gaps for Seedream image generation model family
  (Seedream 4.0, 4.5, 5.0 Lite) vs competitors (Gemini 3.1 Flash, Nano Banana (Gemini 2.5 Flash Image), Nano Banana Pro (Gemini 3.0 Image)).
  Covers e-commerce, virtual try-on, design/marketing, and creator use cases.
  TRIGGER when: user asks about Seedream GTM positioning, competitive analysis, image generation
  strengths, gaps, what to highlight, what to de-prioritize, pricing comparison, e-commerce image
  quality, or customer-facing messaging for Seedream.
  Also trigger on: "Seedream GTM", "Seedream 竞品", "Seedream 对比", "Seedream 优势", "Seedream 差距",
  "图片生成定位", "AIGC GTM", "Seedream e-commerce", "Seedream 电商", "Nano Banana 对比",
  "Gemini 图片对比", "Seedream 推介", "Seedream talking points".
  DO NOT TRIGGER for: Seedream API usage / image generation commands (use polym-eval-generate-seedream skill),
  Seedance video generation (use seedance-doc skill), or Seed LLM models (use polym-eval-seed-llm-gtm skill).
---

# Seedream AIGC GTM Analyst

You are a GTM analyst for ByteDance's Seedream image generation model family. You have access to
curated evaluation data and positioning conclusions for Seedream 4.0, 4.5, and 5.0 Lite vs
global competitors.

## Data Sources

| Source | Description | Access |
|--------|-------------|--------|
| Seedream vs Gemini 3.1 Flash eval | E-commerce image generation pairwise comparison (207 pairs) | `python skills/polym-eval-db/scripts/query.py stats` |
| Seedream vs Nano Banana (Gemini 2.5 Flash Image) comparison | Internal agile eval across all dimensions | `lark-cli docs +fetch --doc BTikw88A0i6XLAk0SIYcT6HqnIh` |
| Seedream 5.0 e-commerce sectors | GSB ratings across 5 sectors, 29 use cases | `lark-cli docs +fetch --doc N6dcwcXaqie1Y9kOQMuc7mKGnOd` |
| Seedream 4.5 PDP production test | Before/after 4.0→4.5 improvement analysis | `lark-cli docs +fetch --doc UilqwozQki2kVgkkPPhcAiWqnFb` |
| Seedream 5.0 Lite bad-case breakdown | Known issues & failure modes | `lark-cli docs +fetch --doc UW2HwGEECiJbdTkD3YBcLWVTntf` |
| Seedream 4.5 & 5.0L vs Nano Banana 2 (Gemini 3.1 Flash Image Preview) | Pricing & model matrix comparison | `lark-cli docs +fetch --doc TvOkwDUnTi8lrbkSmIgcrtVznPh` |
| HTML eval report (Seedream 5.0L vs Gemini) | Detailed pairwise with dimension scores | polym-eval-db report `20260322_134321_d8e98043` |

To refresh polym-eval-db data:
```bash
python skills/polym-eval-db/scripts/query.py list
python skills/polym-eval-db/scripts/query.py stats
python skills/polym-eval-db/scripts/query.py dims
python skills/polym-eval-db/scripts/query.py elo
```

---

## Model Family Overview

| | Seedream 5.0 Lite | Seedream 4.5 | Seedream 4.0 |
|---|---|---|---|
| Positioning | Latest, best overall | Creativity-first, aesthetic | Legacy baseline |
| Price | **$0.035/image** | $0.04/image | $0.03/image |
| 4K support | No (known limitation) | Yes | Yes |
| Best for | E-commerce, try-on, design | Creative, editing, fashion | Budget bulk generation |

**Competitor pricing (Nano Banana 2 (Gemini 3.1 Flash Image Preview)):**

| Resolution | Nano Banana 2 (Gemini 3.1 Flash Image Preview) | vs Seedream 4.5 | vs Seedream 5.0 Lite |
|---|---|---|---|
| 2K | $0.101/image | 2.5x more expensive | 2.9x more expensive |
| 4K | $0.151/image | 3.8x more expensive | 4.3x more expensive |

**Key pricing takeaway:** Seedream is only 23-40% of Nano Banana 2 (Gemini 3.1 Flash Image Preview)'s cost.

---

## Competitive Landscape

### Seedream 5.0 Lite vs Gemini 3.1 Flash (E-commerce, n=207)

**Overall: Gemini leads by ~15pp**

| Outcome | Count | Percentage |
|---|---|---|
| Seedream wins | 57 | 27.5% |
| Gemini wins | 88 | 42.5% |
| Tie | 62 | 30.0% |

**Elo: Gemini 1582.6 vs Seedream 1417.4 (gap: 165.2 pts)**

**Per-dimension breakdown:**

| Dimension | Seedream Wins | Gemini Wins | Tie | Gap | Verdict |
|---|---|---|---|---|---|
| Prompt Fidelity | 23.2% | 36.2% | 40.6% | -13.0pp | Gemini leads |
| Usefulness | 20.8% | 37.2% | 42.0% | -16.4pp | **Gemini leads (biggest gap)** |
| Edit Consistency | 14.0% | 19.8% | 66.2% | -5.8pp | Gemini leads |
| Text Rendering | 2.4% | 7.7% | 89.9% | -5.3pp | Gemini leads |
| Texture Quality | 6.3% | 10.1% | 83.6% | -3.8pp | Gemini leads |
| Lighting | 7.7% | 10.6% | 81.6% | -2.9pp | Gemini leads |
| Factual Consistency | 0.0% | 1.4% | 98.6% | -1.4pp | Near parity |
| Composition/Structure | 2.9% | 2.4% | 94.7% | **+0.5pp** | **Seedream leads** |
| Artifact Control | 5.3% | 3.4% | 91.3% | **+1.9pp** | **Seedream leads** |

**Takeaway:** Gemini dominates on usefulness and prompt fidelity. Seedream's only edges are in
artifact control and composition — both marginal and in high-tie dimensions.

### Seedream 4.5 vs Nano Banana Family (Internal Agile Eval)

**Elo ranking across all dimensions:**

| Dimension | Nano Banana Pro (Gemini 3.0 Image) | Seedream 4.5 | Seedream 4.0 | Nano Banana (Gemini 2.5 Flash Image) |
|---|---|---|---|---|
| Text-to-Image Expert Elo | **1st** | 2nd | 3rd | 4th |
| Image-Text Matching | **1st** | 2nd | 3rd | 4th |
| Content Accuracy | **1st** | 2nd | 3rd | 4th |
| Structure Accuracy (T2I) | **1st** | 2nd | 3rd | 3rd |
| Aesthetics | **1st** | 2nd | 3rd | 4th |
| Single-Image Input Elo | **1st** | 2nd | 4th | 3rd |
| Instruction Compliance | **1st** | 2nd | 4th | 3rd |
| Consistency | **1st** | **3rd** | 4th | 2nd |
| Structure Accuracy (Single) | **1st** | **3rd** | 4th | 2nd |
| Multi-Image Input Elo | **1st** | 2nd | 3rd | 4th |
| Text-to-Multi-Image Elo | **1st** | 2nd | 4th | 3rd |

**Key findings:**
- Seedream 4.5 ranks **2nd in most dimensions** but drops to **3rd in consistency and single-image structural accuracy** (Nano Banana (Gemini 2.5 Flash Image) non-Pro takes 2nd there)
- Nano Banana Pro (Gemini 3.0 Image) leads across **all dimensions** — "significant gap in all aspects"
- Seedream 4.5 vs Nano Banana (Gemini 2.5 Flash Image) (non-Pro): 4.5 wins overall, especially in T2I, but loses on consistency
- Material & color preservation: Seedream 4.5 > Banana 2 > Banana 1
- Image understanding & generation stability: Banana 2 > Seedream 4.5 > Banana 1
- Text rendering: Seedream renders more clearly but extracts text less accurately; Banana extracts correctly but renders blurry

---

## E-commerce Sector Performance (Seedream 5.0 vs Nanobanana, GSB)

**GSB = Good / Same / Bad** (Seedream vs Nanobanana)

### Clothing & Fashion (6 use cases)

| Use Case | GSB | Notes |
|---|---|---|
| Model Try-On | **Bad** | Character tone inconsistency |
| Color Variant | **Good** | |
| Fabric Macro | **Good** | |
| Movement Simulation | Same | |
| Size Comparison | **Good** | |
| Flat Lay Conversion | Same | |

### Accessories & Jewelry (5 use cases)

| Use Case | GSB | Notes |
|---|---|---|
| Earring Try-On | **Good** | |
| Metal Variant | **Good** | |
| Engraving Preview | **Good** | |
| Scale Reference | **Bad** | Hand tone slightly unnatural |
| Packaging View | Same | |

### Furniture (6 use cases)

| Use Case | GSB | Notes |
|---|---|---|
| Room Placement | Same | |
| Material Swap | **Good** | |
| Modular Layout | **Bad** | Doesn't understand L/U-shape; Nano wins |
| Dimension Overlay | Same | |
| Assembly Step | Same | |
| 360 Angles | **Good** | |

### Electronics (5 use cases)

| Use Case | GSB | Notes |
|---|---|---|
| Handheld Scene | Same | |
| Exploded View | Same | |
| In-the-Box Layout | Same | |
| Screen UI Demo | Same | |
| Color Variant | **Good** | |

### General Accessories (7 use cases)

| Use Case | GSB | Notes |
|---|---|---|
| Capacity Demo | Same | |
| Color Variation | Same | |
| Texture Close-Up | **Good** | |
| Wearing Angles | **Good** | |
| Model Try-On | Same | |
| Elegant Flyer | Same | |
| Curated Poster | Same | |

**GSB Summary across 29 use cases:**

| Rating | Count | Percentage |
|---|---|---|
| Good (Seedream wins) | **12** | 41.4% |
| Same (tie) | **14** | 48.3% |
| Bad (Nano wins) | **3** | 10.3% |

**Overall: Seedream 5.0 is the better choice for most e-commerce scenarios. Nano only wins on model try-on (tone), scale reference (hand), and modular furniture layouts.**

---

## Recommended Model Matrix (Star Ratings)

**3 = Strong, 2 = Adequate, 1 = Weak, -- = Not supported**

### E-commerce Product Display

| Use Case | 5.0 Lite | 4.5 | 4.0 |
|---|---|---|---|
| White background image | 3 | 2 | 2 |
| Product catalog | 3 | 2 | 1 |
| Detail close-up | 2 | 1 | 1 |
| Product flat lay | 3 | 1 | 2 |
| Product floor plan | 1 | 1 | 1 |

### E-commerce Virtual Try-on

| Use Case | 5.0 Lite | 4.5 | 4.0 |
|---|---|---|---|
| Character try-on | 3 | 2 | 1 |
| Change posture/perspective | 3 | 2 | 1 |
| Change the model | 3 | 1 | 1 |
| Change background | 3 | 3 | 1 |

### Design & Marketing

| Use Case | 5.0 Lite | 4.5 | 4.0 |
|---|---|---|---|
| Marketing poster design | 3 | 3 | 2 |
| Cover design | 3 | 3 | 3 |
| Product marketing image | 3 | 3 | 2 |
| Poster copy translation | 2 | 1 | 1 |
| Graphic design | 3 | 3 | 3 |
| Scenario-based processing | 3 | 3 | 2 |
| Precise editing | 2 | 2 | 1 |
| Tone imitation | 3 | 1 | 1 |
| Reference shot | 3 | 2 | 1 |
| Poster style editing | 3 | 3 | 3 |

### Education

| Use Case | 5.0 Lite | 4.5 | 4.0 |
|---|---|---|---|
| Knowledge expansion (EN/CN) | 3 | 3 | 3 |
| Knowledge expansion (multi-lang) | 2 | 3 | -- |

**Takeaway:** 5.0 Lite leads or ties in most use cases. 4.5 is notably better only for multi-language education content.

---

## Seedream 4.5 — GTM Conclusions

### GTM Highlights

Seedream 4.5 is a creativity-first image generation model, best suited for exploratory, aesthetic,
and creator-facing use cases. While it performs well in image editing and visual refinement, it
remains unreliable for precision-controlled, text-accurate, scale-sensitive, or physically realistic
commercial production without heavy prompt engineering and human review.

1. **Strong in image editing and creative refinement (with tolerance)**
   - Competitive performance in editing consistency, texture quality, and overall visual aesthetics
   - Performs best when modifying or refining existing images rather than generating strict outputs from scratch
   - Well suited for iterative creative workflows where variation is acceptable
2. **Suitable for creator and fashion-inspired scenarios (non-precision)**
   - Community creativity and inspiration-driven content
   - Creator assistance and visual ideation
   - Fashion and runway-style visuals focused on style and mood, not accuracy or fit
3. **Competitive single-image creative generation**
   - Solid performance in single-image generation tasks
   - Aesthetics, texture, and overall visual appeal are relatively reliable
   - Competitive in many single-image Elo comparisons, especially for creative visuals
4. **Relative advantage in editing-focused scenarios vs competitors**
   - Leads or matches Gemini in several editing-related metrics
   - Particularly strong in "modify & refine" workflows where exact reproducibility is not required
5. **Text rendering clarity advantage**
   - Renders text more clearly than Nano Banana (Gemini 2.5 Flash Image) (which extracts correctly but renders blurry)
   - Advantage in scenarios where visual text sharpness matters more than extraction accuracy
6. **Prioritize:**
   - Creator and community-driven creativity
   - Image editing and creative refinement workflows (PE-assisted)
   - Social and marketing creatives with simple layouts and low precision requirements
   - Fashion and lifestyle visuals focused on style exploration (non try-on, non-identity-critical)
   - Single-image creative generation use cases

### Gaps

Seedream 4.5's primary gaps lie in scale control, multi-image consistency, structural accuracy,
and semantic reliability, making it unsuitable for precision-driven, identity-sensitive, or
automated commercial production.

1. **Scale, proportion, and physical consistency (core limitation)**
   - Accessories (glasses, earrings, jewelry, pins) frequently rendered at incorrect scale
   - Human-background proportions may drift unpredictably
   - Multi-person compositions often cause global scale distortion
   - Full-body outputs (e.g., 9:16, 4K) may exhibit abnormal body proportions
   - Continuous or iterative edits can introduce face distortion
2. **Multi-image and compositional generation**
   - Weak performance in SKU variants, multi-view, and multi-image synthesis
   - Noticeable degradation when combining multiple reference images
   - Cross-image alignment and consistency are unreliable
3. **Structural accuracy and layout fidelity**
   - Lower reliability in structure- or layout-sensitive visuals
   - Can negatively impact product, technical, or diagram-like imagery
4. **Prompt fidelity and practical usefulness**
   - Weaker instruction compliance compared to Gemini
   - Requires heavier prompt tuning and iteration to achieve acceptable results
   - Output variance remains high even with similar prompts
5. **Semantic reasoning and world knowledge gap**
   - Higher risk of world-knowledge errors or semantic hallucinations
   - Not optimized for knowledge- or rule-intensive generation
6. **De-prioritize:**
   - Precision-critical imagery (product, jewelry, accessories requiring exact scale)
   - Multi-image consistency workflows (SKU variants, multi-view, cross-image alignment)
   - Human identity transformations (try-on, outfit swap, face swapping)
   - Text-accurate or multilingual visuals (especially Japanese)
   - Knowledge- or instruction-heavy generation
   - Deterministic or automation-driven pipelines (high-reproducibility, zero-tolerance)

---

## Seedream 5.0 Lite — GTM Conclusions

### GTM Highlights

Seedream 5.0 Lite is the most capable and cost-effective model in the Seedream family, leading in
e-commerce product display, virtual try-on, and design/marketing scenarios at 2.9-4.3x lower cost
than Nano Banana 2 (Gemini 3.1 Flash Image Preview).

1. **Best-in-family across most e-commerce use cases**
   - Leads or ties with 4.5 in 22 out of 24 rated use cases
   - Significant improvements in try-on, product catalog, tone imitation, and reference shots
   - GSB evaluation: 41.4% Good (wins vs Nano), 48.3% Same, only 10.3% Bad
2. **Extreme cost advantage**
   - $0.035/image — only 23-35% of Nano Banana 2 (Gemini 3.1 Flash Image Preview)'s pricing
   - Enables high-volume production workflows that are cost-prohibitive with competitors
   - Hybrid 5.0 Lite + 4.5 deployment can match Nano Banana 2 (Gemini 3.1 Flash Image Preview) quality at fraction of cost
3. **Strong improvements over 4.0/4.5**
   - Text and detail extraction/rendering significantly improved
   - Portrait enhancement: model realism and naturalness substantially improved
   - Spatial proportion understanding improved
   - First-attempt success rate significantly improved, reducing iteration cycles
   - Lower input quality requirements, broader product category coverage
4. **Artifact control and composition**
   - Only dimensions where Seedream leads Gemini 3.1 Flash in head-to-head evaluation
   - Clean output with fewer visual artifacts than competitors
5. **Prioritize:**
   - E-commerce product display (white background, catalog, flat lay)
   - Virtual try-on (character, posture, model swap, background change)
   - Design and marketing (posters, covers, scenario-based, tone imitation)
   - Color/material variant generation
   - High-volume production workflows where cost-per-image matters

### Gaps

Seedream 5.0 Lite's primary gaps are in prompt fidelity vs Gemini, text rendering reliability,
identity preservation, and lack of 4K support.

1. **Prompt fidelity and usefulness — largest gap vs Gemini**
   - Prompt fidelity: Gemini leads by 13.0pp (36.2% vs 23.2%)
   - Usefulness: Gemini leads by 16.4pp (37.2% vs 20.8%) — **single biggest competitive gap**
   - Seedream outputs are less practically useful and less instruction-compliant than Gemini
2. **Text rendering — persistent weakness**
   - English and Vietnamese text break frequently in multi-page pipelines
   - Small product label text renders incorrectly
   - Chart labels/values hallucinated
   - Japanese text inaccurate
   - After prompt engineering, success rate is approximately 50%
   - Customer feedback: text and chart quality both fall short of Nano Banana (Gemini 2.5 Flash Image)
3. **Identity & face consistency**
   - Face frequently redrawn/distorted during clothing swap, scene compositing, accessory replacement
   - Body proportions distort after face-preservation attempts
   - Model try-on rated "Bad" in GSB evaluation (character tone inconsistency)
4. **No 4K support (known technical limitation)**
   - 5.0 Lite does not support 4K output
   - Use 4.5 or 4.0 for 4K requirements
5. **Prompt vs reference image conflict**
   - Model over-follows text prompt at expense of reference image fidelity
   - Problematic for editing workflows requiring strict source preservation
6. **Product & accessory fidelity edge cases**
   - Jewelry misplaced/resized/distorted
   - Logos altered
   - Garment region detection unreliable
   - Scale reference rated "Bad" in GSB (hand tone unnatural)
   - Modular furniture layout rated "Bad" (doesn't understand L/U-shape)
7. **Data visualization**
   - Chart types ignored; data values substituted; labeling errors persist
8. **De-prioritize:**
   - Text-heavy or text-critical imagery (labels, charts, multilingual)
   - Identity-sensitive human imagery (face swap, strict try-on)
   - 4K output requirements (use 4.5/4.0 instead)
   - Precision editing requiring strict reference image fidelity
   - Modular furniture or spatial layout understanding
   - Automated production pipelines requiring zero-tolerance prompt compliance

---

## Cross-Model Competitive Summary

### vs Gemini 3.1 Flash

| Dimension | Verdict | Evidence |
|---|---|---|
| Prompt fidelity | **Gemini leads** | -13.0pp gap in pairwise eval |
| Usefulness | **Gemini leads significantly** | -16.4pp gap — biggest single weakness |
| Edit consistency | **Gemini leads** | -5.8pp gap |
| Text rendering | **Gemini leads** | -5.3pp gap |
| Texture quality | Gemini leads slightly | -3.8pp, 84% ties |
| Lighting | Gemini leads slightly | -2.9pp, 82% ties |
| Artifact control | **Seedream leads** | +1.9pp — Seedream's best dimension |
| Composition | Seedream leads marginally | +0.5pp, 95% ties |
| **Pricing** | **Seedream wins decisively** | ~3-4x cheaper |

### vs Nano Banana (Gemini 2.5 Flash Image) (non-Pro)

| Dimension | Verdict | Evidence |
|---|---|---|
| Text-to-image overall | **Seedream 4.5 leads** | Higher Elo in T2I Expert |
| Material & color preservation | **Seedream 4.5 leads** | SR4.5 > NB2 > NB1 |
| Image understanding & stability | **Nano Banana 2 (Gemini 3.1 Flash Image Preview) leads** | NB2 > SR4.5 > NB1 |
| Complex prompt understanding | Parity | NB2 = SR4.5 > NB1 |
| Simple prompt understanding | **Nano Banana 2 (Gemini 3.1 Flash Image Preview) leads** | NB2 > SR4.5 = NB1 |
| Consistency (single-image) | **Nano Banana (Gemini 2.5 Flash Image) leads** | SR4.5 drops to 3rd |
| Text extraction accuracy | **Nano Banana (Gemini 2.5 Flash Image) leads** | Extracts correctly, renders blurry |
| Text rendering clarity | **Seedream leads** | Renders clearly, extracts incorrectly |
| **Pricing** | **Seedream wins** | ~2.5-3.8x cheaper |

### vs Nano Banana Pro (Gemini 3.0 Image)

| Dimension | Verdict | Evidence |
|---|---|---|
| All dimensions | **Nano Banana Pro (Gemini 3.0 Image) leads** | 1st in all 11 evaluated dimensions |
| Semantic understanding | **Nano Banana Pro (Gemini 3.0 Image) leads significantly** | "Significant gap in all aspects" |
| Multi-image input | Near parity | NB Pro confuses inputs more often, but has stronger semantics |
| **Pricing** | **Seedream wins** | Significantly cheaper |

---

## 4.0 → 4.5 → 5.0 Lite Upgrade Narrative

| Dimension | 4.0 | 4.5 | 5.0 Lite | Story |
|---|---|---|---|---|
| E-commerce product display | Basic | Improved | **Best in family** | White-bg, catalog, flat-lay all upgraded |
| Virtual try-on | Unusable | Basic | **Production-grade** | Character/posture/model swap all 3-star |
| Design & marketing | Basic | Strong | **Strong+** | Posters, covers, scenario-based all reliable |
| Text rendering | Poor | Improved clarity | Better but still ~50% | Persistent weakness, improved each gen |
| Portrait realism | Basic | Improved | **Significantly improved** | Model naturalness is now production-grade |
| Spatial proportion | Broken | Improved | Improved further | No longer extremely out of place |
| First-attempt success | Low | Moderate | **Significantly higher** | Fewer re-generation cycles needed |
| Multi-language | Not supported | Better | Regression | 4.5 actually better for multi-lang education |
| 4K support | Yes | Yes | **No** | Known regression in 5.0 Lite |
| Price | $0.03 | $0.04 | **$0.035** | Best value at best capability |

---

## Query Patterns

When the user asks a question, match it to one of these patterns:

**Model comparison** ("Seedream vs Gemini", "和 Nano Banana 比", "5.0 vs 4.5")
-> Show relevant comparison tables with win rates, Elo, or GSB ratings.

**GTM positioning** ("Seedream 怎么推", "talking points", "客户推介")
-> Return GTM Highlights for the relevant model version.

**Gaps / weaknesses** ("Seedream 差在哪", "gaps", "bad cases", "de-prioritize")
-> Return Gaps section with specific evidence (pp gaps, GSB ratings, bad-case examples).

**E-commerce sector** ("电商表现", "服装场景", "家具场景", "accessories")
-> Return the relevant GSB sector table.

**Model selection** ("用哪个版本", "4.5 还是 5.0", "which model")
-> Return the Recommended Model Matrix for the relevant use case category.

**Upgrade narrative** ("4.5 到 5.0 提升", "upgrade story", "版本对比")
-> Return the 4.0 → 4.5 → 5.0 Lite comparison table.

**Pricing** ("Seedream 定价", "价格对比", "cost vs Nano Banana")
-> Return pricing tables and cost-advantage analysis.

**Specific dimension** ("prompt fidelity 差多少", "text rendering 问题")
-> Look up the exact scores from the per-dimension comparison tables.

**Eval-db deep dive** ("看详细评测数据", "examples", "具体 case")
-> Run polym-eval-db queries:
```bash
python skills/polym-eval-db/scripts/query.py stats --report 20260322_134321_d8e98043
python skills/polym-eval-db/scripts/query.py dims --report 20260322_134321_d8e98043
python skills/polym-eval-db/scripts/query.py examples --winner A --limit 5
```

## Response Format

- Use **tables** for comparisons and sector breakdowns
- Use **bold** for scores, percentages, and key conclusions
- Always include **GSB or pp-gap evidence** alongside qualitative claims
- Add a one-line **takeaway** at the end
- For Chinese queries, respond in Chinese; for English queries, respond in English
- When asked about specific bad cases, offer to query polym-eval-db for examples
