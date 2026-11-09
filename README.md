# isis-report-lib

Biblioteca Python para geração de relatórios **PDF tabulares** com layouts hierárquicos customizáveis — extraída do POC [isis_report](https://github.com/thepaneb/isis_report) (microserviço Robyn), sem o servidor.

- Entrada: `dict`/`ReportPayload` (`meta` + `layout` opcional + `data`) ou texto **`.toon`**
- Renderização: Jinja2 (templates embutidos no pacote)
- PDF: Playwright (Chromium)
- API: síncrona (`generate_pdf`) + assíncrona (`agenerate_pdf`)

## Instalação

```bash
pip install isis-report-lib
playwright install chromium   # necessário p/ gerar PDF
```

Dev:

```bash
pip install -e ".[dev]"
```

## Uso rápido

```python
from isis_report_lib import generate_pdf, generate_pdf_from_toon, render_html

payload = {
    "meta": {"title": "Pedido de Vendas", "sub_title": "2024", "mode": "exact"},
    "layout": {
        "empresa": {"label": "Empresa", "format_mask": "str", "alignment": "left"},
        "pedidos": {
            "pedido": {"label": "Código", "format_mask": "int", "alignment": "right"},
            "valor_total": {"label": "Valor Total", "format_mask": "float", "alignment": "right"},
        },
    },
    "data": [{"empresa": "CQ CONSULTORIA", "pedidos": [{"pedido": 750, "valor_total": 4000}]}],
}

pdf_bytes = generate_pdf(payload)
open("relatorio.pdf", "wb").write(pdf_bytes)

# Sem Playwright: só o HTML intermediário
html = render_html(payload)

# A partir de .toon
toon = open("examples/pedido.toon", encoding="utf-8").read()
open("relatorio_toon.pdf", "wb").write(generate_pdf_from_toon(toon))
```

Async:

```python
from isis_report_lib import agenerate_pdf, agenerate_pdf_from_toon

pdf = await agenerate_pdf(payload)
pdf = await agenerate_pdf_from_toon(toon_text)
```

Opções do PDF (repassadas ao `page.pdf` do Playwright):

```python
generate_pdf(payload, pdf_options={"format": "A4", "margin": {"top": ".2in", "bottom": ".5in"}})
```

Exemplo completo em `examples/`.

## Payload

| Campo | Tipo | Obrigatório | Descrição |
| --- | --- | --- | --- |
| `meta` | object | sim | `title`, `sub_title`, `mode` (`"exact"`/`"gray"`), `company` |
| `layout` | object | não | definição hierárquica; omitir = inferido dos dados |
| `data` | array | sim | registros crus ou formato template (`{"fields": ..., "groups": ...}`) |

Máscaras: `str` · `int` (milhar `1.234`) · `float` (pt-BR `1.234,50`) · `date`.

## Sintaxe `.toon`

```toon
meta:
  title: Pedido de Vendas
  mode: exact
layout:
  produto{Produto,str,left}
  valor{Valor,float,right}
dados[1]:
  - produto: Caneta
    valor: 5.50
```

`dados[n]` é mapeado para `data`. Ver `examples/pedido.toon`.

## API

| Função | Descrição |
| --- | --- |
| `generate_pdf(payload, pdf_options?) -> bytes` | PDF sync a partir de dict/`ReportPayload` |
| `agenerate_pdf(...)` | idem, async |
| `generate_pdf_from_toon(text, ...)` / `agenerate_pdf_from_toon` | PDF a partir de `.toon` |
| `render_html(payload)` / `arender_html` / `render_html_from_toon` | HTML intermediário (sem browser) |
| `ToonParser().parse(text)` / `parse_toon(text)` | parse `.toon` -> dict |
| `TabularReportService(pdf_options?)` | pipeline `execute(payload)` (Obter→Tratar→HTML→PDF) |

## Testes

```bash
pytest -q
ruff check src tests
```

Testes de PDF real exigem `playwright install chromium` e são pulados (`-m "not browser"`) se o browser não estiver disponível.

## Licença

MIT — ver `LICENSE`.
