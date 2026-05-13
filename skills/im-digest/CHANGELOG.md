# im-digest CHANGELOG

## [0.3.0] — 2026-05-13

### Changed
- Remove all "双写" / confirmation prompts from user-facing UX
- Local wiki is now resolved silently; only one question asked if not found
- Lark wiki always written automatically (no [Y/n] gate)
- Follow core/local-wiki-ux.md standard (shared with all skills)
- Phase 6 report simplified; risk signals highlighted prominently

## [0.2.0] — 2026-05-13

### Changed
- **Dimensions expanded from 6 → 12**: added 商务进展, 竞品信号, 风险信号, 用量 & 配额,
  人员 & 组织变动, 产品理解偏差; split 客户反馈 into positive/negative
- **Local wiki path memory**: on first use without LOCAL_WIKI_ROOT, skill probes
  common paths (~/ sa-wiki, ~/wiki, ~/LLM-Wiki) before asking; user-provided path
  is saved to Claude memory system to avoid re-asking in future sessions
- **Lark wiki write delegated to sa-wiki**: Phase 5 now reads sa-wiki SKILL.md §5
  WRITE workflow instead of reimplementing write_queue logic (single source of truth
  for Bitable constants, desensitisation rules, and page templates)
- Updated output format template and wiki write decision tree in digest-schema.md

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
