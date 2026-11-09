"""Exemplo: gera relatorio.pdf a partir do payload dict + pedido.toon."""

from pathlib import Path

from isis_report_lib import generate_pdf, generate_pdf_from_toon

HERE = Path(__file__).parent

payload = {
    "meta": {
        "title": "Pedido de Vendas",
        "sub_title": "De 01/01/2024 até 31/12/2024",
        "mode": "exact",
    },
    "layout": {
        "empresa": {"label": "Empresa", "format_mask": "str", "alignment": "left"},
        "data_entrega": {"label": "Data Entrega", "format_mask": "date", "alignment": "center"},
        "pedidos": {
            "pedido": {"label": "Código", "format_mask": "int", "alignment": "right"},
            "data_pedido": {"label": "Data Pedido", "format_mask": "date", "alignment": "center"},
            "nome_produto": {"label": "Produto", "format_mask": "str", "alignment": "left"},
            "total_tarifa": {"label": "Total Tarifa", "format_mask": "float", "alignment": "right"},
            "valor_total": {"label": "Valor Total", "format_mask": "float", "alignment": "right"},
            "cargas": {
                "qtde": {"label": "Quantidade", "format_mask": "int", "alignment": "right"},
                "valor_unitario": {"label": "Valor Unitário", "format_mask": "float", "alignment": "right"},
                "valor_total": {"label": "Valor Total", "format_mask": "float", "alignment": "right"},
            },
        },
    },
    "data": [
        {
            "empresa": "CQ CONSULTORIA ADMINITRATIVA",
            "data_entrega": "01/12/2024",
            "pedidos": [
                {
                    "pedido": 750,
                    "data_pedido": "01/12/2024",
                    "nome_produto": "CQ REFEIÇÃO",
                    "total_tarifa": 9.01,
                    "valor_total": 4000,
                    "cargas": [
                        {"qtde": 1, "valor_unitario": 1500, "valor_total": 1500},
                        {"qtde": 1, "valor_unitario": 1000, "valor_total": 1000},
                        {"qtde": 1, "valor_unitario": 1500, "valor_total": 1500},
                    ],
                },
            ],
        },
    ],
}


def main() -> None:
    (HERE / "relatorio.pdf").write_bytes(generate_pdf(payload))
    print("OK:", HERE / "relatorio.pdf")
    toon_text = (HERE / "pedido.toon").read_text(encoding="utf-8")
    (HERE / "relatorio_toon.pdf").write_bytes(generate_pdf_from_toon(toon_text))
    print("OK:", HERE / "relatorio_toon.pdf")


if __name__ == "__main__":
    main()
