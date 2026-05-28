# Seedream 4.5 API reference

Seedream 4.5 is the BytePlus ModelArk image model. This skill uses it in **Phase 2** to
optionally restyle the user's portrait (new outfit / environment / lighting) before
generating the A-roll.

Credentials: `modelark_api_key` from `~/.explainer-video/config.json`.

---

## Endpoint

`POST https://ark.ap-southeast.bytepluses.com/api/v3/images/generations`
Header: `Authorization: Bearer <modelark_api_key>`

Model ID: `seedream-4-5-251128`.

---

## Image edit (restyle the portrait)

```json
{
  "model": "seedream-4-5-251128",
  "prompt": "<the restyle instruction>",
  "image": "<a TOS presigned URL of the source portrait>",
  "size": "1440x2560",
  "response_format": "url"
}
```

- `image` — a downloadable URL of the source portrait (upload the local file to TOS first;
  run TOS uploads with the proxy disabled). Accepts a string URL or an array of URLs.
- `size` — **the pixel count must be ≥ 3,686,400**. For 9:16 use **`"1440x2560"`**
  (3,686,400 px exactly). `1080x1920` is rejected (`image size must be at least 3686400 pixels`).
- The edit returns **one** image per call. The `n` parameter is not honored for edits.

## Generating 4 variations (Phase 2 review step)

Seedream returns one image per request, so fire **4 requests in parallel** (threads) with
the same prompt — natural sampling variance gives 4 distinct options. Download all 4,
build a 2×2 contact sheet, and let the user review: pick one / revise the prompt and
regenerate / skip.

```python
import json, urllib.request, concurrent.futures

URL = "https://ark.ap-southeast.bytepluses.com/api/v3/images/generations"

def generate_one(key, prompt, src_url, idx):
    body = json.dumps({"model": "seedream-4-5-251128", "prompt": prompt,
                       "image": src_url, "size": "1440x2560",
                       "response_format": "url"}).encode()
    req = urllib.request.Request(URL, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    out_url = json.loads(urllib.request.urlopen(req, timeout=240).read())["data"][0]["url"]
    urllib.request.urlretrieve(out_url, f"seedream-v{idx}.jpg")
    return f"seedream-v{idx}.jpg"

def generate_four(key, prompt, src_url):
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        return list(ex.map(lambda i: generate_one(key, prompt, src_url, i), [1,2,3,4]))
```

---

## Prompt guidance for portrait restyle

Write the prompt to **preserve identity** and only change styling. Cover:
- Keep the person's face, glasses, hairstyle and identity exactly — photorealistic.
- The requested outfit / clothing.
- The requested environment / background and lighting.
- 9:16 vertical framing, subject centred.
- "natural realistic skin texture, not over-beautified" — Seedream tends to either
  over-smooth or over-texture skin; state the desired level explicitly.
- "do NOT place the person inside a phone / screen / device / frame" — Seedream will
  otherwise sometimes render a literal phone mock-up when it sees "phone-screen / 9:16".

## Notes

- Seedream stamps a small **"AI generated"** watermark in a corner. If the restyled
  portrait will be re-used downstream (e.g. fed to Seedance), remove it by cropping the
  affected strip and re-cropping to a clean 9:16 — do not run a second AI pass over an
  already-AI-edited image (it compounds artifacts and degrades quality).
- Editing an already-AI-generated image again visibly lowers quality. Always restyle
  from the **original photo**, applying all desired changes in a single pass.
