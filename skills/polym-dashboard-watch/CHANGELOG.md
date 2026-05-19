# polym-dashboard-watch CHANGELOG

## 0.1.2 — 2026-05-19

- Inlined the C360 browser-automation runbooks (`customer-list-extraction.md`,
  `customer-usage-query.md`, `subagent-prompt-template.md`) into `references/`.
  The skill no longer depends on the external `c360-customer-usage` skill, so
  it works on a fresh polym install without any extra setup.
- Rewrote `references/c360-query.md` as the workflow entry point pointing at
  the three new local runbooks.
- Updated SKILL.md Phase 1 and the Reference Documents section accordingly.

## 0.1.1 — 2026-05-13

- Renamed package to `polym-dashboard-watch` to adopt the Polym `polym-` prefix convention.

## [0.1.0] — 2026-05-13

### Added
- Initial release
- Input: customer name + specific query; default to 30-day usage overview
- Chrome extension detection: checks mcp__Claude_in_Chrome__list_connected_browsers;
  if missing, shows step-by-step installation guide (Chrome Web Store + connect to Claude Code)
- C360 query via c360-customer-usage skill browser automation (no duplicate logic)
- 6 insight types: usage growth, usage decline, usage stop, quota alert,
  usage spike, new product activation — each with severity and suggested action
- Insight save: asks user once ("要保存到知识库吗？") only when actionable insights found;
  plain data queries never trigger save prompt
- Local wiki write (silent) + Lark wiki write via polym-sa-wiki (on user confirmation)
- Follows core/local-wiki-ux.md UX standard
