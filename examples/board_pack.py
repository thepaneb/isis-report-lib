"""Example: composed board-pack report (text + table + kpi + charts) and a bank statement."""

from pathlib import Path

from isis_report_lib import generate_pdf

HERE = Path(__file__).parent

BOARD_PACK = {
    "meta": {"title": "Board Pack - Q1", "sub_title": "Sales review", "mode": "exact", "locale": "en-US"},
    "sections": [
        {
            "type": "text",
            "title": "Highlights",
            "paragraphs": [
                "Revenue grew for the second quarter in a row, driven by Product Alpha.",
                "Churn stayed flat at 2%.",
            ],
        },
        {
            "type": "table",
            "title": "Revenue by product",
            "layout": {
                "product": {"label": "Product", "format_mask": "str", "alignment": "left"},
                "total": {"label": "Total", "format_mask": "float", "alignment": "right", "aggregate": "sum"},
            },
            "data": [{"product": "Alpha", "total": 12000}, {"product": "Beta", "total": 8000}],
        },
        {
            "type": "kpi",
            "title": "Key figures",
            "items": [
                {"label": "Orders", "value": 152, "format_mask": "int"},
                {"label": "Churn", "value": 0.02, "format_mask": "percent"},
            ],
        },
        {
            "type": "chart",
            "title": "Quarterly revenue",
            "chart": {"kind": "bar", "labels": ["Q3", "Q4", "Q1"], "values": [15000, 18000, 20000]},
        },
        {
            "type": "chart",
            "title": "Revenue trend",
            "chart": {"kind": "line", "labels": ["Q3", "Q4", "Q1"], "values": [15000, 18000, 20000], "color": "#1B7A3D"},
        },
    ],
}

STATEMENT = {
    "meta": {"title": "Account statement", "sub_title": "January 2024", "mode": "exact", "locale": "en-US"},
    "layout": {
        "date": {"label": "Date", "format_mask": "date", "alignment": "left"},
        "moves": {
            "desc": {"label": "Description", "format_mask": "str", "alignment": "left"},
            "amount": {"label": "Amount", "format_mask": "float", "alignment": "right"},
            "balance": {"label": "Balance", "format_mask": "float", "alignment": "right", "running_balance": "amount"},
        },
    },
    "data": [
        {
            "date": "01/31/2024",
            "moves": [
                {"desc": "Opening", "amount": 0},
                {"desc": "Invoice #101", "amount": 2500},
                {"desc": "Office supplies", "amount": -320.5},
                {"desc": "Invoice #102", "amount": 1175.25},
                {"desc": "Bank fee", "amount": -9.9},
            ],
        }
    ],
}


def main() -> None:
    (HERE / "board_pack.pdf").write_bytes(generate_pdf(BOARD_PACK))
    print("OK:", HERE / "board_pack.pdf")
    (HERE / "statement.pdf").write_bytes(generate_pdf(STATEMENT))
    print("OK:", HERE / "statement.pdf")


if __name__ == "__main__":
    main()
