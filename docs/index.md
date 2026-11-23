# isis-report-lib

Tabular PDF reports from Python — hierarchical layouts, Jinja2 rendering, Playwright PDF. One function call from data to a print-ready document: sync or async, from a Python dict or a compact `.toon` file.

[PyPI](https://pypi.org/project/isis-report-lib/) · [Source](https://github.com/thepaneb/isis-report-lib) · [Releases](https://github.com/thepaneb/isis-report-lib/releases) · [Wiki](https://github.com/thepaneb/isis-report-lib/wiki)

## What it does

From nested records to a polished PDF. The document adapts to the data instead of rigid bands.

- **Hierarchical layouts** — nested groups become sections; flat child lists render as tables.
- **JSON or `.toon`** — pass a dict/`ReportPayload` or a compact indented `.toon` document.
- **Jinja2 templates** — bundled in the package; point `template_dir` at your own directory to override the layout or reuse its macros.
- **Playwright PDF** — Chromium renders the final document. Sync API opens/closes the browser per call; async API reuses a shared pool.
- **Sync and async** — `generate_pdf`, `agenerate_pdf` and `render_html` for the intermediate HTML (no browser needed).
- **Locale-aware masks** — `str`, `int`, `float`, `date`, `percent`, `currency` and `bool` via Babel/CLDR.

## Quickstart

```bash
pip install isis-report-lib
playwright install chromium   # required to generate PDFs
```

> After upgrading `playwright`, reinstall the browser: each Playwright version pins a specific Chromium build.

```python
from isis_report_lib import generate_pdf

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
```

Async, intermediate HTML (no browser) and CLI:

```python
from isis_report_lib import agenerate_pdf, render_html

pdf_bytes = await agenerate_pdf(payload)
html = render_html(payload)
```

```bash
isis-report generate examples/sales_order.toon -o report.pdf
isis-report render examples/sales_order.toon -o report.html
```

## Payload at a glance

Declarative behavior, not rigid templates. See the full parameter table in the project README.

| Field | What it controls |
|---|---|
| `meta` | Title, subtitle, mode, locale, currency, accent color, page size/orientation, quotas (`max_rows`, `max_bytes`) and `printed_at` (auto-filled). |
| `layout` | Hierarchical field definitions — labels, masks, alignment, visibility. Omit to infer from the data. |
| `data` | Raw records or the template format with nested groups. |
| `aggregate` | `sum`, `count`, `avg`, `min`, `max`, `median`, `distinct` — group footers, detail footers and grand summaries. |
| `$print_when` | Keep only rows matching a field condition. |
| `$order_by` | Sort rows by one or more fields, with nulls last. |
| `visible` / `visible_when` | Hide a column, conditionally. |

## Going further

- **User guide** — task-oriented walkthroughs: first report, data inputs, sections, signing, hardening, CLI recipes, troubleshooting.
- **Standards** — architecture, engineering, security and design rules for contributors.
- **Security model (ASVS)** — OWASP ASVS 4.0.3 applicability mapping.
- **Contributing** — how to report bugs, propose changes and run the checks.
- **Roadmap** — what comes next, done log and non-goals.
- **Changelog** and **Security policy** live with the source on GitHub.

!!! note "Templates are code"
    Report *data* is escaped and never executed as template code — it is interpolated only. Custom templates (`.jinja` files, `template_dir`) execute: only load them from sources you trust.
