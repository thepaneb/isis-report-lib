# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). Releases are published to PyPI via
the `Publish` workflow (tagged `vX.Y.Z` + GitHub Release, trusted publishing).

## [Unreleased]
### Added
- Report theming via `meta.accent_color` (overrides the header brand color)
- TestPyPI auto-publish for pre-releases (`vX.Y.ZrcN`)
- `percent`, `currency` and `bool` format masks (now locale-aware)
- `meta.printed_at` auto-filled with the print timestamp; custom PDF header/footer via `pdf_options` and CLI flags
- Locale-aware formatting via `meta.locale` (Babel/CLDR, default `pt-BR`) + `meta.currency` override; `--locale` CLI flag
### Changed
- print timestamp moved to the repeated page footer (right side, next to page count), out of the report body
- `meta.printed_at` auto-filled with the print timestamp; custom PDF header/footer via `pdf_options` and CLI flags
### Changed
- Print timestamp moved to the repeated page footer (right side, next to page count), out of the report body
- Coverage: 85% gate enforced in CI (currently ~97%)

## [0.2.0] - 2026-11-09
### Added
- `isis-report` CLI with `generate` (.json/.toon to PDF) and `render` (HTML to stdout/file) subcommands
- Custom templates: `template_dir` + `template_name` across the API and CLI
- Dynamic version from git tags (`hatch-vcs`); automated PyPI publishing on Release
### Changed
- Full English rebase: code, templates (`base`/`tabular`/`tabular_sections.jinja`), tests, examples, docs
### Fixed
- Wheel shipped empty (hatchling `packages` misconfiguration); templates now bundled correctly
- Sync API no longer leaks Chromium processes (browser closed per call)

## [0.1.1] - 2026-11-09
### Changed
- Infra-only release validating the trusted publishing pipeline

## [0.1.0] - 2026-11-09
### Added
- Initial release: dict/`.toon` to PDF, sync + async API, Jinja2 + Playwright, 31 tests, CI matrix
