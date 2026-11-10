# AI Agent Guide — isis-report-lib

Python library (`src/isis_report_lib`) for tabular PDF reports with hierarchical
layouts. Extracted from the `isis_report` PoC (Robyn microservice); there is **no
server** here — only the library + tests + examples.

## Golden Rules
1. **Dual API:** every new public feature needs an `async def a...` version and
   a sync wrapper in `src/isis_report_lib/api.py` (via `_run`, which handles a
   running loop). The sync API closes its own browser per call (`close_owned_browser`).
2. **No Robyn:** no `robyn`, routes, or `JSONResponse` in this repo. The pipeline lives in
   `service.py` (`TabularReportService.execute`: Fetch → Process → HTML → PDF).
3. **Bundled templates:** live in `src/isis_report_lib/templates/` and load via
   `rendering.get_jinja_env()` (importlib.resources). Never use paths relative to `cwd`.

## Layout
```
src/isis_report_lib/
├── __init__.py    # public exports (update __all__ when exposing something new)
├── api.py         # generate_pdf/agenerate_pdf, ..._from_toon, render_html/...
├── models.py      # MetaInfo, ReportPayload (pydantic v2)
├── layout.py      # convert_layout, convert_data, infer_layout, is_template_format
├── toon.py        # ToonParser, parse_toon
├── formatting.py  # format_value (int/float/date/str masks)
├── rendering.py   # arender_report_html / render_report_html
├── pdf.py         # Playwright pool (ensure_browser, get_pdf_from_html, close_browser)
├── service.py     # BaseReportService + TabularReportService
├── cli.py         # isis-report generate/render (console script)
└── templates/     # base/tabular*.jinja
tests/             # test_formatting/layout/toon/service (mocks), test_pdf_e2e (browser)
examples/          # generate_example.py + sales_order.toon
```

## Pitfalls (do not reintroduce)
- **Raw data without `layout`:** the template iterates `row.fields`, so raw records must
  be wrapped in `{"fields": ...}` (see `_process_data` and `arender_html`).
- **Playwright pool × event loops:** `_browser` is a singleton bound to a loop. `pdf.py`
  tracks `_owner_loop` and recreates the browser on a new/closed loop (suites create one
  loop per test). Never go back to a plain `if _browser is not None` check.
- **Never `await` a foreign-loop close:** `_reset_unlocked` abandons (without awaiting)
  state from a different/closed loop — cross-loop `await` hangs on Linux. The sync API
  shuts down its own browser at the end via `close_owned_browser` (current loop only).
- **`_run` with a running loop:** uses `ThreadPoolExecutor + asyncio.run` to avoid
  blocking (Jupyter). Do not simplify to a bare `asyncio.run`.

## Workflow (`main` is protected: branch → PR → CI → merge)
```bash
git checkout -b feat/xyz
# ... work ...
python -m ruff check src tests && python -m pytest tests -q
git push -u origin feat/xyz   # then open a PR; merge after the gate passes
```
Release flow: tag `vX.Y.Z` + GitHub Release → PyPI via Trusted Publishing.

```bash
pip install -e ".[dev]"
playwright install chromium   # only for e2e tests / real PDF generation
python -m pytest tests -q -m "not browser"   # without browser
python -m pytest tests -q                    # full suite (needs Chromium)
python -m pytest tests -q --cov=isis_report_lib  # 85% gate (enforced in CI e2e job)
python -m ruff check src tests
python -m ruff format --check src tests
```

## Tests
- Unit tests use mocks for `rendering.arender_report_html` and `pdf.get_pdf_from_html`
  (see `test_service.py`); never require a browser outside `test_pdf_e2e.py`.
- `test_pdf_e2e.py` is marked `browser` and skips itself without Chromium
  (`_browser_available`). Register new marks in `pyproject.toml`.
- When changing `layout.py`/`toon.py`/`formatting.py`, port/add cases to the
  matching test files.

## Conventions
- Code and docstrings in English; pipeline methods use short verbs
  (`_fetch_data`, `_process_data`, `_render_html`, `_generate_pdf`).
- Masks are locale-aware (Babel/CLDR, `meta.locale`, default `pt-BR`): `str` · `int` · `float` · `date` · `percent` · `currency` (territory default, `meta.currency` override) · `bool` (`Yes`/`No`).
- Templates extend `base.jinja`; formatting via the Jinja `fmt(value, mask)` helper.
  Custom dirs layer over bundled templates (`template_dir`/`template_name`); every
  template gets `dataset`, `layout`, `meta`, `fmt`, `zip`.
- Report parameters: `meta.page`, field `aggregate`, `$print_when`, `$order_by`,
  `visible`/`visible_when` — see `layout.build_report`; one nested group per level
  (extra group keys merge into the same list).

## Commits
Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
