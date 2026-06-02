---
name: polym-seed3d
description: Generate textured 3D models (GLB + PBR) from an image and/or text prompt via Volcengine Ark Seed3D (doubao-seed3d). Use for image-to-3D / text-to-3D, "把图片转成3D模型", "生成一个3D模型", "Seed3D"; submits, polls, downloads the .glb. Domestic Volcengine Ark only, not BytePlus overseas.
---

# Seed3D (Volcengine Ark)

Generate a 3D model from a reference image and/or a text prompt via Volcengine Ark Seed3D
(`doubao-seed3d`). Seed3D is an **async task API**: submit → poll → download a `.zip` that
contains a textured `.glb` (mesh + UVs + baseColor + metallic-roughness PBR maps).

Verified working 2026-06-02 against `doubao-seed3d-2-0-260328` on the domestic endpoint.

## When to use this skill
- Image-to-3D: turn a reference image into a textured 3D mesh.
- Text-to-3D: generate a 3D asset from a text prompt.
- Steered generation: combine an image + a prompt.
- Re-attach to / poll an already-submitted Seed3D async task and download the `.glb`.

## When NOT to use this skill
- You want a BytePlus **overseas** 3D model — Seed3D is domestic-only; overseas
  ModelArk offers Hyper3D / Hitem3d instead (different skill/API).
- You only need a 2D image — use an image-generation skill (e.g. `seedream`).

## Prerequisites
- **`ARK_API_KEY`** — a **domestic Volcengine** Ark API key (UUID form, e.g.
  `512d8492-...`). NOT a BytePlus overseas key. If set in the shell, use it;
  otherwise ask the user and `export ARK_API_KEY="..."` before running.
- `python3 >= 3.10` (standard library only — no extra pip installs).
- Endpoint defaults to `https://ark.cn-beijing.volces.com/api/v3`.
  Do **not** point this at `ark.ap-southeast.bytepluses.com` (no Seed3D there).

## Model
- **`doubao-seed3d-2-0-260328`** — Seed3D 2.0 (default). Image and/or text input →
  textured GLB. A task typically takes ~3–6 minutes; usage ≈ 30k tokens/task.
- Echoes `subdivisionlevel` (default `medium`) and `fileformat` (default `glb`).

## Quickstart
```bash
export ARK_API_KEY="..."   # domestic Volcengine key
python3 scripts/seed3d.py \
  --image /path/or/url/to/sofa.jpg \
  --download \
  --output-dir out/sofa_3d
```
- Image-to-3D: pass `--image` (http(s) URL, `data:` URL, or local file — local
  files are inlined as base64 automatically).
- Text-to-3D: pass `--prompt` alone. Steered: pass both `--image` and `--prompt`.
- Optional: `--subdivision-level {low,medium,high}`, `--file-format {glb,obj,fbx,usdz,...}`,
  `--draft` (faster), `--extra KEY=VALUE` for any other top-level field.
- Polling: `--poll-interval` (default 10s), `--max-wait` (default 900s).
- Re-attach to a running task: `--task-id cgt-...` (skips submission, just polls/fetches).

On `succeeded`, `content.file_url` is a `.zip` (24h TTL). With `--download --output-dir`
the script saves `model.zip`, extracts it (e.g. `model/pbr/mesh_textured_pbr.glb`),
and writes `task.json`.

## Tips
- For image-to-3D, use a clean reference: single object, centered, **pure white
  seamless background, even lighting, no props**. Use a **colored / patterned**
  subject for an obvious texture — a near-white subject yields a near-white albedo
  that looks like untextured "white clay". (Often paired with the `seedream` skill
  to produce the reference image first.)
- View the `.glb` by dragging into a web viewer (gltf-viewer.donmccurdy.com,
  sandbox.babylonjs.com) or Blender (`File → Import → glTF 2.0`). macOS Quick Look
  needs a `.usdz` conversion (Apple Reality Converter) for space-bar preview / AR.
- To confirm textures exist, check the GLB for `images`, `textures`,
  `materials[].pbrMetallicRoughness.baseColorTexture`, and a `TEXCOORD_0` mesh attribute.

## Raw API (without the script)
```bash
# 1) submit
curl -X POST "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks" \
  -H "Authorization: Bearer $ARK_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"doubao-seed3d-2-0-260328",
       "content":[{"type":"image_url","image_url":{"url":"<IMAGE_URL>"}}]}'
# -> {"id":"cgt-..."}

# 2) poll until status == succeeded
curl "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/cgt-..." \
  -H "Authorization: Bearer $ARK_API_KEY"
# succeeded -> content.file_url is a .zip containing pbr/mesh_textured_pbr.glb
```
Same shared async `contents/generations/tasks` interface as Seedance video, differentiated by `model`.

## Constraints
- Don't hard-code the API key; prefer `export ARK_API_KEY="..."`.
- Don't point Seed3D at the BytePlus overseas endpoint — the model isn't there.
- Result URLs expire (~24h); download promptly when the user needs the file.

## IO contract (must match manifest.yaml)
- Reads: `local-filesystem/reference-images` (the optional `--image` input).
- Writes: `local-filesystem/generated-assets` — the downloaded/extracted `.glb`
  (+ `model.zip`, `task.json`) under `--output-dir`.
