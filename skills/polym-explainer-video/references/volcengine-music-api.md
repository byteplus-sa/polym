# Volcengine BGM (instrumental music) API reference

Generate copyright-free background music for the video using Volcengine's AI music model. Pure instrumental (no vocals, no lyrics).

**This step runs only when `config.music_enabled` is `true`.** If AI music is disabled in
`~/.explainer-video/config.json`, skip music generation entirely.

Credentials come from `~/.explainer-video/config.json`:
- `volc_music_ak` — Volcengine access key
- `volc_music_sk` — Volcengine secret key (base64-encoded; pass raw to the SDK without decoding)

Do NOT hardcode credentials. Do NOT print them in full.

**Music prompt:** the per-task workflow drafts a suggested music prompt from the product
brief and storyboard context (see SKILL.md Phase 3 "Music plan") and the user approves or
edits it before this step runs. Use the approved prompt as the `Prompt` field below.

Docs:
- Generate BGM: https://www.volcengine.com/docs/84992/2100970
- Query task: https://www.volcengine.com/docs/84992/2100960

---

## API endpoints

| Action | Method | Notes |
|---|---|---|
| `GenBGM` | POST | Prepaid — submit a music generation task |
| `QuerySong` | POST | Poll task status / get audio URL |

Common host: `open.volcengineapi.com`
Version: `2024-08-12`
Service: `imagination`
Region: `cn-beijing`
Auth: Volcengine SigV4 (X-Date, X-Content-Sha256, Authorization headers)

---

## Step 1 — Submit GenBGM task

```python
import json, requests
from pathlib import Path
from volcengine.auth.SignerV4 import SignerV4
from volcengine.Credentials import Credentials
from volcengine.base.Request import Request

CFG = json.loads((Path.home() / ".explainer-video" / "config.json").read_text())

def call_volc(action, body_dict):
    body = json.dumps(body_dict)
    req = Request()
    req.method = "POST"; req.scheme = "https"; req.host = "open.volcengineapi.com"
    req.path = "/"; req.query = {"Action": action, "Version": "2024-08-12"}
    req.headers = {"Content-Type": "application/json", "Host": req.host}
    req.body = body
    SignerV4.sign(req, Credentials(CFG["volc_music_ak"],
                                   CFG["volc_music_sk"],
                                   "imagination", "cn-beijing"))
    r = requests.post(f"https://{req.host}/", params=req.query, data=body, headers=req.headers)
    return r.json()

resp = call_volc("GenBGM", {
    "Text": "Cinematic uplifting ambient instrumental music for a tech product launch. "
            "Starts mysterious, builds confident energy, soft synth pads, electronic textures, "
            "no vocals, no lyrics, instrumental only.",
    "Duration": 30,        # range [30, 120] for v5.0
    "Version": "v5.0",
    "EnableInputRewrite": False
})
task_id = resp["Result"]["TaskID"]
```

### Body parameters

| Parameter | Required | Notes |
|---|---|---|
| `Text` | yes | Prompt describing the music. Include genre, mood, scene, instruments. No need to set `Genre`/`Mood`/`Instrument` separately for v5.0 — describe everything in `Text`. |
| `Duration` | no | Seconds. v5.0 range: **[30, 120]**. Default 60. **For shorter videos, generate ≥30s and trim with ffmpeg.** |
| `Version` | no | Default `v5.0` (current). |
| `Segments` | no | List of `{Name, Duration}` to control structure. Names: `intro`, `verse`, `chorus`, `inst`, `bridge`, `outro`. Sum of durations must be in [30, 120]. |
| `EnableInputRewrite` | no | Default false. Setting true lets the model rewrite the prompt for better generation. |
| `TosBucket` | no | If set, music is also saved to your TOS bucket. |
| `CallbackURL` | no | HTTP webhook fired on completion. |

**Important:** Short / generic prompts can trigger copyright-violation errors (`code: 50000001`). Use rich descriptions or specify Segments.

---

## Step 2 — Poll QuerySong

Music generation typically takes 30-90 seconds. Poll every 10s.

```python
import time

while True:
    resp = call_volc("QuerySong", {"TaskID": task_id})
    status = resp["Result"]["Status"]   # 0=waiting, 1=processing, 2=success, 3=failed
    if status == 2:
        audio_url = resp["Result"]["SongDetail"]["AudioUrl"]
        duration = resp["Result"]["SongDetail"]["Duration"]
        break
    if status == 3:
        raise RuntimeError(f"Music task failed: {resp['Result'].get('FailureReason')}")
    time.sleep(10)
```

The audio URL points to a `*.douyinvod.com` host with `mime_type=audio_wav`.
Per docs: URL is for transfer use only; download and re-host. URL valid for 1 year.

---

## Step 3 — Trim and mix into video

```bash
# Download the wav
curl -sL -o music_raw.wav "<audio_url>"

# Trim to match video length, add fade-out at the end
ffmpeg -y -i music_raw.wav -t <video_duration> \
  -af "afade=t=out:st=<video_duration - 3>:d=3,volume=0.95" \
  -c:a aac -b:a 192k -ar 48000 \
  music_bed.m4a

# Mix into the final video — SIDECHAIN DUCKING (preferred): music auto-drops while voice
# is present and breathes back in during gaps, so VO is always clearly dominant.
ffmpeg -y -i video_with_voice.mp4 -i music_bed.m4a \
  -filter_complex "\
    [0:a]asplit=2[voice_trigger][voice_out]; \
    [1:a]volume=0.5[music_in]; \
    [music_in][voice_trigger]sidechaincompress=threshold=0.03:ratio=10:attack=10:release=300:makeup=1[music_ducked]; \
    [voice_out][music_ducked]amix=inputs=2:duration=first:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 \
  final.mp4
```

### Why sidechain ducking, not static volume

A static `[music]volume=0.35,amix` is the simple approach but compromises both ways: music either competes with voice during speech, or feels too quiet in gaps. Sidechain ducking solves this by compressing the music *only when voice is loud*.

**Settings explained:**
- `volume=0.5` — music base level before ducking. The compressor pulls it down further during voice.
- `threshold=0.03` — voice amplitude above ~3% of full scale triggers ducking.
- `ratio=10` — heavy compression (10:1) when triggered. Music drops noticeably under voice.
- `attack=10` — 10ms onset so the music ducks before the first phoneme of speech is reached.
- `release=300` — 300ms recovery so music smoothly rises during pauses between phrases.
- `makeup=1` — no extra gain after compression (keep voice dominant).

**Verification with `ffmpeg -af volumedetect`:**
- Voice moments: RMS around -18 dB (loud and clear)
- Music-only gaps: RMS around -22 to -28 dB (audible but supportive, never competing)
- Fade-out tail: RMS below -30 dB

### When to use static volume instead

If sidechain ducking sounds unnatural for the project (e.g. fully musical short with no clear "speak vs not-speak" structure), fall back to static `volume=0.18-0.25`:
```bash
ffmpeg -y -i video_with_voice.mp4 -i music_bed.m4a \
  -filter_complex "[1:a]volume=0.20[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -ar 48000 \
  final.mp4
```
Use `0.18-0.20` (not the older `0.35`) — anything higher competes with the avatar voice.

---

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `code: 50000001 InputLyricsPlagiarized` | Prompt too generic; output matched copyrighted material | Use a richer prompt, specify Segments, or change instrumentation |
| `Status: 3 FailureReason` populated | Generation failed (copyright, content policy, model error) | Inspect `FailureReason.Code` and `Msg`, adjust prompt |
| HTTP 401 / SignatureDoesNotMatch | AK/SK wrong, or service/region in signing wrong | Service must be `imagination`, region `cn-beijing` |
| Empty AudioUrl in response | Task not yet complete | Keep polling — Status will be 0 or 1 |

---

## Prompt patterns for product video music

| Video tone | Prompt template |
|---|---|
| Tech / product launch | "Cinematic uplifting ambient instrumental for a tech product launch, mysterious to confident, soft synth pads, electronic textures, gentle pulsing rhythm, modern futuristic feel, no vocals, instrumental only." |
| Lifestyle / consumer | "Warm cheerful instrumental for a lifestyle product, acoustic guitar, light percussion, optimistic and modern, no vocals." |
| Serious / B2B | "Confident corporate instrumental, piano and strings, focused and clean, gradual build, modern professional feel, no vocals." |
| Energy / sports | "High-energy electronic instrumental, driving beat, synth bass, building tension, motivational, no vocals." |
| Quiet / contemplative | "Slow ambient instrumental, reverberant pads, sparse piano, meditative and calm, no vocals, no rhythm." |
