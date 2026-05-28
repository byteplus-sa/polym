# Seedance 2.0 API reference

Seedance 2.0 (Dreamina Seedance 2.0) is a BytePlus ModelArk video-generation model. This skill uses it for **all A-roll** (digital-human talking-head) and optionally for cinematic B-roll.

Credentials come from `~/.explainer-video/config.json`:
- `modelark_api_key` — Bearer token for the video/image generation REST API.
- `iam_ak`, `iam_sk` — BytePlus IAM keys for the SigV4-signed asset-library API and for TOS.

> **These endpoints and field names are verified working (2026-05). Earlier drafts of this
> file had the wrong host and a non-existent `asset_uri` content type — do not reintroduce them.**

---

## Endpoints

| Purpose | Endpoint | Auth |
|---|---|---|
| Video generation (create task / poll) | `https://ark.ap-southeast.bytepluses.com/api/v3/contents/generations/tasks` | `Authorization: Bearer <modelark_api_key>` |
| Image generation (Seedream) | `https://ark.ap-southeast.bytepluses.com/api/v3/images/generations` | `Authorization: Bearer <modelark_api_key>` |
| Asset library (CreateAssetGroup / CreateAsset / GetAsset) | `https://ark.ap-southeast-1.byteplusapi.com/?Action=<...>&Version=2024-01-01` | **Volcengine SigV4** with `iam_ak`/`iam_sk`, service `ark`, region `ap-southeast-1` |

Model ID: `dreamina-seedance-2-0-260128`.

---

## Why the asset library is mandatory for real people

The video-generation API runs content moderation on inputs. A real person passed as a
**raw image/video URL** is rejected:
`InputImageSensitiveContentDetected.PrivacyInformation` /
`InputVideoSensitiveContentDetected.PrivacyInformation`.

The fix: upload the asset to the ModelArk **asset library**, wait for `Status: Active`,
then reference it inside the generation `content` array as **`asset://<AssetId>`**.
Approved assets are trusted and skip re-moderation. This is the only working path for
real-person A-roll.

The `content` array `type` field accepts **`text`, `image_url`, `audio_url`, `video_url`,
`draft_task`** — there is **no `asset_uri` type**. An approved asset is referenced by
putting `asset://<AssetId>` in the `url` field of an `image_url` / `video_url` item.

---

## Step 0 — Asset library workflow (SigV4)

The asset API is a Volcengine "Action" API — sign with SigV4 (`iam_ak`/`iam_sk`).

```python
import json, os, requests
from volcengine.auth.SignerV4 import SignerV4
from volcengine.Credentials import Credentials
from volcengine.base.Request import Request

HOST = "ark.ap-southeast-1.byteplusapi.com"

def call_ark(action, body, ak, sk):
    req = Request()
    req.method, req.scheme, req.host, req.path = "POST", "https", HOST, "/"
    req.query = {"Action": action, "Version": "2024-01-01"}
    req.headers = {"Content-Type": "application/json", "Host": HOST}
    req.body = json.dumps(body)
    SignerV4.sign(req, Credentials(ak, sk, "ark", "ap-southeast-1"))
    r = requests.post(f"https://{HOST}/", params=req.query, data=req.body, headers=req.headers, timeout=60)
    return r.json()
```

**CreateAssetGroup** → `call_ark("CreateAssetGroup", {"Name": "...", "Description": "..."})`
→ `Result.Id` (e.g. `group-2026...`).

**CreateAsset** — field names are exact (`GroupId`, `URL`, `AssetType`):
```python
call_ark("CreateAsset", {
    "GroupId": "<group id>",
    "Name": "portrait-xyz",
    "AssetType": "Image",          # "Image" or "Video"
    "ContentType": "image/jpeg",   # or "video/mp4"
    "URL": "<a TOS presigned URL of the file>",
})  # → Result.Id = "asset-2026..."
```

**GetAsset** — poll until approved:
```python
call_ark("GetAsset", {"Id": "<asset id>"})  # → Result.Status == "Active" when ready
```

The local file must first be uploaded to TOS (use the `tos-upload` skill) to get the `URL`.
Run TOS uploads with the proxy disabled (`HTTPS_PROXY="" NO_PROXY="*"`).

**Asset size limits:**
- Image asset: ≥ 300×300 px.
- Video asset: **pixel count 409,600–2,086,876** (e.g. 720×1280 = 921,600 ✓, 1080×1920 = 2,073,600 ✓, 405×720 = 291,600 ✗ too small).

---

## Step 1 — Video generation (A-roll)

`POST /api/v3/contents/generations/tasks`, `Authorization: Bearer <modelark_api_key>`.

### Mode A — image + text (native 9:16, generated voice)

```json
{
  "model": "dreamina-seedance-2-0-260128",
  "content": [
    {"type": "text", "text": "The man from the image speaks directly to the camera in a warm, confident tone, saying: \"<the spoken line>\". Clean modern office background, photorealistic."},
    {"type": "image_url", "image_url": {"url": "asset://<portrait AssetId>"}}
  ],
  "parameters": {"aspect_ratio": "9:16", "duration": 6, "resolution": "720p"}
}
```
- Honors `aspect_ratio: "9:16"` → native 720×1280 output.
- Voice is Seedance-generated (no cloning). The person speaks the quoted line in the prompt.

### Mode B — r2v (reference-to-video)

```json
{
  "model": "dreamina-seedance-2-0-260128",
  "content": [
    {"type": "text", "text": "The person keeps the exact face and appearance of the reference image, with the voice and facial-muscle motion of the reference video, saying: \"<the spoken line>\"."},
    {"type": "image_url", "image_url": {"url": "asset://<portrait AssetId>"}, "role": "reference_image"},
    {"type": "video_url", "video_url": {"url": "asset://<reference video AssetId>"}, "role": "reference_video"}
  ],
  "parameters": {"aspect_ratio": "9:16", "duration": 10, "resolution": "720p"}
}
```
- The image (`role: reference_image`) drives appearance; the video (`role: reference_video`) drives voice character + facial motion.
- **Output follows the reference video's aspect ratio** — the reference video MUST be 9:16 for a 9:16 result. Centre-crop a landscape source, then scale so the asset is within the pixel-count limits.
- Reference video must be **≤ 15.2 s**.
- To control the spoken words, put the script in the `text` prompt (the reference video then supplies voice character + facial style).
- `resolution` in `parameters` is effectively capped by the reference video's resolution — for a sharper result, make the reference-video asset 1080×1920.

### Parameters

| Param | Values |
|---|---|
| `aspect_ratio` | `"9:16"` (use this), `"16:9"`, `"1:1"` |
| `duration` | 5–10 (seconds) |
| `resolution` | `"720p"`, `"1080p"` |

Response: `{"id": "cgt-..."}`.

---

## Step 2 — Poll the task

`GET /api/v3/contents/generations/tasks/<task_id>`, `Authorization: Bearer <key>`.

Poll every ~15–20 s. Status is `queued` → `running` → `succeeded` / `failed`.
On `succeeded`, the video URL is at `content.video_url` (or `output.url`). Download it.

**Reliability note:** parallel r2v tasks occasionally stall — a task can sit on `running`
with a stale `updated_at` for many minutes. Before resubmitting, re-query: stalled tasks
often still finish. If a task's `updated_at` has not advanced for ~10+ minutes, resubmit it.

---

## Cinematic B-roll (optional, non-person)

Seedance can also do text-to-video for non-person cinematic B-roll:
```json
{"model": "dreamina-seedance-2-0-260128",
 "content": [{"type": "text", "text": "<cinematic prompt>"}],
 "parameters": {"aspect_ratio": "9:16", "duration": 5, "resolution": "720p"}}
```
Most B-roll in this skill is HyperFrames (typographic / data scenes) — see
`references/production-techniques.md`. Use Seedance B-roll only for non-person
cinematic shots. Avoid humanoid robots / mech / anime (triggers output moderation).

---

## Python helpers

```python
import json, urllib.request, urllib.error

BASE = "https://ark.ap-southeast.bytepluses.com/api/v3"

def submit_task(key, content, parameters):
    body = json.dumps({"model": "dreamina-seedance-2-0-260128",
                       "content": content, "parameters": parameters}).encode()
    req = urllib.request.Request(f"{BASE}/contents/generations/tasks", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["id"]

def poll_task(key, task_id):
    req = urllib.request.Request(f"{BASE}/contents/generations/tasks/{task_id}",
        headers={"Authorization": f"Bearer {key}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
```

Install the Volcengine SDK for the asset-library SigV4 calls:
`pip3 install --break-system-packages volcengine requests`.
