# Lark (Feishu) Bot Setup — Detailed Guide

## 1. Create a Custom App

1. Visit https://open.feishu.cn/app (or https://open.larksuite.com/app for international tenants).
2. Click **Create Custom App**.
3. App name: `Mira Slack Digest Notifier`.
4. App icon: any (the bot is internal-use only).

## 2. Add Permissions / Scopes

Navigate to **Permissions & Scopes**.

| Scope | Purpose |
|---|---|
| `im:message` | Send messages to users |
| `im:message:send_as_bot` | Send as the bot identity |
| `contact:user.base:readonly` | Resolve email → open_id |
| `contact:contact:readonly_as_app` | Read contact info for the user (alternative) |
| `docx:document` | Create / edit documents |
| `docx:document:readonly` | Read documents (for watchdog) |
| `drive:drive` | Move documents to a folder |
| `drive:file:readonly` | List folder contents |

## 3. Enable Bot Capability

Navigate to **Features** → **Bot** → **Enable bot ability**.

## 4. Publish the App

1. Go to **Version Management & Release**.
2. Click **Create Version** with version `1.0.0`.
3. Submit for review.
4. In a corporate workspace, an admin must approve.
5. In a self-managed test workspace, you can self-approve.

## 5. Copy Credentials

Navigate to **Credentials & Basic Info**.

- Copy `App ID` (looks like `cli_a01234567890abcd`).
- Copy `App Secret` (a long alphanumeric string).

## 6. Validate

```bash
curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_...","app_secret":"..."}' | jq
```

Expected:
```json
{
  "code": 0,
  "msg": "ok",
  "tenant_access_token": "t-...",
  "expire": 7200
}
```

`code = 0` means success. The token expires every 2 hours — `lark_helpers.py` caches it for 90 minutes.

## 7. Verify the User Email Resolves

```bash
TOK=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"cli_...","app_secret":"..."}' | jq -r .tenant_access_token)

curl -s "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id?user_id_type=open_id" \
  -X POST -H "Authorization: Bearer $TOK" \
  -H "Content-Type: application/json" \
  -d '{"emails":["yourname@yourcompany.com"]}' | jq
```

Expected: `data.user_list[0].user_id` is non-empty.

## 8. Common Errors

| Error code | Meaning | Fix |
|---|---|---|
| 99991663 / 4 / 5 / 8 | Token expired | Re-acquire `tenant_access_token` |
| 99991401 | App secret mismatch | Re-copy from the open platform |
| 99991403 | Permission missing | Add the missing scope and re-publish |
| 99991671 | App not yet released | Wait for admin approval |
