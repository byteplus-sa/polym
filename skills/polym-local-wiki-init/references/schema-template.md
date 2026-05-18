# Wiki Schema

Conventions the LLM follows when reading and writing this wiki.
This is the **schema layer** from Karpathy's pattern: it tells the LLM how the wiki is structured.

Tuned for a **BytePlus Sales Engineer workflow** — the first-class entities are **customers**, **products**, and the **relationships between them**. Sources include static documents, Lark group chats, meetings, and transcripts of prior AI conversations.

---

## Directory layout

- `raw/` — immutable. Source documents, chat snapshots, conversation transcripts, meeting notes. The LLM reads but never writes here.
- `wiki/` — LLM-owned. Everything under here can be created, edited, or deleted by the LLM.
  - `wiki/index.md` — catalog of every page.
  - `wiki/log.md` — append-only activity log.
  - `wiki/entities/` — split by kind:
    - `entities/customers/` — `kind: customer`
    - `entities/people/` — `kind: person`
    - `entities/products/` — `kind: product`
    - `entities/orgs/` — `kind: org`
  - `wiki/concepts/` — flat. `kind:` selects the template.
  - `wiki/interactions/` — per-touchpoint pages (meetings, calls, substantial chat threads, demos).
  - `wiki/sources/` — one page per item in `raw/`.

## Entity kinds

| `kind` | Represents | Examples |
|---|---|---|
| `customer` | A customer organization | Acme Corp |
| `product` | A BytePlus product or feature | Seedance 2.0, Seedream, Asset Library |
| `person` | A human — customer POC or internal colleague | Jane Doe (Acme), John Smith (BytePlus) |
| `org` | A non-customer organization | Sony Music, a partner, a vendor, an internal team |
| `model` | A specific AI model when the model itself is the subject | a specific VLM |
| `paper` | A research paper | Attention Is All You Need |

## Concept kinds

| `kind` | Represents |
|---|---|
| `concept` | Generic idea / method / technique |
| `error-code` | A named API error identifier |
| `feedback` | A specific customer ask — tracked across requesters |
| `use-case` | A customer scenario or workload |
| `pain-point` | A friction / gap reported by customers |
| `integration-pattern` | A recurring deployment / integration shape |

## Source kinds

| `kind` | Represents | `raw/` filename convention |
|---|---|---|
| `doc` | Static document — PDF, article, Lark doc export | `doc-<slug>-<YYYY-MM-DD>.md` |
| `chat` | Lark group chat snapshot | `chat-<slug>-<YYYY-MM-DD>.md` |
| `meeting` | Meeting notes / Lark Minutes | `meeting-<slug>-<YYYY-MM-DD>.md` |
| `conversation` | Transcript of a prior AI conversation | `conversation-<slug>-<YYYY-MM-DD>.md` |
| `email` | Email thread | `email-<slug>-<YYYY-MM-DD>.md` |

Snapshots are **immutable**. Re-ingesting the same chat on a later date produces a **new file** with a new date suffix — old snapshots are preserved.

---

## File naming

- Lowercase kebab-case for entity/concept pages: `acme-corp.md`, `seedance-2.md`, `feedback-seedance-lyric-fp-dialogue.md`.
- Dates **only** in interaction filenames and source filenames: `2026-04-21-acme-demo-followup.md`.
- Filename matches the page title in kebab-case.
- **Forbidden characters in any NAME** (filename, H1 title, wiki-link target, YAML alias): `:` `.` `/` `\`.
  - Version numbers: drop the dot. `Seedance 2.0` → page name `Seedance 2` (file `seedance-2.md`). The full marketing string can still appear in **prose**.
  - Namespaced identifiers with dots: treat the dot as a word separator.
  - Slashes in titles: rewrite using " and " or a dash.

## Wiki-links

**Hard rule: every wiki-link target is the filename slug. Never use a display name, alias, or H1 as the target.** Display names go after a pipe `|`.

Canonical form:
```
[[acme-corp|Acme Corp]] is evaluating [[seedance-2|Seedance 2]]; they hit
[[output-audio-content-sensitive-detected|OutputAudioContentSensitiveDetected]]
```

Why: Obsidian's alias resolver can be inconsistent for targets with parentheses, mixed scripts, or spaces mixed with punctuation. Slug-form targets bypass the resolver entirely, producing exactly one node per file.

- Target (inside `[[ ]]` before any `|`) must equal a filename without `.md`. Lowercase, kebab-case.
- Display label (after `|`) is free-form and carries any characters (Chinese, parens, punctuation).
- If no display is needed, drop the pipe: `[[seedance-moderation-onepager]]`.
- Source pages are referenced by their slug: `[[doc-acme-demo-2026-04-18]]`. Do NOT use a `source:` prefix.
- `aliases:` in frontmatter is for Obsidian search only — **not** for link resolution.

Unresolved `[[slug]]` = **stub**. Lint tracks them. Next ingest touching the concept creates it.

### Wiki-links in YAML frontmatter — critical rule

YAML parses `products: [[Seedance 2]]` as a nested array. **Every wiki-link in frontmatter MUST use:**

1. **Filename slug** (not display name).
2. **Double-quoted string**.
3. **Proper array syntax** for multiple values.

✅ Correct:
```yaml
products: ["[[seedance-2]]"]
customers: ["[[acme-corp]]", "[[betacorp]]"]
```

❌ Wrong:
```yaml
products: [[Seedance 2]]
customers: [[Acme]], [[BetaCorp]]
```

---

## Relationships

**Customer ↔ Product is the load-bearing relationship of this wiki.** Every relationship is expressed **bidirectionally** — both sides link, both sides note it inline.

### On a customer page

```markdown
## Products in play
- [[seedance-2|Seedance 2]] — **POC** · use case: [[short-form-ad-generation|Short-form ad generation]] · since: 2026-03
- [[seedream|Seedream]] — **evaluating** · use case: [[product-photography|Product photography]]
```

### On a product page

```markdown
## Customers
- [[acme-corp|Acme Corp]] — **POC** · use case: [[short-form-ad-generation|Short-form ad generation]] · since: 2026-03
- [[betacorp|BetaCo]] — **live** · use case: [[influencer-style-content|Influencer-style content]]
```

**Status vocabulary:** `lead` → `evaluating` → `poc` → `live` · `churned` (terminal).

Feedback is a **separate first-class page** (`kind: feedback`) so it aggregates across customers.

---

## Page templates

### Customer (`wiki/entities/customers/<slug>.md`)

```markdown
---
type: entity
kind: customer
aliases: [zh name, brand name]
status: lead | evaluating | poc | live | churned
region: CN | APAC | EMEA | NA | other
industry: ...
account_owner: ...
lark_chat: <chat name or id, if any>
---

# <Customer Name>

**One-liner: who they are and what they care about.**

## Profile
Size, industry, region, anything distinctive.

## Products in play
- [[product-slug|Product Name]] — **status** · use case: [[use-case-slug]] · since: YYYY-MM

## Key contacts
- [[person-slug|Person Name]] — role · primary POC.

## Recent interactions
- [[YYYY-MM-DD-customer-topic]] — short hook.
- YYYY-MM-DD · quick chat message, no dedicated page _(inline-only, too short for a page)_.

## Open feedback / pain points
- [[feedback-slug]] — one-liner.

## Sources
- [[source-slug]]
```

### Product (`wiki/entities/products/<slug>.md`)

```markdown
---
type: entity
kind: product
aliases: [...]
---

# <Product>

**One-line definition.**

## Summary
2–4 sentences.

## Key features
- ...

## Customers
- [[customer-slug|Customer Name]] — **status** · use case: [[use-case-slug]] · since: YYYY-MM

## Open feedback
- [[feedback-slug]] — requester, short ask.

## Known issues / error codes
- [[error-code-slug]] — short description.

## Related
- [[concept-slug]] — how it relates.

## Sources
- [[source-slug]]
```

### Person (`wiki/entities/people/<slug>.md`)

```markdown
---
type: entity
kind: person
aliases: [...]
affiliation: "[[customer-slug|Customer X]]"
role: ...
contacts:
  email: ...
  lark: ...
---

# <Name>

**One-line who and role.**

## Interactions
- [[YYYY-MM-DD-topic]]

## Notes
Durable context — preferences, technical background, interests.

## Sources
- [[source-slug]]
```

### Feedback (`wiki/concepts/feedback-<slug>.md`)

```markdown
---
type: concept
kind: feedback
product: "[[product-slug]]"
requesters: ["[[customer-a]]", "[[customer-b]]"]
status: open | passed-to-pm | in-progress | shipped | wontfix
priority: P0 | P1 | P2 | P3
---

# Feedback: <short title>

**One-line summary of the ask.**

## The ask
What exactly is requested.

## Why
Customer reasoning. Quote when possible.

## Internal status
- Passed to: <person/team> on <date>.
- Current state: ...

## Sources
- [[source-slug]] — location / quote.
```

### Interaction (`wiki/interactions/<YYYY-MM-DD>-<customer-slug>-<topic>.md`)

> **When to create an interaction page vs. inline on the customer page:**
> - Create a **separate page** only when the event is referenced by **multiple entity pages simultaneously** (cross-customer incidents, product launches, policy announcements).
> - Log **inline** as a dated bullet under `## Recent interactions` for all single-customer events, no matter how substantial.

```markdown
---
type: interaction
channel: lark-chat | meeting | call | email | demo
customer: "[[customer-slug]]"
date: YYYY-MM-DD
participants: ["[[person-a]]", "[[person-b]]"]
---

# <YYYY-MM-DD>-<customer-slug>-<topic>

## Summary
2–3 sentences of what happened.

## Key points
- Point with [[link]].

## Outcomes
What was decided or what landed. Past tense. No open-ended todos.

## Quotes
> "..." — <speaker>

## Pages touched
- [[customer-slug]] — updated products-in-play / recent interactions.
- [[product-slug]] — logged new [[feedback-slug]].

## Sources
- [[source-slug]]
```

### Generic concept / use-case / pain-point / error-code / integration-pattern

```markdown
---
type: concept
kind: concept | use-case | pain-point | error-code | integration-pattern
aliases: [...]
---

# <Name>

**One-line definition.**

## Summary
2–4 sentences.

## <Section appropriate to kind>
...

## Related
- [[page-slug]] — relationship.

## Sources
- [[source-slug]]
```

### Source (`wiki/sources/<slug>.md`)

```markdown
---
type: source
kind: doc | chat | meeting | conversation | email
raw_path: raw/<filename>
customer: "[[customer-slug]]"   # optional
date: YYYY-MM-DD
url: https://...                 # original URL (strip disposable_login_token)
---

# <Source title>

## TL;DR
3–5 bullets.

## Extracted pages
- [[page-a]]
- [[page-b]]

## Verbatim quotes worth keeping
> Quote. (speaker, date)
```

---

## index.md format

```markdown
# Index

## Customers
- [[customer-slug|Customer Name]] — one-line hook.

## Products
- [[product-slug|Product Name]] — one-line hook.

## People
- [[person-slug|Person Name]] — role, affiliation.

## Organizations
- [[org-slug]] — one-line hook.

## Feedback
- [[feedback-slug]] — status · product · one-liner.

## Concepts
- [[concept-slug]] — one-line hook.

## Interactions (recent)
- [[YYYY-MM-DD-subject-slug]]

## Sources
- [[source-slug]] — kind · one-line hook.
```

Updated on every ingest. Sorted alphabetically within each section, except **Interactions** (reverse-chronological, last 10–20 only — full list lives in `log.md`).

## log.md format

```markdown
## [YYYY-MM-DD] ingest | chat-<customer> (YYYY-MM-DD .. YYYY-MM-DD)
- Created: [[person-a]], [[YYYY-MM-DD-topic]], [[feedback-slug]]
- Updated: [[customer-x]], [[product-y]]
- Stubs: [[pending-page]]
- Flagged: none
```

Op types: `init`, `ingest`, `daily-ingest`, `query`, `lint`, `schema-change`.

## Contradictions

When two sources disagree, don't silently pick one. Inline:

```markdown
## Pricing
- [[acme-call-2026-04-18]] says $X/month.
- > ⚠️ Contradiction: [[acme-email-2026-04-20]] says $Y/month. Email is newer; check which is current.
```

Lint surfaces unresolved contradictions.

---

## Rules

1. **Raw is immutable.** Never edit `raw/`.
2. **Cite sources.** Every non-trivial claim links to a source page by slug.
3. **Bidirectional relationships.** If A ↔ B is meaningful, both sides note it.
4. **Feedback is shared.** Use a dedicated `feedback-*` page as soon as one ask might recur.
5. **Absolute dates.** No "yesterday", "last week", "recently".
6. **Snapshot sources.** Re-ingesting a chat produces a new dated `raw/` file; old snapshots stay.
7. **Lark chat named after a customer = that customer's primary chat.** Store in `lark_chat` frontmatter.
8. **Don't cross-pollinate.** A Lark chat's content updates *that* customer's pages only; flag cross-mentions.
9. **Naming charset.** Filenames, H1 titles, wiki-link targets, and YAML aliases MUST NOT contain `:` `.` `/` `\`.
10. **Knowledge, not todos.** Wiki pages record *what happened, what was decided, what is true now* — not open-ended personal todos. No `- [ ]` checkboxes on wiki pages.
