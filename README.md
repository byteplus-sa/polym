# super-skill

> **For contributors / agents:** This README is the routing manual. Read it top-to-bottom once.
> **For new SA members:** See the quickstart below — two commands and you're set.

`super-skill` is a curated, versioned collection of Claude Code skills for the SA Native AI program.
It is **not** a single skill — it is the package manager + registry + contribution workflow
that lets many people (and many agents) ship skills into a shared, governed catalog.

## Quickstart (new SA member)

> **Access first:** Ask the repo owner to add you as a GitHub collaborator before running any install command.

Pick whichever option matches your setup:

### Option A — gh CLI (recommended)

```bash
# One-time setup (if you don't have gh yet)
brew install gh && gh auth login

# Install
gh repo clone Carey8175/sa-super-skill /tmp/sa-super-skill \
  && /tmp/sa-super-skill/install.sh
```

### Option B — SSH (if you have an SSH key on GitHub)

```bash
git clone git@github.com:Carey8175/sa-super-skill.git /tmp/sa-super-skill \
  && /tmp/sa-super-skill/install.sh
```

### Option C — GitHub Personal Access Token (no special CLI needed)

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens) → **Generate new token (classic)**
2. Select scope: **repo** (read-only is enough)
3. Copy the token (starts with `ghp_`)

```bash
# Replace ghp_xxxx with your actual token
GITHUB_TOKEN=ghp_xxxx bash <(curl -fsSL \
  -H "Authorization: token ghp_xxxx" \
  https://raw.githubusercontent.com/Carey8175/sa-super-skill/main/install.sh)
```

---

After any install option, if `~/.local/bin` is not in your PATH:

```bash
# Add to ~/.zshrc (run once)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc

# Verify
super-skill list
super-skill doctor
```

Once installed, open Claude Code and say **"help"** for an interactive guide.

## Update

```bash
super-skill self-update     # update the CLI/catalog repo only
super-skill update          # update CLI + refresh currently installed skills
super-skill update profile:sa-mvp
```

For contributors pushing local skill changes back to GitHub:

```bash
super-skill bump <skill-name> <new-version>
# edit SKILL.md + CHANGELOG.md
super-skill publish -m "feat(<skill-name>): describe the change"
```

Contributor flow (probably you, if you are reading this):

```
read this file → read CONTRIBUTING.md → super-skill new <name> → edit → open PR
```

---

## If you are an agent, do this in order

1. **Identify the task.** Map the user's request to one of:
   - `A` — author a NEW skill (most common)
   - `B` — edit an EXISTING skill in `skills/<name>/`
   - `C` — add or edit a PROFILE in `profiles/`
   - `D` — change the SHARED CONTRACT in `core/` (rare; needs 2 owners)
   - `E` — work on the CLI in `cli/`
2. **Read the matching doc**:
   - `A` or `B` → `CONTRIBUTING.md` (mandatory; covers manifest, IO contract, lint rules)
   - `C` → `profile.schema.yaml` + `profiles/sa-mvp.yaml`
   - `D` → `core/signal-envelope.schema.json` + ping CODEOWNERS for `core/`
   - `E` → `cli/README.md`
3. **Never reach across skills.** Skill `foo` MUST NOT `Read skills/bar/references/*`.
   Cross-skill calls go through the CLI surface of the other skill (e.g. `lark-cli`, `super-skill`),
   or through a shared schema in `core/`. See "Hard rules" below.
4. **Never bloat the catalog with a skill that has no owner, no version, or no `stage`.**
   The CI will block it. Fill the manifest first; write the SKILL.md second.

---

## Folder map

```
super-skill/
├─ README.md                    ← you are here (agent-facing entry)
├─ CONTRIBUTING.md              ← how to add or edit a skill
├─ manifest.schema.yaml         ← JSON-Schema for skills/*/manifest.yaml
├─ profile.schema.yaml          ← JSON-Schema for profiles/*.yaml
├─ registry.yaml                ← AUTO-generated index, do not hand-edit
├─ CODEOWNERS                   ← path → owner mapping, enforced on PR
├─ skills/
│  ├─ _template/                ← copy this to start a new skill
│  └─ <skill-name>/
│     ├─ SKILL.md               ← runtime: loaded into Claude's context
│     ├─ manifest.yaml          ← governance: version, owners, deps, contracts
│     ├─ CHANGELOG.md
│     ├─ references/            ← long-form docs, lazily loaded by SKILL.md
│     ├─ scripts/               ← executable helpers
│     └─ tests/smoke.sh         ← one-line smoke test, run in CI
├─ profiles/
│  └─ sa-mvp.yaml               ← curated bundles users install by name
├─ core/
│  └─ signal-envelope.schema.json  ← shared data contract between skills
├─ cli/                         ← source of the `super-skill` CLI
├─ tools/                       ← lint, scaffold, registry-build scripts
└─ .github/workflows/           ← CI: lint manifests, check trigger collisions, run smoke tests
```

---

## Concepts

### Skill
A self-contained folder under `skills/`. Anything in it can be installed
independently by copying that folder to `~/.claude/skills/<name>/`.
**A skill must not depend on files outside its own folder, except via:**
- declared `depends_on.skills` in `manifest.yaml`
- declared `depends_on.binaries` (e.g. `lark-cli`)
- the JSON schemas in `core/`

### Manifest (`manifest.yaml`)
Governance metadata. Distinct from `SKILL.md` frontmatter (which is for the Claude runtime).
See `manifest.schema.yaml` for the full schema. Minimum fields:
`name`, `version` (semver), `stage`, `owners`, `description_for_install`.

### Profile
A named bundle of skills, pinned to version ranges. Users install profiles,
not individual skills, so that Claude's context budget is not blown out by
loading 50+ skill descriptions at once. See `profiles/sa-mvp.yaml`.

### Signal envelope
The shared message shape that any skill writing into the data foundation
(currently `sa-wiki`) must produce. Defined in `core/signal-envelope.schema.json`.
**If your skill writes customer-related output, it produces signal envelopes.**

### Stages
| stage          | meaning                                              | profile allowed to pin? |
|----------------|------------------------------------------------------|-------------------------|
| `experimental` | contract may break without notice                    | no                      |
| `beta`         | contract stable for a minor version, may break major | yes, pin minor          |
| `stable`       | breaking changes require deprecation window          | yes, pin major          |
| `deprecated`   | CLI warns on install; removed after 90 days          | no                      |

---

## Hard rules (CI enforces these)

1. **Every skill folder has a `manifest.yaml`** that validates against `manifest.schema.yaml`.
2. **Every skill has at least one `owner`** in `manifest.yaml` AND in `CODEOWNERS`.
3. **No cross-skill file reads.** A skill MUST NOT `Read`, `import`, or `source` files
   under another skill's folder. Use the other skill's CLI / Bash surface instead.
4. **Trigger-word collisions across skills are warned on PR.** If two skills declare
   `triggers: ["会议摘要"]`, one must be renamed or scoped.
5. **Breaking changes bump major.** Changing input/output of a skill (its CLI flags,
   what it writes to `sa-wiki`, what it expects from upstream) is a major bump and
   requires a CHANGELOG entry with a migration note.
6. **No `experimental` skills inside profiles.** Profiles are user-facing; they need beta+.

---

## Quickstart: add a skill (agent recipe)

```bash
# 1. scaffold
cp -r skills/_template skills/my-new-skill
cd skills/my-new-skill

# 2. fill manifest.yaml FIRST (forces you to commit to ownership, version, contract)
#    then write SKILL.md to match

# 3. run local lint
../../tools/lint.sh my-new-skill

# 4. (optional) add to a profile if you want it shipped to users
#    edit profiles/sa-mvp.yaml

# 5. open PR — CODEOWNERS routes review automatically
```

Full step-by-step (with manifest field walkthrough) lives in `CONTRIBUTING.md`.

---

## What this repo is NOT

- Not a place to dump one-off scripts. Those belong in your own repo.
- Not a documentation site. Each skill's docs live inside the skill folder.
- Not a runtime. Claude Code is the runtime; this repo only **builds** the catalog
  that Claude Code consumes from `~/.claude/skills/`.

---

## Status

Bootstrapped. Not yet wired to CI. CLI is design-only (see `cli/README.md`).
First profile target: `sa-mvp` covering meeting summary, IM digest, dashboard watch, sa-wiki.
