# IM Digest Blacklist

The blacklist is a local-only preference file for conversations that should not
enter the daily digest. It is used for long-lived exclusions such as noisy
internal groups, private P2P threads, or groups the user never wants summarized.

## Location

Resolve in this order:

1. `$LOCAL_WIKI_ROOT/config/polym-im-digest-blacklist.json`
2. `~/.config/polym/im-digest/blacklist.json`

If the selected file does not exist, treat the blacklist as empty. Create parent
directories only when the user asks to add the first blacklist entry.

## Schema

```json
{
  "version": 1,
  "groups": [
    {
      "chat_id": "oc_xxx",
      "name": "Display name",
      "reason": "optional",
      "created_at": "2026-05-26T10:00:00+08:00"
    }
  ],
  "p2p": [
    {
      "chat_id": "oc_xxx",
      "open_id": "ou_xxx",
      "name": "Display name",
      "reason": "optional",
      "created_at": "2026-05-26T10:00:00+08:00"
    }
  ]
}
```

Rules:

- `version` is required and currently must be `1`.
- `groups` and `p2p` are required arrays.
- Prefer stable IDs over names. Names are allowed as a fallback, but matching is
  exact and case-sensitive.
- De-dupe groups by `chat_id` when present, otherwise exact `name`.
- De-dupe P2P entries by `open_id` when present, then `chat_id`, then exact
  `name`.
- Keep entries local. Never write them into Feishu docs, Lark wiki, raw
  snapshots, or digest markdown.

## Management Workflow

### Add Group

Input examples:

- `把 oc_xxx 加入 IM digest 黑名单`
- `以后不要拉 <群名> 这个群`

Resolution:

1. If input is `oc_xxx`, write it directly as `chat_id`.
2. Otherwise resolve by group name with `lark-cli im +chat-search --query`.
3. If multiple groups match, ask the user to choose.
4. Append to `groups`, preserving any existing entries.

### Add P2P

Input examples:

- `以后不要拉 ou_xxx 的私聊`
- `把 <人名> 加入 IM digest 黑名单`

Resolution:

1. If input is `ou_xxx`, write it directly as `open_id`.
2. Otherwise resolve by contact name with `lark-cli contact +search`.
3. If a P2P `chat_id` is known from a recent discovery run, store it too.
4. Append to `p2p`, preserving any existing entries.

### Remove

Remove matching entries by `chat_id`, `open_id`, or exact `name`. If more than
one entry matches, show the matches and ask for confirmation.

### List

Show:

- resolved blacklist file path
- group entries
- P2P entries

Do not include blacklist entries in normal digest output unless the user asks to
list or edit the blacklist.

## Digest-Time Filtering

Group chats:

1. Enumerate joined groups.
2. Drop blacklisted groups before activity probes.
3. Do not call `lark-cli im +chat-messages-list` for blacklisted group chats.

P2P:

1. Run global P2P discovery.
2. Group by `chat_id`.
3. Drop blacklisted P2P threads before showing the confirmation list.
4. Do not Phase 1 fetch, analyze, persist, or write blacklisted P2P threads.

Current limitation: `lark-cli im +messages-search --chat-type p2p` does not
support negative filters, so P2P blacklist filtering cannot happen before the
global discovery query. It still prevents all downstream digest processing and
persistence for those P2P threads.
