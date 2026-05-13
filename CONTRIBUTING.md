# Contributing a skill

This file is the operational guide for **adding or modifying a skill**.
Read `README.md` first for the big picture. If you are an agent, treat this
file as the procedure to follow when the user asks "add a skill that …".

---

## TL;DR for an agent

1. `cp -r skills/_template skills/supper-<name>` — never start from a blank folder.
2. Fill `manifest.yaml` BEFORE `SKILL.md`. The manifest forces you to decide
   ownership, version, dependencies, and what data your skill produces.
3. Write `SKILL.md` to match the manifest. Keep it terse — long-form content
   goes into `references/<topic>.md`, lazy-loaded by the SKILL.
4. Add a `tests/smoke.sh` that exits 0 on a minimal happy-path call.
5. If the skill is user-facing and stable enough for SA, add it to a profile
   under `profiles/`.
6. Open the PR. CODEOWNERS routes review; CI runs lint + smoke.

---

## The manifest in detail

`manifest.yaml` is the single source of truth for governance. The schema is
`manifest.schema.yaml`. Below is each field with the reasoning so you can
make judgement calls.

```yaml
name: supper-meeting-summary        # kebab-case, globally unique, must start with supper-
version: 0.1.0                      # semver, independent of other skills
stage: experimental                 # experimental | beta | stable | deprecated
owners:                             # at least one; emails or @handles
  - bojie@
description_for_install: |
  Summarises a Lark meeting and writes a structured signal into supper-sa-wiki.

depends_on:
  skills:                           # other skills in THIS repo
    - supper-sa-wiki: ">=0.2.0 <1.0.0"
    - lark-minutes: "*"
  binaries:                         # external CLIs the skill shells out to
    - lark-cli: ">=1.0.20"
  env:                              # required env vars (names only, never values)
    - LARK_USER_TOKEN

io_contract:                        # what data this skill reads / writes
  reads:
    - lark-minutes                  # logical sources, not physical paths
  writes:
    - target: supper-sa-wiki/write_queue
      schema: core/signal-envelope.schema.json
      signal_type: meeting

triggers:                           # the phrases that should route to this skill
  - "会议摘要"
  - "meeting summary"
  - "整理会议纪要"

deprecates: []                      # names of skills this one replaces
```

### Field-by-field judgement notes

- **`name`** — must match the folder name and the SKILL.md frontmatter `name`.
  Pick something a user might type. Don't prefix with team names.
- **`version`** — start at `0.1.0`. Bump rules:
  - patch: doc-only or internal refactor
  - minor: new optional capability, no breaking change
  - major: removed/renamed flag, changed output schema, removed trigger
- **`stage`** — be honest. `experimental` is fine; it just means profiles can't pin you yet.
  Moving to `stable` is a deliberate one-way door (deprecation window kicks in).
- **`owners`** — at least one human who will answer questions. Also add the path
  to `CODEOWNERS` so PR review is automatic.
- **`depends_on.skills`** — only list skills you actually call. Listing more
  inflates install size and breaks profile resolution.
- **`io_contract.writes`** — if your skill produces customer data, it MUST point
  at a schema in `core/`. Free-form writes are not allowed; that is what kept
  earlier wiki initiatives from compounding.
- **`triggers`** — used by lint to detect collisions across skills. If you
  collide with an existing skill's triggers, you must either (a) rename your
  triggers to be more specific, or (b) deprecate the older skill (with its
  owner's sign-off).

---

## SKILL.md vs manifest.yaml

| Concern                                  | Lives in        |
|------------------------------------------|-----------------|
| Frontmatter `name`, `description` for Claude runtime | `SKILL.md`     |
| Body of instructions for Claude          | `SKILL.md`     |
| Long-form references                     | `references/*.md` (linked from SKILL.md) |
| Version, owners, deps, contracts         | `manifest.yaml` |
| Trigger word list for lint               | `manifest.yaml` |
| Stage and deprecation info               | `manifest.yaml` |

Keep `SKILL.md` description ≤ 250 chars. Long descriptions are the #1 reason
Claude misroutes between skills.

---

## Cross-skill calls: how to depend on another skill

You must NOT `Read` files inside another skill's folder. Two legal patterns:

1. **CLI surface.** If skill B exposes a CLI (e.g. `lark-cli`, or a script
   it installs into `$PATH`), shell out to it from your skill. Pin the
   binary version in `depends_on.binaries`.
2. **Shared schema.** If you and skill B exchange data, define the shape in
   `core/<topic>.schema.json` and reference it in both manifests'
   `io_contract`. Skill B reads from a known queue/table; you write to it.

Why: each skill has to install standalone. A user might install `supper-meeting-summary`
without `supper-sa-wiki`, and the CLI should detect missing deps and warn, not crash
on a dangling relative path.

---

## Writing the smoke test

`tests/smoke.sh` runs in CI on every PR that touches the skill. It must:
- Exit `0` on success, non-zero on failure
- Run in under 60 seconds
- Not require live external services with secrets (use mocks / `--dry-run`)
- Validate at minimum: the manifest parses, the SKILL.md exists, and the
  skill's primary CLI invocation does not error on `--help` or `--dry-run`.

Template provided in `skills/_template/tests/smoke.sh`.

---

## Deprecating a skill

1. Set `stage: deprecated` in `manifest.yaml`.
2. Add a `deprecation:` block:
   ```yaml
   deprecation:
     since: 2026-05-12
     remove_after: 2026-08-12         # 90 days minimum
     replaced_by: new-skill-name      # optional
     migration: |
       Short note on how to migrate callers.
   ```
3. Remove the skill from all profiles in the SAME PR (or open a follow-up PR
   linked from the CHANGELOG).
4. After `remove_after`, an owner deletes the folder. CI blocks the delete
   if any profile still references it.

---

## PR checklist (paste into PR description)

- [ ] `manifest.yaml` validates (`tools/lint.sh <skill>`)
- [ ] `SKILL.md` description ≤ 250 chars, matches manifest `name`
- [ ] No `Read` / `source` / `import` of other skills' files
- [ ] Triggers don't collide with existing skills (lint passes)
- [ ] `CHANGELOG.md` entry added
- [ ] `tests/smoke.sh` passes locally
- [ ] If user-facing & ≥ beta: added to at least one profile, or noted why not
- [ ] If contract change: bumped major, migration note in CHANGELOG
