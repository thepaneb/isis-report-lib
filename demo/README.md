# 5-minute demo

A board pack with a **table of contents**, **watermark**, KPI cards, a table
with totals, inline SVG charts and a crosstab — from one JSON payload. The
same payload produces PDF, HTML, XLSX and CSV.

## Run it

From the repository root:

```bash
python -m pip install -e ".[xlsx]"
python -m playwright install chromium
python demo/render.py
```

If the package is already installed:

```bash
python -m pip install "isis-report-lib[xlsx]"
python demo/render.py
```

Outputs:

| File | What it is |
|---|---|
| `out/report.pdf` | print-ready PDF with bookmarks and the DRAFT watermark |
| `out/report.html` | the same layout, no browser needed |
| `out/report.xlsx` | one sheet per table, plus **native Excel charts** |
| `out/report.csv` | flattened sections with a UTF-8 BOM for Excel |

Open `out/report.pdf` when it finishes. No Chromium? Skip the PDF:

```bash
python demo/render.py --no-pdf
```

## Change it

Edit [`payload.json`](payload.json) and run again. The interesting bits are:

- `meta.watermark` — repeated on every printed page;
- `sections[0].type: "toc"` — linked contents, PDF bookmarks from the headings;
- `table.layout.total.aggregate: "sum"` — the footer total;
- `chart` sections — inline SVG in PDF/HTML, native charts in XLSX;
- `crosstab` — rows × columns with row, column and grand totals.

## CLI

```bash
isis-report generate demo/payload.json -o demo/out/report.pdf
```

## Docker

From the repository root:

```bash
mkdir -p demo/out
docker build -t isis-report .
docker run --rm -v "$PWD:/work" isis-report generate demo/payload.json -o demo/out/report.pdf
```

The image bundles Chromium and fonts; see the root `Dockerfile`. On Linux, add
`--user "$(id -u):$(id -g)"` if your host UID is not 1000.

## GitHub Actions

The composite action can render the same payload in CI:

```yaml
- uses: thepaneb/isis-report-lib/.github/actions/render@v0.15.1
  with:
    input: demo/payload.json
    output: demo/out/report.pdf
```

See [`examples/github-action.md`](../examples/github-action.md) for a complete
workflow.
