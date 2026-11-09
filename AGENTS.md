# Guia de Agentes de IA — isis-report-lib

Biblioteca Python (`src/isis_report_lib`) para geração de PDFs tabulares com layouts
hierárquicos. Extraída do POC `isis_report` (microserviço Robyn); aqui **não há
servidor** — só a lib + testes + exemplos.

## Regras de Ouro
1. **API dupla:** toda funcionalidade pública nova precisa de versão `async def a...`
   e wrapper sync em `src/isis_report_lib/api.py` (via `_run`, que lida com loop ativo).
2. **Sem Robyn:** nada de `robyn`, rotas ou `JSONResponse` neste repo. O pipeline vive em
   `service.py` (`TabularReportService.execute`: Obter → Tratar → HTML → PDF).
3. **Templates embutidos:** ficam em `src/isis_report_lib/templates/` e são carregados via
   `rendering.get_jinja_env()` (importlib.resources). Nunca use caminho relativo a `cwd`.

## Estrutura
```
src/isis_report_lib/
├── __init__.py    # exports públicos (atualizar __all__ ao expor algo novo)
├── api.py         # generate_pdf/agenerate_pdf, ..._from_toon, render_html/...
├── models.py      # MetaInfo, ReportPayload (pydantic v2)
├── layout.py      # convert_layout, convert_data, infer_layout, is_template_format
├── toon.py        # ToonParser, parse_toon
├── formatting.py  # format_value (máscaras int/float/date/str)
├── rendering.py   # arender_report_html / render_report_html
├── pdf.py         # pool Playwright (ensure_browser, get_pdf_from_html, close_browser)
├── service.py     # BaseReportService + TabularReportService
└── templates/     # relatorio_base/tabular*.jinja
tests/             # test_formatting/layout/toon/service (mocks), test_pdf_e2e (browser)
examples/          # generate_example.py + pedido.toon
```

## Detalhes que já morderam (não reintroduzir)
- **Dados crus sem `layout`:** o template itera `data.fields`, então registros crus precisam
  ser embrulhados em `{"fields": ...}` (ver `_tratar_dados` e `arender_html`). O POC tinha
  esse bug (HTML vazio); a lib corrige — manter.
- **Pool Playwright × event loops:** `_browser` é singleton mas preso a um loop. `pdf.py`
  rastreia `_owner_loop` e recria o browser em loop novo/fechado (suítes criam um loop por
  teste). Não volte a checar só `if _browser is not None`.
- **`_run` com loop ativo:** usa `ThreadPoolExecutor + asyncio.run` para não travar
  (Jupyter). Não simplificar para `asyncio.run` direto.

## Workflow
```bash
pip install -e ".[dev]"
playwright install chromium   # só p/ testes e2e / geração real de PDF
python -m pytest tests -q -m "not browser"   # sem browser
python -m pytest tests -q                    # completo (precisa do chromium)
python -m ruff check src tests
python -m ruff format --check src tests
```

## Testes
- Unitários com mocks para `rendering.arender_report_html` e `pdf.get_pdf_from_html`
  (ver `test_service.py`); nunca exigir browser fora de `test_pdf_e2e.py`.
- `test_pdf_e2e.py` é marcado `browser` e pula sozinho sem Chromium
  (`_browser_available`). Registrar marks novas em `pyproject.toml`.
- Ao mudar `layout.py`/`toon.py`/`formatting.py`, portar/adicionar casos nos testes
  correspondentes.

## Convenções
- Código e docstrings: classes em Inglês; pipeline do serviço pode usar PT
  (`_obter_dados`, `_tratar_dados`, `_gerar_html`, `_gerar_pdf`) por paridade com o POC.
- Máscaras: `str` · `int` (`1.234`) · `float` pt-BR (`1.234,50`) · `date` (pass-through).
- Templates: estendem `relatorio_base.jinja`; formatação via `fmt(valor, mascara)` do Jinja.

## Commits
Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
