# Guia rápido (PT-BR)

Crie relatórios tabulares em PDF a partir de um dicionário Python ou de um
arquivo `.toon` compacto. Esta página cobre apenas o caminho da instalação ao
primeiro PDF; a tabela completa de parâmetros está no README do projeto.

> **Nota:** esta é uma página PT-BR isolada. A documentação completa — guia,
> galeria, referência da API, changelog e políticas — é mantida em inglês.

## Instalação

```bash
pip install isis-report-lib
playwright install chromium   # necessário para gerar PDFs
```

> Após atualizar o `playwright`, reinstale o navegador: cada versão do Playwright
> usa uma build específica do Chromium.

## Primeiro relatório com um dicionário

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

O mesmo payload também gera HTML sem navegador, ou PDF de forma assíncrona:

```python
from isis_report_lib import agenerate_pdf, render_html

pdf_bytes = await agenerate_pdf(payload)
html = render_html(payload)
```

## Primeiro relatório com `.toon`

O formato `.toon` é uma forma compacta de escrever o mesmo payload. O bloco
`data[n]` contém os registros:

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

```python
from isis_report_lib import generate_pdf_from_toon

pdf_bytes = generate_pdf_from_toon(open("order.toon", encoding="utf-8").read())
open("report.pdf", "wb").write(pdf_bytes)
```

## Linha de comando

A CLI usa os mesmos arquivos `.toon`:

```bash
isis-report generate examples/sales_order.toon -o report.pdf
isis-report render examples/sales_order.toon -o report.html
```

`generate` produz o PDF e `render` produz o HTML intermediário, sem abrir o
navegador.

## Próximos passos

- Veja saídas reais na [Galeria](../gallery.md).
- Consulte assinaturas e docstrings na [Referência da API](../api.md).
- Para agrupamentos, assinatura, limites de segurança e todas as opções de
  `meta`, `layout` e `data`, leia o guia do usuário e o README do projeto.
