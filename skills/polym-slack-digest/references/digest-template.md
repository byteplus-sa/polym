# Daily Digest Synthesis Template (v4)

The agent must produce the per-day Lark doc following this exact structure. The doc title is `Slack Daily Digest · YYYY-MM-DD`.

---

```markdown
> Last updated: YYYY-MM-DD HH:MM (configured timezone) · Channels monitored: N · Active channels: A · Effective messages: M
> Time window: YYYY-MM-DD HH:MM ~ YYYY-MM-DD HH:MM (configured timezone)

## 🎯 Executive Summary

1. 🔴 **P0 — <one-line headline>** (#channel): <2-3 sentences with names, dates, amounts>. **<Owner Name>** must <action> by <deadline>.
2. 🟡 **P1 — <headline>** (#channel): ...
3. 🟢 **P2 — <headline>** (#channel): ...

## 📌 Highlights

- 🔴 **<Title>** (#channel) — <stakeholder>: <one-liner>
- 🟡 ...

## ✅ TODO Backlog

| Priority | Owner | Item | Deadline | Source channel |
|---|---|---|---|---|
| 🔴 P0 | <Name> | <action> | <date> | #channel |

## 📈 Business Pipeline

| Partner | Stage / Amount | Status | Owner | Health |
|---|---|---|---|---|
| <Partner> | <Stage> | <Status> | <Name> | 🟢 / 🟡 / 🔴 |

## ⚠️ Risk Signals

- 🔴 **<Risk title>** (#channel): <description>
- 🟡 ...

## 🗂️ By Channel

### #channel-name · 💬 N msgs · 👥 K participants · 👤 Owner: <Name>

**📖 Context**: <2-4 sentences about the channel state, partner, and what changed in this window>

**💬 Full Messages**:
- **<Speaker (Title)>**: <verbatim message text, newlines normalized to ` / `>
- **<Speaker>**: <verbatim>

**🎯 Next Steps**:
- **[P0] <Owner>**: <action> by <deadline>; <context>
- **[P1] <Owner>**: <action>

**Risk**: 🔴/🟡/🟢 <one line>

---

(repeat per active channel, sorted by msg_count desc; tie-breaker: speaker_count desc)

## 📝 Statistics

**Top active channels (by msg count)**
1. #channel-A — N msgs / K participants
2. ...

**Top contributors**
- Speaker A — N msgs

**Identified BytePlus owners this window**
- #channel-A: Name (rule: @-mention / cache fallback)

---

## 🕙 16:00 Update
```

---

## Hard Rules

- ❌ **NEVER** truncate a message with `[:N]`.
- ❌ **NEVER** collapse a long message into ellipsis.
- ❌ **NEVER** keep only a summary while dropping the original text.
- ✅ Filter out `channel_join`, `channel_leave`, pure-emoji replies, pure greetings.
- ✅ Allowed to merge consecutive messages from the same speaker for compactness, but text content must remain verbatim.

## Priority Rubric

| Tier | Trigger |
|---|---|
| 🔴 P0 | Customer service interruption risk / Large-contract critical milestone / Engineering blocker |
| 🟡 P1 | Schedule slippage risk / Mid-size commercial milestone / Pending customer ask |
| 🟢 P2 | Routine progress / Brand cooperation opportunity / Internal grooming |

## Owner Identification Cascade

1. Speaker `display_name` / `real_name` contains `(BytePlus)` or `(ByteDance)` suffix
2. Speaker email ends in `@bytedance.com` (requires `users:read.email` scope)
3. Speaker `profile.title` contains `BytePlus` / `ByteDance` / `Solution` / `Customer Engineer` / `Technical Account` / `TAM` / `SA`
4. If none in this window, fall back to `channel_owner_cache.json` last-seen owner.
