# isis-report-lib — Architecture, Engineering, Security & Design Standards

Binding standards for contributors (human or agent). `AGENTS.md` covers the
daily workflow; this document covers *why the code looks the way it does* and
what must not be violated. Rules are written as **MUST** (CI or review blocks),
**SHOULD** (justify deviations in the PR), and **GUIDELINE** (preferred style).

The project's maxim: **faithful presentation of data beats rigid layout**.
Every rule below serves it — the layout adapts to the data, missing data is
explicit, and provenance is preserved. Nothing here may silently drop, invent,
or misrepresent data.

Planned work lives in [`ROADMAP.md`](ROADMAP.md) — consult it before starting
a feature so effort goes to the prioritized items first.

---

## 1. Architecture

### 1.1 The pipeline

```
payload (dict | ReportPayload | .toon)
  → Fetch → Process → HTML → PDF        (service.TabularReportService.execute)
  → XLSX / CSV                          (export, no browser)
```

- **MUST**: all outputs share `service.prepare_report(payload)`, which returns
  exactly `(dataset, layout, meta)`. No output path may build its own variant
  of the dataset — divergence between PDF and XLSX is a correctness bug.
- **MUST**: `execute` keeps the step order Fetch → Process → HTML → PDF.
  New stages (e.g. validation) slot into this order, never around it.

### 1.2 Module map and dependency direction

| Module | Owns | Must NOT import |
|---|---|---|
| `api.py` | public sync/async surface; `_normalize_payload`, `_run` | anything except service/export/inputs/models/toon |
| `service.py` | orchestration, `prepare_report`, sections assembly | `pdf` internals beyond `get_pdf_from_html`/`close_owned_browser` |
| `layout.py` | pure data shaping (`build_report`, aggregates, footnotes, color domains) | `rendering`, `pdf`, `export` |
| `formatting.py` | pure value functions (masks, rules, scales, footnotes) | anything except `babel`, stdlib (lazy `charts` for sparkline SVG) |
| `rendering.py` | Jinja env, CSS vars/inlining | `pdf`, `export` |
| `pdf.py` | browser pool singleton (loop-bound) + egress route guard | `rendering`, `export` |
| `export.py` | `collect_tables` + XLSX/CSV builders | `rendering`, `pdf` |
| `inputs.py` | adapters *in* (dataframe/csv/json) | output logic |
| `signing.py` | seal (bytes in/out); `verify_*` never raise | network, filesystem |
| `charts.py`, `crosstab.py` | pure SVG strings / pure pivot math | I/O, network |
| `cli.py` | thin argv → API mapping; exit codes `0/1/2` | business logic |
| `templates/` | presentation only | Python |

- **MUST**: lower layers never import upper layers. `layout`, `formatting`,
  `charts`, `crosstab` are **pure**: no I/O, no network, no global state
  (except `functools.lru_cache` on side-effect-free functions).
- **GUIDELINE**: lazy imports for optional extras (`openpyxl`, `pandas`,
  `css_inline`, `cryptography`) with an install-hint `ImportError`.

### 1.3 Shared state rules

- The Playwright pool (`pdf.py`) is a singleton bound to one event loop.
  Foreign/closed-loop state is **abandoned, never awaited** (cross-loop
  `await` hangs on Linux). The sync API shuts down only its own browser
  (`close_owned_browser`, current loop only).
- Jinja environments are cached keyed by `template_dir`. The browser context
  renders with **JavaScript disabled** — reports are static documents.
- Mark assignment, numbering and totals are computed once in `prepare_report`
  with shared traversal state, so HTML, XLSX and CSV always agree.

### 1.4 Data shapes

- Normalized layout fragments: `header` / `details` / `groups` / `footer`
  field-dict lists plus top-level `summary`. Field dicts carry
  `name/label/format_mask/alignment` and optional `cell_rules`,
  `missing_text`, `substitutions`, `footnote(+_mark)`, `color_scale(+_domain)`,
  `data_bar`, `spark_*`, `aggregate`, `running_balance`, `visible*`.
- `export.Table/Column` mirror the layout so exports stay faithful without
  re-deriving anything.

---

## 2. Engineering

### 2.1 Dual API

- **MUST**: every new public feature ships as `async def a...` plus a sync
  wrapper through `_run` (which handles an already-running loop). Pure
  helpers are exported in `__init__.py` and added to `__all__`.
- **MUST**: new public parameters are keyword-friendly. Never add a
  positional parameter after a `functools.partial`-bound function
  (context: `formatter_for` binds `locale`/`currency` by keyword, so
  templates and CSV code pass `field=` by keyword).

### 2.2 Types and validation

- **MUST**: `mypy src` is clean. Payloads are `dict[str, Any]`; validate at
  system boundaries (`prepare_report`, `with_meta_defaults`, field
  normalizers), not in hot per-cell loops.
- **MUST**: fail closed with `ValueError` naming the offending value and the
  expected set (`f"...: {x!r} (expected ...)"`). Verdict-style APIs
  (`verify_pdf`) return result objects and never raise on input.
- Recursion is bounded: parsers and builders convert `RecursionError` into
  `ValueError` (see `toon`, `inputs.from_json`, `prepare_report`).

### 2.3 Data integrity rules

- **MUST NOT** mutate caller-owned structures. Copy rows before enriching
  (`_apply_running_balance` pattern); normalize into fresh field dicts.
- **MUST** be deterministic: sorted JSON keys, stable traversal order,
  shared numbering state. The same payload always yields the same bytes.
- **MUST NOT** silently drop data: empty tables render `empty_text` (or a
  header plus export note); `None` renders `missing_text` (default blank, but
  explicit); unknown masks stringify; unobserved crosstab cells are `0` for
  `count`/`sum` and blank otherwise — each documented.

### 2.4 Tests and gates

- Unit tests use mocks and never touch the network/browser; browser tests are
  marked `browser` and skip without Chromium. Match test file to source file.
- Coverage gate is 85% (CI enforces; keep the suite near 100%).
- `bench/bench.py --check` is the perf gate: smoke-level budgets with
  headroom for shared runners, enforced in the `e2e` job.
- New behavior ships with tests; bugfixes ship with regression tests.

### 2.5 Docs and releases

- User-facing knobs (`README.md` parameters table) and `CHANGELOG.md`
  (`Unreleased` → versioned sections on release) update in the same PR.
- `docs/` publishes as a Zensical site (`docs.yml` build on PRs, deploy on
  push to `main`); nav updates ship with the feature they document.
- Conventional Commits; `main` via squash-merge after the `gate` check.
- Release: tag `vX.Y.Z` + GitHub Release → PyPI/TestPyPI via Trusted
  Publishing. Never publish from a laptop.

---

## 3. Security

The binding control mapping lives in [`ASVS.md`](ASVS.md)
(OWASP ASVS 4.0.3, L1 target with L2/L3 where met); vulnerability reports
follow [`SECURITY.md`](https://github.com/thepaneb/isis-report-lib/blob/main/SECURITY.md). This section states the rules.

### 3.1 Trust boundaries

| Zone | Examples | Rule |
|---|---|---|
| Code (operator-trusted) | bundled/custom templates, CLI flags, keys | may execute; load templates only from trusted dirs |
| Schema (validated) | layout defs, `meta`, `cell_rules`, colors | validate shape on ingest; escape on render |
| Data (untrusted) | records, CSV/JSON/dataframe cells, `.toon` values | escaped, never executed; no network fetch triggered by it |
| Output (untrusted context) | HTML viewed in browsers/mail clients | must be safe to open: escaped, no scripts, no remote refs |

Report *layout* from untrusted authors is treated as schema: validated
strictly, escaped on output. Only `template_dir` is code. Network egress
policy (`allowed_hosts`) is operator configuration like `template_dir` and
keys: accepted from API/CLI arguments only, never from the payload.

### 3.2 Rendering rules (MUST)

- Jinja `autoescape` stays **ON**. Only pre-built SVG (`charts.*`, returned
  as `Markup`) is exempt — never mark caller-controlled strings.
- No JavaScript in the PDF browser context (`java_script_enabled=False`).
- No remote resources at render time: `_inline_css` strips `<link>`
  stylesheets instead of fetching them (email clients ignore them anyway).
- Outbound http(s) from Chromium is denied by default via a per-page route
  guard; `allowed_hosts` (bare hostnames, API/CLI only) opts specific hosts
  back in. Data URIs and other non-network schemes always pass.
- Spreadsheet safety: text cells starting with `= + - @` (or tab/CR) are
  `'`-prefixed in CSV/XLSX; numeric values are never prefixed.
- `verify_pdf` is total: malformed blocks/keys/algorithms yield `invalid`
  verdicts, never exceptions.

### 3.3 Cryptography and secrets (MUST)

- HMAC-SHA256 via `hmac.compare_digest` on a canonical JSON body that
  includes `key_id`; Ed25519 keys are type-checked after PEM load;
  algorithms are allow-listed on both sign and verify paths.
- Keys arrive as bytes (files); never log, print, or embed them in outputs.
  Key files should be `0600` (the CLI warns otherwise on POSIX).
- Rotation runbook (no flag days): sign new reports with the new key under a
  new `key_id`; configure verifiers with the keyring (`{key_id: key}` mapping
  or ordered key list — the envelope `key_id` selects first, the rest are
  tried in order); retire the old key once its seals expire out of circulation.
- This is a tamper-evident **seal**, not Adobe PAdES: no CAs, no timestamps
  as trust anchors (`issued_at` is informational).

### 3.4 Supply chain (MUST)

- `pip-audit` gates every PR (e2e job); Dependabot stays enabled with a
  7-day `cooldown` on version updates (security updates are exempt).
- Semgrep SAST gates every PR (plus push and weekly full scans): registry
  pack (`p/default`) and custom rules in `.semgrep/` locking §3.2
  (sandboxed autoescaped templates, `Markup`-only-SVG, JS-disabled contexts,
  no network at render time); findings fail the job (`--error`) and upload
  as SARIF to code scanning under `semgrep`. The scan image
  (`semgrep/semgrep`) is version-pinned; rule changes ship with fixture
  updates (`semgrep --test`).
- Gitleaks secret scanning gates every PR (plus push and weekly scans of the
  working tree and history); findings fail the job and upload as SARIF under
  `gitleaks`. The scan image (`zricethezav/gitleaks`) is digest-pinned; a
  `.pre-commit-config.yaml` hook offers the same scan as an optional local gate.
- GitHub Actions are pinned by **commit SHA** (with `# tag` comments);
  `GITHUB_TOKEN` permissions are minimal; publishing uses OIDC.
- OpenSSF Scorecard runs weekly + on push (SARIF to code scanning);
  Codecov reports coverage via OIDC (no stored token; the gate stays on pytest).
- Every GitHub Release (stable + prerelease) carries a reproducible
  CycloneDX 1.6 `sbom.json`, built in an isolated env from the release wheel.
- No secrets in the repo (`.env` is gitignored); release artifacts come only
  from CI (`twine check` + trusted publishing).

### 3.5 Security review checklist (every PR touching I/O, templates, export)

1. Does any new output interpolate untrusted data without escaping?
2. Does any new code fetch the network at render/generate time?
3. Does any new browser capability get enabled (JS, plugins, downloads)?
4. Does any new export path write attacker-controlled strings unevaluated?
5. Does any new `verify_*`/parser raise where callers expect a verdict/`ValueError`?
6. Does any new dependency widen the install or need a system package?

---

## 4. Design (data-first report design)

### 4.1 Principles

1. **Layout follows data.** Buckets, columns and groups derive from observed
   values (crosstab, inferred layouts); the author declares *mappings*, never
   pixel positions.
2. **Absence is explicit.** `missing_text`, `substitutions`, `empty_text`,
   NaN→`None` normalization — a blank cell must mean "no data", never "lost data".
3. **Provenance travels with numbers.** Footnotes and `source_note`/`source`
   render in every output (HTML list, XLSX `Notes` sheet, CSV `# [..]` lines).
4. **Totals agree everywhere.** One aggregate implementation (`layout`),
   reused by templates, crosstab and export — including `median`/`distinct`.
5. **Conditional presentation, unconditional data.** `cell_rules`,
   `color_scale`, `data_bar`, sparklines and visibility never remove values;
   `$print_when`/`$order_by` are the only row operators, and both are
   declarative in the payload.

### 4.2 Template conventions

- Templates render; they don't compute. Formatting goes through `fmt(value,
  mask, field=...)`, conditional style through `cellstyle(value, field)`.
- New macro parameters default (`mark=""`, `empty_text=""`) so custom
  templates overriding bundled macros keep working.
- Header labels carry footnote `<sup>` marks; notes lists close each
  report/section; `source` lines sit under their section.
- Print CSS keeps groups together (`break-after/inside: avoid` on headers,
  rows, summaries) and repeats `thead`; the page footer carries timestamp,
  pagination and brand.

### 4.3 Email-safe output (`inline_css=True`)

- Stylesheets are inlined and CSS variables resolved to literals (Outlook
  ignores `var()`); `<html lang>` follows `meta.locale`; `color-scheme:
  light` is declared.
- No external resources, no scripts, no flex-dependent critical layout —
  degradation is graceful and content-complete.

### 4.4 XLSX/CSV fidelity contract

- Same labels, numbers, totals and notes as the HTML report.
- Native Excel types with number formats; `data_bar` uses native
  conditional formatting; empty tables keep headers plus their note.
- Formula guard is disclosed (leading `'`); `Notes` sheets never shift
  data rows (appended last).

---

## 5. Changing these standards

Amendments ship as PRs against this file with rationale and, when they
alter guarantees (escaping, exports, verification), regression tests. The
maxim outranks every rule: on conflict, prefer the option that keeps
displayed data faithful.

## References (normative for §3)

- OWASP Application Security Verification Standard 4.0.3 —
  `docs/ASVS.md` maps each applicable requirement to evidence.
- OWASP Cheat Sheets: Cross Site Scripting Prevention, Injection
  Prevention in Python, Deserialization, Key Management, Logging.
- CWE: CWE-79 (XSS), CWE-918 (SSRF), CWE-502 (deserialization),
  CWE-327/798/320 (crypto/keys), CWE-400 (DoS), CWE-22/73/78/98
  (path/file injection), CWE-116/176 (encoding), CWE-829 (untrusted includes).
- SLSA / Sigstore provenance model: releases ship via OIDC trusted
  publishing; Actions are SHA-pinned.
- Keep a Changelog + Conventional Commits (process standards).
