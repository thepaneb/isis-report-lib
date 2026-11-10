"""Example: generate sales_order.pdf from the dict payload + sales_order.toon."""

from pathlib import Path

from isis_report_lib import generate_pdf, generate_pdf_from_toon

HERE = Path(__file__).parent

_PATTERN = [(1, 1500, 1500), (2, 1000, 2000), (1, 1500, 1500)]
ITEMS_750 = [
    {"qty": q, "unit_price": u, "line_total": t} for _ in range(20) for (q, u, t) in _PATTERN
]

payload = {
    "meta": {
        "title": "Sales Order",
        "sub_title": "From 01/01/2024 to 12/31/2024",
        "mode": "exact",
    },
    "layout": {
        "company": {"label": "Company", "format_mask": "str", "alignment": "left"},
        "delivery_date": {"label": "Delivery Date", "format_mask": "date", "alignment": "center"},
        "orders": {
            "order": {"label": "Code", "format_mask": "int", "alignment": "right"},
            "order_date": {"label": "Order Date", "format_mask": "date", "alignment": "center"},
            "product_name": {"label": "Product", "format_mask": "str", "alignment": "left"},
            "fee_total": {"label": "Fee Total", "format_mask": "float", "alignment": "right"},
            "grand_total": {"label": "Grand Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
            "items": {
                "qty": {"label": "Qty", "format_mask": "int", "alignment": "right", "aggregate": "sum"},
                "unit_price": {"label": "Unit Price", "format_mask": "float", "alignment": "right"},
                "line_total": {"label": "Line Total", "format_mask": "float", "alignment": "right"},
            },
            "fees": {
                "kind": {"label": "Fee", "format_mask": "str", "alignment": "left"},
                "amount": {"label": "Fee Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
            },
        },
    },
    "data": [
        {
            "company": "ACME CONSULTING",
            "delivery_date": "12/01/2024",
            "orders": [
                {
                    "order": 750,
                    "order_date": "12/01/2024",
                    "product_name": "ACME MEAL",
                    "fee_total": 9.01,
                    "grand_total": 100000,
                    "items": ITEMS_750,
                    "fees": [
                        {"kind": "Service fee", "amount": 5.00},
                        {"kind": "Shipping", "amount": 2.50},
                        {"kind": "Tax", "amount": 1.51},
                    ],
                },
            ],
        },
    ],
}


def main() -> None:
    (HERE / "sales_order.pdf").write_bytes(generate_pdf(payload))
    print("OK:", HERE / "sales_order.pdf")
    toon_text = (HERE / "sales_order.toon").read_text(encoding="utf-8")
    (HERE / "sales_order_toon.pdf").write_bytes(generate_pdf_from_toon(toon_text))
    print("OK:", HERE / "sales_order_toon.pdf")


if __name__ == "__main__":
    main()
