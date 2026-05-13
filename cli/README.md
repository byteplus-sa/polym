# `super-skill` CLI — design doc

Status: **not implemented**. This file specifies what the CLI must do so
several contributors (and agents) can build it without diverging.

---

## Command surface

```
super-skill install <name>[@<version>]      # install a single skill
super-skill install profile:<name>          # install all skills in a profile (recommended UX)
super-skill update [<name>]                 # update one or all installed skills
super-skill uninstall <name>
super-skill list                            # show available skills + versions
super-skill list --installed
super-skill search <query>
super-skill doctor                          # check deps, env vars, binaries, version skew
super-skill new <name>                      # scaffold a new skill from skills/_template
super-skill publish                         # CI-only; cuts a release and updates registry.yaml
```

## Where things go

| Concept             | Path                                     |
|---------------------|------------------------------------------|
| Source of truth     | this repo's `skills/<name>/`             |
| Registry index      | `registry.yaml` at repo root             |
| Local install dir   | `~/.claude/skills/<name>/`               |
| Local lockfile      | `~/.claude/skills/.super-skill.lock`     |
| Local cache         | `~/.cache/super-skill/`                  |

The lockfile records `{ name, version, installed_at, source_commit }` per
skill so `update` is deterministic and `doctor` can detect drift.

## Install semantics

1. Resolve `<name>` (or all `name`s in a profile) against `registry.yaml`.
2. Resolve `depends_on.skills` transitively. Refuse on conflict (two
   requirements with non-overlapping ranges) with a clear error pointing
   at the offending edges.
3. For each resolved skill: copy `skills/<name>/` → `~/.claude/skills/<name>/`.
   Files outside the skill folder are NEVER copied.
4. Write/update the lockfile.
5. Run `doctor` and report missing binaries / env vars as warnings, not errors.

## Profile install — the default path

`super-skill install profile:sa-mvp` is the canonical onboarding command.
Single-skill `install <name>` is supported but discouraged in docs:
loading too many skills into one Claude session inflates the system prompt
and hurts routing accuracy. Keep profiles small (≤ ~10 skills).

## `doctor` checks

- Every installed skill's `depends_on.binaries` are on `$PATH` at required version
- Every `depends_on.env` is set (value not logged)
- No two installed skills have colliding `triggers`
- No installed skill is at `stage: deprecated` past its `remove_after` date
- Lockfile matches what's actually on disk

## Versioning of the CLI itself

The CLI is versioned separately from any skill. Pin it in
`~/.claude/skills/.super-skill.lock` so `doctor` can warn when a user's
CLI is too old for a skill's manifest schema.

## Implementation notes (non-binding)

- Language: Go or Python single-file script. Bias toward Python for
  contribution accessibility; bias toward Go for static binary distribution.
  Decision deferred until first contributor signs up.
- No network deps beyond pulling this repo (clone or zipball).
- The one-liner installer (`curl … | bash`) only installs the CLI itself;
  the CLI then handles skill installs.
