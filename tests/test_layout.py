"""Testes do conversor de layout (portados do POC)."""

from isis_report_lib.layout import convert_data, convert_layout, infer_layout, is_template_format


def test_empty_layout():
    assert convert_layout({}) == {"groups": {"header": []}}


def test_simple_fields():
    result = convert_layout(
        {
            "nome": {"label": "Nome", "format_mask": "str", "alignment": "left"},
            "idade": {"label": "Idade", "format_mask": "int", "alignment": "right"},
        }
    )
    assert len(result["groups"]["header"]) == 2
    assert result["groups"]["header"][0]["name"] == "nome"


def test_single_group():
    result = convert_layout(
        {
            "empresa": {"label": "Empresa", "format_mask": "str", "alignment": "left"},
            "pedidos": {
                "pedido": {"label": "Pedido", "format_mask": "int", "alignment": "right"},
                "valor": {"label": "Valor", "format_mask": "float", "alignment": "right"},
            },
        }
    )
    assert result["groups"]["header"][0]["name"] == "empresa"
    assert result["groups"]["groups"]["header"][0]["name"] == "pedido"


def test_group_with_detail():
    result = convert_layout(
        {
            "titulo": {"label": "Título", "format_mask": "str", "alignment": "left"},
            "grupo": {
                "campo1": {"label": "Campo 1", "format_mask": "str", "alignment": "left"},
                "detalhes": {
                    "sub1": {"label": "Sub 1", "format_mask": "str", "alignment": "left"},
                    "sub2": {"label": "Sub 2", "format_mask": "int", "alignment": "right"},
                },
            },
        }
    )
    groups = result["groups"]["groups"]
    assert groups["header"][0]["name"] == "campo1"
    assert groups["detail"][0]["name"] == "sub1"


def test_convert_data_template_format_passthrough():
    data = [{"fields": {"nome": "João"}, "groups": []}]
    assert convert_data(data, {}) == {"groups": data}


def test_convert_data_with_group_and_detail():
    data = [{"titulo": "A", "grupo": [{"campo": "x", "detalhes": [{"sub": 1}, {"sub": 2}]}]}]
    layout = {
        "titulo": {"label": "Título", "format_mask": "str", "alignment": "left"},
        "grupo": {
            "campo": {"label": "Campo", "format_mask": "str", "alignment": "left"},
            "detalhes": {"sub": {"label": "Sub", "format_mask": "int", "alignment": "right"}},
        },
    }
    result = convert_data(data, layout)
    subgroup = result["groups"][0]["groups"][0]
    assert subgroup["fields"] == {"campo": "x"}
    assert subgroup["detail"] == [{"sub": 1}, {"sub": 2}]


def test_infer_layout_types():
    result = infer_layout([{"nome": "João", "idade": 30, "preco": 9.9, "ativo": True, "itens": [1]}])
    by_name = {f["name"]: f for f in result["groups"]["header"]}
    assert set(by_name) == {"nome", "idade", "preco", "ativo"}
    assert by_name["idade"]["format_mask"] == "int"
    assert by_name["preco"]["format_mask"] == "float"
    assert by_name["ativo"]["format_mask"] == "str"


def test_is_template_format():
    assert is_template_format([]) is False
    assert is_template_format([{"fields": {}}]) is True
    assert is_template_format([{"nome": 1}]) is False
