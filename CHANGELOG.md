# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). Releases are published to PyPI via
the `Publish` workflow (tagged `vX.Y.Z` + GitHub Release, trusted publishing).

## [Unreleased]
### Added
- DoS quotas: opt-in `meta.limits` (`max_rows` records, `max_bytes` payload bytes) enforced fail-closed in `prepare_report` for every output; CLI `--max-rows`/`--max-bytes`
- Chromium egress deny-by-default: outbound http(s) blocked via per-page route guard, opt-in `allowed_hosts` (API/CLI only, never payload); closes ASVS 12.1.1 (opt-in quotas) and 12.6.1 (deny-by-default + allow-list)
- Signing key rotation: `verify_pdf` accepts `{key_id: key}` mappings (envelope `key_id` selects first) and ordered key lists; `verify` takes repeatable `--key-file`; rotation runbook in `docs/STANDARDS.md` §3.3
- CycloneDX 1.6 `sbom.json` attached to every GitHub Release (stable + prereleases), built reproducibly from the release wheel in an isolated CI env
- SAST: Semgrep workflow on PR/push/weekly (registry packs + custom `.semgrep/` rules locking `STANDARDS.md` §3.2), SARIF to code scanning; drive-by: `publish.yml` tag interpolation now via env (shell-injection), `charts.py` pre-built-SVG exemption documented inline
### Docs
- `docs/ROADMAP.md`: prioritized next items, done log v0.1.0→v0.11.0, and non-goals (single source of truth for what comes next)

## [0.11.0] - 2026-11-19
### Added
- Explicit missing data: field `missing_text` (display text for `None`) and `substitutions` (`{raw: display}` map applied before formatting) in HTML, XLSX and CSV; `empty_text` on flat detail lists, `table` sections and `meta` (whole report) renders a message instead of an empty table (note row/line in XLSX/CSV)
- Dynamic pivot tables: `crosstab` sections (`rows`/`columns` buckets, `measure` + `sum|count|avg|min|max`, row/column/grand totals, `empty_text`) in HTML, XLSX and CSV
- Sparklines: `sparkline` format mask (list of numbers → inline SVG `line`/`bar` nanoplot; `spark_kind`/`spark_color` field options) in HTML/PDF, block-art text (`▁▂▃▄▅▆▇█`) in CSV/XLSX
- Provenance: field `footnote` (`"text"` or `{"mark", "text"}`) with auto marks (`*†‡§‖¶`, then numbers) listed per report/section and exported to the XLSX `Notes` sheet and CSV `# [mark]` lines; `meta.source_note` / section `source` provenance lines
- Expressiveness: `median`/`distinct` aggregates; `color_scale` gradient fills (explicit `cell_rules` win) and `data_bar` native Excel bars; `meta.summary_side` top/bottom grand-summary placement; keep-together print CSS for group headers/rows
- Supply-chain visibility: OpenSSF Scorecard workflow (weekly + on push, SARIF to code scanning) and Codecov coverage reporting via OIDC (no stored token; the 85% bar stays on the pytest gate)
### Docs
- `docs/STANDARDS.md`: architecture, engineering, security and design standards
- `docs/ASVS.md`: OWASP ASVS 4.0.3 applicability mapping, plus `SECURITY.md` disclosure policy
- README badges row with divider (CI, PyPI, docs, ASVS, pip-audit, security)
### Security
- Formal alignment: OWASP ASVS 4.0.3 applicability mapping (`docs/ASVS.md`, L1 target with L2/L3 where met), `SECURITY.md` disclosure policy with private vulnerability reporting enabled, Jinja `SandboxedEnvironment` (SSTI defense in depth), `ruff` S-rules, single-char CSV delimiter validation, world-readable key-file warning
- Stored XSS closed: Jinja autoescaping is now enabled (charts/sparklines emit pre-built `Markup` SVG); remote `<link>` stylesheets are stripped before CSS inlining (no server-side fetches); Chromium renders pages with JavaScript disabled
- Spreadsheet formula injection neutralized: text cells starting with `= + - @` (or tab/CR) are `'`-prefixed in CSV/XLSX (numeric values, including negatives, untouched)
- `verify_pdf` is total again: malformed envelopes/keys report `invalid` instead of raising
- `pip-audit` dependency gate and SHA-pinned GitHub Actions in CI

## [0.10.0] - 2026-11-18
### Added
- Compound rule conditions: several comparison operators in one rule combine with AND (`{"gte": 10, "lt": 20}`); new `between` (`[lo, hi]`, inclusive) and `contains` (substring) operators for `cell_rules`, `$print_when` and `visible_when`; `in`/`not_in` against a non-container is a no-match instead of `TypeError`
- Email-safe inline HTML: `inline_css=True` now resolves CSS variables to literal values (Outlook ignores `var()`), sets `<html lang>` from `meta.locale` and declares `color-scheme: light`
- Perf gate: `bench/bench_budgets.json` smoke budgets + `bench.py --check`, enforced as a CI step in the `e2e` job
### Docs
- CHANGELOG consolidated into per-version sections 0.3.0–0.9.0

## [0.9.0] - 2026-11-13
### Added
- Report signing: `sign_pdf`/`verify_pdf` (HMAC-SHA256 stdlib + Ed25519 via `.[sign]` extra), `keygen`/`sign`/`verify` CLI commands, `SignatureInfo` verdicts
- Batch generation: `generate_many` / `agenerate_many` (semaphore-limited concurrency over the shared pool, ordered rejoin)
- Conditional cell formatting: field `cell_rules` (`{operator, color, background, bold, italic}`, first match wins, optional catch-all) in HTML and XLSX
- Email-ready HTML: `inline_css=True` / `--inline-css` (needs `.[email]` extra)
- `bench/bench.py` timing harness (3000-row baseline: render 0.55s, csv 0.53s, xlsx 1.8s)
- Test coverage 100% (85% gate enforced in CI)

## [0.8.0] - 2026-11-12
### Added
- Data inputs: `from_dataframe` (pandas, optional `.[pandas]` extra), `from_csv`, `from_json`; `.csv` CLI input with `--delimiter`; `isis-report schema` JSON Schema export
### Docs
- Wiki linked from README

## [0.7.0] - 2026-11-11
### Added
- Composed documents: `sections` payloads (`table` with the full tabular engine, `text`, `kpi`, `chart` with dependency-free inline SVG `bar`/`line` charts + `build_chart` API)
- `running_balance` field option: cumulative sums computed in row order (e.g. statement balances); opening balance via `{"of": "<field>", "start": <value>}`
- PDF passthrough: `outline` (clickable outline), `tagged` (accessible PDF), `prefer_css_page_size` via `pdf_options`
- XLSX print polish: repeated header rows, frozen panes, autofilters on every sheet
- CSV `--bom` flag / `bom=True` (UTF-8 BOM for Excel)
- Localized page footer from `meta.locale` (pt → "Impresso em / Página X de Y")
- Charts: `pie`/`donut` kinds and horizontal bars
- `mypy` type-check gate in CI
- XLSX/CSV export aware of sections (each section becomes a sheet/CSV section)
### Changed
- Print timestamp moved to the repeated page footer (right side, next to page count), out of the report body
### Docs
- Landing page linked from README

## [0.6.0] - 2026-11-10
### Added
- Output formats: XLSX (one sheet per detail table, bold totals, `Summary` sheet; needs `.[xlsx]` extra) and CSV (locale-formatted, `# table:`/`# summary` sections), plus `collect_tables`; `isis-report generate --format pdf|xlsx|csv|html`

## [0.5.0] - 2026-11-10
### Added
- Report parameters: `meta.page` (size/orientation/margins), field `aggregate`
  (sum/count/avg/min/max → group footers, detail `tfoot`, grand summary),
  `$print_when` row filters, `$order_by` sorting, `visible`/`visible_when` columns

## [0.4.0] - 2026-11-09
### Added
- Locale-aware formatting via `meta.locale` (Babel/CLDR, default `pt-BR`) + `meta.currency` override; `--locale` CLI flag; `percent`, `currency` and `bool` masks locale-aware
### Changed
- Playwright 1.65, dead code and dead CSS removed
### Fixed
- Recursion guard in the `.toon` parser; security model documented

## [0.4.0rc1] - 2026-11-09
### Added
- `py.typed` marker (typed package)
### Fixed
- PyPI packaging metadata
### Changed
- Dependabot bumps (actions + deps) consolidated in one PR

## [0.3.0] - 2026-11-09
### Added
- Custom templates: `template_dir` + `template_name` across the API and CLI
- `meta.printed_at` auto-filled with the print timestamp; custom PDF header/footer via `pdf_options` and CLI flags
- Extra format masks
- Report theming via `meta.accent_color` (overrides the header brand color)
- TestPyPI auto-publish for pre-releases (`vX.Y.ZrcN`)

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
