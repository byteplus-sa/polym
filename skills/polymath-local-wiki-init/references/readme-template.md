# SA Local Wiki

A personal, LLM-maintained knowledge base for BytePlus SA work.
Inspired by [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

Wiki root: `{{WIKI_ROOT}}`

## The idea

Instead of running RAG over raw documents every time, the LLM **compiles** your sources into a persistent, cross-linked markdown wiki. The wiki grows, gets cleaned, and compounds over time.

- **You** source material (docs, chat exports, meeting notes), ask questions, steer.
- **The LLM** summarizes, cross-references, files entities, and maintains consistency.

First-class entities for this wiki: **customers**, **products**, and the relationships between them.

## Layout

```
{{WIKI_ROOT}}/
├── README.md        ← you are here
├── SCHEMA.md        ← structure, conventions, page templates
├── PROMPTS.md       ← ready-to-paste Ingest / Query / Lint prompts
├── raw/             ← immutable source material (docs, chat exports, meeting notes)
├── drafts/          ← work-in-progress before filing into wiki/
├── minutes/         ← Lark Minutes transcripts
└── wiki/
    ├── index.md     ← catalog of every page
    ├── log.md       ← append-only activity log
    ├── entities/    ← customers / products / people / orgs
    ├── concepts/    ← feedback, use-cases, pain-points, error-codes
    ├── interactions/← cross-entity events (meetings, launches, incidents)
    └── sources/     ← one page per raw/ document
```

## Getting started

1. **Drop a source into `raw/`.** A meeting note, a doc export, a Lark chat snapshot — anything.
2. **Run the Ingest prompt** from [PROMPTS.md](PROMPTS.md), pointing it at the new file.
   The LLM will create/update entity and concept pages in `wiki/` and append to `log.md`.
3. **Query** the wiki for anything. If the answer is a useful new synthesis, file it back.
4. **Lint** every ~20 ingests to catch contradictions, orphans, and stale claims.

## The three operations

| Op | When | What it does |
|---|---|---|
| **Ingest** | New source lands in `raw/` | Read it, summarize, create/update entity & concept pages, update index, log it |
| **Query** | You have a question | Search relevant pages, answer with citations, optionally file new synthesis pages |
| **Lint** | Every ~20 ingests, or on demand | Scan for contradictions, orphan pages, missing links, stale claims |

See [SCHEMA.md](SCHEMA.md) for structure details and [PROMPTS.md](PROMPTS.md) for the actual prompts.

## Tips

- Open `wiki/` in [Obsidian](https://obsidian.md) to view the knowledge graph (`Cmd/Ctrl-G`). `[[wiki-links]]` render as a navigable network.
- Keep `raw/` read-only. The LLM never edits source material.
- If the LLM and a source disagree, flag it with `> ⚠️ Contradiction:` — don't silently resolve.
- Dates in `log.md` are absolute (YYYY-MM-DD), never "yesterday."
- Relationship quick-check after any ingest: did every new customer ↔ product link get noted on **both** pages?
