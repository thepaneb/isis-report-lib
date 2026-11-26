# How it compares

There is no single best PDF library — the right choice depends on where the
layout lives, which outputs you need and how much runtime you can ship. This
page is a fair summary of the main alternatives, last reviewed in November
2026. WeasyPrint, ReportLab and fpdf2 are mature and actively maintained; this
project is newer, so weigh maturity and ecosystem accordingly. Pick by
constraint, not by feature count.

| | **isis-report-lib** | [WeasyPrint](https://weasyprint.org/) | [ReportLab](https://www.reportlab.com/) | [fpdf2](https://py-pdf.github.io/fpdf2/) |
|---|---|---|---|---|
| **Layout model** | Jinja/HTML + hierarchical data | HTML/CSS | Python API (canvas/platypus) | Python API |
| **PDF engine** | Chromium via Playwright | own renderer | own renderer | own renderer |
| **Browser required** | Yes, for PDF | No | No | No |
| **CSS support** | Full Chromium | CSS Paged Media | Own styles | Limited |
| **JavaScript** | Disabled at render | Not executed | N/A | N/A |
| **Outputs** | PDF, HTML, XLSX, CSV | PDF, PNG | PDF (+ bitmap via `renderPM`) | PDF |
| **Nested records** | Built in (groups → sections/tables) | Manual | Manual | Manual |
| **Tables + totals** | Built in (`aggregate`, crosstab) | Manual HTML | Platypus tables | Manual |
| **Charts** | Inline SVG (PDF/HTML); native Excel charts (XLSX) | External/HTML | External | External |
| **Signing** | HMAC-SHA256 / Ed25519 seal | — | — | — |
| **Runtime footprint** | Playwright + Chromium | Pango/fontconfig | Pure Python | Pure Python |

## When to choose each

**isis-report-lib** — data-heavy reports made of nested records, where the same
payload must also produce XLSX/CSV, and where you want quotas, a tamper-evident
seal or Jinja templates without writing a server. The cost is Chromium: PDF
generation needs Playwright plus a browser download, and the sync API starts a
browser per call (the async API reuses a pool). If you only need simple PDFs or
cannot ship a browser, one of the alternatives is a better fit.

**WeasyPrint** — HTML/CSS designs that must become PDFs without a browser.
Excellent CSS Paged Media support (running headers, page counters, named
pages) and a much smaller runtime than Chromium. You still write the HTML
yourself; nested data shaping, spreadsheets and signing are application code.

**ReportLab** — precise programmatic control over every element, a long track
record in invoice/statement pipelines, and no browser or system libraries. The
trade-off is that layout is code: tables, page breaks and styles are assembled
explicitly, and HTML/CSS is not the primary model.

**fpdf2** — a small, pure-Python dependency for straightforward PDFs. Great for
scripts, labels and simple reports; basic HTML support but far less CSS than
Chromium or WeasyPrint. You build the document cell by cell.

## Notes on the comparison

- “Signing” means an application-level origin/integrity seal. `isis-report-lib`
  is **not** a PAdES implementation; none of these libraries replaces a
  qualified electronic signature.
- isis-report-lib denies outbound http(s) at render time by default and runs
  Chromium with JavaScript disabled; if you allow hosts, treat the rendered
  HTML as untrusted content.
- Footprint is qualitative: ReportLab and fpdf2 are pure Python, WeasyPrint
  needs Pango/fontconfig, and isis-report-lib needs Playwright plus Chromium.
  Measure install size and cold-start time for your own deployment.
- The `.toon` input format is specific to this project; JSON and Python dicts
  are the portable path.

See the [gallery](gallery.md) for real outputs and the
[user guide](guide.md) for the full feature set.
