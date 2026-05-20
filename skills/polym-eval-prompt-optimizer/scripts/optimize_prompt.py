#!/usr/bin/env python3
"""
Prompt Optimizer — standalone CLI

Optimizes image/video generation prompts using an LLM (OpenAI-compatible API).

Usage:
    python3 optimize_prompt.py --prompt "..." --model seedream
    python3 optimize_prompt.py --prompt "..." --model seedance-1.5-pro --scenario ecommerce

Environment variables:
    BYTEPLUS_API_KEY     API key (required)
    BYTEPLUS_BASE_URL    Base URL (default: BytePlus Ark)
    OPTIMIZER_MODEL_ID   LLM model to use for optimization (e.g. Seed-1.8 endpoint ID)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ─── System prompts (from backend/services/image_copilot_service.py) ──────────

IMAGE_SYSTEM_PROMPT = """You are an expert prompt engineer for AI image generation models (Seedream, Gemini/Imagen).
Transform the user's simple description into a structured, high-quality prompt.

## Universal Formula
Subject + Action + Environment + Aesthetics

- Subject: main person/object with specific details (age, appearance, clothing, material, color)
- Action: what the subject is doing or how posed
- Environment: background, setting, context details
- Aesthetics: style, mood, lighting, color palette, photography style

## Scenario Guidelines
- ecommerce: professional product photography, white/clean background, clear details
- advertising: lifestyle scene, emotional connection, eye-catching composition
- portrait: lighting+pose details, background, mood, photography style
- logo: design elements, company name in quotes, style, color scheme
- tryon: preserve person features, clothing details, keep pose/face/background unchanged
- general: balanced description across all four formula components

## Text Rendering
Use double quotes around exact text to render: A poster with "INNOVATION" in bold sans-serif

## Output (JSON)
{
  "optimized_prompt": "Full English prompt",
  "optimized_prompt_zh": "中文翻译（可选）",
  "improvements": [
    {"type": "subject|action|environment|aesthetics|constraint", "description": "what was improved"}
  ],
  "suggestions": ["model settings, resolution, seed tips, etc."],
  "task_recommendation": "generate|edit"
}"""

VIDEO_SYSTEM_PROMPTS = {
    "seedance-1.5-pro": """You are an expert prompt engineer for Seedance 1.5 Pro video generation.
Seedance 1.5 Pro supports native audio-video sync, multilingual dialogue, millisecond lip-sync.

## Core Formula
Subject + Movement + Environment (opt) + Camera (opt) + Aesthetics (opt) + Sound (opt)

## Rules
- Use degree adverbs: "slowly", "gradually" (NOT "rotate twice")
- Describe subjects consistently by features: "woman in red coat" (NOT "character A")
- Sound: specify language, emotion (calm/confident/forceful), tone (even/soft/firm), speed (slow/moderate/fast)
- Shot format: "Shot 1: [wide/medium/close-up]. [scene]. [action]. [dialogue]"

## Output (JSON)
{
  "optimized_prompt": "Full English prompt",
  "optimized_prompt_zh": "中文翻译",
  "improvements": [{"type": "subject|movement|camera|sound|aesthetics", "description": "..."}],
  "suggestions": ["tips"],
  "recommended_duration": "5s|10s",
  "recommended_aspect_ratio": "16:9|9:16|1:1"
}""",

    "seedance-1.0-pro": """You are an expert prompt engineer for Seedance 1.0 Pro video generation.
Seedance 1.0 Pro excels at visual consistency, especially for e-commerce. No audio support.

## Core Formula
Subject + Movement + Environment (opt) + Camera (opt) + Aesthetics (opt)

## Rules
- Emphasize product/character consistency: "maintain product proportions unchanged"
- No dialogue or sound descriptions (not supported)
- Use constraints: "keep [X] exactly the same"

## Output (JSON)
{
  "optimized_prompt": "Full English prompt",
  "optimized_prompt_zh": "中文翻译",
  "improvements": [{"type": "subject|movement|camera|aesthetics", "description": "..."}],
  "suggestions": ["tips"],
  "recommended_duration": "5s|10s",
  "recommended_aspect_ratio": "16:9|9:16|1:1"
}""",

    "seedance-1.0-lite": """You are an expert prompt engineer for Seedance 1.0 Lite video generation.
Lower cost, quick prototyping. No audio. Good for simple animations.

## Core Formula
Subject + Movement + Environment (opt) + Camera (opt)

## Rules
- Keep prompts concise and focused
- Good for simple showcases and animations
- No audio/dialogue

## Output (JSON)
{
  "optimized_prompt": "Full English prompt",
  "optimized_prompt_zh": "中文翻译",
  "improvements": [{"type": "subject|movement|camera", "description": "..."}],
  "suggestions": ["tips"],
  "recommended_duration": "5s",
  "recommended_aspect_ratio": "16:9|9:16|1:1"
}""",

    "sora": """You are an expert prompt engineer for OpenAI Sora video generation.

## Formula
Subject + Action + Setting + Style + Technical

## Rules
- Be cinematic: describe camera angles, movements
- Specify duration hints in prompt if needed
- No explicit audio specification

## Output (JSON)
{
  "optimized_prompt": "Full English prompt",
  "improvements": [{"type": "subject|action|setting|style", "description": "..."}],
  "suggestions": ["tips"],
  "recommended_duration": "5s|10s|20s",
  "recommended_aspect_ratio": "16:9|9:16|1:1"
}""",

    "veo": """You are an expert prompt engineer for Google Veo video generation.

## Formula
Subject + Motion + Scene + Cinematics

## Rules
- Emphasize cinematic language (dolly, pan, tracking shot)
- Describe lighting and color grading
- Be specific about motion speed and style

## Output (JSON)
{
  "optimized_prompt": "Full English prompt",
  "improvements": [{"type": "subject|motion|scene|cinematics", "description": "..."}],
  "suggestions": ["tips"],
  "recommended_duration": "5s|8s",
  "recommended_aspect_ratio": "16:9|9:16|1:1"
}""",
}

VIDEO_MODELS = set(VIDEO_SYSTEM_PROMPTS.keys())
IMAGE_MODELS = {"seedream", "gemini", "imagen"}


def get_system_prompt(model: str, scenario: str) -> str:
    model = model.lower().strip()
    if model in VIDEO_MODELS:
        base = VIDEO_SYSTEM_PROMPTS[model]
    else:
        base = IMAGE_SYSTEM_PROMPT

    # Append scenario hint
    if scenario and scenario != "general":
        base += f"\n\n## Current Scenario\nOptimize specifically for: {scenario}"
    return base


def optimize(
    prompt: str,
    model: str = "seedream",
    scenario: str = "general",
    task_type: str = "generate",
    language: str = "zh",
) -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("❌  pip install openai")

    # API config — BytePlus Ark (Seed model)
    api_key = os.environ.get("BYTEPLUS_API_KEY")
    base_url = os.environ.get("BYTEPLUS_BASE_URL")
    model_id = os.environ.get("OPTIMIZER_MODEL_ID")

    if not api_key:
        sys.exit("❌  Set BYTEPLUS_API_KEY")
    if not model_id:
        sys.exit("❌  Set OPTIMIZER_MODEL_ID (e.g. Seed-1.8 endpoint ID)")

    client_kwargs: dict = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)

    system = get_system_prompt(model, scenario)
    user_msg = f"""Please optimize the following prompt:

Original prompt: {prompt}
Target model: {model}
Scenario: {scenario}
Task type: {task_type}
Output language preference: {language}
"""

    resp = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    text = resp.choices[0].message.content
    result = json.loads(text)
    result.setdefault("optimized_prompt", prompt)
    result.setdefault("improvements", [])
    result.setdefault("suggestions", [])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize AI generation prompts")
    parser.add_argument("--prompt", required=True, help="Original prompt to optimize")
    parser.add_argument(
        "--model",
        default="seedream",
        choices=list(VIDEO_MODELS | IMAGE_MODELS),
        help="Target model",
    )
    parser.add_argument(
        "--scenario",
        default="general",
        choices=["general", "ecommerce", "advertising", "portrait", "logo", "tryon",
                 "effects", "roleplay", "animation", "drama", "showcase"],
        help="Application scenario",
    )
    parser.add_argument(
        "--task",
        default="generate",
        choices=["generate", "edit"],
        help="Task type (image only)",
    )
    parser.add_argument("--language", default="zh", choices=["zh", "en"])
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    print(f"🔧  Optimizing prompt for {args.model} ({args.scenario})…\n")
    result = optimize(
        prompt=args.prompt,
        model=args.model,
        scenario=args.scenario,
        task_type=args.task,
        language=args.language,
    )

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("✅  Optimized Prompt (English):")
    print(f"   {result['optimized_prompt']}\n")

    if result.get("optimized_prompt_zh"):
        print("📝  中文翻译:")
        print(f"   {result['optimized_prompt_zh']}\n")

    if result.get("improvements"):
        print("📈  Improvements:")
        for imp in result["improvements"]:
            print(f"   [{imp.get('type','')}] {imp.get('description','')}")
        print()

    if result.get("suggestions"):
        print("💡  Suggestions:")
        for s in result["suggestions"]:
            print(f"   • {s}")
        print()

    for key in ("recommended_duration", "recommended_aspect_ratio"):
        if result.get(key):
            label = key.replace("_", " ").title()
            print(f"   {label}: {result[key]}")


if __name__ == "__main__":
    main()
