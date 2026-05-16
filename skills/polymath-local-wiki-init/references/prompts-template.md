# Prompts

Copy-paste these into Claude Code when operating the wiki.
They assume Claude Code has filesystem access to `{{WIKI_ROOT}}`.
All prompts begin by reading `SCHEMA.md` — it defines the page templates, entity kinds, and conventions every operation must honor.

---

## 1. Ingest — static doc / meeting note / any file in `raw/`

Use when you drop a new source into `raw/`.

```
You are maintaining an LLM Wiki at {{WIKI_ROOT}}. Read SCHEMA.md first.

New source(s) to ingest: <filename(s) in raw/>

Steps:

1. Read the source end-to-end. Before writing any files, tell me the 3–5 most
   important takeaways and who/what the source is about (customer? product? internal reference?).

2. Create a source page at wiki/sources/<slug>.md using the Source template.
   Set `kind:` appropriately (doc / meeting / email / etc.).
   Set `customer:` in frontmatter if the source is customer-specific.

3. Identify all entities and concepts:
   - Customers → entity (kind: customer)
   - BytePlus products / features → entity (kind: product)
   - People (customer POCs or internal colleagues) → entity (kind: person)
   - Non-customer orgs (partners, vendors, internal teams) → entity (kind: org)
   - Feedback / feature asks → concept (kind: feedback)
   - Use-cases / pain-points / error codes / generic ideas → concept (appropriate kind)

   For each:
   - If a page exists → UPDATE: add new facts, links, sources. Do not overwrite correct existing content.
   - If no page exists → CREATE using the per-kind template in SCHEMA.md.

4. Maintain relationships bidirectionally:
   - Customer page "Products in play" mirrors Product page "Customers" — update BOTH.
   - Feedback pages list `requesters:` and `product:`; both customer and product pages link into it.

5. Cite sources on every non-trivial claim. Do not invent facts.

6. Contradictions: if this source disagrees with an existing page, do NOT silently pick one.
   Use the "> ⚠️ Contradiction:" convention from SCHEMA.md.

7. Update wiki/index.md — new entries in the right sections, sorted alphabetically.

8. Append an entry to wiki/log.md using the log format.

9. Report back: files created, files updated, stubs introduced, anything uncertain.

Do not touch raw/.
```

---

## 2. Ingest — Lark group chat

Use when a Lark chat represents a customer relationship.

```
You are ingesting a Lark group chat into the LLM Wiki at {{WIKI_ROOT}}. Read SCHEMA.md first.

Chat: <chat name, chat URL, or chat_id>
Date range: <optional — default: last 30 days, or since last ingested per log.md>

Steps:

1. Fetch messages with lark-im. Cover the requested date range.

2. Identify the customer:
   - If the chat name matches a customer name, that is the subject customer.
     Per SCHEMA.md rule 7, record the chat in the Customer page `lark_chat` frontmatter.
   - If ambiguous, stop and ask.

3. Dump the fetched messages as an immutable snapshot to
   raw/chat-<customer-slug>-<today-date>.md (chronological, with sender + timestamp per message).
   Do not edit the snapshot afterwards.

4. Create the source page at wiki/sources/chat-<customer-slug>-<today-date>.md (kind: chat).

5. Create or update the [[customer-slug]] page:
   - Set `lark_chat` if not set.
   - Update Profile if the chat reveals new context.
   - People in the chat → create / update [[person-slug]] pages under "Key contacts".

6. Extract meaningful content — SUMMARIZE, do not dump verbatim:
   - Product mentions → update Product's "Customers" AND Customer's "Products in play" (bidirectional).
   - Feedback / feature asks → create or update [[feedback-slug]]; add customer to `requesters:`.
   - Pain points → create or update [[pain-point-slug]] (kind: pain-point).
   - Substantive threads with cross-entity scope → interaction page under wiki/interactions/.
   - Single-customer chats, escalations, debug sessions → inline bullet on the customer page.

7. Preserve 1–2 verbatim quotes per interaction where wording matters.

8. Cross-mention rule: if another customer is mentioned in passing, do NOT update that customer's page.
   Note "cross-mention: [[other-customer]]" in the log entry flags.

9. Update wiki/index.md and append a log.md entry.

10. Report back.
```

---

## 3. Ingest — Lark Minutes / meeting transcript

Use when you have a meeting transcript (from Lark VC or Lark Minutes).

```
You are ingesting a meeting transcript into the LLM Wiki at {{WIKI_ROOT}}. Read SCHEMA.md first.

Transcript source: <path in raw/ OR a Lark Minutes URL>

If a URL is provided, download the transcript first:
  lark-cli minutes +list   # find the minute token
  lark-cli minutes +get --token <token>   # fetch transcript text

Steps:

1. Save the raw transcript to raw/meeting-<slug>-<YYYY-MM-DD>.md.

2. Create the source page at wiki/sources/meeting-<slug>-<YYYY-MM-DD>.md (kind: meeting).
   Set `customer:` if the meeting is customer-specific.

3. Extract:
   - Key decisions (past tense, declarative — not todos)
   - Participants → create / update person pages
   - Customer / product mentions → update bidirectionally
   - Feedback / feature asks → create / update feedback pages
   - Action items → note in Outcomes as prose, not checkboxes

4. Create an interaction page in wiki/interactions/<YYYY-MM-DD>-<customer>-<topic>.md
   ONLY if multiple entities are involved (otherwise inline on the customer page).

5. Update wiki/index.md and append a log.md entry.

6. Report back.
```

---

## 4. Ingest — current conversation

Use at the end of a session to file what was discussed.

```
You are ingesting the current conversation into the LLM Wiki at {{WIKI_ROOT}}.
Read SCHEMA.md first.

Topic hint (optional): <e.g., "Acme demo prep">

Steps:

1. Review the session. Extract the substantive content — ideas, decisions,
   commitments, facts, customer / product / feedback mentions.
   Skip tool-call noise and scaffolding back-and-forth.

2. Dump a cleaned transcript to raw/conversation-<topic-slug>-<today-date>.md.

3. Create the source page at wiki/sources/conversation-<topic-slug>-<today-date>.md (kind: conversation).

4. Extract entities and concepts exactly as in the generic Ingest flow.

5. If customer-specific: route through the customer page.
   Substantive content → create an interaction page.
   Light content → inline bullet under "Recent interactions".

6. Update wiki/index.md and append a log.md entry.

7. Report back.
```

---

## 5. Query

Use when you want to ask the wiki a question.

```
You are answering from the LLM Wiki at {{WIKI_ROOT}}. Read SCHEMA.md and wiki/index.md first.

Question: <your question>

Steps:

1. Search the wiki for relevant pages. Start from index.md and follow [[wiki-links]].
   - Customer queries: customer page → products-in-play, recent interactions, open feedback.
   - Product queries: product page → customers, open feedback.
   - Topic queries: search concepts/ and entities/ for keyword matches.

2. Answer the question, citing the pages with [[wiki-links]]. Quote sparingly; synthesize.

3. If the wiki can't answer, say so explicitly. Do not use training data without flagging it.

4. If the answer is a useful new synthesis not on any existing page, ask whether to file it:
   - Cross-customer aggregations → relevant feedback or product page.
   - New standalone syntheses → wiki/concepts/.

5. Append a log entry with the query op.
```

Good query patterns for the SA workflow:
- "Which customers have asked for X?"
- "What's the current status of [[customer-slug]]?"
- "What feedback is open on [[product-slug]]?"
- "What did we commit to [[customer-slug]] last week?"
- "Which error codes have hit [[customer-slug]] in production?"
- "Who at [[customer-slug]] is our primary technical contact?"

---

## 6. Lint

Use every ~20 ingests, or on demand.

```
You are running a lint pass over the LLM Wiki at {{WIKI_ROOT}}. Read SCHEMA.md first.

Scan every file under wiki/ and report on:

1. Contradictions — find "> ⚠️ Contradiction:" blocks. Propose resolution or mark "unresolved — need human."

2. Relationship asymmetry — customer↔product or customer↔feedback links that appear on one side but not the other. Propose the missing side.

3. Orphan pages — pages with no incoming [[wiki-links]]. Propose adoption or removal.

4. Stub links — [[wiki-links]] pointing at non-existent pages. Decide: create the stub, or fix the link.

5. Stale status — customer pages where `status` disagrees with the most recent interaction's evidence.

6. Stale feedback — `kind: feedback` pages with `status: open` where the last source is older than 90 days.

7. Duplicate feedback — two feedback pages describing the same ask. Propose a merge.

8. Missing cross-references — pages that mention a concept/customer/product in prose but don't [[link]] it.

9. index.md drift — pages not in index.md, or index entries pointing at missing pages.

Present findings as a checklist. Do not fix anything yet — wait for per-category approval, then execute and append a lint entry to log.md.
```

---

## Tips

- **First ingest** in a fresh wiki: tell the LLM *"This is the first ingest. Seed the directories as needed."*
- **Claude Code** runs everything directly on the filesystem. Just say "Run the Ingest prompt on `raw/foo.md`".
- **Relationship quick-check after any ingest:** did every new customer ↔ product link get noted on *both* pages?
- **Obsidian**: open `wiki/` in Obsidian (`Cmd/Ctrl-G`) to see the knowledge graph as a live network.
- **Daily routine**: schedule a daily-ingest to process your Lark chats and meeting notes automatically.
