"""Value formatting tests."""

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
