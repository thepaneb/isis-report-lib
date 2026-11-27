# Roadmap — isis-report-lib

Single source of truth for *what comes next*, so plans don't live only in
chat memory. Status is updated when a PR merges (move the item to
[Done](#done-v010-v0110), never delete it).

Guiding maxim: **faithful presentation of data beats rigid layout.**
Non-goals are listed at the bottom and stay out unless the maxim demands
otherwise.

## Next (prioritized)

**Survey (2026-11-25):** the library is feature-rich and the hardening work is
done; the constraint is adoption, not surface area. The order below reflects
that. Completed in the same pass: output gallery, comparison page, generated
API reference and the docs drift fixes (see [Done](#done-2026-11-25)); the 0.15
visible features landed on 2026-11-26 (see [Done](#done-2026-11-26)).

**Update (2026-11-27):** 0.16.0 shipped with the runnable demo, PT-BR quickstart
and GHCR image, followed by 0.17.0 with the security redaction, AI governance
and safe text export (see [Done](#done-2026-11-27)); distribution is now the
main constraint and is tracked under Adoption below.

### Adoption
- **Distribution (in progress)** — 0.17.0 is out; the distribution kickoff used
  0.16.0. Published: r/coolgithubprojects post + first comment, and the 0.16.0
  LinkedIn posts in EN and PT-BR. Submitted: PyCoder's Weekly, the Console.dev
  beta pitch and the Python Bytes news item. Scheduled: Hacker News
  (2026-12-01) and the r/Python Showcase Thread (2026-12-04), both citing
  0.17.0. Pending: Python Weekly (curator contact), Lobsters (invitation-only)
  and awesome lists (deferred until 1.0/traction).
  The GitHub Action, Dockerfile, Discussions and starter issues are done (see
  [Done](#done-2026-11-26)).

### Security & AI governance
- **Ongoing** — keep the AI-disclosure and security pages current; revisit
  formal AI BOM/OWASP LLM controls only if the library adds an AI runtime.

### 1.0 — packaging and contract
- **Playwright as an optional `[pdf]` extra** so HTML/XLSX/CSV users do not
  download a browser. Breaking change; schedule it with 1.0.
- **Support/deprecation policy** — last two minors, Python 3.11+, one-minor
  warning before removal.
- **CI smoke on Windows/macOS** (currently Ubuntu only) and
  `Development Status :: 5 - Production/Stable`.

### Continuous
Hypothesis property tests + mutation testing; RTL (`meta.direction`);
Arrow/Polars/DuckDB/DB-API adapters. PDF/A stays an optional
extra only if demand appears; PAdES remains a non-goal.

### Jev (local advisory)
Done: English reports/questions, `--auto-packs`, calibration harness,
remote release preflight, `scripts/jev_packs.py`, CI artifact + compact
comment and the monthly calibration reminder.
Future (only with demand): a `data` pack (determinism/locale/rounding/mutation)
and an `async` pack (cancellation/timeouts/browser lifecycle); add them only if
recurring findings justify the extra passes and calibration. Also consider a
CI cost budget and an explicit `OPENCODE_API_KEY` rotation policy.

## Done (2026-11-27)

- **0.17.0 release** — security redaction, AI usage/security disclosure, safe
  visible-only text export and GHCR image `:0.17.0`; **404 tests**, **98.66%**.
- **0.16.0 release** — runnable demo, PT-BR quickstart, GHCR image
  (`ghcr.io/thepaneb/isis-report-lib:0.16.0`), curated release notes and the
  Docker runtime lock at 0.16.0; **387 tests**, **98.66%** coverage. The GitHub
  release is immutable and attested; the GHCR image is public.
- **Distribution kickoff** — r/coolgithubprojects post + first comment,
  Console.dev beta pitch, Python Bytes news item, PyCoder's Weekly form and the
  0.16.0 LinkedIn posts in EN and PT-BR. HN and r/Python are scheduled; the
  remaining channels are tracked under Adoption.
- **Security P0** — payload values are no longer included in validation errors
  or logs; AI agents have explicit untrusted-content/prompt-injection/secrets
  rules in `AGENTS.md`.
- **AI governance** — `AI_USAGE.md`, CONTRIBUTING/PR-template disclosure, the
  docs security page and `security.txt`; AI-ingestion and
  prompt-injection guidance in `SECURITY.md`.
- **Visible-text export** — `render_text`/`arender_text` (and `.toon` variants)
  return a visible-only, sanitized text export with a `REPORT DATA` boundary;
  prompt-injection and invisible-Unicode regression tests.

## Done (2026-11-26)

- **Media and contents** — `image` sections (data-URI PNG/JPEG/WebP/GIF with
  `alt`/`caption`/`width`/`align`), `meta.logo`, `meta.watermark` (string or
  object) and `toc` sections with internal links. Images are payload-only
  (2 MiB decoded max; SVG rejected); the TOC is link-based, not page-numbered.
- **Native XLSX charts** — chart sections keep the label/value table and gain a
  native bar/line/pie/donut chart, including horizontal bars.
- **PDF outline** — bookmarks from the headings by default; the outline
  implies a tagged PDF and `pdf_options={"outline": False}` opts out.
- **Adoption surface** — issue forms, pull-request template, Discussions and
  five starter issues (#89–#93: PT-BR quickstart, `--version`, `from_jsonl`,
  Windows/macOS CI and RTL); #89 is closed, #90–#93 remain open.
- **PT-BR quickstart** — `docs/pt-br/quickstart.md`, scoped with a notice that
  the full documentation stays in English; the two-build foundation is tracked
  in #99.
- **Fork PR SARIF** — docs-only fork PRs get trusted empty GuardDog, Semgrep and
  CodeQL analyses; code- or dependency-changing forks require a same-repo
  integration branch.
- **Distribution** — composite GitHub Action (`.github/actions/render`) and a
  Dockerfile with Chromium/fonts, including an example workflow; shipped in
  v0.15.1.
- **Runnable demo** — `demo/` with a board-pack payload and a renderer for
  PDF/HTML/XLSX/CSV, plus CLI, Docker and GitHub Action instructions.

## Done (2026-11-25)

- **Output gallery** — `docs/gallery.md` with real PDF/HTML/XLSX/CSV and PNG
  covers, generated by `scripts/gen_gallery.py` from `examples/board_pack.py`.
- **Comparison page** — `docs/comparison.md`, an honest matrix and "when to
  choose" for WeasyPrint, ReportLab and fpdf2.
- **API reference** — `docs/api.md` generated from the public docstrings by
  `scripts/gen_api_docs.py` (`--check` detects drift).
- **Docs drift fixed** — ASVS 5.2.2 is Pass with the operator caps; the
  "mandatory review" wording in 1.10.1/10.2.3 and the opt-in quota note are
  gone; `Signed-Releases` updated to 8.

## Structural Scorecard limits (accepted)

`Code-Review` and `Contributors` stay at 0 until a second reviewer or
organization contributes; `Maintained` rises on its own 90 days after repo
creation; `SAST` is 10. `CII-Best-Practices` is 5 (Passing); Silver (7) and Gold
(10) are optional and Gold needs a second maintainer. `Signed-Releases` is **10**
after v0.17.0: the five releases in the window (v0.14.0–v0.17.0) are immutable
and attested.

`Branch-Protection` is 4. The remaining gaps — required approvers, stale-review
dismissal, CODEOWNERS review and last-push approval — need a **second human
reviewer**. Enabling them without one either deadlocks merges (self-approval is
not a review) or is cosmetic, so the ruleset stays as is and the limit is
accepted; revisit if a co-maintainer joins.

## Done (post-v0.13.0)

- **Stricter defaults (decided)**: operator quota caps are on by default (1M
  records / 64 MiB; payload `meta.limits` may only tighten; `limits={}` or
  `--unlimited` opts out); HMAC keygen/sign require **≥32 bytes** (verify still
  accepts legacy short keys with a warning); LGPL/MPL remain allowed (weak
  copyleft; MPL appears via `certifi`/`pathspec` in the CI toolchain).
- **Socket Security (advisory)**: GitHub App installed on `isis-report-lib`
  only (organization `thepaneb`); it scans dependency/manifest changes and
  reports on PRs. The Socket check is **not** a required check — GuardDog
  remains the blocking supply-chain gate.
- **ASVS 7.3.1 log encoding**: `logging_utils.log_value` escapes CR/LF/tabs,
  ANSI/control characters and Unicode separators; the package logger installs
  `LogEncodingFilter` as a safety net. Applied to the egress host and service
  name, with tests for injection and no double encoding. ASVS 7.3.1 now Pass.
- **Release immutability**: enabled on the repository; `publish.yml` now runs
  on the tag push, attaches wheel/sdist/SBOM/SLSA `provenance.intoto.jsonl` to
  a **draft** release, uploads to PyPI and publishes the release **last**
  (immutable releases lock assets at publication). v0.13.0's wheel, sdist and
  real SLSA provenance were backfilled; v0.13.1 shipped through the new flow
  (immutable, all assets). Scorecard `Signed-Releases` confirmed 7 after
  v0.13.1. v0.12.0 predates the attestations; it drops out of the last-5
  window as new releases ship.
- **OpenSSF Best Practices badge (Passing)**: self-certified at
  [bestpractices.dev/projects/17047](https://www.bestpractices.dev/projects/17047);
  all Passing MUST/SHOULD criteria met (63 Met, 5 N/A). Scorecard
  `CII-Best-Practices` lifts 0 → 5 on the next scan.
- **Fuzzing**: Atheris targets for the untrusted-input parsers (`.toon`, JSON
  payload envelope, layout specs), run time-boxed on every PR and deeper
  weekly; the first runs found and fixed three real crash paths (scalar nested
  group value, scalar top-level record, malformed `sections` layout). Scorecard
  `Fuzzing` confirmed 10.
- **Hash-pinned CI dependencies**: every workflow installs tools from
  `pip install --require-hashes` locks (`.github/requirements/requirements-*.txt`,
  `docs/requirements-docs.txt`), regenerated by `scripts/lock-requirements.sh`
  (uv, universal, py3.11); the project itself installs editable with
  `--no-deps`. Scorecard `Pinned-Dependencies` confirmed 10.

## Done (v0.12.0 → v0.13.0)

- **Secret scanning**: Gitleaks workflow on PR/push/weekly (working tree + history, digest-pinned image, SARIF) plus an optional pre-commit hook; ASVS 10.2.3 now Pass.
- **User guide**: task-oriented walkthroughs on the docs site (`docs/guide.md`), README kept as exhaustive reference.
- **Strict payload envelope**: raw dicts validated against the canonical `ReportPayload` schema (known top-level/meta keys, correct types) fail-closed in `prepare_report`; ASVS 13.2.2 now Pass.
- **Supply-chain layer 2**: CodeQL advanced setup, dependency-review PR gate, GuardDog malicious-package scan with SARIF, `pip-licenses` copyleft gate, docs-deps `pip-audit`, Sigstore attestations (SLSA provenance + SBOM) on every release.

## Done (v0.11.0 → v0.12.0)

- **Documentation site (polish)**: Zensical + GitHub Pages (`docs.yml` build/deploy, unified landing as `docs/index.md`, Standards/ASVS/Roadmap/Changelog/Security discoverable with search, strict link-checked build).

- **Configurable payload size quotas (DoS hardening)**: opt-in `meta.limits`
  (`max_rows`/`max_bytes`) enforced fail-closed in `prepare_report` for every
  output (CLI `--max-rows`/`--max-bytes`); ASVS 12.1.1 now Pass.
- **Outbound network allow-list for Chromium (defense in depth)**: outbound
  http(s) denied by default via per-page route aborting, opt-in `allowed_hosts`
  (API/CLI only, never payload); ASVS 12.6.1 now Pass.
- **Semgrep SAST gate**: `semgrep.yml` CI job (PR/push/weekly, `p/default` + 8
  custom rules locking `STANDARDS.md` §3.2–§3.3, SARIF to code scanning,
  required in branch protection); ASVS 10.1.1 now Pass. Drive-by: `publish.yml`
  tag interpolation via env, `charts.py` exemption documented, Dependabot
  7-day cooldown.
- **CycloneDX SBOM as a release artifact**: `sbom.json` (CycloneDX 1.6,
  reproducible) generated in an isolated env from the release wheel and
  attached to every GitHub Release (stable + prerelease); ASVS 14.2.5 now met.
- **Signing key rotation**: `verify_pdf` accepts `{key_id: key}` mappings
  (envelope `key_id` selects first) and ordered key lists; CLI `verify`
  takes repeatable `--key-file`. Rotation runbook in `STANDARDS.md` §3.3.

## Done (v0.1.0 → v0.11.0)

- **v0.1.0–v0.2.0**: library extraction, dual sync/async API, CLI, Jinja2 + Playwright core.
- **Report parameters**: `meta.page`, `aggregate` (sum/count/avg/min/max), `$print_when`, `$order_by`, `visible`/`visible_when`, multi-table details.
- **Outputs**: XLSX (styled, print polish, data bars), CSV (locale, BOM), HTML/email (`inline_css`, CSS vars resolved, `lang`, `color-scheme`).
- **Composed documents**: `sections` (table/text/kpi/chart), running balances, dependency-free inline SVG charts + sparklines.
- **Data-first fidelity**: `missing_text`, `substitutions`, `empty_text`, footnotes + `source_note`/`source` (HTML list, XLSX `Notes` sheet, CSV `#` lines), locale-aware masks (`percent`/`currency`/`bool`/`date`), `median`/`distinct` aggregates, `color_scale` gradients.
- **Declarative analysis**: crosstab/pivot sections, compound rule conditions (`AND`, `between`, `contains`), `sparkline` masks, email-safe HTML.
- **Integrity**: HMAC-SHA256 + Ed25519 seals (`sign_pdf`/`verify_pdf`, `keygen`/`sign`/`verify` CLI) — a seal, not PAdES.
- **Throughput**: `generate_many` batch API, `bench/bench.py` with CI perf budgets.
- **Trust & supply chain**: Jinja autoescape + sandboxed env, no-JS browser context, formula-injection guard, total `verify_pdf`, recursion guards, `pip-audit` gate, SHA-pinned Actions, OIDC publishing, OSSF Scorecard, Codecov, `SECURITY.md`, `docs/STANDARDS.md`, `docs/ASVS.md` (OWASP ASVS 4.0.3 mapping, L1 target).

## Non-goals (deliberate)

PAdES signatures · WYSIWYG/visual report designer · scheduled bursting and
mail delivery (application layer) · server/daemon mode (library only) ·
ORM/query engine (inputs accept plain structures) · chart interactivity
(static SVG by design).
