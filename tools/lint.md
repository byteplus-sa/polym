# `tools/lint.sh` — spec

Status: **not implemented**. Specification below; implement when CI is wired up.

## What lint must check

For each skill folder under `skills/` (excluding `_template/`):

1. **Manifest validates** against `manifest.schema.yaml`.
2. **Folder name == `manifest.name` == `SKILL.md` frontmatter `name`.**
3. **SKILL.md exists**, has frontmatter, description ≤ 250 chars.
4. **No cross-skill reads.** Grep the skill folder for paths like
   `skills/<other>/` or `../<other>/`. Any hit fails the lint.
5. **CHANGELOG entry exists for the current version.**
6. **`tests/smoke.sh` exists and is executable.**

For each profile under `profiles/`:

7. Validates against `profile.schema.yaml`.
8. All `includes` resolve to existing skills.
9. No included skill is at `stage: experimental`.

Repo-wide:

10. **Trigger collision check.** Build a map `trigger → [skills]` from all
    manifests. If any trigger is claimed by ≥ 2 skills, fail with the list.
11. **CODEOWNERS coverage.** Every `skills/<name>/` path has a CODEOWNERS rule.

## Invocation

```bash
tools/lint.sh                  # lint the whole repo
tools/lint.sh <skill-name>     # lint a single skill (used pre-PR)
```

Exit 0 on success, non-zero with a categorised report on failure.
