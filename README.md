# isis-report-lib

[![CI](https://github.com/thepaneb/isis-report-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/thepaneb/isis-report-lib/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/isis-report-lib.svg)](https://pypi.org/project/isis-report-lib/)
[![Python](https://img.shields.io/pypi/pyversions/isis-report-lib.svg)](https://pypi.org/project/isis-report-lib/)

Python library for **tabular PDF reports** with customizable hierarchical layouts — extracted from the [isis_report](https://github.com/thepaneb/isis_report) PoC (Robyn microservice), without the server.

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
# PDF from .toon or .json (format guessed from extension)
isis-report generate examples/sales_order.toon -o report.pdf
isis-report generate payload.json --page-format Letter

# Intermediate HTML without a browser (prints to stdout unless -o is given)
isis-report render examples/sales_order.toon -o report.html
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

Via CLI: `--page-format`, `--header-template FILE`, `--footer-template FILE`. The report footer shows `meta.printed_at`, auto-filled with the current timestamp when absent.

Full example in `examples/`. Note: the sync API opens/closes the browser per call (no leaked processes); the async API reuses the shared pool.

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

## Payload

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `meta` | object | yes | `title`, `sub_title`, `mode` (`"exact"`/`"gray"`), `company`, `locale` (`"pt-BR"`, `"en-US"`…), `currency` (override, e.g. `"EUR"`), `accent_color`, `printed_at` (auto-filled) |
| `layout` | object | no | hierarchical field definition; omit to infer from data |
| `data` | array | yes | raw records or template format (`{"fields": ..., "groups": ...}`) |

Masks (locale-aware via Babel/CLDR): `str` · `int` · `float` · `date` (localized for `date`/`datetime` objects) · `percent` · `currency` · `bool` (`Yes`/`No`).

```python
payload = {
    "meta": {"title": "Sales Order", "locale": "en-US"},  # numbers as 1,234.50, $1,234.50
    "data": [...],
}
```

```bash
isis-report generate order.toon --locale en-US -o out.pdf   # overrides meta.locale
```

## `.toon` syntax

```toon
meta:
  title: Sales Order
  mode: exact
layout:
  product{Product,str,left}
  total{Total,float,right}
data[1]:
  - product: Pen
    total: 5.50
```

`data[n]` holds the records (`dados[n]` still accepted as a legacy alias). See `examples/sales_order.toon`.

## API

| Function | Description |
| --- | --- |
| `generate_pdf(payload, pdf_options?) -> bytes` | sync PDF from dict/`ReportPayload` |
| `agenerate_pdf(...)` | same, async |
| `generate_pdf_from_toon(text, ...)` / `agenerate_pdf_from_toon` | PDF from `.toon` |
| `render_html(payload)` / `arender_html` / `render_html_from_toon` | intermediate HTML (no browser) |
| `ToonParser().parse(text)` / `parse_toon(text)` | `.toon` -> dict |
| `TabularReportService(pdf_options?)` | pipeline `execute(payload)` (Fetch→Process→HTML→PDF) |

## Tests

```bash
pytest -q
pytest -q --cov=isis_report_lib   # coverage gate: 85% (enforced in the CI e2e job)
ruff check src tests
```

Real-PDF tests require `playwright install chromium` and are skipped (`-m "not browser"`) when no browser is available.

## License

MIT — see `LICENSE`.

## Security

- **Dependencies**: audited with `pip-audit` (no known vulnerabilities); Dependabot keeps actions and packages updated; releases are built and published by CI via OIDC trusted publishing (no stored tokens).
- **Trust boundary**: templates (`.jinja` files, `template_dir`) are code — only load them from sources you trust. Report *data* (dict/JSON/`.toon`) is never executed as template code, only interpolated. Jinja autoescaping is off by design (report HTML is rendered to PDF, not served to browsers).
- **Robustness**: deeply nested `.toon` input is rejected with `ValueError` instead of crashing the interpreter; the Playwright browser runs headless in its own Chromium sandbox per call (sync API) or a shared pool (async API).
