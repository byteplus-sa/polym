# meeting-summary CHANGELOG

## [0.1.0] — 2026-05-13

### Added
- Initial release
- Time range: default yesterday 00:00 to now; user-overridable
- Meeting discovery via lark-vc +meetings-list + lark-minutes +list; dedup by
  time overlap + title similarity + participant overlap
- Content fetch priority: 妙记 AI summary → chapters → transcript → VC detail
- 10-dimension analysis: meeting purpose, decisions, customer feedback (pos/neg),
  feature asks, technical issues, business progress, competitive signals, risk
  signals, pending items, participants
- Cross-meeting aggregation: multiple meetings per customer merged; cross-meeting
  patterns surfaced
- Local wiki write (silent): source pages, customer page updates, person pages
- Lark wiki write via sa-wiki WRITE workflow (no duplicate logic)
- Follows core/local-wiki-ux.md UX standard (no "双写", one-time local wiki setup)
