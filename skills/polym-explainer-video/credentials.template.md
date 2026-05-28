# explainer-video — onboarding credential sheet

Fill in every value below, then hand this file back to whoever is setting up the
**explainer-video** skill (or, if you run the skill yourself, give it the path to this
filled-in file when it asks how you want to onboard).

- Replace each `<...>` placeholder. Do **not** rename the keys or remove the colons.
- Paths must be **absolute** (e.g. `/Users/you/Pictures/portrait.jpg`).
- This file contains secrets once filled in — share it only over a trusted channel,
  keep it out of git, and delete it after onboarding.

---

## Required for everyone

```yaml
# BytePlus ModelArk API key — generates Seedance 2.0 video and Seedream images.
modelark_api_key: <paste ModelArk API key>

# BytePlus IAM access key / secret key — operate the ModelArk asset library and TOS.
iam_ak: <paste BytePlus IAM access key>
iam_sk: <paste BytePlus IAM secret key>

# Digital-human A-roll source files (absolute paths).
#  - portrait_image: a clear, front-facing personal photo (drives appearance).
#  - reference_video: a short clip of you talking, WITH audio (drives voice + facial motion).
portrait_image: <absolute path to personal photo, e.g. /Users/you/Pictures/portrait.jpg>
reference_video: <absolute path to portrait video, e.g. /Users/you/Movies/me-talking.mov>

# Where finished videos are saved. Leave as ~/Downloads if unsure.
output_folder: ~/Downloads
```

## AI background music (optional)

Set `music_enabled` to `yes` only if you want the skill to auto-generate background
music with the Volcengine music model. If `no`, leave the two Volcengine keys blank —
videos will simply have no music bed.

```yaml
music_enabled: <yes | no>

# Only required when music_enabled is yes — Volcengine access key / secret key.
volc_music_ak: <paste Volcengine access key, or leave blank>
volc_music_sk: <paste Volcengine secret key, or leave blank>
```

---

### Where to get each credential

| Field | Where to find it |
|---|---|
| `modelark_api_key` | BytePlus ModelArk console → API keys |
| `iam_ak` / `iam_sk` | BytePlus console → IAM → access keys |
| `volc_music_ak` / `volc_music_sk` | Volcengine console → access keys (music model) |
| `portrait_image` / `reference_video` | Your own files — record their absolute paths |

Once this file is complete, the skill reads it and writes
`~/.explainer-video/config.json` (mode `600`) for you.
