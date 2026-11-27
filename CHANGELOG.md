# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/). Releases are published by the
`Publish` workflow on a `vX.Y.Z` tag push: it builds, attaches the assets to a
draft GitHub Release, uploads to PyPI via trusted publishing and publishes the
release last.

## [Unreleased]
### Added
- Local Jev review tooling: English reports/questions, path-based auto-packs, calibration harness, release preflight (local and `--remote`) and advisory CI artifacts with compact sticky comments
- Monthly Jev calibration reminder workflow (no API call or secret)
- Reusable isis-report-lib logo assets for the docs site, README and favicon, generated from the report template
### Changed
- The Jev review CI workflow now uses `--auto-packs` for PRs and only comments when there are findings or a `comment`/`block` verdict
### Fixed
- The docs header revalidates the cached GitHub release tag hourly, so long-lived tabs no longer keep an old project version

## [0.17.0] - 2026-11-27
### Added
- `AI_USAGE.md`, docs security page and `security.txt`; AI-assisted contribution disclosure in CONTRIBUTING and the PR template
- `render_text`/`arender_text` (and `.toon` variants): visible-only, sanitized plain-text export with a `REPORT DATA` boundary for AI/RAG ingestion
### Changed
- Docker runtime lock bumped to 0.16.0; the local image matches the published release
### Security
- Validation errors no longer include payload values; messages name the field/path and expected type, and the schema-validation cause is suppressed so Pydantic never logs input values
- Documented AI-ingestion and prompt-injection guidance; agents now follow explicit untrusted-content and secrets rules

## [0.16.0] - 2026-11-26
### Added
- Runnable `demo/` folder: a board-pack payload that renders PDF/HTML/XLSX/CSV with TOC, watermark, KPI, crosstab and native XLSX charts
- Portuguese (pt-BR) quickstart page in the documentation, linked from the site navigation
- GHCR image (`ghcr.io/thepaneb/isis-report-lib`) built from the release wheel and pushed by `publish.yml`; stable releases also update `latest`
### Changed
- Dockerfile pins the Python base image by digest and installs the runtime from a hash-pinned `docker/requirements.txt`
- Fork PRs with only docs/config changes get trusted empty GuardDog, Semgrep and CodeQL analyses from `fork-sarif.yml`; code- or dependency-changing forks still need a same-repo integration branch

## [0.15.1] - 2026-11-26
### Added
- Composite GitHub Action (`.github/actions/render`) that installs a pinned release and skips Chromium for non-PDF outputs, plus an example workflow (`examples/github-action.md`)
- `Dockerfile` with Chromium and fonts, including a build-time PDF smoke test
- Issue forms, pull request template, Discussions and starter `good first issue`s for contributors
### Fixed
- `examples/sales_order.toon` no longer carries the legacy `meta.type` key, so the committed example passes the strict payload gate

## [0.15.0] - 2026-11-26
### Added
- `image` sections (data-URI PNG/JPEG/WebP/GIF, `alt`/`caption`/`width`/`align`), `meta.logo` and `meta.watermark` (string or `{text, opacity, color, angle, size}`); images are payload-only, capped at 2 MiB decoded, and SVG is rejected
- `toc` sections with internal links to every titled section
- Native Excel charts for `chart` sections (`bar`/`line`/`pie`/`donut`, including horizontal bars)
- PDF outline/bookmarks generated from headings by default (implies a tagged PDF; `pdf_options={"outline": False}` opts out)
### Changed
- XLSX chart sections keep the label/value data table and add a native Excel chart

## [0.14.0] - 2026-11-25
### Added
- Operator-level DoS quotas: `DEFAULT_LIMITS` (1M records / 64 MiB) enforced by default, `limits=` on the API and CLI `--max-rows/--max-bytes/--unlimited`; payload `meta.limits` may only tighten
- `--require-key-permissions` on `sign`/`verify` to fail (instead of warn) on POSIX when a key file is group/other-readable
### Changed
- HMAC keygen/sign require at least 32 bytes; `verify_pdf` still accepts legacy short keys for existing seals and reports a warning
- License policy reviewed: LGPL/MPL remain allowed (weak copyleft compatible with MIT; MPL appears via `certifi`/`pathspec` in the CI toolchain)
- CI: GuardDog scans the project's dependency environment (only `threat-*` findings go to code scanning; full capability SARIF stays an artifact); the previous job scanned its own toolchain

## [0.13.1] - 2026-11-24
### Added
- Project: OpenSSF Best Practices **Passing** badge (self-certified at `bestpractices.dev/projects/17047`); Scorecard `CII-Best-Practices` now 5
- Fuzzing: Atheris targets for the untrusted-input parsers (`.toon`, JSON payload envelope, layout specs) in `fuzz/`, run time-boxed on every PR and deeper weekly (`fuzz.yml`); closes Scorecard `Fuzzing`
- Hash-pinned CI toolchain: every workflow install from `pip install --require-hashes` locks (`.github/requirements/requirements-*.txt`, `docs/requirements-docs.txt`), regenerated by `scripts/lock-requirements.sh` (uv, universal); closes Scorecard `Pinned-Dependencies`
### Changed
- Releases are now draft-first: `publish.yml` runs on the tag push, attaches the wheel, sdist, SBOM and `provenance.intoto.jsonl` to a draft release, uploads to PyPI and publishes the release last; this is required for GitHub immutable releases
### Fixed
- Log encoding: caller-controlled log fields are escaped (CR/LF, ANSI/control characters, Unicode separators) via `logging_utils.log_value`, with `LogEncodingFilter` on the package logger as a safety net; ASVS 7.3.1 now Pass
- Nested group fields holding a scalar (or a bare dict) now fail closed with `ValueError` naming the field, instead of raising `TypeError` from inside traversal (found by fuzzing)
- Top-level records that are not objects fail closed with `ValueError` naming the index (found by fuzzing)
- Composed documents: `table`/`crosstab` sections with a non-list `data` or a non-object `layout` fail closed with `ValueError` instead of `AttributeError`/`TypeError` (found by fuzzing)

## [0.13.0] - 2026-11-23
### Added
- Supply-chain layer: CodeQL advanced setup (Python + Actions, weekly + per-PR), dependency-review PR gate (high+ vulns, GPL/AGPL denied), GuardDog malicious-package scan with SARIF, `pip-licenses` copyleft gate, docs-deps `pip-audit`, Sigstore attestations (SLSA provenance for the release artifacts + SBOM file) on every release
- Strict payload envelope: raw dicts validated against the canonical `ReportPayload` schema (known top-level/meta keys, correct types) fail-closed in `prepare_report`; closes ASVS 13.2.2
- User guide on the docs site (`docs/guide.md`): task-oriented walkthroughs (first report, inputs, sections, signing, hardening, CLI, troubleshooting) with the README kept as exhaustive reference
- Secret scanning: Gitleaks workflow on PR/push/weekly (working tree + history, digest-pinned image, SARIF to code scanning) plus an optional pre-commit hook; closes ASVS 10.2.3

## [0.12.0] - 2026-11-23
### Added
- Documentation site: Zensical + GitHub Pages (`docs.yml`, unified landing + Standards/ASVS/Roadmap/Changelog/Security), strict link-checked build
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
