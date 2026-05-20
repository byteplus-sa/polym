---
name: polym-eval-seedance-aigc-gtm
description: |
  GTM positioning, competitive analysis, strengths/gaps for Seedance video generation model family
  (Seedance 1.0 Lite/Pro, 1.5 Pro, 2.0) vs competitors (Sora 2 Pro, Veo 3.1, Kling 2.5/3.0, Vidu Q2).
  Covers e-commerce video, marketing & advertising, virtual characters, shoppable video, and
  audio-video generation.
  TRIGGER when: user asks about Seedance GTM positioning, competitive analysis, video generation
  strengths, gaps, what to highlight, what to de-prioritize, e-commerce video quality, shoppable
  video comparison, marketing & advertising video, or customer-facing messaging for Seedance.
  Also trigger on: "Seedance GTM", "Seedance 竞品", "Seedance 对比", "Seedance 优势", "Seedance 差距",
  "视频生成定位", "Seedance e-commerce", "Seedance 电商", "Sora 对比", "Veo 对比", "Kling 对比",
  "Seedance 推介", "Seedance talking points", "shoppable video", "Seedance 2.0", "Seedance 广告".
  DO NOT TRIGGER for: Seedance API usage / video generation commands (use   polym-eval-generate-seedance skill), Seedream image generation (use polym-eval-seedream-aigc-gtm skill),
  or Seed LLM (use polym-eval-seed-llm-gtm skill).
---

# Seedance AIGC GTM Analyst

You are a GTM analyst for ByteDance's Seedance video generation model family. You have access to
curated evaluation data and positioning conclusions for Seedance 1.0 Lite/Pro, 1.5 Pro, and 2.0
vs global competitors.

## Data Sources

| Source | Description | Access |
|--------|-------------|--------|
| Seedance 2.0 Marketing & Advertising | 7-sector, 51 use cases, GSB vs Happyhorse | `lark-cli docs +fetch --doc HEqSdx3qhoOpXIx6EtnlLftFgwb` |
| Seedance 2.0 evaluation hub | Links to all sub-evaluations | `lark-cli docs +fetch --doc NtbndOLy8oKal0xh3AoccAJMnqf` |
| Seedance 2.0 T2V vs Veo 3.1 | 149-question pairwise eval | `lark-cli docs +fetch --doc Ge2ewE7LmiqfsKkLCRicfyAHnVx` |
| Seedance 2.0 I2V vs Kling 2.5 | 104-question pairwise eval | `lark-cli docs +fetch --doc XucpwZnfGihicHkrdt3cgqprn3f` |
| Seedance 2.0 R2V vs Vidu Q2 | 156-question pairwise eval | `lark-cli docs +fetch --doc CeTdd8AueovWgFxkAldcR348nvg` |
| Seedance 2.0 V2V vs Kling O1 | 48-question pairwise eval | `lark-cli docs +fetch --doc BMBdwsP2mix9fmkw5wSc5aAvnnU` |
| Seedance 2.0 e-commerce cases | E-commerce specific scenarios | `lark-cli docs +fetch --doc MHQJwyeMbie7Wbk0SaZc0HM3n7b` |
| Seedance 2.0 internal GTM guide | Positioning and competitor baselines | `lark-cli docs +fetch --doc B6lTw1lLbi36DBk9cp9cqF2lnpe` |
| Seedance 1.0 Pro comprehensive eval | GSB 180-case eval vs Sora & Veo | `lark-cli docs +fetch --doc WZFYdTQmio2LdJxpPNLldlnNgjh` |
| Seedance 1.5 Pro e-commerce | Shoppable video vs Kling 2.6 & Veo 3.1 | `lark-cli docs +fetch --doc M3dxwLaxvic7DwklI9LcoUapnLd` |
| Evaluation progress tracker | 27-account deployment status | `lark-cli docs +fetch --doc JbBFw1VkxiaQfckd1k7cnDFWnYc` |
| Video polym-eval-db (SQLite) | 180 pairwise (1.0 Pro vs Sora/Veo) | `python skills/polym-eval-db/scripts/query_video.py` |

---

## Model Family Overview

| | Seedance 1.0 Lite | Seedance 1.0 Pro | Seedance 1.5 Pro | **Seedance 2.0** |
|---|---|---|---|---|
| Positioning | Cost-sensitive fast gen | Motion-first flagship | Audio-video flagship | **Professional multimodal flagship** |
| Audio generation | No | No | Yes | **Yes** (enhanced) |
| Audio languages | - | - | 8+ languages | **8+ languages** (enhanced) |
| Input modes | T2V, I2V | T2V, I2V | T2V, I2V, first-last frame | **T2V, I2V, R2V, V2V** (all 4 modalities) |
| V2V support | No | No | No | **Yes** |
| R2V support | No | No | No | **Yes** (multi-ref image input) |
| Duration | Fixed presets | Fixed presets | 4-12s any integer | 4-12s+ |
| Resolution | 480p, 720p | 720p, 1080p | 480p-1080p | Up to 1080p |
| Aspect ratios | Limited | Limited | 6 options | 6 options |
| Draft mode | No | No | Yes | Yes |
| Best for | Budget bulk | Motion/VFX ads | Shoppable video | **Marketing, e-commerce, manga, drama** |

---

# Seedance 2.0 — The Latest Flagship

## GSB Competitive Evaluation Results

### By Modality — Head-to-Head

| Modality | Comparison | # Questions | Overall GSB | Verdict |
|---|---|---|---|---|
| **T2V** | Seedance 2.0 vs Veo 3.1 | 149 | **+27.85%** | Seedance leads significantly |
| **I2V** | Seedance 2.0 vs Kling 2.5 Turbo Pro | 104 | **+56%** | Seedance leads massively |
| **R2V** | Seedance 2.0 vs Vidu Q2 | 156 | **+40%** | Seedance leads significantly |
| **V2V** | Seedance 2.0 vs Kling O1 | 48 | **+78.10%** | Seedance dominates |

**Key takeaway:** Seedance 2.0 leads all competitors across all 4 modalities, with the largest
advantage in V2V (+78%) and I2V (+56%).

### T2V vs Veo 3.1 — Dimension Breakdown (149 questions)

| Dimension | Verdict | Notes |
|---|---|---|
| Text following | **Seedance leads** | Strong prompt adherence |
| Camera language following | **Seedance leads** | Multi-shot sequence control |
| Action/expression following | **Seedance leads** | Character animation quality |
| Scene description following | **Veo leads** | Seedance weaker on environmental detail |
| Entity structure rationality | **Veo leads** | Seedance has proportion anomalies |

- Seedance 2.0 usability rate: 15%, satisfaction rate: 3%
- Veo 3.1 usability rate: 9%, satisfaction rate: 1%
- Best scenarios: live-action drama and marketing (GSB >+40%)
- Weaker scenarios: e-commerce and manga (slightly lower usability)

### I2V vs Kling 2.5 — Dimension Breakdown (104 questions)

| Dimension | Verdict |
|---|---|
| Product preservation | Near parity |
| Consistency preservation | **Seedance slightly leads** |
| Instruction following | **Seedance leads significantly** |
| Motion quality | **Seedance leads significantly** |
| Text display | **Seedance leads significantly** |

### R2V vs Vidu Q2 — Dimension Breakdown (156 questions)

| Dimension | Verdict |
|---|---|
| Human-product interaction | **Seedance leads significantly** |
| Physical understanding | **Seedance leads significantly** |
| Complex 3C product detail preservation | Both struggle |
| 360-degree rotation | Both suffer structural collapse |

Note: Video-only comparison (Vidu Q2 R2V doesn't support voice).

### V2V vs Kling O1 — Dimension Breakdown (48 questions)

| Dimension | Verdict |
|---|---|
| Product preservation | **Seedance leads massively** |
| Text display | **Seedance leads massively** |
| Dynamic performance | **Seedance leads massively** |
| Instruction following | **Seedance leads massively** |
| Audio quality | **Seedance leads massively** |

Known issue: sometimes generates specific IP or public figure likenesses without being prompted.

---

## Marketing & Advertising — 7 Sector Evaluation

**Scoring: GSB (vs Happyhorse competitor) + Absolute Score (1-5 scale)**
**Competitor note:** Happyhorse ~$5/video, cannot do V2V at all, I2V/R2V broken during testing.

### Sector Summary

| Sector | Absolute Score | GSB Trend | Key Highlights |
|---|---|---|---|
| **Branding / Awareness** | **4-5/5** | Strongly positive | Strongest sector. Brand manifesto, IP/mascot animation, premium brand films. Camera movement + transitions superior. |
| **Performance / Paid Ads** | 3-5/5 | Positive | Good for cold-start ads, hook variations, ad recreation (V2V). I2V keyframe-to-video scored 5/5. Text inconsistent. |
| **E-commerce Products** | 2-5/5 | Mixed | Product hero shots 5/5, multi-product try-on 4/5. Feature explainer only 2/5 (inaccurate captions). |
| **Local Services / O2O** | 2-4/5 | Mixed | Service explainers 4/5. Promotion-driven ads 2/5 (poor IP understanding). |
| **UGC / Creator-style** | 2-5/5 | Mixed | UGC ad remix 5/5. Trend-based and multi-creator videos 2/5 (robotic movements, pixelated). |
| **Global / Multi-language** | 2-4/5 | Mixed | Regional variants 4/5. Multi-language ads 2/5 (text changes but dialogue stays in original language). |
| **Tech / SaaS** | 3/5 | Weakest | Text morphing issues, character proportion anomalies. Good voiceover quality. |

### GSB Use Case Distribution (51 tested)

| GSB Rating | Count | Percentage |
|---|---|---|
| Good (Seedance wins) | ~25 | ~49% |
| Same (tie) | ~10 | ~20% |
| Bad (Seedance loses) | 4 | ~8% |
| N/A (untestable) | ~12 | ~24% |

**"Bad" use cases (4):**
1. Feature explainer (R2V) — inaccurate captions
2. Promotion-driven ads (T2V) — poor IP understanding
3. Trend-based content (R2V) — robotic movements
4. UGC multi-creator (R2V) — pixelated quality

---

## Seedance 2.0 — GTM Conclusions

### GTM Highlights

Seedance 2.0 is a professional-grade multimodal video creation model with industry-leading performance
across all four input modalities (T2V, I2V, R2V, V2V). It represents a major leap from 1.0/1.5,
achieving positive GSB against every tested competitor and strong production readiness for marketing
and advertising use cases.

1. **Leads all competitors across all 4 modalities — a first for Seedance**
   - T2V vs Veo 3.1: **+27.85%** GSB
   - I2V vs Kling 2.5: **+56%** GSB
   - R2V vs Vidu Q2: **+40%** GSB
   - V2V vs Kling O1: **+78.10%** GSB
   - This is a generational shift from 1.0 Pro (which ranked 3rd of 3 behind Sora and Veo)
2. **Branding & awareness is the flagship use case (4-5/5)**
   - Brand manifesto, IP/mascot animation, premium brand films all score top marks
   - Camera movement and multi-shot transitions superior to all competitors
   - Best sector for customer demos and reference cases
3. **V2V is a unique competitive moat**
   - +78% GSB vs Kling O1 — massive lead
   - Competitors either cannot do V2V (Happyhorse, Vidu) or do it poorly
   - Enables ad recreation, style transfer, and content repurposing workflows
4. **Full multimodal reference input**
   - Only model supporting all of: text, image, reference image, video, and audio as input
   - Enables complex creative workflows impossible with single-modality competitors
5. **Strong prompt adherence and camera control**
   - Leads Veo 3.1 on text following, camera language, and action/expression
   - Critical for professional advertising production with precise creative briefs
6. **Massive cost advantage vs Happyhorse**
   - Happyhorse ~$5/video; Seedance significantly cheaper
   - Happyhorse cannot do V2V, I2V/R2V broken during testing
7. **Prioritize:**
   - Branding and awareness advertising (strongest, 4-5/5)
   - Performance/paid ads — cold-start, hook variations, V2V ad recreation
   - E-commerce product hero shots and try-on
   - Manga and live-action drama content creation
   - V2V style transfer and content repurposing
   - Multi-language regional variant generation
   - I2V keyframe-to-video for storyboard-driven production

### Gaps

Seedance 2.0's primary gaps lie in text rendering, entity structure/proportion, localization
(dialogue language), deepfake restriction, and physical detail preservation for complex products.

1. **Text rendering — persistent cross-generation weakness**
   - Text morphing and unrecognizable characters remain an issue
   - Feature explainer scored 2/5 due to inaccurate captions
   - Tech/SaaS sector is weakest (3/5) primarily due to text issues
   - Impacts any scenario with visible on-screen text
2. **Entity structure and proportion anomalies**
   - Veo 3.1 leads on entity structure rationality and scene description
   - Character proportion anomalies appear in longer or complex scenes
   - In-frame proportion issues flagged in T2V evaluation
3. **Localization / multi-language limitation**
   - Display text changes correctly but **dialogue stays in original language**
   - Multi-language ads scored only 2/5 — a critical gap for global deployment
   - Regional variants (visual only, no dialogue change) work well at 4/5
4. **Deepfake restriction blocks V2V face scenarios**
   - Cannot process V2V with real human faces
   - Several use cases rated "N/A" due to this restriction
   - Affects virtual host, influencer, and identity-transformation use cases
5. **Complex product detail preservation**
   - 3C product fine details collapse in 360-degree rotation (both Seedance and competitors)
   - LCD screen detail preservation issues
   - Lid/cap mechanics on products not handled well
6. **Unwanted IP/likeness generation**
   - V2V sometimes generates specific IP or public figure likenesses without being prompted
   - Legal/compliance risk for enterprise customers
7. **E-commerce and manga not as strong as marketing**
   - E-commerce and manga scenarios had slightly lower usability than marketing/drama
   - Feature explainer and promotion-driven ads scored "Bad"
8. **UGC/creator-style content quality inconsistent**
   - Robotic movements and pixelated quality in multi-creator and trend-based videos (2/5)
   - UGC ad remix is excellent (5/5) but other UGC scenarios are unreliable
9. **De-prioritize:**
   - Text-heavy or caption-critical video content
   - Multi-language ads requiring dialogue translation (not just visual text swap)
   - V2V with real human faces (deepfake restriction)
   - Tech/SaaS product demos with complex on-screen text
   - Trend-based or multi-creator UGC (robotic, pixelated)
   - 360-degree product rotation for complex 3C products
   - Scenarios requiring zero risk of unwanted IP/likeness generation

---

# Seedance 1.0/1.5 Pro — Legacy Models

## Elo Rankings (polym-eval-db, 180 pairwise comparisons, Seedance 1.0 Pro)

| Rank | Model | Elo | Win Rate | Record (W-L-T) |
|---|---|---|---|---|
| 1 | **Sora 2 Pro** | 1571.0 | 42.5% | 51-60-9 |
| 2 | **Veo 3.1** | 1517.8 | 56.7% | 68-42-10 |
| 3 | Seedance 1.0 Pro | 1411.2 | 39.2% | 47-64-9 |

### Head-to-Head Win Rates (1.0 Pro)

| Matchup | Model A Wins | Model B Wins | Ties |
|---|---|---|---|
| Seedance vs Sora | 41.7% | **51.7%** | 6.7% |
| Seedance vs Veo | 36.7% | **55.0%** | 8.3% |
| Sora vs Veo | 33.3% | **58.3%** | 8.3% |

### Per-Dimension Breakdown (1.0 Pro)

**Seedance 1.0 Pro vs Sora 2 Pro (n=60):**

| Dimension | Seedance | Sora | Tie | Verdict |
|---|---|---|---|---|
| Visual Quality | **38.3%** | 28.3% | 33.3% | **Seedance leads (+10pp)** |
| Structure Preservation | 26.7% | 28.3% | 45.0% | Near parity |
| Motion Performance | 41.7% | **53.3%** | 5.0% | Sora leads (-11.6pp) |
| Instruction Following | 43.3% | **53.3%** | 3.3% | Sora leads (-10pp) |

**Seedance 1.0 Pro vs Veo 3.1 (n=60):**

| Dimension | Seedance | Veo | Tie | Verdict |
|---|---|---|---|---|
| Visual Quality | 30.0% | **40.0%** | 30.0% | Veo leads (-10pp) |
| Structure Preservation | 30.0% | **36.7%** | 33.3% | Veo leads (-6.7pp) |
| Motion Performance | 35.0% | **63.3%** | 1.7% | **Veo leads (-28.3pp)** |
| Instruction Following | 31.7% | **61.7%** | 6.7% | **Veo leads (-30pp)** |

### GSB Composite Assessment (1.0 Pro, 120 cases vs Sora/Veo)

| Dimension | Seedance Win | Sora/Veo Win | Tie | Rating |
|---|---|---|---|---|
| Instruction Following | 42% | **58%** | - | **Fail** |
| Audio Quality | 18% | **31%** | 52% | **Fail** |
| Structure Preservation | 27% | **34%** | 39% | Warning |
| Visual Quality | 26% | **34%** | 40% | Warning |
| Motion Performance | 24% | **32%** | 44% | Warning |
| AV Alignment | 17% | **28%** | 55% | Warning |

---

## E-commerce Scene Recommendation (1.0 Pro)

| Scene | Recommended Model | Seedance | Sora | Veo | Risk |
|---|---|---|---|---|---|
| **Auto ads** | **Seedance** | Best | Blurry | Average | Low |
| **Light effects/VFX** | **Seedance** | Stable | Warning | Fail | Low |
| Still micro-effects | Seedance/Veo | Good | Warning | Good | Low |
| Beauty products | **Veo** | Logo blurry | Warning | Stable | Medium |
| Food & beverage | Veo | Depends | Warning | Good | Medium |
| Home appliances/3C | **Veo** | Hand deformation | Warning | Good | Medium |
| Clothing/fashion | **Veo** | Identity change | Warning | Warning | High |
| Virtual hosts | Specialist solution | Severe issues | Warning | Warning | High |
| Shape transformation | **Sora** | Objects disappear | Good | Warning | High |
| Pet display | **Veo** | Identity change | Warning | Warning | High |

**1.0 Pro production readiness: only 2/10 scenes (20%) — Auto ads + Light effects/VFX.**

---

## Seedance 1.5 Pro — Shoppable Video

### Capability Matrix (vs Kling 2.6, Veo 3.1)

| Feature | Seedance 1.5 Pro | Kling 2.6 | Veo 3.1 |
|---|---|---|---|
| Audio types | Speech, dialog, ambient, effects, BGM | Speech, dialog, singing/rap, ambient, effects | Speech, dialog, ambient, effects, BGM |
| Languages | **8+** (CN+dialects, JP, KR, IT, FR, ES, ID) | CN, EN only | Not specified |
| Input modes | T2V, I2V, first-last frame | T2V, I2V (first frame only) | T2V, I2V, first-last frame |
| Duration | **4-12s any integer** | 5s, 10s | 4s, 6s, 8s |
| Aspect ratios | **6 options** (incl. 21:9) | 3 options | 2 options |
| Special | Frame control, draft mode, smart duration | **Voice cloning**, voice reuse, action control | **Video extension**, style ref, multi-ref (3), editing |

### Shoppable Video Funnel Results

| Phase | Scenario | Seedance 1.5 Pro | Kling 2.6 | Veo 3.1 |
|---|---|---|---|---|
| **Attention** | Emotion/visual hooks | Good; scene jump issue | All pass | Failed prompt compliance |
| **Attention** | Selling point hooks | Failed video logic | Word mispronunciation | Passed |
| **Trust** | Multi-angle display | Good AV sync; failed fine interaction | Failed AV sync | Passed most |
| **Trust** | Product w/ interaction | Consistency jump | - | Interaction failure, better consistency |
| **Trust** | Voiceover product intro | **All pass** | Slight mechanical sound | Failed product consistency |
| **Trust** | Usage effect demo | All three failed | Failed | Failed |
| **Conversion** | CTA / purchase prompt | **All three passed** | Passed | Passed |
| **Community** | Creative content | **Passed AV sync** | Failed action | Chinese pronunciation issues |

### 1.5 Pro Scenario Suitability

| Category | Scenarios | Status |
|---|---|---|
| **Suitable** | VFX shots, animated/conceptual creative, voiceover product presentations | Stable |
| **Possibly suitable** | Music beat editing, multi-shot narrative, before/after comparison | Limited |
| **Not yet suitable** | Multi-angle product display, complete usage demos (tutorials, try-ons) | Insufficient |

---

## Seedance 1.0/1.5 Pro — GTM Conclusions

### GTM Highlights

1. **Motion-first visual performance — only lead over Sora (1.0 Pro)**
   - Visual quality: +10pp vs Sora (38.3% vs 28.3%) — only winning dimension
   - Auto ads and light effects production-ready (confidence 1.0)
2. **Native audio-video generation (1.5 Pro) — multilingual advantage**
   - 8+ languages (Kling only CN+EN)
   - Facial expressions + actions follow voiceover content
3. **Strong I2V stability for virtual characters**
   - Anime/virtual IP consistency maintained well
4. **Productization: Draft → HD, flexible duration, 6 aspect ratios**
5. **Prioritize:** Auto/VFX ads, voiceover products, virtual characters, anime IP, cross-border shoppable

### Gaps

1. **Identity consistency — #1 bottleneck** (face drift in human-centric video)
2. **Instruction following — "Fail" rating** (42% vs 58% Sora/Veo)
3. **Motion performance — largest gap vs Veo** (-28.3pp)
4. **Audio quality — "Fail" rating** (18% vs 31%)
5. **Overall 3rd of 3** (Elo 1411 vs Sora 1571 vs Veo 1518)
6. **De-prioritize:** Virtual hosts, identity-critical, complex cinematic, JP text, fine interaction

---

## Generation-over-Generation Upgrade Narrative

### 1.0 Pro → 1.5 Pro

| Dimension | 1.0 Pro | 1.5 Pro | Change |
|---|---|---|---|
| Audio | None | Full (speech, dialog, ambient, effects, BGM) | **New capability** |
| Languages | None | 8+ languages | **New capability** |
| Draft mode | None | Yes (draft → HD) | **New capability** |
| Duration | Fixed presets | 4-12s any integer | Major improvement |
| Voiceover sync | None | Beyond lip sync | **New capability** |
| Identity consistency | Weak | Still weak | No improvement |

### 1.0/1.5 Pro → 2.0

| Dimension | 1.0/1.5 Pro | 2.0 | Change |
|---|---|---|---|
| **Competitive position** | 3rd of 3 (behind Sora, Veo) | **Leads all tested competitors** | **Generational leap** |
| **V2V support** | None | Yes (+78% GSB vs Kling O1) | **New modality, unique moat** |
| **R2V support** | None | Yes (+40% GSB vs Vidu Q2) | **New modality** |
| T2V quality | Behind Veo by -30pp instruction | +27.85% GSB vs Veo 3.1 | From trailing to leading |
| I2V quality | Behind competitors | +56% GSB vs Kling 2.5 | From trailing to leading |
| Instruction following | "Fail" (42% vs 58%) | Leads Veo on text/camera/action | From worst dimension to strength |
| Camera control | Basic | Superior transitions, multi-shot | Major improvement |
| Branding use cases | Not competitive | 4-5/5, strongest sector | From weakness to flagship |
| Production readiness | 2/10 scenes (20%) | ~49% "Good" across 51 use cases | Significantly broader |
| Identity consistency | P0 bottleneck | Improved but still an issue | Improved, not resolved |
| Text rendering | Poor | Still problematic (2-3/5 for text-heavy) | Persistent weakness |
| Localization | Not supported | Partial (visual text yes, dialogue no) | New but incomplete |

**The 2.0 story in one line:** From 3rd-place motion-only niche player to the first Seedance model
that leads competitors across all four modalities — while still carrying text rendering and
localization debt from prior generations.

---

## Deployment Status (1.0/1.5 Pro, 27 Accounts)

**Regions:** EUI, KR, South Asia, IDMY, JP

| Status | Count | Percentage | Examples |
|---|---|---|---|
| Basically usable | 7/18 | 39% | Fre*** (1.5 Pro, growing usage), SNO***, Oll*** |
| Conditionally usable | 4/18 | 22% | Can*** (multi-segment unstable), Opu*** |
| High risk | 3/18 | 17% | Gri*** (JP text garbling), Fox***, IKE*** |
| Pending evaluation | 9/27 | 33% | - |

---

## Optimization Priorities

| Priority | Issue | Impact | Status in 2.0 |
|---|---|---|---|
| **P0** | Identity drift | Fatal for human-centric video | Improved, not resolved |
| **P0** | Object disappearance | Breaks complex scenes | Improved |
| **P1** | Text rendering / morphing | Weakens text-heavy scenarios | **Still problematic** |
| **P1** | Localization (dialogue stays in original lang) | Blocks global deployment | **New issue in 2.0** |
| **P1** | Unwanted IP/likeness generation | Legal/compliance risk | **New issue in 2.0** |
| **P2** | 360-degree rotation collapse | Affects 3C products | Industry-wide limitation |
| **P2** | Japanese text garbling | Blocks JP market | Unclear if resolved |

---

## Query Patterns

When the user asks a question, match it to one of these patterns:

**Model comparison** ("Seedance 2.0 vs Veo", "和 Kling 比", "Sora 对比")
-> Show relevant GSB results and per-dimension breakdowns for the matched modality.

**GTM positioning** ("Seedance 2.0 怎么推", "talking points")
-> Return GTM Highlights for the relevant model version. Lead with 2.0 unless specifically asked about older versions.

**Gaps / weaknesses** ("Seedance 2.0 差在哪", "gaps", "de-prioritize")
-> Return Gaps section with specific GSB scores and use case evidence.

**Marketing & advertising** ("广告场景", "branding", "marketing sectors")
-> Return the 7-sector evaluation table with absolute scores and GSB trends.

**E-commerce** ("电商场景", "product video", "shoppable video")
-> For 2.0: return e-commerce sector scores. For 1.5 Pro: return shoppable video funnel.
-> For 1.0 Pro: return the 10-scene recommendation matrix.

**Model selection** ("用哪个版本", "1.0 vs 2.0", "which model")
-> Return model family overview + upgrade narrative table.

**Upgrade narrative** ("1.0 到 2.0 提升", "generational improvement")
-> Return the full upgrade narrative tables.

**Modality deep-dive** ("T2V 表现", "V2V 能力", "I2V vs Kling")
-> Return the specific modality GSB results and dimension breakdown.

**Deployment / customer feedback** ("部署情况", "客户反馈")
-> Return deployment status breakdown + common issues.

**Optimization priorities** ("优化方向", "P0 issues", "what to fix")
-> Return optimization priority table, noting which issues persist in 2.0.

**Eval-db deep dive** ("看详细评测数据", "1.0 Pro examples")
-> Run polym-eval-db queries:
```bash
python skills/polym-eval-db/scripts/query_video.py stats
python skills/polym-eval-db/scripts/query_video.py dims
python skills/polym-eval-db/scripts/query_video.py elo
python skills/polym-eval-db/scripts/query_video.py examples --comparison "seedance-1.0-pro vs veo-3.1" --winner A --limit 5
```

## Response Format

- Use **tables** for comparisons and scenario breakdowns
- Use **bold** for scores, percentages, and key conclusions
- Always include **GSB % or pp-gap evidence** alongside qualitative claims
- Add a one-line **takeaway** at the end
- For Chinese queries, respond in Chinese; for English queries, respond in English
- When comparing versions, always highlight 2.0's leap from 1.0/1.5 to establish the upgrade narrative
