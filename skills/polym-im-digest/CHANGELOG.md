# polym-im-digest CHANGELOG

## 0.7.2 — 2026-05-26

### Changed
- Locked the Feishu visual digest layout as the default: metric cards,
  Executive Summary callout, Priority Queue, Owner / Deadline Gaps, Highlights,
  Action Items, Product Drill-Down, Cross-Chat Patterns, Risks, Pipeline, and
  full Chat Appendix.
- Replaced the ambiguous `AI Model / ModelArk / MaaS` vs `AIGC Video / Image`
  product split with a three-field taxonomy: product line, offering/model, and
  capability/modality.
- Treats `ModelArk / MaaS` as the product line and `Seedance`, `Seedream`,
  `Seed2.0`, `Seed-SC`, `Ark API`, `DeepSeek`, etc. as concrete offerings.
  `AIGC Video / Image` is now a capability/modality tag, not a product line.

## 0.7.1 — 2026-05-26

### Changed
- Removed the drafted external-source merge design. `polym-im-digest` is scoped to
  Lark IM sources only.
- Replaced the self-run scheduling design with Codex routine setup guidance. The
  skill remains a single-run workflow; Codex owns recurrence.
- Made Feishu Doc XML the default rendering path, using metric cards, callouts,
  real tables, checkboxes, and section dividers instead of Markdown pipe tables.
- Added a content-parity requirement so visual XML output cannot drop sections,
  P2/P3 rows, risks, pipeline updates, or chat appendix evidence from the
  Markdown digest.
- Corrected the Feishu doc creation command for current `lark-cli`: use
  `--content @<relative-file> --doc-format xml` from the digest directory, keep
  Markdown as a fallback, and do not pass `--format` to `docs +create`.

## 0.7.0 — 2026-05-26

### Added
- Reworked the digest output contract into a priority-first SA intelligence
  report: Executive Summary, Priority Queue, Owner / Deadline Gaps, Highlights,
  product-area drill-down, cross-chat patterns, risks, pipeline updates, and
  compact chat appendix.
- Added product context and focus ordering so MaaS / ModelArk / model-platform
  signals are sorted ahead of AIGC video/image, public cloud, and low-signal
  internal chatter.
- Added mandatory `P0` / `P1` owner, deadline, channel/background, status,
  next-step, and evidence fields.
- Added canonical issue de-duplication to prevent the same issue from being
  repeated in top summaries and lower sections.
- Added coverage checks for Seedance / Seedream / ModelArk / Ark / Doubao /
  xLLM / Viking / ArkClaw / AgentKit terms so active product signals are not
  silently dropped.

### Fixed
- Updated Phase 4 doc creation command to current `lark-cli docs +create
  --api-version v2` flags: `--title`, `--markdown`, and `--folder-token`.

## 0.6.0 — 2026-05-26

### Added
- Added a local-only IM digest blacklist for long-lived group and P2P
  exclusions.
- Blacklist resolution prefers
  `$LOCAL_WIKI_ROOT/config/polym-im-digest-blacklist.json` and falls back to
  `~/.config/polym/im-digest/blacklist.json`.
- Added management workflow for adding, removing, and listing blacklisted group
  chats and P2P contacts.
- Group blacklist entries are filtered before activity probes, so blacklisted
  groups are not fetched by `+chat-messages-list`.
- P2P blacklist entries are filtered immediately after global P2P discovery and
  never enter confirmation, Phase 1 fetch, analysis, raw snapshots, Feishu docs,
  or wiki writes.

### Notes
- Current `lark-cli im +messages-search --chat-type p2p` does not support
  negative filters, so P2P blacklist filtering cannot happen before the global
  discovery query.

## 0.5.1 — 2026-05-26

### Fixed
- Replaced the full group enumeration command in Phase 0 / fetch workflow:
  use `lark-cli im chats list --page-all --params '{"page_size":100,"sort_type":"ByActiveTimeDesc"}'`
  instead of an empty `lark-cli im +chat-search`.
- `+chat-search` requires `--query` or `--member-ids` in current `lark-cli`
  versions, so it remains appropriate only for resolving user-specified group
  names, not for listing every joined group.

## 0.5.0 — 2026-05-19

### Added
- **Phase 4 — Create Feishu Doc**: each run now materialises the rendered
  digest as a standalone Feishu document titled `IM Digest · <YESTERDAY>`,
  so the user has a real artefact to open / share instead of just terminal
  output and write_queue proposals. The doc is created via
  `lark-cli docs +create --doc-format markdown` from the same markdown
  Phase 3 writes to `$TMPDIR/polym-im-digest-<date>.md`.
- Asks the user once per run where to put the doc — Enter for personal
  drive root, paste a folder URL, or `new <name>` to create one.
- Phase 7 (Final Report) now surfaces the Feishu doc URL.

### Changed
- Phase 3 now persists the rendered markdown to `$TMPDIR` (was: terminal
  only) so Phase 4 can hand it to `lark-cli docs +create`.
- Renumbered the old Phases 4/5/6 to 5/6/7 to make room for the doc
  creation step. Behaviour of those phases is unchanged.
- Bumped `lark-cli` dependency note in SKILL.md to call out the `docs` and
  `drive` modules in addition to `im`.

### Notes
- This intentionally ships the minimal Feishu doc surface — no onboarding
  state file, no index-doc pin, no IM notification card. The fuller design
  with state persistence + pin-to-top + interactive card lives on the
  `feat/im-digest-lark-doc` branch (commit `767f937`).
- Doc creation failures (auth missing, scope missing, folder invalid) log
  a one-line warning and continue — local wiki and Lark write_queue
  writes still happen.

## 0.3.1 — 2026-05-13

- Renamed package to `polym-im-digest` to adopt the Polym `polym-` prefix convention.

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
  common paths (~/sa-wiki, ~/wiki, ~/LLM-Wiki) before asking; user-provided path
  is saved to Claude memory system to avoid re-asking in future sessions
- **Lark wiki write delegated to polym-sa-wiki**: Phase 5 now reads polym-sa-wiki SKILL.md §5
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
- Phase 5: Lark wiki write — TIMELINE APPEND + feedback CREATE via polym-sa-wiki write_queue,
  desensitisation check before every write
- Phase 6: summary report with all proposal_ids
- References: fetch-workflow.md (chat discovery, pagination, error handling),
  digest-schema.md (dimensions, filter, output format, write decision tree)
