# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). Releases are published to PyPI via
the `Publish` workflow (tagged `vX.Y.Z` + GitHub Release, trusted publishing).

## [Unreleased]
### Added
- Data inputs: `from_dataframe` (pandas, optional `.[pandas]` extra), `from_csv`, `from_json`; `.csv` CLI input with `--delimiter`; `isis-report schema` JSON Schema export
- PDF passthrough: `outline` (clickable outline), `tagged` (accessible PDF), `prefer_css_page_size` via `pdf_options`
- XLSX print polish: repeated header rows, frozen panes, autofilters on every sheet
- CSV `--bom` flag / `bom=True` (UTF-8 BOM for Excel)
- Localized page footer from `meta.locale` (pt → "Impresso em / Página X de Y")
- `running_balance` opening balance: `{"of": "<field>", "start": <value>}`
- Charts: `pie`/`donut` kinds and horizontal bars
- `mypy` type-check gate in CI
- Composed documents: `sections` payloads (`table` with the full tabular engine, `text`, `kpi`, `chart` with dependency-free inline SVG `bar`/`line` charts + `build_chart` API)
- `running_balance` field option: cumulative sums computed in row order (e.g. statement balances)
- XLSX/CSV export aware of sections (each section becomes sheet/CSV section)
- Output formats: XLSX (one sheet per detail table, bold totals, `Summary` sheet; needs `.[xlsx]` extra) and CSV (locale-formatted, `# table:`/`# summary` sections), plus `collect_tables`; `isis-report generate --format pdf|xlsx|csv|html`
- Report parameters: `meta.page` (size/orientation/margins), field `aggregate`
  (sum/count/avg/min/max → group footers, detail `tfoot`, grand summary),
  `$print_when` row filters, `$order_by` sorting, `visible`/`visible_when` columns
- Report theming via `meta.accent_color` (overrides the header brand color)
- TestPyPI auto-publish for pre-releases (`vX.Y.ZrcN`)
- `percent`, `currency` and `bool` format masks (now locale-aware)
- `meta.printed_at` auto-filled with the print timestamp; custom PDF header/footer via `pdf_options` and CLI flags
- Locale-aware formatting via `meta.locale` (Babel/CLDR, default `pt-BR`) + `meta.currency` override; `--locale` CLI flag
### Changed
- print timestamp moved to the repeated page footer (right side, next to page count), out of the report body
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
