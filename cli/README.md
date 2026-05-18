# `polym` CLI

Status: **implemented as a bash CLI** in [`cli/polym`](polym).

The CLI has two jobs:

1. Install/update skills on a user's machine.
2. Help contributors maintain versions and publish skill changes back to GitHub.

---

## Command Surface

```bash
polym install [all]              # install all skills
polym install profile:<name>     # install a named profile bundle
polym install <skill-name>       # install one skill

polym self-update                # update this repo + relink CLI only
polym update [target]            # self-update + reinstall installed skills
polym sync [target]              # alias for update

polym list                       # show available skills
polym list --installed           # show local installed versions
polym doctor                     # check deps/env vars for installed skills

polym new <name>                 # scaffold; auto-prefixes to polym-<name>
polym bump <name> <version>      # update SKILL.md + manifest version fields
polym publish -m "<message>"     # lint, build registry, commit, rebase, push
```

`target` for `update/sync` can be:

```bash
installed          # default: refresh what is already installed
all                # install every skill in the repo
profile:sa-mvp     # install a profile
polym-meeting-summary    # install one skill
```

---

## Update Semantics

### CLI/catalog update

```bash
polym self-update
```

This runs:

```bash
git pull --ff-only
ln -sf <repo>/cli/polym ~/.local/bin/polym
```

Because the installer symlinks the CLI into `~/.local/bin`, pulling this repo updates the CLI for the next invocation.

### Skill update

```bash
polym update
```

This does:

1. `self-update`
2. Read `~/.claude/skills/.polym.lock`
3. Reinstall the already-installed skills from the updated catalog

This preserves the user's install selection. A profile install does not accidentally become "install every skill".

---

## Contributor Publishing

Normal flow:

```bash
polym bump my-skill 0.2.0
# edit SKILL.md + CHANGELOG.md
polym publish -m "feat(my-skill): add new workflow"
```

`publish` runs:

1. `git pull --rebase --autostash`
2. `bash tools/lint.sh`
3. `bash tools/build-registry.sh`
4. `git add -A`
5. `git commit -m ...`
6. `git push`

If GitHub's registry auto-build races with the local push and only `registry.yaml` conflicts, `publish` rebuilds the registry and continues the rebase automatically.

---

## Where Things Go

| Concept | Path |
|---|---|
| Source of truth | this repo's `skills/<name>/` |
| Registry index | `registry.yaml` at repo root |
| Local install dir | `~/.claude/skills/<name>/` |
| Local lockfile | `~/.claude/skills/.polym.lock` |
| CLI symlink | `~/.local/bin/polym` |

The lockfile records `{ name, version, installed_at, source }` per skill.
