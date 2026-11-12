"""Payload builder tests (pandas/CSV/JSON/schema)."""

import json

import pytest


def test_from_dataframe_converts_and_cleans():
    pd = pytest.importorskip("pandas")
    import datetime

    from isis_report_lib.inputs import from_dataframe

    df = pd.DataFrame(
        {
            "product": ["Pen", None],
            "total": [10.5, float("nan")],
            "when": [pd.Timestamp("2024-01-01"), pd.NaT],
            "active": [True, False],
        }
    )
    payload = from_dataframe(df, meta={"title": "T"})
    assert payload["meta"] == {"title": "T"}
    rows = payload["data"]
    assert rows[0]["product"] == "Pen"
    assert rows[1]["product"] is None
    assert rows[1]["total"] is None
    assert rows[0]["when"] == datetime.datetime(2024, 1, 1)
    assert rows[1]["when"] is None
    assert "layout" not in payload
    payload = from_dataframe(df, layout={"product": {"label": "Product"}})
    assert payload["layout"]["product"]["label"] == "Product"


def test_from_dataframe_missing_pandas(monkeypatch):
    import sys

    from isis_report_lib import inputs

    monkeypatch.setitem(sys.modules, "pandas", None)
    with pytest.raises(ImportError, match="pip install isis-report-lib\\[pandas\\]"):
        inputs.from_dataframe(object())


def test_from_csv_file_and_handle(tmp_path):
    from isis_report_lib.inputs import from_csv

    src = tmp_path / "in.csv"
    src.write_text("product,total,active\nPen,10.5,true\nPencil,2,\n", encoding="utf-8")
    payload = from_csv(src)
    assert payload["data"] == [
        {"product": "Pen", "total": 10.5, "active": True},
        {"product": "Pencil", "total": 2, "active": ""},
    ]
    with open(src, encoding="utf-8") as handle:
        assert from_csv(handle, meta={"title": "T"}, delimiter=",")["meta"] == {"title": "T"}
    semi = tmp_path / "semi.csv"
    semi.write_text("a;b\n1;2\n", encoding="utf-8")
    assert from_csv(semi, delimiter=";")["data"] == [{"a": 1, "b": 2}]


def test_from_json_list_dict_and_errors(tmp_path):
    from isis_report_lib.inputs import from_json

    src = tmp_path / "in.json"
    src.write_text('[{"a": 1}]', encoding="utf-8")
    assert from_json(src) == {"data": [{"a": 1}]}
    assert from_json(src, meta={"title": "T"})["meta"] == {"title": "T"}
    full = tmp_path / "full.json"
    full.write_text(json.dumps({"meta": {"title": "A"}, "data": [{"a": 1}]}), encoding="utf-8")
    assert from_json(full)["meta"] == {"title": "A"}
    assert from_json(full, meta={"title": "B"})["meta"] == {"title": "B"}
    assert from_json([{"a": 1}]) == {"data": [{"a": 1}]}
    assert from_json({"meta": {"title": "A"}}, layout={"x": {}})["layout"] == {"x": {}}
    bad = tmp_path / "bad.json"
    bad.write_text("42", encoding="utf-8")
    with pytest.raises(ValueError, match="list or a payload object"):
        from_json(bad)


def test_payload_schema_shape():
    from isis_report_lib import payload_schema

    schema = payload_schema()
    assert schema["title"] == "ReportPayload"
    assert set(schema["$defs"]) >= {"MetaInfo"}
    assert "meta" in schema["properties"] and "data" in schema["properties"]


def test_clean_value_edge_cases():
    pd = pytest.importorskip("pandas")

    from isis_report_lib.inputs import _clean_value

    assert _clean_value([1, 2], pd) == [1, 2]  # pd.isna() unusable -> passthrough
    assert _clean_value("x", pd) == "x"


def test_from_json_file_handle():
    import io

    from isis_report_lib.inputs import from_json

    assert from_json(io.StringIO('[{"a": 1}]')) == {"data": [{"a": 1}]}
