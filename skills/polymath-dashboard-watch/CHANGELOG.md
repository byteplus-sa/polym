# polymath-dashboard-watch CHANGELOG

## 0.1.1 — 2026-05-13

- Renamed package to `polymath-dashboard-watch` to adopt the Polymath `polymath-` prefix convention.

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
- Local wiki write (silent) + Lark wiki write via polymath-sa-wiki (on user confirmation)
- Follows core/local-wiki-ux.md UX standard
