# im-digest CHANGELOG

## [0.1.0] — 2026-05-13

### Added
- Initial release
- Phase 0: date calculation (yesterday), local wiki path resolution, chat discovery
  from local wiki `lark_chat` frontmatter + `lark-cli im +chat-search` fallback
- Phase 1: message fetch via `lark-cli im +chat-messages-list` with date range filter,
  auto-pagination (cap 500 messages/chat), raw snapshot write to local wiki
- Phase 2: analysis across 6 dimensions: key points, customer feedback, feature asks,
  technical issues, decisions, pending items; signal-to-noise filter
- Phase 3: structured digest output in terminal
- Phase 4: local wiki write — customer page updates, source pages, index.md, log.md
- Phase 5: Lark wiki write — TIMELINE APPEND + feedback CREATE via sa-wiki write_queue,
  desensitisation check before every write
- Phase 6: summary report with all proposal_ids
- References: fetch-workflow.md (chat discovery, pagination, error handling),
  digest-schema.md (dimensions, filter, output format, write decision tree)
