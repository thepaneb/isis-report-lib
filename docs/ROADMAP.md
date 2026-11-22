# Roadmap — isis-report-lib

Single source of truth for *what comes next*, so plans don't live only in
chat memory. Status is updated when a PR merges (move the item to
[Done](#done-v010--v0110), never delete it).

Guiding maxim: **faithful presentation of data beats rigid layout.**
Non-goals are listed at the bottom and stay out unless the maxim demands
otherwise.

## Next (prioritized)

### 1. Semgrep SAST gate (assurance)
Add a Semgrep CI job over `src/` (Python ruleset, blocking on high severity).
Today `ruff -S` + review + tests cover the intent; a real SAST closes ASVS
10.1.1 (currently Partial).

### 2. Configurable payload size quotas (DoS hardening)
Opt-in limits (e.g. max rows / max payload bytes), fail-closed with
`ValueError`, consistent with the existing recursion guards.
Closes ASVS 12.1.1 (currently Partial: deployer duty).

### 3. Outbound network allow-list for Chromium (defense in depth)
Deny outbound requests by default via route aborting, with an opt-in
allow-list (e.g. self-hosted fonts). JS is already off and data can't inject
elements; this covers operator-authored templates that pull remote assets.
Narrows ASVS 12.6.3 gap.

### 4. Documentation site (polish)
`mkdocs` + GitHub Pages from `docs/` (`STANDARDS.md`, `ASVS.md`, this file).
Landing page and wiki already exist, so this is discoverability, not new
content.

## Done (unreleased, post-v0.11.0)

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
