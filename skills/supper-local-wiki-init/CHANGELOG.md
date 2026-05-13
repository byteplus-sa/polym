# supper-local-wiki-init CHANGELOG

## 0.1.1 — 2026-05-13

- Renamed package to `supper-local-wiki-init` to adopt the SA Super Skill `supper-` prefix convention.

## [0.1.0] — 2026-05-13

### Added
- Initial release
- Interactive setup: asks user for wiki root path (default: ~/sa-wiki)
- Creates full directory structure: raw/, drafts/, minutes/, wiki/entities/{customers,products,people,orgs}/, wiki/concepts/, wiki/interactions/, wiki/sources/
- Writes SCHEMA.md tuned for BytePlus SA workflow (customers + products as first-class entities)
- Writes PROMPTS.md with 6 ready-to-use prompts: Ingest (static), Ingest (Lark chat), Ingest (Lark Minutes), Ingest (conversation), Query, Lint
- Writes README.md with orientation and tips
- Creates starter wiki/index.md and wiki/log.md with init entry
- Based on Karpathy's LLM Wiki pattern, evolved from /Users/bytedance/demo/Data/LLM-Wiki
