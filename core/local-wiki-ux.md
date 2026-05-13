# Local Wiki UX Standard

> Shared reference — all skills that write knowledge MUST follow this pattern.
> Never use the word "双写" or expose implementation details to the user.

## The rule in one sentence

**Always save to Lark wiki. Save to local wiki silently when it exists; offer to create it when it doesn't.**

---

## Decision flow (run once per session, at the start of Phase 0)

```
1. Resolve local wiki path (in order):
   a. Env var LOCAL_WIKI_ROOT
   b. Claude memory system — look for a memory file containing "local wiki root" or "LOCAL_WIKI_ROOT"
   c. Auto-probe common paths: ~/sa-wiki  ~/wiki  ~/LLM-Wiki  ~/Documents/sa-wiki
      (check if path exists AND contains SCHEMA.md or README.md)
   d. → NOT FOUND

2. If FOUND → set LOCAL_WIKI_ROOT, proceed silently (no mention to user)

3. If NOT FOUND → ask ONCE:
   「还没有本地 wiki，要创建一个吗？[Y/n]」
   - Y → 「保存在哪里？（直接回车默认 ~/sa-wiki）」
         → run local-wiki-init skill at that path
         → save path to Claude memory (write memory file)
         → set LOCAL_WIKI_ROOT
   - N → set LOCAL_WIKI_ROOT="" (skip local write for this session)
         → remember this preference in memory so we don't ask again soon

4. After resolution, never mention local wiki to user again — just write silently.
```

## What the user sees (and doesn't see)

| Situation | User sees |
|---|---|
| Local wiki exists | Nothing — writes happen silently |
| Local wiki doesn't exist | One question: "还没有本地 wiki，要创建一个吗？" |
| User said N | Nothing — only Lark wiki is written |
| Writing to Lark wiki | Nothing — happens automatically, proposal_ids shown in final report |

## Memory file format

When saving a user-provided path, write to the Claude memory system:

```markdown
---
name: local-wiki-root
description: User's local SA wiki root directory path
type: user
---

Local wiki root: <path>
Set on: <YYYY-MM-DD>
```

## Lark wiki write

- Always write to Lark wiki via **sa-wiki skill WRITE workflow** (§5 in sa-wiki SKILL.md)
- Never reimplement write_queue logic in another skill
- Desensitisation check is part of sa-wiki's write flow — handled there
- Show proposal_ids in the final summary (so user can track/audit)

## Banned phrases

Never use these in user-facing output:
- "双写"
- "写入两个 wiki"  
- "本地 wiki 和 Lark wiki"
- "是否双写"
- "要把内容写入 wiki 吗？[Y/n]" ← do not ask, just write
