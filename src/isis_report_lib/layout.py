"""Conversão de layout hierárquico e de dados para o formato dos templates.

O layout de entrada é o formato "cru" do POC::

    {
        "empresa": {"label": "Empresa", "format_mask": "str", "alignment": "left"},
        "pedidos": {
            "pedido": {"label": "Código", "format_mask": "int", "alignment": "right"},
            "cargas": {
                "qtde": {"label": "Quantidade", "format_mask": "int", "alignment": "right"},
            },
        },
    }

Chaves cujo valor é um dict **sem** ``label`` são tratadas como grupos aninhados.
"""

from typing import Any


def format_field(name: str, field_def: dict[str, Any]) -> dict[str, Any]:
    """Normaliza a definição de um campo com defaults (label=str, left)."""
    return {
        "name": name,
        "label": field_def.get("label", name),
        "format_mask": field_def.get("format_mask", "str"),
        "alignment": field_def.get("alignment", "left"),
    }


def convert_layout(layout_raw: dict[str, Any]) -> dict[str, Any]:
    """Converte o layout hierárquico para o formato pronto p/ renderização."""
    header: list[dict[str, Any]] = []
    groups: dict[str, Any] | None = None

    for key, value in layout_raw.items():
        if isinstance(value, dict) and "label" in value:
            header.append(format_field(key, value))
        elif isinstance(value, dict):
            field_header: list[dict[str, Any]] = []
            detail: list[dict[str, Any]] = []
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict) and "label" in sub_value:
                    field_header.append(format_field(sub_key, sub_value))
                elif isinstance(sub_value, dict):
                    for inner_key, inner_value in sub_value.items():
                        if isinstance(inner_value, dict) and "label" in inner_value:
                            detail.append(format_field(inner_key, inner_value))
            if groups is None:
                groups = {}
            groups["header"] = field_header
            if detail:
                groups["detail"] = detail

    result: dict[str, Any] = {"groups": {"header": header}}
    if groups:
        result["groups"]["groups"] = groups
    return result


def is_template_format(data: list[Any]) -> bool:
    """True se os dados já estão no formato do template (itens com ``fields``)."""
    return bool(data and isinstance(data[0], dict) and "fields" in data[0])


def convert_data(data_raw: list[dict[str, Any]], layout_raw: dict[str, Any]) -> dict[str, Any]:
    """Converte dados crus + layout cru para ``{"groups": [...]}`` do template."""
    if is_template_format(data_raw):
        return {"groups": data_raw}

    group_keys: dict[str, Any] = {}
    for k, v in layout_raw.items():
        if isinstance(v, dict) and "label" not in v:
            group_keys[k] = v

    items: list[dict[str, Any]] = []
    for record in data_raw:
        fields: dict[str, Any] = {}
        groups: list[dict[str, Any]] = []

        for key, value in record.items():
            if key in group_keys:
                sub_layout = group_keys[key]
                detail_key = next(
                    (sk for sk, sv in sub_layout.items() if isinstance(sv, dict) and "label" not in sv),
                    None,
                )
                for sub_item in value:
                    sub_fields = {sk: sub_item[sk] for sk in sub_layout if sk != detail_key and sk in sub_item}
                    detail = sub_item.get(detail_key, []) if detail_key else []
                    group_entry: dict[str, Any] = {"fields": sub_fields}
                    if detail:
                        group_entry["detail"] = detail
                    groups.append(group_entry)
            else:
                fields[key] = value

        item: dict[str, Any] = {"fields": fields}
        if groups:
            item["groups"] = groups
        items.append(item)

    return {"groups": items}


def infer_layout(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Infere um layout simples (só header) a partir da primeira linha de dados."""
    if not data:
        return {"groups": {"header": []}}

    sample = data[0] if isinstance(data[0], dict) else {}
    header: list[dict[str, Any]] = []
    for key, value in sample.items():
        if isinstance(value, list):
            continue
        dtype = "str"
        alignment = "left"
        if isinstance(value, bool):
            dtype = "str"
        elif isinstance(value, int):
            dtype = "int"
            alignment = "right"
        elif isinstance(value, float):
            dtype = "float"
            alignment = "right"
        header.append({"name": key, "label": key.replace("_", " ").title(), "format_mask": dtype, "alignment": alignment})

    return {"groups": {"header": header}}
