# supper-sa-wiki CHANGELOG

## 0.2.1 — 2026-05-13

- Renamed package to `supper-sa-wiki` to adopt the SA Super Skill `supper-` prefix convention.

## [0.2.0] — 2026-05-13

### Added
- Initial release into sa-super-skill registry
- READ workflow: 3-source parallel search (SA Wiki + Lark messages + BytePlus docs)
- WRITE workflow: write_queue with 4 actions (CREATE / APPEND / REPLACE / LINT)
- Compound mechanism: gap detection prompts user to save new knowledge to wiki
- Multi-agent concurrency safety via mandatory write_queue serialisation
- Full references: query-workflow.md, write-workflow.md, examples.md
- Desensitisation enforced before every write proposal
