# polym-customer-brief CHANGELOG

## 0.1.1 — 2026-05-13

- Renamed package to `polym-customer-brief` to adopt the Polym `polym-` prefix convention.

## [0.1.0] — 2026-05-13

### Added
- Initial release
- 3 speed tiers: --quick (wiki only ~5s), default (+ live IM ~10s), --full (+ C360 ~20s)
- 4 parallel query agents: polym-sa-wiki (PROFILE+TIMELINE+feedback), local wiki
  (entities+sources), live Lark IM search (last N days), optional C360 usage
- Result merging: deduplication by source priority, conflict tagging
- Rule-driven "建议今天聊" section: P0/P1/P2 rules based on quota alert,
  overdue commitments, risk signals, competitor mentions, open feedback
- Output: 6 fixed sections (速览, 近期动态, 未关闭事项, 我们的承诺, 竞品雷达, 建议今天聊);
  empty sections auto-hidden
- --days flag (default 14) to control activity window
- --date flag for upcoming-meeting context
- Read-only: no wiki writes triggered
- Deprecates customer-lookup (same concept, richer implementation)
