# Lark CLI upload guide

How to upload the final MP4 to Lark Drive in Phase 5.

## Prerequisites

The user has installed `@larksuite/cli` globally:
```bash
npm install -g @larksuite/cli
```

The binary is `lark-cli`. (Both `lark` and `lark-cli` may work — they alias.)

## Verify installation

```bash
lark-cli --version
# expect: 1.0.x or later
```

## Authentication

Lark CLI uses OAuth 2.0 device flow. First run requires user to authorize in browser.

```bash
# Interactive mode — best for first-time setup
lark-cli auth login --recommend
# This opens a browser; user clicks Authorize; CLI receives token via OAuth callback.
```

For subsequent runs, the token is stored in OS-native keychain. Just verify status:

```bash
lark-cli auth status
# Should show: ✓ Authenticated as <user>
```

## Required scope for upload

The skill needs write access to user's drive. The `--recommend` flag auto-approves the right scopes. If user runs into permission errors:

```bash
lark-cli auth login --scope "drive:drive"
```

## Upload command (the core step)

```bash
lark-cli drive +upload --file dist/main.mp4 --output json
```

Output JSON:
```json
{
  "code": 0,
  "data": {
    "file_token": "boxcnXXXXXXXXXXXXX",
    "file_name": "main.mp4",
    "type": "file",
    "size": 12345678,
    "url": "https://example.larksuite.com/file/boxcnXXXXXXXXXXXXX"
  }
}
```

The `file_token` is the canonical reference. The `url` is the shareable link.

## Upload to specific folder

If the user wants the file in a specific folder (not the root of My Files):

```bash
# Step 1: get the folder token
# User pastes a folder URL like https://example.larksuite.com/drive/folder/fldcnXXX
# Extract the token from the URL (the part after /folder/)

lark-cli drive +upload --file dist/main.mp4 --folder-token fldcnXXXXXX --output json
```

Or if user only knows folder name, search first:
```bash
lark-cli drive +list-files --output json | jq '.data.items[] | select(.name=="Videos")'
```

## Send the URL to a Lark chat (optional)

If the user wants the link delivered to themselves or a chat:

```bash
# To self (DM with bot)
lark-cli im +messages-send --as user --to-self --text "Video ready: <url>"

# To a chat
lark-cli im +messages-send --as user --chat-id "oc_xxx" --text "Video ready: <url>"
```

## Common issues

### `lark-cli: command not found`

Either not installed or not in PATH:
```bash
which lark-cli
npm install -g @larksuite/cli
```

### `unauthorized` / 401

Token expired. Re-run:
```bash
lark-cli auth login --recommend
```

### `file too large`

Lark Drive default upload limit is 100MB. A 15-30s 720p video is well under this. If you hit it: check that you're not trying to upload a higher-resolution intermediate file.

### `folder not found`

Folder token is wrong. Double-check the URL the user provided — the token is the segment AFTER `/folder/`, not the full URL.

### Slow upload

Lark's upload bandwidth depends on user's region. For 15-MB files, should complete in 5-15 seconds. If consistently slow (>1 minute), check user's network.

## Domain awareness

`lark-cli` works for both:
- **Lark** (international) — `larksuite.com`
- **Feishu** (China) — `feishu.cn`

The CLI auto-detects based on the user's authenticated account. The returned `url` will use the correct domain.

## Final summary template

After Phase 5 completes, present this to the user:

```
✅ Video produced and uploaded

Local file:    ~/projects/<product>-video/dist/main.mp4
File size:     12.3 MB
Duration:      15.0s
Resolution:    720x1280 (9:16)

Lark Drive:    https://example.larksuite.com/file/boxcnXXX
Click to view, share, or download.

Total cost:
  Seedance 2.0 tokens:   <A-roll generation>
  Volcengine music:      <1 track>
  HyperFrames B-roll:    free

Want me to also send this to a Lark chat? (yes / specify chat / no)
```
