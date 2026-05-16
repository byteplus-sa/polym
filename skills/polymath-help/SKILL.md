---
name: polymath-help
version: 0.2.2
description: "Onboarding guide for Polymath — what it does, how to install it, common use cases, and how to contribute new skills. Trigger when a user seems lost, asks what this is, or asks how to get started."
metadata:
  requires:
    bins: []
---

# polymath-help — Onboarding Guide

Answer any question a new SA might have about the Polymath: what it does, how to set it up, what to use it for, and how to contribute.

## Trigger Scenarios

- "What is polymath?"
- "How do I use this?"
- "How do I get started?"
- "help"
- "What can you do?"
- "How do I install this?"
- "How do I add a skill?"
- "What skills are available?"
- "polymath help"
- User seems confused about what the system does

---

## Section 1 — What Is Polymath?

### The one-sentence pitch

Polymath is a curated collection of AI skills for BytePlus SAs. Install once, and Claude Code becomes your daily assistant for IM digests, meeting summaries, customer research, and more — all connected to a shared knowledge base.

### The big picture

```
Daily signals                Processed by skill       Saved to
─────────────────────────────────────────────────────────────────
Lark group chats      →  polymath-im-digest          →  knowledge base
Live meetings         →  polymath-meeting-recorder   →  knowledge base
Lark VC / Minutes     →  polymath-meeting-summary    →  knowledge base
C360 usage data       →  polymath-dashboard-watch    →  knowledge base (on demand)
Lark documents        →  polymath-lark-doc-ingest    →  knowledge base

knowledge base
  └── polymath-sa-wiki (Lark Bitable + Wiki)    ← shared SA team wiki
  └── local wiki (~/sa-wiki/)         ← your private local copy

Consumer skills
  polymath-customer-brief   →  pulls everything about one customer before a meeting
```

### Common daily scenarios

| Scenario | Skill | Example phrase |
|---|---|---|
| Morning: catch up on yesterday's chats | `polymath-im-digest` | "Organize yesterday's messages" |
| During a meeting: record and transcribe live | `polymath-meeting-recorder` | "Start meeting recording" |
| Morning: see what meetings happened | `polymath-meeting-summary` | "Summarize yesterday's meetings" |
| Pre-meeting: prep for a customer | `polymath-customer-brief` | "Give me a brief on Acme before my 2pm" |
| Ad-hoc: how much is X using? | `polymath-dashboard-watch` | "How many tokens did Acme use last month?" |
| Ad-hoc: save a Lark doc to the wiki | `polymath-lark-doc-ingest` | "Ingest this document" |
| First time: create your local wiki | `polymath-local-wiki-init` | "Set up my local wiki" |
| Searching SA knowledge | `polymath-sa-wiki` | "What do we know about AK/SK rotation?" |

---

## Section 2 — Installation & Setup

### Step 1: Prerequisites

Make sure you have these installed:

| Requirement | Check | Install |
|---|---|---|
| Claude Code | `claude --version` | [claude.ai/code](https://claude.ai/code) |
| `gh` (GitHub CLI) | `gh --version` | `brew install gh` |
| `lark-cli` | `lark-cli --version` | Ask your team for the installer |
| Python 3 | `python3 --version` | Pre-installed on macOS |

### Step 2: Install the skill pack

Pick the option that matches your setup. All three do the same thing.

**Option A — gh CLI (recommended)**
```bash
brew install gh && gh auth login   # one-time setup if you don't have gh
gh repo clone byteplus-sa/polymath /tmp/polymath \
  && /tmp/polymath/install.sh
```

**Option B — SSH** (if you have an SSH key on GitHub)
```bash
git clone git@github.com:byteplus-sa/polymath.git /tmp/polymath \
  && /tmp/polymath/install.sh
```

**Option C — GitHub Personal Access Token** (no special CLI needed)
1. Go to github.com/settings/tokens → Generate new token (classic) → scope: **repo**
2. Copy the token (starts with `ghp_`)
```bash
GITHUB_TOKEN=ghp_xxxx bash <(curl -fsSL \
  -H "Authorization: token ghp_xxxx" \
  https://raw.githubusercontent.com/byteplus-sa/polymath/main/install.sh)
```

> **Note:** Ask the repo owner to add you as a GitHub collaborator before installing.

The installer will:
1. Clone the repo to `~/.local/share/polymath`
2. Link `polymath` CLI to `~/.local/bin/`
3. Install all skills to `~/.claude/skills/`

If `~/.local/bin` is not in your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
```

### Step 3: Install only the SA MVP bundle (recommended for new users)

```bash
polymath install profile:sa-mvp
```

This installs the core skills: `polymath-sa-wiki`, `polymath-meeting-recorder`, `polymath-meeting-summary`, `polymath-im-digest`, `polymath-dashboard-watch`, `polymath-local-wiki-init`, `polymath-customer-brief`, and `polymath-help`.

### Step 4: Authorize lark-cli

The skills need lark-cli authenticated with your Lark account.

```bash
# Initialize config (first time only)
lark-cli config init

# Log in as user (required for reading chats, docs, VC)
lark-cli auth login --as user
```

Follow the browser prompt to authorize. After login, verify:

```bash
lark-cli im +chat-search --keyword "test" --as user
```

If you see results (even empty), auth is working.

### Step 5: Chrome extension (for polymath-dashboard-watch only)

`polymath-dashboard-watch` queries C360 via browser automation. You need the **Claude for Chrome** extension:

1. Open Chrome → search "Claude" in the Chrome Web Store
2. Click **Add to Chrome**
3. Pin the extension in the toolbar
4. With Claude Code running, click **Connect to Claude Code** in the extension

Verify:
```
In Claude Code, say: "Check if Chrome extension is connected"
```

### Step 5b: Syncore setup (for polymath-meeting-recorder)

`polymath-meeting-recorder` uses Syncore to capture mic + system audio.

```bash
curl -fsSL https://syncorelabs.ai/install.sh | sh
syncore login
syncore doctor
```

Grant microphone and Screen Recording permissions when `syncore doctor` asks. Reopen Claude Code after setup.

### Step 6: Set up your local wiki (optional but recommended)

```bash
# In Claude Code, say:
"Set up my local wiki"
# Claude will ask where to create it (default: ~/sa-wiki)
```

Your local wiki stores private notes, raw snapshots, and customer intel that stays on your machine. The team Lark wiki is shared; the local wiki is yours.

### Verify everything works

```bash
polymath list           # shows installed skills
polymath doctor         # checks dependencies
```

---

## Section 3 — How to Use Each Skill

Once installed, invoke skills in Claude Code using natural language:

```
"Organize yesterday's messages"          → polymath-im-digest
"Start meeting recording"                → polymath-meeting-recorder
"End meeting"                            → polymath-meeting-recorder
"Summarize yesterday's meetings"         → polymath-meeting-summary
"Brief me on Acme before my meeting"     → polymath-customer-brief
"Acme used how many tokens last month?"  → polymath-dashboard-watch
"Ingest this document: <URL>"            → polymath-lark-doc-ingest
"What do we know about Seedance quotas?" → polymath-sa-wiki
"Set up my local wiki"                   → polymath-local-wiki-init
```

### Tips

- **First run**: skills ask for your local wiki path once, then remember it. You won't be asked again.
- **Knowledge accumulates**: the more you run `polymath-im-digest`, `polymath-meeting-recorder`, and `polymath-meeting-summary`, the richer your wiki becomes, and the better `polymath-customer-brief` gets.
- **No manual filing**: skills save useful outputs to the knowledge base by default. You only see the final report.
- **polymath-customer-brief modes**: use `--quick` for a 5-second wiki-only brief, or `--full` for a 20-second brief that also pulls C360 data.

---

## Section 4 — Contributing a New Skill

### Quick start

```bash
# Scaffold a new skill
polymath new my-skill-name

# This creates:
# skills/my-skill-name/
# ├── SKILL.md        ← the prompt/instructions Claude reads
# ├── manifest.yaml  ← governance: version, owners, deps
# ├── CHANGELOG.md
# └── tests/smoke.sh
```

### Fill the manifest first

Edit `skills/my-skill-name/manifest.yaml`:

```yaml
name: my-skill-name
version: 0.1.0
stage: experimental   # start here; promote to beta when stable
owners:
  - your-handle@

description_for_install: |
  One paragraph. What does this skill do and when should Claude use it?

depends_on:
  binaries:
    - lark-cli: ">=1.0.20"   # list what CLI tools are needed
  env: []                    # list required env vars

triggers:
  - "natural language phrase that invokes this skill"
```

**Stages:**

| Stage | Meaning | Can be in a profile? |
|---|---|---|
| `experimental` | Contract may break | No |
| `beta` | Stable for minor version | Yes |
| `stable` | Breaking changes need deprecation window | Yes |
| `deprecated` | Warn on install; removed after 90 days | No |

### Write the SKILL.md

`SKILL.md` is what Claude reads when the skill is invoked. Write it as clear instructions:
- What triggers this skill
- Step-by-step execution flow
- What to output / write
- Safety rules

Look at `skills/polymath-im-digest/SKILL.md` for a good example of structure.

### Versioning rules (semver)

| Change type | Version bump | Example |
|---|---|---|
| New features, backwards-compatible | Minor: `0.1.0 → 0.2.0` | Added a new flag |
| Breaking: changed input/output contract | Major: `0.2.0 → 1.0.0` | Renamed a required param |
| Bug fix, doc fix | Patch: `0.1.0 → 0.1.1` | Fixed a wrong command |

Always update `CHANGELOG.md` when bumping the version.

### Run local lint before submitting

```bash
bash tools/lint.sh my-skill-name
```

This checks: required files exist, manifest fields valid, version is semver, name matches folder, no trigger collisions with other skills.

### Submit a PR

```bash
git add skills/my-skill-name/
git commit -m "feat(my-skill-name): describe what it does"
git push
gh pr create --title "feat: add my-skill-name" --body "..."
```

CI will:
1. Run `tools/lint.sh` on all skills (PR gate)
2. After merge to main, auto-rebuild `registry.yaml` and commit it

### Add to a profile (optional)

If the skill should be part of the default install bundle, add it to `profiles/sa-mvp.yaml`:

```yaml
includes:
  - my-skill-name: "^0.1"   # only beta or stable skills
```

Skills must be at `stage: beta` or higher to be included in profiles.

---

## Quick Reference

```bash
# Install
gh repo clone byteplus-sa/polymath ~/.local/share/polymath \
  && ~/.local/share/polymath/install.sh

# Manage
polymath list                        # see all available skills
polymath list --installed            # see what you have
polymath install profile:sa-mvp     # install the MVP bundle
polymath install <skill-name>        # install one skill
polymath self-update                 # update CLI/catalog only
polymath update                      # update CLI + refresh installed skills
polymath update profile:sa-mvp       # update CLI + refresh MVP profile
polymath doctor                      # check deps & auth

# Develop
polymath new <name>                  # scaffold a new skill (auto-prefixes to polymath-<name>)
polymath bump <name> <version>       # update SKILL.md + manifest versions
polymath publish -m "feat(...)"      # lint, registry, commit, rebase, push
bash tools/lint.sh <name>               # validate before PR
bash tools/build-registry.sh            # preview registry changes
```
