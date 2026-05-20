---
name: polym-eval-prompt-optimizer
description: >
  Optimize prompts for Seedream, Seedance, Gemini, Sora, and Veo. Use when the user
  wants a stronger image/video generation prompt.
---

# Prompt Optimizer

Optimize generation prompts for image and video AI models.

## Quick Usage

```
优化这个提示词：<your prompt>
帮我写一个适合 Seedream 的电商产品图提示词
把这个中文描述转成 Seedance 视频提示词：<description>
```

## Supported Models

| Model | Type | Key Formula |
|-------|------|-------------|
| Seedream 4.5 | Image | Subject + Action + Environment + Aesthetics |
| Seedance 1.5 Pro | Video | Subject + Movement + Environment + Camera + Aesthetics + Sound |
| Seedance 1.0 Pro | Video | Subject + Movement + Environment + Camera + Aesthetics |
| Seedance 1.0 Lite | Video | Subject + Movement + Environment + Camera |
| Gemini / Imagen | Image | Subject + Style + Technical specs |
| Sora | Video | Subject + Action + Setting + Style |
| Veo | Video | Subject + Motion + Scene + Cinematics |

---

## Agent Instructions

When the user wants to optimize a prompt, apply the appropriate formula below.
Always output:
1. **Optimized prompt (English)** — the main output
2. **中文翻译** — if user wrote in Chinese
3. **Improvements** — briefly explain what was added/changed
4. **Suggestions** — model settings, duration, aspect ratio, etc.

---

## Seedream Image Prompt Formula

**Formula:** Subject + Action + Environment + Aesthetics

- **Subject**: person/object with specific details (age, appearance, clothing, material, color)
- **Action**: what the subject is doing or how it's posed
- **Environment**: background, setting, lighting context
- **Aesthetics**: style, mood, lighting type, color palette, photography style

**Scenarios:**

### E-commerce (电商产品图)
- Professional product photography style
- White or clean minimal background
- Clear product details, accurate proportions
- Suitable for online retail display
- Example: `A sleek black wireless headphone, placed on a white surface, soft studio lighting from above, minimal shadow, professional product photography, 8K detail`

### Advertising (广告图)
- Lifestyle scene with emotional connection
- Brand tone and target audience context
- Eye-catching composition, clear visual focus
- Example: `A young woman enjoying morning coffee by a sunlit window, warm golden hour lighting, lifestyle photography, cozy and aspirational mood`

### Portrait (人像)
- Lighting type + pose details
- Background/environment description
- Mood and expression
- Photography style (portrait / documentary / fashion)

### Logo Design
- Describe design elements
- Company name in double quotes
- Style (minimal / modern / vintage / bold)
- Color scheme

### Virtual Try-on (虚拟试穿)
- Preserve person's features unchanged
- Clothing details
- Pose and proportions
- Lighting consistency
- Use editing formula: `Action + Object + Characteristic; Keep [person's face/pose/background] exactly the same`

### Text Rendering (文字渲染)
- Use double quotes around exact text
- Describe position and style
- Example: `A poster with the title "INNOVATION" in bold sans-serif font, centered, white text on dark blue background`

---

## Seedance Video Prompt Formula

### Seedance 1.5 Pro (supports audio)
**Formula:** Subject + Movement + Environment + Camera + Aesthetics + Sound

**Key rules:**
- Use degree adverbs: "slowly", "gradually" (NOT "rotate twice")
- Describe subjects consistently: "the woman in red coat" (NOT "character A")
- For dialogue: specify language, emotion, tone, speed

**Sound format:**
```
In a [emotion] tone, [speed] speed, [language]: "[dialogue text]"
Background music: [style], [pacing], [mood]
```

**Shot format:**
```
Shot 1: [wide/medium/close-up]. [scene]. [action]. [dialogue if any]
Shot 2: Cut to [shot type]. [description]...
```

### Seedance 1.0 Pro (no audio, strong visual consistency)
**Formula:** Subject + Movement + Environment + Camera + Aesthetics

- Best for e-commerce, product showcasing
- Emphasize: "maintain product consistency", "keep proportions unchanged"
- No audio/dialogue in prompt

### Seedance 1.0 Lite (low cost, quick prototyping)
**Formula:** Subject + Movement + Environment + Camera

- Keep prompts concise
- Good for simple animations and showcases
- No audio

---

## Optimization Rules

1. **Be specific, not vague**: "a professional woman" → "a 30-year-old woman in a navy blazer and white shirt"
2. **Add lighting**: always specify lighting type (soft studio, golden hour, rim lighting, etc.)
3. **Add style reference**: photography style, art style, rendering quality
4. **For video**: always specify camera movement and subject movement separately
5. **English prompts perform best** for all models
6. **Avoid**: abstract emotions without visual grounding ("happy" → "smiling, eyes crinkling")

---

## Standalone CLI Usage

```bash
# Optimize an image prompt
python3 skills/polym-eval-prompt-optimizer/scripts/optimize_prompt.py \
  --prompt "一个女孩站在花园里" \
  --model seedream \
  --scenario ecommerce

# Optimize a video prompt
python3 skills/polym-eval-prompt-optimizer/scripts/optimize_prompt.py \
  --prompt "产品展示视频" \
  --model seedance-1.5-pro \
  --scenario ecommerce

# Environment variables
export BYTEPLUS_API_KEY=your_key
export BYTEPLUS_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
export OPTIMIZER_MODEL_ID=your_llm_model_id  # e.g. Seed-1.8 or GPT-5.4
```
