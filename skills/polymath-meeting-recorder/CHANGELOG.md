# Changelog

## 0.1.2 — 2026-05-16

- Demoted to `stage: experimental` while the Syncore upstream stabilizes.
  Now excluded from bulk installs (`polymath install all`,
  `polymath install profile:sa-mvp`); still installable explicitly via
  `polymath install polymath-meeting-recorder`.

## 0.1.1 — 2026-05-13

- Renamed package to `polymath-meeting-recorder` to adopt the Polymath `polymath-` prefix convention.

## 0.1.0 — 2026-05-13

- Initial `polymath-meeting-recorder` skill.
- Uses Lark Calendar (`lark-cli calendar +agenda`) for current-meeting lookup instead of Google Calendar.
- Starts/stops Syncore note-taker recording.
- Supports mid-meeting progress checks and Q&A.
- Requires finalization sequence: `end_session` -> AI summary -> `finalize_meeting`.
- Saves final summary to SA Lark Wiki via `polymath-sa-wiki` and to local wiki when available.

