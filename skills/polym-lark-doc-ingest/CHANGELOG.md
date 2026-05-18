# polym-lark-doc-ingest CHANGELOG

## 0.1.1 — 2026-05-13

- Renamed package to `polym-lark-doc-ingest` to adopt the Polym `polym-` prefix convention.

## [0.1.0] — 2026-05-13

### Added
- Initial release
- Discovery: parallel drive +search (--edited-since + --created-since) for time range;
  dedup by token; paginate up to 3 pages (60 docs max)
- Filtering: skip already-ingested (local wiki doc_id check + polym-sa-wiki knowledge_index);
  skip by title blacklist; skip after full-fetch if content < 200 chars
- Outline-first strategy: cheap outline fetch → classify → full fetch only for
  qualifying docs (reduces API calls for irrelevant docs)
- Classification: customer / product / competitor / knowledge / general
  based on title + outline vs known customer/product lists
- 8-dimension extraction: TL;DR, customer, product, people, feature asks,
  decisions, competitive intel, business progress
- --url flag: single-doc ingest mode
- --folder flag: restrict discovery to a folder
- --days flag: override time range (default 1 day)
- --dry-run flag: preview without writing
- Batch parallel processing: up to 5 docs in parallel
- Local wiki write (silent): raw snapshot, source page, entity updates
- Lark wiki write via polym-sa-wiki WRITE workflow (no duplicate logic)
- URL cleanup: strips disposable_login_token, dcuId, from params before storing
- Follows core/local-wiki-ux.md UX standard
