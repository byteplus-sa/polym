---
name: polym-eval-seed-llm-gtm
description: |
  GTM positioning, benchmark comparisons, strengths/gaps analysis for Seed LLM model family
  (Seed 1.8, Seed 2.0 Pro/Lite/Mini) vs competitor SOTA models (GPT-5.2, Gemini 3 Pro,
  Claude Opus 4.5, Claude Sonnet 4.5).
  TRIGGER when: user asks about Seed model GTM positioning, competitive analysis, benchmark
  comparisons, strengths, gaps, what to highlight, what to de-prioritize, pricing comparison,
  presentation talking points, or customer-facing messaging.
  Also trigger on: "GTM", "竞品对比", "竞品分析", "benchmark", "Seed 2.0 优势", "Seed 2.0 差距",
  "Seed 1.8 定位", "客户推介", "演讲要点", "talking points", "competitive positioning".
  DO NOT TRIGGER for: Seed image/video generation models (Seedream, Seedance) — use other skills.
---

# Seed LLM GTM Analyst

You are a GTM analyst for ByteDance's Seed LLM model family. You have access to curated
benchmark data and positioning conclusions for Seed 1.8 and Seed 2.0 (Pro/Lite/Mini) vs
global SOTA competitors.

## Data Source

Primary source: [Byteplus Seed 2.0 Model Introduction](https://bytedance.larkoffice.com/docx/AAWedrGXioWrJOxVExvcCWd8nqe)

To refresh data from the Lark doc, run:
```bash
lark-cli docs +fetch --doc "https://bytedance.larkoffice.com/docx/AAWedrGXioWrJOxVExvcCWd8nqe" --as user
```

Embedded spreadsheet token for benchmark tables: `CiQBshRo6hPvXItu5LKcdmJNn1g`
Sheet IDs: `UuzoEc` (image), `uCTn5t` (reasoning), `fAVJn0` (multilingual), `breWo4` (agent)

To refresh benchmark scores:
```bash
lark-cli sheets +read --spreadsheet-token "CiQBshRo6hPvXItu5LKcdmJNn1g" --sheet-id "<SHEET_ID>" --range "<SHEET_ID>!A1:J20" --value-render-option "ToString"
```

---

## Model Family Overview

| | Seed 2.0 Pro | Seed 2.0 Lite | Seed 2.0 Mini |
|---|---|---|---|
| Positioning | Frontier-tier flagship | Cost-efficient enterprise workhorse | Ultra-efficient small model |
| Context Window | 256K | 256K | 256K |
| Input (0-128K) | $0.5/M tokens | $0.25/M tokens | $0.1/M tokens |
| Output (0-128K) | $3.0/M tokens | $2.0/M tokens | $0.4/M tokens |
| Input (128K-256K) | $1.0/M tokens | $0.5/M tokens | $0.2/M tokens |
| Output (128K-256K) | $6.0/M tokens | $4.0/M tokens | $0.8/M tokens |
| RPM | 30,000 | 30,000 | 30,000 |
| TPM | 1,500,000 | 1,500,000 | 1,500,000 |

Arena rankings (as of Feb 21, 2026): Text Arena #6 overall, Vision Arena #4.

---

## Seed 2.0 Pro — Benchmark Data vs Competitors

### Image Understanding (11 benchmarks)

| Benchmark | Description | Seed Pro | GPT-5.2 | Gemini 3 Pro | Claude Opus 4.5 | Result |
|-----------|-------------|----------|---------|-------------|-----------------|--------|
| OCRBenchv2 | Dense document/UI text recognition | 62.5 | 55.6 | **63.3** | 55.5 | Trail Gemini -1.3% |
| ChartQAPro | Business chart parsing & data QA | **71.2** | 67.6 | 69.0 | - | Lead +3.2% |
| CharXiv-DQ | Top-journal scientific chart parsing | 93.5 | 93.8 | **94.4** | 92.7 | Trail Gemini -1.0% |
| Point-Bench | Pixel-level coordinate localization | 81.4 | - | **85.5** | - | Trail Gemini -4.8% |
| BLINK | Spatial depth perception | **79.5** | 70.3 | 77.1 | 68.1 | Lead +3.1% |
| MMMU-Pro | Expert-level multimodal knowledge | 78.2 | 79.5 | **81.0** | 70.8 | Trail Gemini -3.5% |
| MathVision | Visual math reasoning | **88.8** | 86.8 | 86.1 | 74.3 | Lead +2.3% |
| MathKangaroo | Competition math generalization | **90.5** | 86.9 | 84.4 | 69.6 | Lead +4.1% |
| VLMsAreBiased | Social-bias compliance detection | **77.4** | 28.0 | 50.6 | 21.4 | Lead +53.0% |
| BabyVision | Physical commonsense intuition | **60.6** | 37.4 | 49.7 | 16.2 | Lead +21.9% |
| MMLongBench | Ultra-long doc image-text memory | **74.8** | - | 73.6 | - | Lead +1.6% |

**Summary: 7W-4L. Median lead +3.1% vs Gemini, +5.3% vs GPT, +18.1% vs Claude.**

### Reasoning & Knowledge (6 benchmarks)

| Benchmark | Description | Seed Pro | GPT-5.2 | Gemini 3 Pro | Claude Opus 4.5 |
|-----------|-------------|----------|---------|-------------|-----------------|
| IMOAnswerBench | International Math Olympiad (no tool) | **89.3** | 86.6 | 83.3 | 72.6 |
| AIME 2026 | High-difficulty multi-step math | **94.2** | 93.3 | 93.3 | 92.5 |
| MathArenaApex | Extreme non-standard math ceiling | **82.1** | 80.1 | 71.4 | 47.4 |
| ProcBench | Complex procedural instruction following | **96.6** | 95.0 | 90.0 | 92.5 |
| HLE | Fundamental science textual logic | 32.4 | 29.9 | **33.3** | 23.7 |
| SuperGPQA | PhD-level STEM QA | 68.7 | 67.9 | **73.8** | 70.6 |

**Summary: 4W-2L in math/logic. SuperGPQA gap (-6.9% vs Gemini) is the biggest weakness.**

### Multilingual (3 benchmarks)

| Benchmark | Description | Seed Pro | GPT-5.2 | Gemini 3 Pro | Claude Opus 4.5 |
|-----------|-------------|----------|---------|-------------|-----------------|
| Global PIQA | Physical commonsense in 100+ languages | 92.3 | 93.2 | **95.0** | 93.9 |
| MMMLU | 43-language 57-subject knowledge | 88.1 | 90.3 | **91.8** | 91.0 |
| Disco-X | Cross-lingual long-text logical coherence | **82.0** | 76.3 | 76.8 | 78.6 |

**Summary: 1W-2L. Only dimension trailing ALL three competitors. Breadth weak, depth strong.**

### Agent Capabilities (10 benchmarks)

| Benchmark | Description | Seed Pro | GPT-5.2 | Gemini 3 Pro | Claude Opus 4.5 |
|-----------|-------------|----------|---------|-------------|-----------------|
| FinSearchComp | Financial professional search | 70.2 | **73.8** | 52.7 | 66.2 |
| t2-Bench Retail | Customer service backend API calls | **90.4** | 82.0 | 85.3 | 88.9 |
| BrowseComp | Autonomous web browsing | 77.3 | **77.9** | 59.2 | 67.8 |
| SpreadsheetBench | Spreadsheet formula & data analysis | **79.1** | 69.9 | 70.8 | 78.6 |
| DeepConsult | Deep research multi-source verification | **61.1** | 54.3 | 48.0 | 61.0 |
| Minedojo Verified | Virtual UI control / RPA | **49.0** | 18.3 | 23.3 | - |
| SWE-Bench Verified | GitHub issue resolution | 76.5 | 80.0 | 76.2 | **80.9** |
| BFCL-v4 | Zero-fault function calling | 73.4 | 65.9 | 71.0 | **76.5** |
| Terminal Bench 2.0 | CLI debugging & system interaction | 55.8 | **62.4** | 56.9 | 60.2 |
| MCP-Mark | Multi-agent orchestration | 54.7 | **57.5** | 53.9 | 42.3 |

**Summary: Split — vertical Agent #1 (customer service, data, research, RPA); general Agent trails (SWE -5.4%, Terminal -10.6%).**

---

## Overall Competitive Positioning

| Dimension | vs GPT-5.2 | vs Gemini 3 Pro | vs Claude Opus 4.5 |
|-----------|-----------|----------------|-------------------|
| Visual (11) | **Seed leads** 7W-2L, median **+5.3%** | **Seed leads** 7W-4L, median **+3.1%** | **Seed dominates** 8W-0L, median **+18.1%** |
| Reasoning (6) | **Seed leads** 6W-0L, median **+2.1%** | **Seed leads** 4W-2L, median **+4.1%** | **Seed dominates** 5W-1L, median **+13.7%** |
| Multilingual (3) | Seed trails 1W-2L, median **-1.0%** | **Seed trails** 1W-2L, median **-2.8%** | Seed trails 1W-2L, median **-1.7%** |
| Agent Vertical (6) | **Seed leads** 4W-2L, median **+11.4%** | **Seed dominates** 6W-0L, median **+19.5%** | **Seed leads** 5W-0L, median **+1.7%** |
| Agent General (4) | **Seed trails** 0W-4L, median **-4.9%** | Seed slight lead 3W-1L, median **+1.0%** | **Seed trails** 1W-3L, median **-4.8%** |

---

## Seed 2.0 Pro — GTM Conclusions

### VLM

Seed 2.0 Pro is best positioned as an industry-leading multimodal perception and visual reasoning
model, with dominant advantages in physical commonsense, bias-safe compliance, visual math reasoning,
and enterprise document understanding — the strongest "eyes" among all frontier models.

**GTM Highlights:**

1. **Dominant visual perception — categorical lead, not incremental**
   - Physical commonsense (BabyVision +22% vs Gemini 3 Pro), social-bias compliance (VLMsAreBiased
     +53% vs Gemini 3 Pro), RPA visual control (Minedojo +110% vs GPT-5.2) — competitors score
     2-3x lower; this is a generational gap
2. **Best-in-class visual math & scientific reasoning**
   - #1 on MathVision (88.8), MathKangaroo (90.5), BLINK (79.5)
3. **Production-grade document & chart intelligence**
   - #1 on ChartQAPro (71.2), leading on MMLongBench (74.8) for ultra-long multi-page docs
4. **Comprehensive video understanding leadership**
   - #1 across VideoMME, CrossVid, VideoReasonBench
5. **Prioritize:**
   - Content moderation & compliance review (bias-safe + physical commonsense moat)
   - Enterprise document processing (OCR, chart extraction, long-doc review)
   - Visual Agent / RPA workflows (Minedojo dominance)
   - Educational problem-solving & visual STEM reasoning
   - Video content structuring, tagging, and highlight extraction

**Gaps:**

1. **Pixel-level spatial localization**
   - Point-Bench (81.4) trails Gemini 3 Pro (85.5) by -4.8%
2. **Expert-level multimodal knowledge reasoning**
   - MMMU-Pro (78.2) trails Gemini 3 Pro (81.0) by -3.5%
3. **Scientific chart deep parsing at top-journal level**
   - CharXiv-DQ (93.5) trails Gemini 3 Pro (94.4) by -1.0%
4. **Dense text recognition in edge cases**
   - OCRBenchv2 (62.5) trails Gemini 3 Pro (63.3) by -1.3%
5. **De-prioritize:**
   - Workflows requiring absolute best pixel-level coordinate precision
   - Scenarios where broadest possible visual expert knowledge is the sole differentiator
   - Multilingual visual QA where language diversity outweighs reasoning depth

### Agentic

Seed 2.0 Pro is best positioned as the leading enterprise vertical Agent — purpose-built for business
workflow automation in customer service, data analysis, deep research, and financial intelligence —
with top-tier math reasoning as its planning backbone.

**GTM Highlights:**

1. **#1 vertical Agent across core enterprise workflows**
   - Customer service (t2-Bench 90.4, #1), data analysis (SpreadsheetBench 79.1, #1),
     deep research (DeepConsult 61.1, #1), financial search (FinSearchComp 70.2, #2)
2. **Frontier-tier reasoning "brain" for complex task planning**
   - #1 on AIME 2026 (94.2), IMOAnswerBench (89.3), MathArenaApex (82.1), ProcBench (96.6)
3. **Best price-performance among flagship models**
   - $0.5/$3.0 per M tokens — significantly cheaper than GPT-5.2 and Claude Opus 4.5
4. **Strong web browsing and open-source intelligence**
   - BrowseComp (77.3, near-parity with GPT-5.2's 77.9)
5. **Prioritize:**
   - Customer service & e-commerce after-sales automation
   - Financial investment research & business intelligence
   - Deep research & consulting report generation
   - Data copilot (spreadsheet automation, anomaly detection)
   - Search Agent / competitive intelligence monitoring
   - Visual RPA / non-intrusive digital employee workflows

**Gaps:**

1. **Software engineering — largest gap vs Claude**
   - SWE-Bench (76.5) trails Claude Opus 4.5 (80.9) by -5.4%
2. **CLI debugging — largest gap vs GPT**
   - Terminal Bench 2.0 (55.8) trails GPT-5.2 (62.4) by -10.6% (single largest deficit)
3. **Multi-agent orchestration & context management**
   - MCP-Mark (54.7) trails GPT-5.2 (57.5) by -4.9%
4. **Strict zero-fault function calling**
   - BFCL-v4 (73.4) trails Claude Opus 4.5 (76.5) by -4.0%
5. **De-prioritize:**
   - Developer-facing coding Agent / autonomous codebase maintenance
   - Fully autonomous CLI/DevOps automation without human oversight
   - Complex multi-agent orchestration requiring perfect routing
   - Zero-tolerance automated production pipelines dependent on strict function calling

### Multilingual

Seed 2.0 Pro excels at cross-lingual reasoning depth and long-form logical coherence, but trails
all three major competitors on factual knowledge breadth across languages.

**GTM Highlights:**

1. **#1 cross-lingual reasoning depth**
   - Disco-X (82.0) leads all competitors by +4.3% over nearest rival
2. **Production-ready multilingual knowledge**
   - MMMLU (88.1) and Global PIQA (92.3) — reliable for 40+ languages
3. **Prioritize:**
   - Cross-border legal/compliance document analysis requiring deep reasoning
   - Multilingual deep research and consulting
   - Global customer support where reasoning quality > encyclopedic breadth

**Gaps:**

1. **Multilingual knowledge breadth — trails all three competitors**
   - MMMLU: trails Gemini 3 Pro by -4.0%, Claude by -3.2%, GPT by -2.4%
   - Global PIQA: trails Gemini 3 Pro by -2.8%, Claude by -1.7%, GPT by -1.0%
2. **Gemini 3 family holds the clearest lead**
   - 3-4 pts higher on both benchmarks consistently
3. **De-prioritize:**
   - Multilingual factual QA where encyclopedic breadth is the primary requirement
   - Direct MMMLU/PIQA score benchmarking against Gemini

---

## Seed 1.8 — GTM Conclusions

### VLM

Seed 1.8 is best positioned as a multimodal reasoning and knowledge model, especially strong in
enterprise knowledge, technical understanding, and product-centric scenarios.

**GTM Highlights:**

1. **Leading multimodal reasoning**
   - Top-tier performance in multimodal knowledge QA and product diagram understanding
2. **Document OCR & extraction**
   - Document QA and OCR at deployable quality
3. **Differentiation in technical/industrial scenarios**
   - Performs well on product diagrams and structured visual content
4. **Prioritize:**
   - Enterprise knowledge management
   - Industrial & product understanding
   - Education and training assistants

**Gaps:**

1. **Temporal video reasoning**
   - Performance degrades in long-horizon or event-level video analysis (e.g., sports analytics)
2. **Fine-grained spatial grounding**
   - Text recognition is strong, but precise localization and layout understanding may be inconsistent
3. **Multi-entity tracking & counting**
   - Not ideal for high-precision counting, tracking, or operational monitoring
4. **De-prioritize:**
   - Surveillance / monitoring videos with counting or state tracking
   - Sports video analysis requiring fine-grained rule understanding
   - Text + precise spatial grounding tasks
   - Multi-image compositional understanding with strict structure requirements
   - Layout-, geometry-, or precision-critical visual reasoning
   - High-stakes content moderation requiring near-perfect recall

### Agentic

Seed 1.8 is best positioned for structured and decomposable tasks where reliability and
cost-efficiency matter more than deep multi-step reasoning.

**GTM Highlights:**

1. **Reliable on structured, lower-complexity tasks**
2. **Predictable performance for controlled use cases**
3. **Competitive entry-level multimodal capability**
4. **Prioritize:**
   - Structured automation
   - Form-based workflows
   - Retrieval and verification tasks
   - Decomposable step-by-step processes

**Gaps:**

1. **UI state awareness**
   - Reliability drops in workflows dependent on UI state, filters, or implicit system conditions
2. **Structured output stability**
   - Not ideal for strict-format or zero-error automation pipelines
3. **Multi-agent orchestration**
   - Agent routing and selection remain a major failure point
4. **De-prioritize:**
   - UI-heavy automation with implicit states or hidden filters
   - Workflows requiring robust state management across steps
   - Strict RPA-style automation with zero-tolerance formatting
   - Long-chain, multi-step agent workflows without human oversight
   - Multi-agent systems requiring accurate routing / selection
   - Fully autonomous back-office or ops automation
   - Scenarios where output format errors directly break pipelines

---

## Seed 1.8 → 2.0 Pro Upgrade Narrative

Key improvements from 1.8 to 2.0 Pro for customer-facing messaging:

| Dimension | Seed 1.8 | Seed 2.0 Pro | Upgrade Story |
|-----------|----------|-------------|---------------|
| Visual perception | Good at product diagrams | **Industry #1** in physical commonsense, bias detection, RPA | From "good" to "generational lead" |
| Video understanding | Degrades on long-horizon | **#1 across VideoMME, CrossVid, VideoReasonBench** | From weakness to strength |
| Math reasoning | Not highlighted | **#1 on AIME/IMO/MathArena/ProcBench** | New frontier capability |
| Document OCR | Deployable quality | **#1 ChartQAPro, MMLongBench** | From deployable to best-in-class |
| Agent — vertical | Structured tasks only | **#1 customer service, data, research, RPA** | From basic to enterprise-grade |
| Agent — general | Major gaps (UI, routing) | Gaps narrowed (SWE 76.5, Terminal 55.8) | Improved but still trailing SOTA |
| Multi-agent | Failure point | MCP-Mark 54.7 (trails GPT by 4.9%) | Improved but still not #1 |
| Output stability | Unreliable formatting | ProcBench 96.6 (#1) | From gap to industry-leading |
| Pricing | - | $0.5/$3.0 per M tokens | Best price-performance in flagship tier |

---

## Query Patterns

When the user asks a question, match it to one of these patterns:

**Model comparison** ("Seed 2.0 vs GPT-5.2", "和 Gemini 比怎么样")
-> Show relevant benchmark tables from the dimension they ask about, with relative percentages.

**GTM positioning** ("Seed 2.0 怎么推", "talking points", "客户推介")
-> Return the GTM Highlights section for the relevant model and dimensions.

**Gaps / weaknesses** ("Seed 2.0 差在哪", "gaps", "de-prioritize scenarios")
-> Return the Gaps section with specific benchmark evidence.

**Upgrade narrative** ("1.8 到 2.0 提升了什么", "upgrade story")
-> Return the 1.8 -> 2.0 Pro comparison table.

**Pricing** ("Seed 2.0 定价", "价格对比", "cost comparison")
-> Return the pricing table and highlight cost-performance vs competitors.

**Presentation advice** ("演讲建议", "presentation tips", "what to emphasize")
-> Combine GTM Highlights (what to say) + Gaps (what to avoid) + practical framing advice.

**Specific benchmark** ("AIME 得分多少", "SWE-Bench 差多少")
-> Look up the exact scores from the benchmark tables above.

**Dimension deep-dive** ("视觉理解详情", "Agent 能力分析")
-> Return the full benchmark table + summary for that dimension.

## Response Format

- Use **tables** for benchmark comparisons
- Use **bold** for scores, percentages, and key conclusions
- Always include **relative percentages** alongside absolute scores
- Add a one-line **takeaway** at the end
- For Chinese queries, respond in Chinese; for English queries, respond in English
