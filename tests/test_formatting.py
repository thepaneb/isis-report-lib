"""Value formatting tests."""

import pytest

from isis_report_lib.formatting import format_value


def test_none():
    assert format_value(None, "str") == ""


def test_int_valid():
    assert format_value(1234, "int") == "1.234"


def test_int_invalid():
    assert format_value("abc", "int") == "abc"


def test_float_valid():
    assert format_value(1234.5, "float") == "1.234,50"


def test_float_invalid():
    assert format_value("abc", "float") == "abc"


def test_date():
    assert format_value("2024-01-01", "date") == "2024-01-01"


def test_percent():
    assert format_value(0.091, "percent") == "9,10%"


def test_percent_invalid():
    assert format_value("abc", "percent") == "abc"


def test_currency():
    assert format_value(1234.5, "currency") == "R$\u00a01.234,50"


def test_currency_invalid():
    assert format_value("abc", "currency") == "abc"


def test_currency_en_us():
    assert format_value(1234.5, "currency", locale="en-US") == "$1,234.50"


def test_currency_override():
    assert format_value(1234.5, "currency", locale="pt-BR", currency="EUR") == "€\u00a01.234,50"


def test_float_en_us():
    assert format_value(1234.5, "float", locale="en-US") == "1,234.50"


def test_int_en_us():
    assert format_value(1234, "int", locale="en-US") == "1,234"


def test_percent_en_us():
    assert format_value(0.091, "percent", locale="en-US") == "9.10%"


def test_locale_hyphen_and_underscore_equivalent():
    assert format_value(1234.5, "float", locale="pt_BR") == format_value(1234.5, "float", locale="pt-BR")


def test_unknown_locale_raises():
    import pytest

    with pytest.raises(ValueError, match="Unknown locale"):
        format_value(1, "int", locale="xx-YY")


def test_default_currency_unknown_locale_raises():
    import pytest

    from isis_report_lib.formatting import default_currency

    with pytest.raises(ValueError, match="Unknown locale"):
        default_currency("xx_YY")


def test_match_rule_operators():
    from isis_report_lib.formatting import match_rule

    assert match_rule(5, {"gt": 3}) is True
    assert match_rule("a", {"in": ["a", "b"]}) is True
    assert match_rule(None, {"is_null": True}) is True
    assert match_rule(1, {"not_null": True, "gt": 0}) is True
    with pytest.raises(ValueError, match="no known operator"):
        match_rule(1, {"color": "red"})


def test_cell_style_first_match_wins():
    from isis_report_lib.formatting import cell_style, cell_style_dict

    field = {"cell_rules": [{"lt": 0, "color": "#C00000", "bold": True}, {"lt": 100, "italic": True}]}
    assert cell_style_dict(-5, field) == {"color": "#C00000", "bold": True}
    assert cell_style(-5, field) == "color:#C00000;font-weight:bold"
    assert cell_style_dict(50, field) == {"italic": True}
    assert cell_style(50, field) == "font-style:italic"
    assert cell_style(500, field) == ""
    assert cell_style(1, {}) == ""
    assert cell_style_dict(1, {"cell_rules": [{"background": "#EEE"}]}) == {"background": "#EEE"}
    assert cell_style(1, {"cell_rules": [{"background": "#EEE"}]}) == "background:#EEE"
    with pytest.raises(ValueError, match="Invalid cell rule keys"):
        cell_style_dict(1, {"cell_rules": [{"lt": 1, "blink": True}]})
    with pytest.raises(ValueError, match="must be an object"):
        cell_style_dict(1, {"cell_rules": ["nope"]})


def test_date_object_localized():
    import datetime

    assert format_value(datetime.date(2024, 12, 1), "date") == "1 de dez. de 2024"
    assert format_value(datetime.date(2024, 12, 1), "date", locale="en-US") == "Dec 1, 2024"


def test_date_string_passes_through():
    assert format_value("01/12/2024", "date", locale="en-US") == "01/12/2024"


def test_bool():
    assert format_value(True, "bool") == "Yes"
    assert format_value(0, "bool") == "No"
    assert format_value("false", "bool") == "No"
    assert format_value("YES", "bool") == "Yes"


def test_unknown_mask():
    assert format_value("hello", "unknown") == "hello"
