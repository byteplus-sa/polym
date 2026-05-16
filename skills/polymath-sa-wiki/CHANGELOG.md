# polymath-sa-wiki CHANGELOG

## 0.2.2 — 2026-05-16

### Fixed
- Schema gap in write_queue example payloads: docs referenced a non-existent
  `agent_id` field; actual write_queue schema uses `SA` (Lark display name of
  the real Solution Architect, e.g. `王文杰`). Updated SKILL.md §5 and all
  examples in references/{write-workflow,examples,query-workflow}.md.
  Clarified that `agent_id` exists only on the `log` table and is filled in
  by the coordinator at commit time. (Reported by Bojie Sun, 2026-05-15.)

## 0.2.1 — 2026-05-13

- Renamed package to `polymath-sa-wiki` to adopt the Polymath `polymath-` prefix convention.

## [0.2.0] — 2026-05-13

### Added
- Initial release into polymath registry
- READ workflow: 3-source parallel search (SA Wiki + Lark messages + BytePlus docs)
- WRITE workflow: write_queue with 4 actions (CREATE / APPEND / REPLACE / LINT)
- Compound mechanism: gap detection prompts user to save new knowledge to wiki
- Multi-agent concurrency safety via mandatory write_queue serialisation
- Full references: query-workflow.md, write-workflow.md, examples.md
- Desensitisation enforced before every write proposal
