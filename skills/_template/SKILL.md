---
name: TEMPLATE-RENAME-ME
description: One sentence, ≤ 250 chars, starting with a verb. Describe what the skill does AND when Claude should pick it. Include 2-3 trigger phrases inline.
---

# TEMPLATE-RENAME-ME

> Replace this entire file. Keep it terse. Long-form content goes into `references/`.

## When to use this skill
- (list the user-facing situations that should route here)

## When NOT to use this skill
- (list adjacent skills and why this one isn't the right pick)

## Prerequisites
- Authenticated via `lark-cli auth login --as user` (or whatever your skill needs)
- Required env vars: …

## Quickstart
```bash
# the most common invocation
…
```

## References (lazy-loaded)
- `references/<topic>.md` — read this when …
- `references/<another>.md` — read this when …

## IO contract (must match manifest.yaml)
- Reads: …
- Writes: signal envelopes of type `…` to `polymath-sa-wiki/write_queue`
