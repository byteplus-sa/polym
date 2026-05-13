# Changelog

## 0.1.0 — 2026-05-13

- Initial `meeting-recorder` skill.
- Uses Lark Calendar (`lark-cli calendar +agenda`) for current-meeting lookup instead of Google Calendar.
- Starts/stops Syncore note-taker recording.
- Supports mid-meeting progress checks and Q&A.
- Requires finalization sequence: `end_session` -> AI summary -> `finalize_meeting`.
- Saves final summary to SA Lark Wiki via `sa-wiki` and to local wiki when available.

