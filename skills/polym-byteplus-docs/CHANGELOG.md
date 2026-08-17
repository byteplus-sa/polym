# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/).
Semver per `manifest.yaml`. Breaking changes must include a "Migration" note.

## [Unreleased]

### Changed
- Synced documentation index from byteplus-docs-llms (source commit: 76b31f198874b02d839ca7219544373d6d3fcb3e).
- Updated llms.txt with refreshed BytePlus documentation links.

## [0.1.0] - 2026-07-23

### Added

- Imported the personal `byteplus-docs` skill as the native
  `polym-byteplus-docs` experimental skill.
- Bundled a snapshot of 21,050 official BytePlus documentation links across
  106 product sections.
- Added the standard-library `scripts/search_docs.py` discovery helper.
- Added Polym governance metadata, deterministic unit tests, smoke validation,
  and agent evaluation prompts.

### Changed

- Replaced personal installation paths with the portable Polym skill directory
  contract.
- Split backend VOD discovery into server-side upload and server SDK queries.
