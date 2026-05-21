# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/).
Semver per `manifest.yaml`. Breaking changes must include a "Migration" note.

## [Unreleased]

## [0.1.0] - 2026-05-21
### Added
- Initial import from `autocase-image-gen` (Bojie Sun, internal). Drives
  `autocase.bytedance.net/arena` via Claude in Chrome to generate gpt-image-2
  (ChatGPT-image-2) images. Stopgap until AIDP exposes gpt-image-2 — once it
  does, prefer `polym-eval-generate-gpt-image` with `--model gpt-image-2`.

### Notes from initial end-to-end test (May 21, 2026)
Four issues found in the upstream SKILL.md and fixed in this version:
- `find` returned the wrong element for both the 图片 tab (gave 语言) and the
  send button (gave the fullscreen-toggle icon). The workflow now tells
  callers to click these by coordinate, not via `find`.
- The prompt textarea is a styled contenteditable DIV; `left_click` + `type`
  often does nothing. Switched to `form_input(ref, value)`.
- The generated image renders below the visible viewport; polling by
  screenshot misses completion. The workflow now polls
  `document.body.innerText` for the string `总耗时 <N> s` via `javascript_tool`.
- AutoCase shows a 30-second "自动授权" SSO modal on first visit; the workflow
  now waits for it explicitly before interacting.

End-to-end timing (text-to-image, High quality, 1 image):
nav + auth ~35 s · model select ~5 s · prompt ~2 s · generate ~168 s ·
download ~5 s · **total ~3.5 min**.
