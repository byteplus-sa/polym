---
name: polym-autocase-image-gen
description: Generate images with gpt-image-2 (ChatGPT-image-2) via the internal AutoCase playground (autocase.bytedance.net/arena), supporting reference images for image-to-image. Use when the user wants gpt-image-2 / ChatGPT-image-2 — text-to-image, or image-to-image driven by reference photos. Trigger on "generate with gpt-image-2", "use autocase playground", "ChatGPT-image-2 一张图", "用 autocase 出图". Drives a real Chrome browser, shows the result inline, and saves it to ~/Downloads (or a folder the user specifies).
---

# AutoCase Image Generation (gpt-image-2)

Drive the internal AutoCase playground to generate an image with **gpt-image-2** — labelled **ChatGPT-image-2** in the AutoCase UI. Supports plain text-to-image and image-to-image with one or more reference images.

> **Stopgap.** Once AIDP exposes gpt-image-2, prefer [polym-eval-generate-gpt-image](../polym-eval-generate-gpt-image/) with `--model gpt-image-2` — it is API-based, ~10× faster end-to-end, scriptable, and needs no browser. Track that skill's CHANGELOG.

## Prerequisites

- The **Claude in Chrome** extension must be connected (`mcp__Claude_in_Chrome__*` tools). If not, ask the user to open Chrome with the extension signed in.
- The user must already be logged in to `autocase.bytedance.net` in that Chrome profile. This skill does **not** handle login. If a login wall appears, stop and ask the user to log in.
- On the **first** visit in a session, AutoCase shows a "自动授权 …Xs" modal and runs SSO for ~30 seconds. Wait for the modal to disappear before any interaction.

## Inputs to collect first

1. **Prompt** — required. If the user asked you to come up with one, do so; otherwise ask.
2. **Reference images** — zero or more absolute local paths (`jpg`, `jpeg`, `png`, `webp`, `heif`). Optional; steers image-to-image. If the user mentioned reference images without paths, ask.
3. **Download location** — default `~/Downloads`. Use another folder only if specified.
4. **Output filename** — default a short slug from the prompt (e.g. `neon-city-night.png`).

## Workflow

### 1. Connect to the browser
- `list_connected_browsers` → if exactly one, `select_browser` with its `deviceId`. If none, ask the user to connect Chrome. If several, ask which.
- `tabs_context_mcp` with `createIfEmpty: true`. Reuse the empty tab or `tabs_create_mcp` for a fresh one. Use that `tabId` for every later step.

### 2. Open the playground
- `navigate` to `https://autocase.bytedance.net/arena`. First navigation to this domain in a session may trigger a one-time MCP permission prompt — expected; once approved, retry.
- Wait, then screenshot. If you see the "自动授权 …Xs" modal, wait another 25–30 seconds. Confirm the "Play with Cases" playground loads and the user's name appears at the bottom-left. If a login screen appears, stop and ask the user to log in.

### 3. Select the gpt-image-2 model
- Open the model picker by clicking the model-name dropdown near the top (default is e.g. Doubao-Seed-2.0-pro).
- Click the **图片** tab in the "选择模型" panel. **Do not rely on `find` to locate tabs** — in practice `find` may return the wrong tab (e.g. 语言 instead of 图片). Click by coordinate from a screenshot, or by exact text match. The tabs sit in order: 对比推荐 / 精选 / 语言 / 图片 / 视频.
- Under **OpenAI**, click **ChatGPT-image-2**. The picker should close and the model column header should now read "ChatGPT-image-2 preview".
- **Comparison mode is rare in this flow.** Current UI replaces the active model when you pick from a tab. If you somehow end up with multiple columns, close each extra one with its `×` button until ChatGPT-image-2 is alone.

### 4. Attach reference images (skip for text-to-image)
The page has a **hidden** `<input type="file" multiple>` accepting `jpg/jpeg/png/webp/heif`.
- Do **not** click the "图片" upload button in the input box — it opens a native OS file dialog you cannot control.
- Instead, upload straight to the hidden input:
  - Use `find` (query like "file input for uploading images") or `read_page` to get the input element's `ref`.
  - Call `file_upload` with that `ref` and the absolute path(s). Multiple paths in one call.
- Screenshot to confirm thumbnails appear.

### 5. Enter the prompt
- Find the prompt textarea with `find` (query: "prompt textarea 输入内容").
- **Use `form_input` to set the value, not `left_click` + `type`.** The textarea is a styled DIV with contenteditable behaviour; click-then-type often fails silently. `form_input(ref, value)` is reliable.
- Quality and count controls ("高/中/低" and "上限N张") sit just below the textarea. Defaults are High + 1 image. Raise "上限N张" only if the user asked for multiple.

### 6. Generate
- The send button is the blue arrow at the **bottom-right** of the input box. The icon at the **top-right** is a fullscreen toggle (tooltip "全屏") — clicking it is a no-op for sending and `find` has been observed to return it when asked for "send button". **Click the bottom-right arrow by coordinate**, not via a `find` ref. The button sits roughly at `(viewport_width - 200, input_box_bottom - 10)` — read it off a fresh screenshot.
- After sending, the URL gains `?id=arn-<uuid>` and a "Waving Friend…" style auto-named case appears in the left sidebar. That confirms submission.

### 7. Wait for completion — **use DOM polling, not screenshots**
- Generation at High quality typically takes **2–3 minutes** for gpt-image-2 (~168 s in tests).
- The generated image renders inside a scrollable chat area and is often **below the visible viewport** — a screenshot of the input area will look empty even after the image is ready. Don't trust screenshots alone.
- Poll `document.body.innerText` for the completion marker `总耗时 <N> s` via `javascript_tool`. Example check:
  ```js
  /总耗时\s+[\d.]+\s*s/.test(document.body.innerText)
  ```
  When that matches, generation is done. Poll every ~15 seconds; treat absence after 4 minutes as failure.

### 8. Show the result
- After completion, scroll the chat area down so the generated image is on screen (`computer scroll` at the chat region, direction `down`, a few ticks).
- Click the image to open the full-size viewer.
- Capture it with the `zoom` action over the image region and `save_to_disk: true`, so the user sees the image inline in your reply.

### 9. Download and save
- Chrome always downloads into `~/Downloads`, regardless of the final target folder. Note the newest file first so you can identify the new one:
  `ls -t ~/Downloads | head -1`
- In the open viewer, click the **download icon** (↓, top-right). The file lands in `~/Downloads` with a **UUID filename** (e.g. `967bf258-….png`). A blank tab may flash and close — ignore it.
- Wait ~2–3 seconds, then locate the newest PNG:
  `ls -t ~/Downloads/*.png | head -1`
- `mv` it to the final destination:
  - Default: rename in place → `~/Downloads/<slug>.png`.
  - If the user gave a folder or path: move it there (`mkdir -p` first if needed).
- Confirm the file exists; note its absolute path.

### 10. Report
Tell the user the image is done, show the inline screenshot, give the final saved path. Offer to regenerate with a tweaked prompt, add/swap references, or try a side-by-side with another AutoCase model.

## Notes & gotchas

- **Generated image URLs are signed and short-lived** — `curl`/`wget` won't fetch them. The viewer's download button is the only reliable save path.
- **No batch / poor concurrency.** ~3.5 minutes wall-clock per single image (auth + select + 168 s generation + download). Not suitable for evaluation pipelines; for that, wait for AIDP to expose gpt-image-2 and use [polym-eval-generate-gpt-image](../polym-eval-generate-gpt-image/).
- **MCP safety filter** redacts cookies/tokens. Don't try to dump cookies or auth headers from this skill — querying `document.cookie` returns `[BLOCKED: Cookie/query string data]`.
- **`find` is best for content-named elements** (e.g. "ChatGPT-image-2", "download icon"), not for generic UI roles like "tab" or "send button". For those, prefer coordinate clicks read off the latest screenshot.
- The file input accepts **multiple** images — upload every reference path in one `file_upload` call.
- This skill is tuned for gpt-image-2. The same flow works for other AutoCase models (Doubao-Seedream, Gemini-image, etc.) — pick that model in step 3 — but the polling marker and timing assumptions are specific to gpt-image-2.
