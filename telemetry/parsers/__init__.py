from dataclasses import dataclass, field


@dataclass
class UsageRecord:
    """One assistant turn's token usage. Output of every parser."""

    agent: str           # "claude-code" | "codex"
    timestamp: str       # ISO 8601, UTC
    session_id: str
    model: str           # normalized model name
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int   # 0 for codex
    # Source-side dedup key. cc uses message.id; codex uses (session_id, event_index).
    dedup_id: str
    # Skill names invoked in this turn via the `Skill` tool (cc only).
    # e.g. ["polym-customer-brief", "lark-im", "anthropic-skills:pptx"].
    skills: list[str] = field(default_factory=list)
