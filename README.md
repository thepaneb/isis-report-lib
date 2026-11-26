# isis-report-lib

[![CI](https://github.com/thepaneb/isis-report-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/thepaneb/isis-report-lib/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/isis-report-lib.svg)](https://pypi.org/project/isis-report-lib/)
[![Python](https://img.shields.io/pypi/pyversions/isis-report-lib.svg)](https://pypi.org/project/isis-report-lib/)
[![Wiki](https://img.shields.io/badge/docs-wiki-blue)](https://github.com/thepaneb/isis-report-lib/wiki)
[![Docs](https://img.shields.io/badge/docs-zensical-blue)](https://thepaneb.github.io/isis-report-lib/)
[![ASVS](https://img.shields.io/badge/ASVS-4.0.3%20mapped-blue)](docs/ASVS.md)
[![pip-audit](https://img.shields.io/badge/pip--audit-gated%20in%20CI-green)](.github/workflows/ci.yml)
[![Semgrep](https://img.shields.io/badge/semgrep-gated%20in%20CI-green)](.github/workflows/semgrep.yml)
[![Security](https://img.shields.io/badge/security-policy-blue)](SECURITY.md)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/thepaneb/isis-report-lib/badge)](https://scorecard.dev/viewer/?uri=github.com/thepaneb/isis-report-lib)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/17047/badge)](https://www.bestpractices.dev/projects/17047)
[![codecov](https://codecov.io/gh/thepaneb/isis-report-lib/graph/badge.svg)](https://codecov.io/gh/thepaneb/isis-report-lib)

---

Python library for **tabular PDF reports** with customizable hierarchical layouts — extracted from the [isis_report](https://github.com/thepaneb/isis_report) PoC (Robyn microservice), without the server.

**Landing page:** <https://thepaneb.github.io/isis-report-lib/>

**See real outputs:** <https://thepaneb.github.io/isis-report-lib/gallery/> ·
**How it compares:** <https://thepaneb.github.io/isis-report-lib/comparison/> ·
**API reference:** <https://thepaneb.github.io/isis-report-lib/api/>

- Input: `dict`/`ReportPayload` (`meta` + optional `layout` + `data`) or **`.toon`** text
- Rendering: Jinja2 (templates bundled in the package)
- PDF: Playwright (Chromium)
- API: synchronous (`generate_pdf`) + asynchronous (`agenerate_pdf`)

## Installation

```bash
pip install isis-report-lib
playwright install chromium   # required to generate PDFs
```

> After upgrading `playwright`, reinstall the browser (`playwright install chromium`):
> each Playwright version pins a specific Chromium build.

Dev:

```bash
pip install -e ".[dev]"
```

## Quickstart

```python
from isis_report_lib import generate_pdf, generate_pdf_from_toon, render_html

payload = {
    "meta": {"title": "Sales Order", "sub_title": "2024", "mode": "exact"},
    "layout": {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "orders": {
            "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
            "total": {"label": "Total", "format_mask": "float", "alignment": "right"},
        },
    },
    "data": [{"company": "ACME", "orders": [{"order": 750, "total": 4000}]}],
}

pdf_bytes = generate_pdf(payload)
open("report.pdf", "wb").write(pdf_bytes)

# Without Playwright: just the intermediate HTML
html = render_html(payload)

# From .toon
toon = open("examples/sales_order.toon", encoding="utf-8").read()
open("report_toon.pdf", "wb").write(generate_pdf_from_toon(toon))
```

Async:

```python
from isis_report_lib import agenerate_pdf, agenerate_pdf_from_toon

pdf = await agenerate_pdf(payload)
pdf = await agenerate_pdf_from_toon(toon_text)
```

## CLI

```bash
# PDF from .toon, .json or .csv (format guessed from extension)
isis-report generate examples/sales_order.toon -o report.pdf
isis-report generate payload.json --page-format Letter
isis-report generate data.csv --delimiter ";" -o report.pdf

# JSON Schema of the payload (editors, validation)
isis-report schema -o payload.schema.json

# Same report as XLSX, CSV or HTML (needs no browser)
isis-report generate examples/sales_order.toon -o report.xlsx
isis-report generate examples/sales_order.toon -o report.csv
isis-report generate examples/sales_order.toon -o report.html
isis-report generate input.toon --format xlsx   # or csv | html | pdf

# Intermediate HTML without a browser (prints to stdout unless -o is given)
isis-report render examples/sales_order.toon -o report.html
```

## CI and Docker

A composite GitHub Action is in `.github/actions/render` — copy
[`examples/github-action.md`](examples/github-action.md) or use it directly:

```yaml
- uses: thepaneb/isis-report-lib/.github/actions/render@v0.15.1
  with:
    input: examples/sales_order.toon
    output: artifacts/report.pdf
    format: pdf            # pdf | xlsx | csv | html
```

It installs a pinned PyPI release and downloads Chromium only for `pdf`.
Inputs: `input`, `output`, `format`, `version` and `extra-args`. Linux, macOS
and Windows runners are supported.

The `Dockerfile` bundles Chromium and fonts for a reproducible runner:

```bash
docker build -t isis-report .
docker run --rm -v "$PWD:/work" isis-report generate examples/sales_order.toon -o report.pdf
```

Pin another release with
`docker build --build-arg ISIS_REPORT_VERSION=<version> -t isis-report .`.
The image runs as UID 1000; on Linux, add `--user "$(id -u):$(id -g)"` to the
`docker run` command if your host user has a different UID.

## Report signing (tamper-evident seal)

```bash
isis-report keygen -o secret.key                                  # shared secret (self-validation)
isis-report keygen --kind ed25519 -o private.pem --public-out public.pem   # third-party validation
isis-report sign report.pdf --key-file secret.key --key-id portal-1 -o report.signed.pdf
isis-report verify report.signed.pdf --key-file secret.key       # exit 0 = VALID
# rotation: repeat --key-file; the envelope key_id selects first, the rest are tried in order
isis-report verify report.signed.pdf --key-file old.key --key-file new.key
```

```python
from isis_report_lib import generate_hmac_key, sign_pdf, verify_pdf

secret = generate_hmac_key()
signed = sign_pdf(pdf_bytes, secret, key_id="portal-1")
info = verify_pdf(signed, secret)
assert info.valid  # + info.reason/alg/sha256/key_id/issued_at

# keyring rotation: {"key_id": key} mapping or key list; retired keys stay configured until old seals expire
assert verify_pdf(signed, {"2026-a": old_secret, "portal-1": secret}).valid
```

A `%ISIS-SIGNATURE` block is appended after the PDF `%%EOF` (readers ignore it; any modification invalidates the seal). `verify_pdf` never raises — check `.valid`. This is an origin/integrity seal, not Adobe PAdES.

`generate_hmac_key` and `sign_pdf` require **at least 32 bytes** for HMAC; `verify_pdf` still accepts legacy short keys for existing seals and reports a warning in `info.details`. Key files should be `0600`; `--require-key-permissions` makes `sign`/`verify` fail on POSIX when the key file is group/other-readable (default: warn).

## Data inputs

```python
from isis_report_lib import generate_pdf
from isis_report_lib.inputs import from_csv, from_dataframe, from_json

generate_pdf(from_dataframe(df, meta={"title": "Sales", "locale": "en-US"}))
generate_pdf(from_csv("sales.csv", delimiter=";"))   # light int/float/bool coercion
generate_pdf(from_json("payload.json"))              # list -> data; full payload passes through
```

`pandas` is optional: `pip install isis-report-lib[pandas]` (`NaN`/`NaT` become `None`, `Timestamp` becomes `datetime`).

## Output formats

| Format | API | Notes |
| --- | --- | --- |
| PDF | `generate_pdf` / `agenerate_pdf` | Needs Chromium (`playwright install chromium`) |
| XLSX | `generate_xlsx` / `agenerate_xlsx` | One sheet per detail table (context columns repeated), bold totals, `Summary` sheet, native charts for `chart` sections. Needs `pip install isis-report-lib[xlsx]` |
| CSV | `generate_csv` / `agenerate_csv` | Locale-formatted values, `# table:` / `# summary` sections, `--delimiter` (`;` for Excel PT), `--bom` (UTF-8 BOM for Excel) |
| HTML | `render_html` / `arender_html` | Intermediate output, no browser needed |

```python
from isis_report_lib import generate_csv, generate_xlsx

generate_xlsx(payload)                    # -> bytes (.xlsx workbook, print titles + freeze + filters)
generate_csv(payload, delimiter=";", bom=True)  # -> str (BOM for Excel)
```

PDF options (forwarded to Playwright's `page.pdf`):

```python
generate_pdf(
    payload,
    pdf_options={
        "format": "A4",
        "margin": {"top": ".2in", "bottom": ".5in"},
        "header_template": "<div>My header</div>",
        "footer_template": "<div>Page <span class='pageNumber'></span></div>",
    },
)
```

Via CLI: `--page-format`, `--header-template FILE`, `--footer-template FILE`. The report footer shows `meta.printed_at`, auto-filled with the current timestamp when absent. Footer date/page strings follow `meta.locale` (`pt` → "Impresso em / Página X de Y").

PDF bookmarks are generated from the document headings by default (`outline=True`, which also produces a tagged PDF). Pass `pdf_options={"outline": False}` to opt out.

Full example in `examples/`. Note: the sync API opens/closes the browser per call (no leaked processes); the async API reuses the shared pool.

## Composed documents (sections)

For free-form reports, pass `sections` instead of `data` + `layout`:

```python
payload = {
    "meta": {"title": "Board Pack", "locale": "en-US"},
    "sections": [
        {"type": "toc", "title": "Contents"},
        {"type": "text", "title": "Intro", "paragraphs": ["Hello.", "World."]},
        {"type": "table", "title": "Sales", "layout": {...}, "data": [...]},
        {"type": "kpi", "title": "Totals", "items": [{"label": "Orders", "value": 42, "format_mask": "int"}]},
        {"type": "chart", "title": "Trend", "chart": {"kind": "bar", "labels": ["Jan", "Feb"], "values": [10, 20]}},
        {"type": "image", "title": "Logo", "src": "data:image/png;base64,...", "alt": "Logo", "width": 160},
        {"type": "crosstab", "title": "Sales by region × quarter",
         "data": [...], "rows": "region", "columns": "quarter",
         "measure": "total", "function": "sum"},   # buckets × measure, totals included
    ],
}
generate_pdf(payload)   # HTML/PDF sections.jinja; XLSX gets native charts, CSV flattens the sections
```

A running balance column is just a field with `"running_balance": "<source field>"` — cumulative sums are computed in row order (e.g. bank statements).

`toc` lists every titled section with internal links (the PDF also gets bookmarks). `image` embeds a data-URI image (PNG/JPEG/WebP/GIF, ≤2 MiB) with `alt`, `caption`, `width` and `align`; paths and URLs are never read from the payload. `meta.logo` replaces the header icon and `meta.watermark` stamps every printed page (see the payload table).

## Custom templates

Point `template_dir` at your own `.jinja` directory and pick a file with `template_name`:

```python
generate_pdf(payload, template_dir="my_templates", template_name="invoice.jinja")
```

```bash
isis-report generate order.toon --template-dir my_templates --template-name invoice.jinja
```

The directory is layered over the bundled one, so you can also override `tabular.jinja` or reuse `tabular_sections.jinja` macros. Templates receive `dataset`, `layout`, `meta`, plus the `fmt(value, mask)` formatter and `zip` — see `examples/custom.jinja`.

## Theming

Set `meta.accent_color` to rebrand the report header without a custom template:

```python
payload = {"meta": {"title": "Sales Order", "accent_color": "#1B7A3D"}, ...}
```

It overrides the `--brand-color` CSS variable. More masks: `str` · `int` · `float` (pt-BR) · `date` · `percent` · `currency` (R$) · `bool`.

## Logo, watermark and image sections

Brand a report without a custom template:

```python
payload = {
    "meta": {
        "title": "Statement",
        "company": "ACME",
        "logo": "data:image/png;base64,...",                  # replaces the header icon
        "watermark": {"text": "DRAFT", "opacity": 0.08, "color": "#0A2F46", "angle": -35, "size": 110},
    },
    "sections": [
        {"type": "image", "title": "Signature", "src": "data:image/png;base64,...",
         "alt": "Authorized signature", "width": 180, "align": "right", "caption": "Finance"},
    ],
}
```

Images are **payload data only**: `data:image/png|jpeg|webp|gif;base64,...` up to 2 MiB decoded. The library never reads a path or fetches a URL from a payload; SVG is rejected. `meta.logo` also switches the header text to `meta.company` when set. A watermark can be a plain string or `{text, opacity, color, angle, size}` and is repeated on every printed page. `toc` sections list every titled section with internal links.

## Payload

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `meta` | object | yes | `title`, `sub_title`, `mode` (`"exact"`/`"gray"`), `company`, `locale` (`"pt-BR"`, `"en-US"`…), `currency` (override, e.g. `"EUR"`), `accent_color`, `logo` (data-URI image), `watermark` (string or `{text, opacity, color, angle, size}`), `printed_at` (auto-filled) |
| `layout` | object | no | hierarchical field definition; omit to infer from data |
| `data` | array | yes | raw records or template format (`{"fields": ..., "groups": ...}`) |

Masks (locale-aware via Babel/CLDR): `str` · `int` · `float` · `date` (localized for `date`/`datetime` objects) · `percent` · `currency` · `bool` (`Yes`/`No`) · `sparkline` (list of numbers → inline SVG nanoplot in HTML/PDF, `▁▂▃▄▅▆▇█` block art in CSV/XLSX; field options `spark_kind: line|bar`, `spark_color`).

Payloads are validated against the schema (`payload_schema()`) at every entry point: unknown top-level/`meta` keys and mistyped values fail closed with `ValueError`.

```python
payload = {
    "meta": {"title": "Sales Order", "locale": "en-US"},  # numbers as 1,234.50, $1,234.50
    "data": [...],
}
```

```bash
isis-report generate order.toon --locale en-US -o out.pdf   # overrides meta.locale
```

## Report parameters

Beyond `layout` and `data`, the payload supports declarative behavior — no rigid bands, the document adapts to the data:

```python
payload = {
    "meta": {
        "title": "Sales Order",
        "page": {"size": "A4", "orientation": "landscape", "margins": {"top": ".4in"}},
    },
    "layout": {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "orders": {
            "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
            "status": {"label": "Status", "format_mask": "str", "alignment": "left", "visible": False},
            "total": {"label": "Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
            "$print_when": {"field": "status", "not_equals": "cancelled"},
            "$order_by": "-order",
        },
    },
    "data": [...],
}
```

| Parameter | Where | Effect |
| --- | --- | --- |
| `meta.page` | `meta` | `{size, orientation: portrait\|landscape, margins}` → PDF page (explicit `pdf_options` win) |
| `aggregate` | field def | `sum\|count\|avg\|min\|max\|median\|distinct` → group footers, detail `tfoot`, grand summary (`distinct` counts distinct non-`None`). Flat child lists render as tables (several per item allowed); deeper nesting renders as sections |
| `$print_when` | any level | keep only rows matching `{field, equals\|not_equals\|in\|not_in\|gt\|gte\|lt\|lte\|between\|contains\|is_null\|not_null}` (several operators combine with AND) |
| `$order_by` | any level | sort rows: `[{field, direction}]` or `"field"` / `"-field"` (nulls last) |
| `visible` / `visible_when` | field def | hide a column; `visible_when` supports `{..., scope: any\|all}` |
| `cell_rules` | field def | `[{operator(s), color\|background\|bold\|italic}]` → conditional cell style in HTML and XLSX; first matching rule wins, several operators combine with AND, operator-less rule is a catch-all default (e.g. `{"gte": 1000, "lt": 5000, "color": "#C00000"}`) |
| `missing_text` / `substitutions` | field def | `missing_text` text shown for `None` (default: blank); `substitutions` `{raw: display}` map applied before formatting (`str(value)` fallback, `None` falls back to `missing_text`) — in HTML, XLSX and CSV |
| `empty_text` | flat detail list / `table` section / `meta` | message rendered instead of an empty table (`meta.empty_text` covers the whole report); exported as a note row/line in XLSX/CSV |
| `footnote` | field def | `"text"` or `{"mark", "text"}` → superscript mark on the column label, notes listed per report/section (auto marks `*†‡§‖¶` then numbers); XLSX `Notes` sheet, CSV `# [mark]` lines |
| `source_note` / `source` | `meta` / any section | provenance line under the report/section (`# [source]` in CSV, `Notes` sheet in XLSX) |
| `color_scale` / `data_bar` | field def | `color_scale: {min, max}` gradient fill by value (explicit `cell_rules` win); `data_bar: true` native Excel bars (XLSX only) |
| `meta.summary_side` | `meta` | `top\|bottom` (default) grand-summary placement |
| `meta.limits` | `meta` | DoS quotas `{max_rows, max_bytes}` — may only **tighten** the operator cap (defaults `1M` records / `64 MiB`; API `limits`, CLI `--max-rows/--max-bytes/--unlimited`); fail-closed `ValueError` for unknown keys/non-positive ints |

## `.toon` syntax

```toon
meta:
  title: Sales Order
  mode: exact
layout:
  product{Product,str,left}
  total{Total,float,right,sum}
data[1]:
  - product: Pen
    total: 5.50
```

`data[n]` holds the records (`dados[n]` still accepted as a legacy alias). The compact
layout form accepts an optional 4th part with the aggregate: `total{Total,float,right,sum}`.
See `examples/sales_order.toon`.

## API

| Function | Description |
| --- | --- |
| `generate_pdf(payload, pdf_options?, allowed_hosts?, limits?) -> bytes` | sync PDF from dict/`ReportPayload`; `allowed_hosts=[...]` allow-lists outbound http(s) hosts (default denies all network); `limits` is the operator quota cap |
| `agenerate_pdf(...)` | same, async |
| `generate_many(payloads, max_concurrency=4, ..., limits?) -> list[bytes]` / `agenerate_many` | concurrent PDFs sharing the pool, results in input order (per-call `allowed_hosts`/`limits` supported) |
| `generate_pdf_from_toon(text, ..., limits?)` / `agenerate_pdf_from_toon` | PDF from `.toon` (same `allowed_hosts`/`limits` keywords) |
| `generate_xlsx(payload, limits?) -> bytes` / `agenerate_xlsx` / `..._from_toon` | .xlsx workbook, no browser (needs `.[xlsx]` extra) |
| `generate_csv(payload, delimiter=",", bom=False, limits?) -> str` / `agenerate_csv` / `..._from_toon` | CSV text, no browser (`bom=True` for Excel) |
| `render_html(payload, inline_css=False, limits?)` / `arender_html` / `render_html_from_toon` | intermediate HTML (no browser); `inline_css=True` for email clients (needs `.[email]` extra; resolves CSS variables, sets `lang` from `meta.locale`) |
| Sections payload (`meta` + `sections: [...]`) | composed documents: `table` (full tabular engine), `text`, `kpi`, `chart` (`bar`/`line`/`pie`/`donut` inline SVG), `image` (data URI), `toc` (linked contents) |
| `ToonParser().parse(text)` / `parse_toon(text)` | `.toon` -> dict |
| `from_dataframe(df, ...)` / `from_csv(...)` / `from_json(...)` | payload builders (needs `.[pandas]` for DataFrame) |
| `payload_schema()` | JSON Schema of the payload (`isis-report schema`) |
| `collect_tables(dataset, layout)` | flat tables + summary rows (powers XLSX/CSV) |
| `TabularReportService(pdf_options?, limits?)` | pipeline `execute(payload)` (Fetch→Process→HTML→PDF) |

## Tests

```bash
pytest -q
pytest -q --cov=isis_report_lib   # coverage gate: 85% (enforced in the CI e2e job)
ruff check src tests
semgrep --test --config .semgrep/rules/ .semgrep/targets/   # custom SAST rules
semgrep scan --config p/default --config .semgrep/rules/ --exclude=.semgrep/targets --metrics=off  # (+ the 2 --exclude-rule from semgrep.yml)
pre-commit run --all-files   # gitleaks secret scan (optional local gate; CI runs it too)
bash scripts/lock-requirements.sh   # regenerate the hash-pinned CI locks after bumping a tool
bash scripts/fuzz-smoke.sh 30       # time-boxed fuzzing of the input parsers (Linux/macOS; needs atheris)
```

Real-PDF tests require `playwright install chromium` and are skipped (`-m "not browser"`) when no browser is available.

## Contributing

Contributions are welcome: open an issue for a bug or idea, or a pull request
for code and documentation. The development setup, the full check list that CI
runs, coding standards and the commit convention are in
[`CONTRIBUTING.md`](CONTRIBUTING.md). Security reports must go through the
private advisory flow in [`SECURITY.md`](SECURITY.md), never a public issue.

## License

MIT — see `LICENSE`.

## Security

- **Dependencies**: audited with `pip-audit` in CI on every PR (app + docs envs); Dependabot keeps SHA-pinned actions and packages updated; releases are built and published by CI via OIDC trusted publishing (no stored tokens).
- **Supply chain**: CodeQL (deep SAST) plus Semgrep (fast patterns) scan every PR/push/weekly; GuardDog screens for malicious packages and dependency-review blocks vulnerable/copyleft deps on PRs; every release ships a reproducible SBOM plus Sigstore attestations (`gh attestation verify`).
- **SAST**: Semgrep scans every PR, push and weekly — registry packs plus custom `.semgrep/` rules locking the guarantees below (sandboxed autoescaped templates, pre-built SVG only, JS-off, no fetch at render time); findings fail CI and upload as SARIF to code scanning.
- **Secrets**: Gitleaks scans the working tree and history on every PR, push and weekly; findings fail CI and upload as SARIF to code scanning. Optional local gate: `pip install pre-commit && pre-commit install`.
- **Trust boundary**: templates (`.jinja` files, `template_dir`) are code — only load them from sources you trust. Report *data* is escaped in HTML output and never executed as template code (charts/sparklines emit pre-built SVG); if you serve the HTML/email output to browsers, treat it like any user-content page.
- **Browser**: pages render with JavaScript disabled in an isolated Chromium context per sync call (shared pool in async mode); `inline_css` strips remote `<link>` stylesheets (no server-side fetches on render); outbound http(s) is denied by default at render time — allow hosts with `allowed_hosts=[...]` (`generate_pdf(...)` / CLI `--allowed-hosts`, never from the payload); the Playwright browser runs headless in its own Chromium sandbox.
- **Denial of service**: operator caps (`DEFAULT_LIMITS`: 1M records / 64 MiB) via API `limits=` or CLI `--max-rows/--max-bytes`, with `--unlimited`/`limits={}` opt-out; payload `meta.limits` may only tighten. Enforced before any shaping for every output format; deeply nested layouts/inputs are rejected with `ValueError`.
- **Exports**: text cells starting with `= + - @` (or tab/CR) are `'`-prefixed in CSV/XLSX so spreadsheets cannot evaluate data as formulas (numeric values, including negatives, are untouched).
- **Robustness**: deeply nested `.toon`/JSON input and report layouts are rejected with `ValueError` instead of crashing the interpreter; `verify_pdf` never raises — malformed signatures report `invalid`.
