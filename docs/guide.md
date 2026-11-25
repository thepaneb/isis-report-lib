# User guide

Task-oriented walkthroughs for everyday work with isis-report-lib. The
[README](https://github.com/thepaneb/isis-report-lib#readme) stays the
exhaustive reference (every parameter table lives there); this guide shows
how the pieces fit together.

## First report

Install the library and, for PDFs, a Chromium build:

```bash
pip install isis-report-lib
playwright install chromium
```

A report is a payload dict: `meta` (title and friends), an optional
`layout` (columns), and `data` (records):

```python
from isis_report_lib import generate_pdf

payload = {
    "meta": {"title": "Sales Order", "locale": "en-US"},
    "layout": {
        "product": {"label": "Product", "format_mask": "str", "alignment": "left"},
        "total": {"label": "Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
    },
    "data": [{"product": "Pen", "total": 5.50}, {"product": "Ink", "total": 12.00}],
}

pdf_bytes = generate_pdf(payload)
open("report.pdf", "wb").write(pdf_bytes)
```

Async and HTML without a browser:

```python
from isis_report_lib import agenerate_pdf, render_html

pdf_bytes = await agenerate_pdf(payload)  # shared browser pool
html = render_html(payload)               # no browser needed
```

## Loading data

Payloads also come from `.toon` text, CSV, JSON and dataframes — every
builder returns the same payload dict, so everything below applies equally:

```python
from isis_report_lib import generate_pdf_from_toon, render_html_from_toon
from isis_report_lib.inputs import from_csv, from_dataframe, from_json

generate_pdf_from_toon(open("order.toon", encoding="utf-8").read())
generate_pdf(from_csv("sales.csv", delimiter=";"))   # light int/float/bool coercion
generate_pdf(from_json("payload.json"))              # list -> data; full payload passes through
generate_pdf(from_dataframe(df, meta={"title": "Sales"}))  # needs the pandas extra
```

`.toon` is the compact authoring format (`data[n]` holds the records):

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

## Shaping the report

Omit `layout` to infer columns from the data. Nest a list under a key and
each parent becomes a group with its own detail table (several detail lists
per item are allowed); deeper nesting renders as sections:

```python
payload = {
    "meta": {"title": "By company"},
    "layout": {"company": {"label": "Company", "format_mask": "str", "alignment": "left"}},
    "data": [{"company": "ACME", "orders": [{"order": 1}, {"order": 2}]}],
}
```

Behavior is declarative, not positional — the document adapts to the data:

- `meta.page` (`size`, `orientation`, `margins`) drives the PDF page; explicit `pdf_options` win.
- `aggregate` (`sum|count|avg|min|max|median|distinct`) adds group footers, detail `tfoot` and a grand summary.
- `$print_when` keeps only matching rows; `$order_by` sorts them (nulls last).
- `visible` / `visible_when` hide columns; `cell_rules` tint cells by value (first match wins).
- `missing_text` names `None` explicitly; `substitutions` map raw values before formatting.
- `footnote` (`"text"` or `{"mark", "text"}`) annotates a column label; notes render per report/section, in the XLSX `Notes` sheet and as CSV `# [mark]` lines.
- `color_scale: {min, max}` gradients and `data_bar: true` native Excel bars visualize magnitude; `meta.summary_side` moves the grand summary.

See the README parameters table for the exhaustive list.

## Composed documents

For free-form reports, pass `sections` instead of `data` + `layout`. Each
entry is one of `table` (full tabular engine), `text`, `kpi`, `chart`
(`bar`/`line` inline SVG) or `crosstab` (pivot with totals):

```python
payload = {
    "meta": {"title": "Board Pack", "locale": "en-US"},
    "sections": [
        {"type": "text", "title": "Intro", "paragraphs": ["Hello.", "World."]},
        {"type": "table", "title": "Sales", "layout": {...}, "data": [...]},
        {"type": "kpi", "title": "Totals", "items": [{"label": "Orders", "value": 42}]},
        {"type": "chart", "title": "Trend",
         "chart": {"kind": "bar", "labels": ["Jan", "Feb"], "values": [10, 20]}},
    ],
}
generate_pdf(payload)
```

A running balance is just a field with `"running_balance": "<source field>"` —
cumulative sums computed in row order (e.g. bank statements).

## Signing reports

The signing API is a tamper-evident *seal*, not Adobe PAdES: it proves origin
and integrity to `verify_pdf` holders, without CAs or timestamps.

```bash
isis-report keygen -o secret.key
isis-report sign report.pdf --key-file secret.key --key-id portal-1 -o report.signed.pdf
isis-report verify report.signed.pdf --key-file secret.key   # exit 0 = VALID
```

```python
from isis_report_lib import generate_hmac_key, sign_pdf, verify_pdf

secret = generate_hmac_key()
signed = sign_pdf(pdf_bytes, secret, key_id="portal-1")
assert verify_pdf(signed, secret).valid  # .reason/.alg/.sha256/.key_id/.issued_at
```

Key rotation without flag days: verify against a `{key_id: key}` mapping or an
ordered key list — the envelope `key_id` selects first, the rest are tried in
order. Retire the old key once its seals expire out of circulation.
`verify_pdf` never raises: malformed blocks, keys or algorithms report
`invalid` — always check `.valid`.

HMAC keys must be **at least 32 bytes** (`generate_hmac_key`/`sign_pdf`);
`verify_pdf` still accepts legacy short keys for existing seals and reports a
warning in `info.details`. Key files should be `0600`; add
`--require-key-permissions` to `sign`/`verify` to fail instead of warn on POSIX
when the file is group/other-readable.

## Hardening untrusted input

Report *data* is untrusted by design (escaped, never executed); *templates*
are code (load only from sources you trust). The operator quota cap is
authoritative and on by default (`DEFAULT_LIMITS`: 1M records / 64 MiB);
payload `meta.limits` may only tighten it:

```python
# Operator cap (applies to PDF, XLSX, CSV and HTML); payload can only lower it.
generate_pdf(payload, limits={"max_rows": 10_000, "max_bytes": 1_048_576})
generate_pdf(payload, limits={})  # disable the operator cap (payload limits still apply)
```

```bash
isis-report generate untrusted.toon -o out.pdf --max-rows 10000 --max-bytes 1048576
isis-report generate untrusted.toon -o out.pdf --unlimited   # opt out of the operator caps
```

```python
# Outbound http(s) is denied by default at render time; allow-list hosts explicitly.
# This must come from your code/flags — never from the payload itself.
generate_pdf(payload, allowed_hosts=["fonts.example.com", "127.0.0.1"])
```

```bash
isis-report generate report.toon -o out.pdf --allowed-hosts fonts.example.com
```

## CLI recipes

```bash
isis-report generate order.toon -o report.pdf --page-format Letter
isis-report generate data.csv --delimiter ";" -o report.xlsx
isis-report generate payload.json --format csv --bom -o report.csv
isis-report render order.toon --inline-css -o email.html   # needs the email extra
isis-report schema -o payload.schema.json                 # JSON Schema for editors
```

Exit codes: `0` ok, `1` generation failure, `2` bad input/usage. Key files
should be `0600` (the CLI warns otherwise on POSIX; `--require-key-permissions`
makes it fail).

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ValueError: ... exceeding the max_rows limit (...)` | payload over the effective (operator ∩ payload) quota | raise the operator cap or shrink the input |
| `ValueError: Invalid meta.limits...` / `Unknown meta.limits key` | typo'd or non-positive limit | use `{max_rows, max_bytes}` positive ints |
| `ValueError: HMAC key must be at least 32 bytes` | short/legacy key on sign | generate a new key with `isis-report keygen` |
| `ValueError: Invalid allowed_hosts...` | scheme/port/path/wildcard in an entry | pass bare hostnames (`example.com`), one per `--allowed-hosts` |
| Remote images/fonts missing in the PDF | egress deny-by-default | add the host to `allowed_hosts` |
| `ValueError: ... nested too deeply ...` | hostile `.toon`/JSON/layout nesting | recursion is bounded by design; simplify the input |
| `ValueError: Template ... uses blocked constructs` | custom template reaches Python internals | sandboxed env: rewrite without attribute access |
| `INVALID: ...` from `verify` | modified file, wrong key or algorithm mismatch | check `.reason`; rotate keys via keyring instead of re-signing history |
| `Unknown chart kind` / `Unknown aggregate` / `Rule has no known operator` | typo in a spec value | use the documented value sets (error names them) |
| `Cannot guess ... format from extension` | unknown `-o` suffix | pass `--format` / `--input-format` explicitly |

Still stuck? Open an issue with the minimal payload reproducer (redact real
data) — see [Security policy](https://github.com/thepaneb/isis-report-lib/blob/main/SECURITY.md)
for vulnerability reports.
