# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/).
Semver per `manifest.yaml`. Breaking changes must include a "Migration" note.

## [Unreleased]

## [0.1.0] - 2026-09-10

### Added

- Imported the personal `byteplus-ppt-creator` skill as the native
  `polym-byteplus-ppt-creator` experimental skill.
- Bundled the February 2026 BytePlus Presentation Template (20 slides, 16:9).
- Added the 20-slide template catalog with roles, regions, colors, and usage guidance.
- Added `scripts/create_starter_deck.mjs` for creating clean starter decks from
  selected template slides.
- Added `scripts/validate_byteplus_pptx.py` for PPTX structural validation.
- Added Polym governance metadata, unit tests, smoke validation, and eval scenarios.

### Changed

- Renamed skill from `byteplus-ppt-creator` to `polym-byteplus-ppt-creator` to
  follow Polym naming conventions.
- Updated SKILL.md frontmatter to match Polym conventions (name, description).
