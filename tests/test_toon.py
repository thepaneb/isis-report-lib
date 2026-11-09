"""Testes do parser .toon (portados do POC + parse do exemplo)."""

from pathlib import Path

from isis_report_lib.toon import ToonParser, parse_toon

parser = ToonParser()


def test_simple_key_value():
    assert parser.parse("title: Hello") == {"title": "Hello"}


def test_type_coercion():
    result = parser.parse("a: 1\nb: 2.5\nc: true\nd: false\ne: texto")
    assert result == {"a": 1, "b": 2.5, "c": True, "d": False, "e": "texto"}


def test_compact_layout_field():
    result = parser.parse("layout:\n  produto{Produto,str,left}")
    assert result["layout"]["produto"] == {"label": "Produto", "format_mask": "str", "alignment": "left"}


def test_compact_array_of_objects():
    result = parser.parse("cargas[2]{qtde,valor}:\n  1,1500\n  2,1000")
    assert result["cargas"] == [{"qtde": 1, "valor": 1500}, {"qtde": 2, "valor": 1000}]


def test_dados_maps_to_data():
    result = parser.parse("dados[1]:\n  - produto: Caneta")
    assert result["data"] == [{"produto": "Caneta"}]


def test_full_example_file():
    text = (Path(__file__).parent.parent / "examples" / "pedido.toon").read_text(encoding="utf-8")
    result = parse_toon(text)
    assert result["meta"]["title"] == "Pedido de Vendas"
    assert result["layout"]["empresa"]["label"] == "Empresa"
    assert len(result["data"]) == 1
    assert len(result["data"][0]["pedidos"]) == 2
