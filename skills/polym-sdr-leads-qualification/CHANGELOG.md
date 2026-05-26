# Changelog

All notable changes to this skill. Format: [Keep a Changelog](https://keepachangelog.com/).
Semver per `manifest.yaml`. Breaking changes must include a "Migration" note.

## [Unreleased]

## [0.2.0] - 2026-05-21
### Added
- Multi-provider LLM support via LiteLLM: Anthropic, OpenAI, Google Gemini, BytePlus Ark, Azure, and any other LiteLLM-compatible provider.
- `LLM_PROVIDER` env var and `--provider` CLI flag. Auto-detected from model name if omitted.
- `LLM_API_BASE` / `--api-base` override for custom endpoints (e.g. BytePlus Ark).
- Unit test suite (`tests/test_provider.py`) — 34 tests covering routing logic, JSON parsing, title seniority, and all provider adapter paths.

### Changed
- `runner/score_csv.py`: replaced hand-rolled urllib HTTP client with `litellm.completion()`.
- **Migration**: add `pip install litellm` to your environment before running the scorer.

## [0.1.0] - 2026-05-21
### Added
- Initial skill package: standalone CSV scorer (`runner/score_csv.py`).
- Campaign packs for Seedance and Kling with ICP, signals, qualification, disqualification, and product context.
- Shared campaign rules: scoring framework, signal taxonomy, disqualification rules, evidence extraction.
- Docs: RUNBOOK.md and EXAMPLES.md with command examples and operational notes.
