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
    assert format_value(0.091, "percent") == "9,10 %"


def test_percent_invalid():
    assert format_value("abc", "percent") == "abc"


def test_currency():
    assert format_value(1234.5, "currency") == "R$ 1.234,50"


def test_currency_invalid():
    assert format_value("abc", "currency") == "abc"


def test_bool():
    assert format_value(True, "bool") == "Yes"
    assert format_value(0, "bool") == "No"
    assert format_value("false", "bool") == "No"
    assert format_value("YES", "bool") == "Yes"


def test_unknown_mask():
    assert format_value("hello", "unknown") == "hello"
