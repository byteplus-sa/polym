# Slack App Setup — Detailed Guide

## 1. Create the App

1. Visit https://api.slack.com/apps → **Create New App** → **From scratch**.
2. App name: `Mira Slack Digest`.
3. Pick the workspace you want to monitor.

## 2. Configure OAuth Scopes

Navigate to **OAuth & Permissions** → **Scopes** → **User Token Scopes**.

| Scope | Purpose |
|---|---|
| `channels:history` | Read public channel messages |
| `channels:read` | List public channels |
| `groups:history` | Read private channel messages |
| `groups:read` | List private channels |
| `im:history` | Read direct messages |
| `im:read` | List direct messages |
| `mpim:history` | Read group DMs |
| `mpim:read` | List group DMs |
| `users:read` | Resolve user IDs to names |
| `users:read.email` | Detect company-affiliated users by email domain (optional but recommended) |

⚠️ **User Token Scopes** (not Bot Token) — the digest reads as your user identity to access every channel you joined.

## 3. Install to Workspace

1. Click **Install to Workspace** at the top.
2. Authorize the app.
3. Copy the **User OAuth Token** (`xoxp-...`) shown after install.

## 4. Validate

```bash
curl -s -H "Authorization: Bearer xoxp-..." \
  "https://slack.com/api/auth.test" | jq
```

Expected output:
```json
{
  "ok": true,
  "url": "https://yourworkspace.slack.com/",
  "team": "Your Workspace",
  "user": "your_username",
  "team_id": "T...",
  "user_id": "U..."
}
```

## 5. Rate-Limit Notes

- `users.list` (Tier 2): 20+ req/min — sleep 1s between paginated calls.
- `conversations.history` (Tier 3): 50+ req/min — sleep 0.3s between channels.
- `users.info` (Tier 4): 100+ req/min — usually fine without sleep.

If you hit `ratelimited`, sleep 60s and retry.

## 6. Token Rotation

Slack user tokens do not auto-expire but can be revoked. If you see `invalid_auth` or `token_revoked`:

1. Go back to **OAuth & Permissions**.
2. Click **Reinstall to Workspace** to issue a new token.
3. Run `python3 ~/.claude/skills/slack-daily-digest/scripts/save_credentials.py --slack-token "xoxp-..."`.
