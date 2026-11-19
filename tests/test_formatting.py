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


def test_field_text_missing_and_substitutions():
    from isis_report_lib.formatting import field_text, format_value

    assert field_text(None, None) is None
    assert field_text(1, None) is None
    assert field_text(None, {}) is None
    assert field_text(None, {"missing_text": "n/a"}) == "n/a"
    assert field_text(None, {"missing_text": None}) == ""
    assert field_text(None, {"substitutions": {None: "void"}, "missing_text": "n/a"}) == "void"
    assert field_text("A", {"substitutions": {"A": "Active"}}) == "Active"
    assert field_text(1, {"substitutions": {"1": "one"}}) == "one"  # str() fallback
    assert field_text("B", {"substitutions": {"A": "Active"}}) is None
    assert field_text("A", {"substitutions": {"A": "Active"}, "missing_text": "n/a"}) == "Active"
    assert format_value(None, "int", field={"missing_text": "-"}) == "-"
    assert format_value("A", "str", field={"substitutions": {"A": "Active"}}) == "Active"
    assert format_value(5, "int", field={"substitutions": {"9": "nine"}}) == "5"
    assert format_value(5, "int") == "5"
    import pytest

    with pytest.raises(ValueError, match="Invalid substitutions"):
        field_text("A", {"substitutions": ["A"]})
    with pytest.raises(ValueError, match="Invalid substitutions"):
        format_value("A", "str", field={"substitutions": "A"})


def test_match_rule_compound_and():
    from isis_report_lib.formatting import match_rule

    assert match_rule(15, {"gte": 10, "lt": 20}) is True
    assert match_rule(25, {"gte": 10, "lt": 20}) is False
    assert match_rule(5, {"gte": 10, "lt": 20}) is False
    assert match_rule(1, {"not_null": True, "gt": 0}) is True
    assert match_rule(None, {"not_null": True, "gt": 0}) is False


def test_match_rule_between():
    from isis_report_lib.formatting import match_rule

    assert match_rule(10, {"between": [10, 20]}) is True  # inclusive
    assert match_rule(20, {"between": [10, 20]}) is True
    assert match_rule(21, {"between": [10, 20]}) is False
    assert match_rule("m", {"between": ["a", "z"]}) is True
    assert match_rule(None, {"between": [1, 2]}) is False
    import pytest

    with pytest.raises(ValueError, match="'between' needs a"):
        match_rule(5, {"between": 10})


def test_match_rule_contains():
    import pytest

    from isis_report_lib.formatting import match_rule

    assert match_rule("cancelled by user", {"contains": "cancel"}) is True
    assert match_rule("paid", {"contains": "cancel"}) is False
    assert match_rule(None, {"contains": "x"}) is False
    assert match_rule(12345, {"contains": "234"}) is True
    with pytest.raises(ValueError, match="'contains' needs a string"):
        match_rule("abc", {"contains": 5})


def test_match_rule_in_type_error_is_no_match():
    from isis_report_lib.formatting import match_rule

    assert match_rule("a", {"in": 5}) is False
    assert match_rule("a", {"not_in": 5}) is False


def test_cell_style_compound_rule():
    from isis_report_lib.formatting import cell_style_dict

    field = {"cell_rules": [{"gte": 1000, "lt": 5000, "color": "#C00000"}, {"bold": True}]}
    assert cell_style_dict(2000, field) == {"color": "#C00000"}
    assert cell_style_dict(9000, field) == {"bold": True}  # catch-all default
