# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/).
Semver per `manifest.yaml`. Breaking changes must include a "Migration" note.

## [Unreleased]

## [0.1.0] - 2026-06-16
### Added
- Initial release. Drives Seedance 2.0 Mini via the BytePlus console
  experience-center BFF (no public OpenAPI).
- `creds.py` — credential manager: onboard/refresh/status, caches Chrome cookie
  + csrfToken + AK/SK to `~/.seedance_mini/creds.json` (chmod 600), reads
  keychain only at onboarding.
- `mini.py` — BFF client + 素材库 (Assets API) upload + high-level
  `upload_asset` / `generate` / `wait_for_tasks` / `list_tasks`. CLI: `upload`,
  `gen`, `get`, `list`.
- `assets.py` — Assets API SigV4 client (vendored from the seedance-2-0 skill,
  pure stdlib).
- Supports T2V, image/video-reference I2V/R2V, first/last frame, and
  human-portrait references (routed through 素材库 to pass input moderation).
