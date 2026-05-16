# `polymath` CLI

Status: **implemented as a bash CLI** in [`cli/polymath`](polymath).

The CLI has two jobs:

1. Install/update skills on a user's machine.
2. Help contributors maintain versions and publish skill changes back to GitHub.

---

## Command Surface

```bash
polymath install [all]              # install all skills
polymath install profile:<name>     # install a named profile bundle
polymath install <skill-name>       # install one skill

polymath self-update                # update this repo + relink CLI only
polymath update [target]            # self-update + reinstall installed skills
polymath sync [target]              # alias for update

polymath list                       # show available skills
polymath list --installed           # show local installed versions
polymath doctor                     # check deps/env vars for installed skills

polymath new <name>                 # scaffold; auto-prefixes to polymath-<name>
polymath bump <name> <version>      # update SKILL.md + manifest version fields
polymath publish -m "<message>"     # lint, build registry, commit, rebase, push
```

`target` for `update/sync` can be:

```bash
installed          # default: refresh what is already installed
all                # install every skill in the repo
profile:sa-mvp     # install a profile
polymath-meeting-summary    # install one skill
```

---

## Update Semantics

### CLI/catalog update

```bash
polymath self-update
```

This runs:

```bash
git pull --ff-only
ln -sf <repo>/cli/polymath ~/.local/bin/polymath
```

Because the installer symlinks the CLI into `~/.local/bin`, pulling this repo updates the CLI for the next invocation.

### Skill update

```bash
polymath update
```

This does:

1. `self-update`
2. Read `~/.claude/skills/.polymath.lock`
3. Reinstall the already-installed skills from the updated catalog

This preserves the user's install selection. A profile install does not accidentally become "install every skill".

---

## Contributor Publishing

Normal flow:

```bash
polymath bump my-skill 0.2.0
# edit SKILL.md + CHANGELOG.md
polymath publish -m "feat(my-skill): add new workflow"
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
| Local lockfile | `~/.claude/skills/.polymath.lock` |
| CLI symlink | `~/.local/bin/polymath` |

The lockfile records `{ name, version, installed_at, source }` per skill.
