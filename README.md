# isis-report-lib

[![CI](https://github.com/thepaneb/isis-report-lib/actions/workflows/ci.yml/badge.svg)](https://github.com/thepaneb/isis-report-lib/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/isis-report-lib.svg)](https://pypi.org/project/isis-report-lib/)
[![Python](https://img.shields.io/pypi/pyversions/isis-report-lib.svg)](https://pypi.org/project/isis-report-lib/)
[![Wiki](https://img.shields.io/badge/docs-wiki-blue)](https://github.com/thepaneb/isis-report-lib/wiki)Python library for **tabular PDF reports** with customizable hierarchical layouts — extracted from the [isis_report](https://github.com/thepaneb/isis_report) PoC (Robyn microservice), without the server.

**Landing page:** <https://thepaneb.github.io/isis-report-lib/>

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
| XLSX | `generate_xlsx` / `agenerate_xlsx` | One sheet per detail table (context columns repeated), bold totals, `Summary` sheet. Needs `pip install isis-report-lib[xlsx]` |
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

Full example in `examples/`. Note: the sync API opens/closes the browser per call (no leaked processes); the async API reuses the shared pool.

## Composed documents (sections)

For free-form reports, pass `sections` instead of `data` + `layout`:

```python
payload = {
    "meta": {"title": "Board Pack", "locale": "en-US"},
    "sections": [
        {"type": "text", "title": "Intro", "paragraphs": ["Hello.", "World."]},
        {"type": "table", "title": "Sales", "layout": {...}, "data": [...]},
        {"type": "kpi", "title": "Totals", "items": [{"label": "Orders", "value": 42, "format_mask": "int"}]},
        {"type": "chart", "title": "Trend", "chart": {"kind": "bar", "labels": ["Jan", "Feb"], "values": [10, 20]}},
    ],
}
generate_pdf(payload)   # HTML sections.jinja; XLSX/CSV flatten each table/text/kpi/chart section
```

A running balance column is just a field with `"running_balance": "<source field>"` — cumulative sums are computed in row order (e.g. bank statements).

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
| `aggregate` | field def | `sum\|count\|avg\|min\|max` → group footers, detail `tfoot`, grand summary. Flat child lists render as tables (several per item allowed); deeper nesting renders as sections |
| `$print_when` | any level | keep only rows matching `{field, equals\|not_equals\|in\|not_in\|gt\|gte\|lt\|lte\|is_null\|not_null}` |
| `$order_by` | any level | sort rows: `[{field, direction}]` or `"field"` / `"-field"` (nulls last) |
| `visible` / `visible_when` | field def | hide a column; `visible_when` supports `{..., scope: any\|all}` |

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
| `generate_pdf(payload, pdf_options?) -> bytes` | sync PDF from dict/`ReportPayload` |
| `agenerate_pdf(...)` | same, async |
| `generate_pdf_from_toon(text, ...)` / `agenerate_pdf_from_toon` | PDF from `.toon` |
| `generate_xlsx(payload) -> bytes` / `agenerate_xlsx` / `..._from_toon` | .xlsx workbook, no browser (needs `.[xlsx]` extra) |
| `generate_csv(payload, delimiter=",") -> str` / `agenerate_csv` / `..._from_toon` | CSV text, no browser (`bom=True` for Excel) |
| `render_html(payload, inline_css=False)` / `arender_html` / `render_html_from_toon` | intermediate HTML (no browser); `inline_css=True` for email clients (needs `.[email]` extra) |
| Sections payload (`meta` + `sections: [...]`) | composed documents: `table` (full tabular engine), `text`, `kpi`, `chart` (`bar`/`line` inline SVG) |
| `ToonParser().parse(text)` / `parse_toon(text)` | `.toon` -> dict |
| `from_dataframe(df, ...)` / `from_csv(...)` / `from_json(...)` | payload builders (needs `.[pandas]` for DataFrame) |
| `payload_schema()` | JSON Schema of the payload (`isis-report schema`) |
| `collect_tables(dataset, layout)` | flat tables + summary rows (powers XLSX/CSV) |
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
