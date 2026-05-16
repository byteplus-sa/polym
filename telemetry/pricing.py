"""Per-model USD pricing.

Prices are per 1M tokens. Numbers are deliberately conservative and meant to be
recalibrated against Anthropic Console / OpenAI billing as we observe real spend.
Update freely — pricing drift will not break parsing, only cost_usd accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pricing:
    input_per_mtok: float
    output_per_mtok: float
    cache_read_per_mtok: float = 0.0
    cache_write_per_mtok: float = 0.0


CLAUDE = {
    "claude-opus-4-7": Pricing(15.0, 75.0, 1.50, 18.75),
    "claude-opus-4-6": Pricing(15.0, 75.0, 1.50, 18.75),
    "claude-sonnet-4-6": Pricing(3.0, 15.0, 0.30, 3.75),
    "claude-sonnet-4-5": Pricing(3.0, 15.0, 0.30, 3.75),
    "claude-haiku-4-5": Pricing(1.0, 5.0, 0.10, 1.25),
}

# Codex / OpenAI side — placeholders, calibrate when we have a billing cross-check.
CODEX = {
    "gpt-5": Pricing(1.25, 10.0, 0.125),
    "gpt-5-mini": Pricing(0.25, 2.0, 0.025),
    "gpt-4o": Pricing(2.5, 10.0, 1.25),
}

UNKNOWN = Pricing(0.0, 0.0, 0.0, 0.0)


def lookup(model: str) -> Pricing:
    return CLAUDE.get(model) or CODEX.get(model) or UNKNOWN


def cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> float:
    p = lookup(model)
    return (
        input_tokens * p.input_per_mtok
        + output_tokens * p.output_per_mtok
        + cache_read_tokens * p.cache_read_per_mtok
        + cache_creation_tokens * p.cache_write_per_mtok
    ) / 1_000_000
