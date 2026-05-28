# Known AI coding agents — brand reference

When a video's narrative requires showing "which agents this works with" — typically as an opener chip row, a comparison table, or "made in X" call-out — use this list as the canonical reference. It keeps brand colors / treatments consistent across videos and avoids the skill silently hardcoding "Claude Code" everywhere.

Use the matching `templates/agent-chip-row.html` component to render a row of agent chips with icon + label. That component reads from `agent_list` in storyboard.json which uses the keys below.

---

## Agent registry

| Key | Display name | Brand color | Vibe / motif | Logo asset hint |
|---|---|---|---|---|
| `claude` | Claude Code | `#D97706` (Anthropic orange) | 8-point sparkle / sunburst | rounded square with white sunburst |
| `codex` | Codex | `#0B0B10` (near-black) | Cloud + terminal prompt | blue/purple cloud with `>` `_` cursor |
| `cursor` | Cursor | `#000000` | Black mark, clean editor | sharp triangular cursor on black |
| `openclaw` | OpenClaw | `#D8463C` (lobster red) | Lobster mascot (Molty) with claws | round red mascot with two claws + teal eyes |
| `cline` | Cline | `#8B5CF6` (purple) | Terminal CLI character | purple bracket with C |
| `aider` | Aider | `#10B981` (teal-green) | Conversational/code | simple green geometric mark |
| `hermes` | Hermes | `#B8860B` (goldenrod) | Greek messenger / anime mascot | winged motif OR Nous Research anime icon |
| `continue` | Continue | `#3B82F6` (continue blue) | Arrow forward | blue forward-chevron mark |
| `goose` | Goose (Block) | `#1F2937` (slate) | Bird mark | clean goose silhouette |
| `devin` | Devin | `#0EA5E9` (sky blue) | Engineer/wrench | wrench + circle |

---

## How to use in storyboard

```json
{
  "agent_list": ["claude", "codex", "openclaw", "hermes"],
  "segments": [
    {
      "id": "opener",
      "type": "b-roll",
      "tool": "hyperframes",
      "template": "agent-chip-row",
      "title": "Prompt to Explainer Video",
      "agents": ["claude", "codex", "openclaw", "hermes"]
    },
    ...
  ]
}
```

The `templates/agent-chip-row.html` reads `agents` and looks up each by key. Pick 3–5 agents max — more is noisy.

## Rules

1. **No "Claude Code" hardcoding.** Any copy mentioning a specific agent must come from the user's preflight answer or storyboard config — never inline in a default template.
2. **Recommended phrasing for agent-row openings**: "Prompt to Explainer Video" (the agents fit on the next line, no "in X" preamble needed — the row makes it visually obvious).
3. **For "made in" closing cards**: default to "Made entirely in your agent." If the user wants a specific agent named, surface it as a Phase 3 question.
4. **Logo treatment**: prefer the user's locally provided logo files first (e.g. `~/Downloads/claude-code.png`). If absent, fall back to a minimal monogram in the brand color above.

## Logo asset convention

If the user is doing an agent-comparison video, they may provide logo PNGs in `~/Downloads/` or a custom path. Look for files matching the agent key:
- `claude-code.{png,svg}` → `claude`
- `codex.{png,svg}` → `codex`
- `openclaw-logo.{png,svg}` → `openclaw`
- `hermes-icon.{png,svg}` or `hermes-logo.{png,svg}` → `hermes`
- etc.

Copy matching files into the project's `assets/` directory at Phase 4 setup time. Reference as `assets/claude-code.png` in the chip template.

## Adding a new agent

If a user wants an agent not in this list:
1. Ask for: display name, primary brand color (hex), 1–2 line vibe descriptor
2. Optionally ask for a logo file (PNG/SVG) — otherwise generate a monogram on the brand color
3. Append to this file as a new row (PR back to the skill repo as part of normal updates)

Keep this list curated — only add agents that have at least 1k GitHub stars or known public traction. Don't bloat it with one-off demos.
