# GitHub Action example

Copy the workflow below to `.github/workflows/render.yml` in your repository.
The action installs the pinned `isis-report-lib` release from PyPI and Chromium
only for PDF.

```yaml
name: Render report

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          persist-credentials: false

      - name: Render PDF
        uses: thepaneb/isis-report-lib/.github/actions/render@v0.15.1
        with:
          input: examples/sales_order.toon
          output: artifacts/sales-order.pdf
          format: pdf

      - name: Upload report
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7
        with:
          name: sales-order
          path: artifacts/sales-order.pdf
```

For production, pin the `uses:` reference to the 40-character commit SHA of the
release (tags can be moved); Dependabot can keep it updated.
