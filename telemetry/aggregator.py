"""Aggregate raw UsageRecords into per-(date, agent) leaderboard rows.

Date anchoring uses local time so a session that crosses UTC midnight stays
attributed to the local day the SA was working.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .parsers import UsageRecord
from . import pricing


@dataclass
class DailyRow:
    sa: str
    date: str                # YYYY-MM-DD (local)
    agent: str               # claude-code | codex
    input_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    session_ids: set[str] = field(default_factory=set)
    model_tokens: Counter = field(default_factory=Counter)  # model -> total tokens
    skill_invocations: Counter = field(default_factory=Counter)  # skill -> count

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
            + self.output_tokens
        )

    @property
    def cache_hit_rate(self) -> float:
        denom = self.input_tokens + self.cache_creation_tokens + self.cache_read_tokens
        return (self.cache_read_tokens / denom) if denom else 0.0

    @property
    def session_count(self) -> int:
        return len(self.session_ids)

    def to_record(self, sa: str, cli_version: str, machine_id: str) -> dict:
        top_skills = [name for name, _ in self.skill_invocations.most_common(5)]
        # Drop synthetic / placeholder entries that pollute the breakdown without
        # contributing tokens.
        breakdown = {m: n for m, n in self.model_tokens.items() if n > 0}
        return {
            "sa": sa,
            "date": _date_to_epoch_ms(self.date),
            "agent": self.agent,
            "model_breakdown": json.dumps(breakdown, ensure_ascii=False),
            "input_tokens": self.input_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cache_hit_rate": round(self.cache_hit_rate, 4),
            "cost_usd": round(self.cost_usd, 4),
            "session_count": self.session_count,
            "top_skills": ",".join(top_skills),
            "cli_version": cli_version,
            "machine_id": machine_id,
        }


def _local_date(iso_ts: str) -> str:
    if not iso_ts:
        return ""
    try:
        ts = iso_ts.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().date().isoformat()
    except ValueError:
        return ""


def _date_to_epoch_ms(date_str: str) -> int | None:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str).astimezone()
        return int(dt.timestamp() * 1000)
    except ValueError:
        return None


def aggregate(records: list[UsageRecord]) -> list[DailyRow]:
    bins: dict[tuple[str, str], DailyRow] = {}
    seen: set[str] = set()
    for r in records:
        if r.dedup_id in seen:
            continue
        seen.add(r.dedup_id)

        date = _local_date(r.timestamp)
        if not date:
            continue
        key = (date, r.agent)
        row = bins.get(key)
        if row is None:
            row = DailyRow(sa="", date=date, agent=r.agent)
            bins[key] = row

        row.input_tokens += r.input_tokens
        row.cache_creation_tokens += r.cache_creation_tokens
        row.cache_read_tokens += r.cache_read_tokens
        row.output_tokens += r.output_tokens
        row.cost_usd += pricing.cost_usd(
            r.model,
            r.input_tokens,
            r.output_tokens,
            r.cache_read_tokens,
            r.cache_creation_tokens,
        )
        row.session_ids.add(r.session_id)
        row.model_tokens[r.model] += (
            r.input_tokens + r.output_tokens + r.cache_read_tokens + r.cache_creation_tokens
        )
        for skill in r.skills or ():
            row.skill_invocations[skill] += 1

    return sorted(bins.values(), key=lambda x: (x.date, x.agent))
