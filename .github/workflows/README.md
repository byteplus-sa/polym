# `.github/` — automation for the polym repo

## Polym PR Review (`workflows/polym-pr-review.yml`)

Advisory PR reviewer. On every PR open/update — and whenever a comment mentions
`@polym` in a PR thread — it reads the PR diff plus the repo's own rules
(`CONTRIBUTING.md`, `manifest.schema.yaml`, `profile.schema.yaml`,
`README.md`) and posts a Markdown comment with a verdict, findings, and a
compliance checklist. **Advisory only:** it never blocks merge.

The prompt includes the full GitHub PR file list and a deterministic inventory
of required governance files for every touched skill. This keeps checks like
`manifest.yaml` and `tests/smoke.sh` reliable even when the large diff body is
truncated before those files appear.

### Setup (one-time)

The workflow speaks OpenAI-compatible chat completions, so any OpenAI-compatible
gateway works. Pick one and configure these three values:

All three live as **repo secrets** at `Settings → Secrets and variables → Actions → New repository secret`:

| Key | Value |
|---|---|
| `POLYM_LLM_BASE_URL` | Chat completions root URL (no `/chat/completions` suffix) |
| `POLYM_LLM_API_KEY` | Bearer token for that endpoint |
| `POLYM_LLM_MODEL` | Model id (e.g. `doubao-seed-2.0-pro`) |

`POLYM_LLM_MODEL` isn't sensitive but lives next to the other two for simpler setup.

### Reachable gateways (from a GitHub-hosted runner)

| Gateway | Base URL | Auth | Notes |
|---|---|---|---|
| **BytePlus ModelArk (海外)** | `https://ark.ap-southeast.bytepluses.com/api/v3` | `Authorization: Bearer <ARK_API_KEY>` | Public internet OK. Use this by default. Note: hostname is `ap-southeast` (no `-1`). |
| **Volcengine 火山方舟 (国内)** | `https://ark.cn-beijing.volces.com/api/v3` | `Authorization: Bearer <ARK_API_KEY>` | Public internet OK. |
| **AIDP (内部)** | `https://aidp.bytedance.net/...` | `?ak=<AIDP_API_KEY>` query param | **Not reachable from GitHub-hosted runners.** Requires a self-hosted runner inside ByteDance network, plus a header/query-param shim because AIDP doesn't use bearer auth. |

If you need AIDP, change the workflow's `runs-on:` to your self-hosted runner
labels and replace the `OpenAI()` call in `scripts/polym_review.py` with one
that appends `?ak=...` instead of using a bearer header.

### Trigger semantics

- **PR open / synchronize / reopen** → auto review.
- **Comment containing `@polym`** in a PR thread → re-review, with the comment
  text passed in as a follow-up question. Use this to ask "what about X?"
  after the initial pass.
- The review always posts a **new** comment (it doesn't edit the previous one).
  Old reviews stay in the timeline; the latest one wins.

### What it checks

Just the conventions in `CONTRIBUTING.md` and the two schema files — same rules
`tools/lint.sh` enforces, plus a softer code-review pass over the diff. It does
not invent style rules of its own.

### Cost / quota

One review per PR push. Diff is truncated at 80k chars, but the complete PR file
list and touched-skill governance inventory are still included. Rule files are
truncated at 8k each. Temperature 0.2. Single chat-completions call per run.
