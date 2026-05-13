---
name: local-wiki-init
version: 0.1.0
description: "Initialize a local LLM-maintained wiki for an SA. Creates the full directory structure, SCHEMA.md, PROMPTS.md, and starter wiki pages. Invoke with: 'set up my local wiki', 'init local wiki', '初始化本地 wiki', 'create my SA wiki'."
metadata:
  requires:
    bins: []
---

# local-wiki-init — SA Local Wiki Setup

Karpathy-pattern LLM wiki, tuned for the BytePlus SA workflow.
**One invocation → a fully structured, ready-to-use local wiki.**

## When to use this skill

Triggers (any of these):
- "帮我初始化本地 wiki"
- "set up my local wiki"
- "create my SA wiki"
- "init local wiki"
- "我想建一个本地知识库"
- User mentions wanting a personal wiki to track customers / products

## What you will create

```
<wiki_root>/
├── README.md          ← orientation + the three operations
├── SCHEMA.md          ← structure, templates, conventions (SA-tuned)
├── PROMPTS.md         ← ready-to-paste Ingest / Query / Lint prompts
├── raw/               ← immutable source material (docs, chat exports, meeting notes)
│   └── .gitkeep
├── drafts/            ← work-in-progress before filing into wiki/
│   └── .gitkeep
├── minutes/           ← Lark Minutes transcripts (auto-downloaded)
│   └── .gitkeep
└── wiki/
    ├── index.md       ← master catalog of every page
    ├── log.md         ← append-only activity log
    ├── entities/
    │   ├── customers/ ← one .md per customer org
    │   ├── products/  ← one .md per BytePlus product
    │   ├── people/    ← one .md per person
    │   └── orgs/      ← non-customer orgs (partners, vendors, internal teams)
    ├── concepts/      ← feedback, use-cases, pain-points, error-codes, integration-patterns
    ├── interactions/  ← cross-entity meetings / events (see SCHEMA §interaction)
    └── sources/       ← one .md per item in raw/
```

## Execution steps

### Step 1 — Determine location

Ask the user:

> "Your local wiki will be created as a directory on your machine.
> Where do you want it? (press Enter for `~/sa-wiki`)"

Accept any absolute or `~`-prefixed path. Expand `~` to the actual home dir.
If the directory already exists and is non-empty, warn and ask:
> "That directory already exists and has content. Continue anyway? (y/N)"

Store the confirmed path as `WIKI_ROOT`.

### Step 2 — Create directory structure

```bash
mkdir -p "$WIKI_ROOT/raw"
mkdir -p "$WIKI_ROOT/drafts"
mkdir -p "$WIKI_ROOT/minutes"
mkdir -p "$WIKI_ROOT/wiki/entities/customers"
mkdir -p "$WIKI_ROOT/wiki/entities/products"
mkdir -p "$WIKI_ROOT/wiki/entities/people"
mkdir -p "$WIKI_ROOT/wiki/entities/orgs"
mkdir -p "$WIKI_ROOT/wiki/concepts"
mkdir -p "$WIKI_ROOT/wiki/interactions"
mkdir -p "$WIKI_ROOT/wiki/sources"
touch "$WIKI_ROOT/raw/.gitkeep"
touch "$WIKI_ROOT/drafts/.gitkeep"
touch "$WIKI_ROOT/minutes/.gitkeep"
touch "$WIKI_ROOT/wiki/entities/customers/.gitkeep"
touch "$WIKI_ROOT/wiki/entities/products/.gitkeep"
touch "$WIKI_ROOT/wiki/entities/people/.gitkeep"
touch "$WIKI_ROOT/wiki/entities/orgs/.gitkeep"
touch "$WIKI_ROOT/wiki/concepts/.gitkeep"
touch "$WIKI_ROOT/wiki/interactions/.gitkeep"
touch "$WIKI_ROOT/wiki/sources/.gitkeep"
```

### Step 3 — Write the core files

Read each reference file and write it to the wiki root, substituting `{{WIKI_ROOT}}` with the actual path:

| Source (in this skill's references/) | Destination |
|---|---|
| `references/readme-template.md` | `$WIKI_ROOT/README.md` |
| `references/schema-template.md` | `$WIKI_ROOT/SCHEMA.md` |
| `references/prompts-template.md` | `$WIKI_ROOT/PROMPTS.md` |

### Step 4 — Create starter wiki files

**`$WIKI_ROOT/wiki/index.md`**:
```markdown
# Index

_Updated by the LLM on every ingest. Do not hand-edit._

## Customers
_(none yet)_

## Products
_(none yet)_

## People
_(none yet)_

## Organizations
_(none yet)_

## Feedback
_(none yet)_

## Concepts
_(none yet)_

## Interactions (recent)
_(none yet)_

## Sources
_(none yet)_
```

**`$WIKI_ROOT/wiki/log.md`** — seed with the init event:
```markdown
# Log

_Append-only. Do not edit past entries._

---

## [{{TODAY}}] init | local-wiki-init skill
- Created: directory structure, README.md, SCHEMA.md, PROMPTS.md, wiki/index.md, wiki/log.md
- Root: {{WIKI_ROOT}}
```
Replace `{{TODAY}}` with `YYYY-MM-DD` (today's date) and `{{WIKI_ROOT}}` with the real path.

### Step 5 — Post-setup report

Print a clear summary:

```
✅  Local wiki created at: <path>

Next steps:
  1. Drop your first source into raw/  (a meeting note, a doc export, a chat snapshot)
  2. Open PROMPTS.md and run the "Ingest" prompt against that file
  3. Open wiki/ in Obsidian to see the knowledge graph (Cmd-G)

Core files:
  README.md    — orientation
  SCHEMA.md    — full structure & page templates
  PROMPTS.md   — ready-to-use Ingest / Query / Lint prompts

The wiki is entirely local and under your control.
```

## Important constraints

- **Never touch `raw/`** during ingest — it is immutable. The LLM reads but never writes there.
- **Only write inside `wiki/`** when operating the wiki after init.
- **Absolute dates** only — no "yesterday", "last week".
- **Do not create CLAUDE.md** inside the wiki directory unless the user explicitly asks — the prompts in PROMPTS.md are standalone and don't require a CLAUDE.md.
