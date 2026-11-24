"""Log encoding tests (ASVS 7.3.1)."""

import io
import logging

from isis_report_lib.logging_utils import LogEncodingFilter, get_logger, log_value


def test_log_value_escapes_line_breaks_and_tabs():
    assert log_value("a\nb\rc\td") == "a\\nb\\rc\\td"


def test_log_value_escapes_ansi_and_control_characters():
    assert log_value("\x1b[31mred\x00") == "\\x1b[31mred\\x00"


def test_log_value_escapes_unicode_line_separators():
    assert log_value("a\u2028b\u2029c") == "a\\u2028b\\u2029c"


def test_log_value_keeps_backslashes():
    # Backslashes are not the injection vector; escaping them would double
    # every already-escaped field on its way through the logger filter.
    assert log_value(r"C:\tmp\x") == r"C:\tmp\x"


def test_log_value_truncates():
    encoded = log_value("x" * 300, max_length=10)
    assert len(encoded) == 10
    assert encoded.endswith("...")


def test_filter_encodes_the_formatted_message():
    record = logging.LogRecord("isis_report_lib", logging.INFO, __file__, 1, "host=%s", ("evil\nINJECTED",), None)
    assert LogEncodingFilter().filter(record) is True
    assert record.getMessage() == "host=evil\\nINJECTED"


def test_filter_encodes_ansi_and_unicode_separators():
    record = logging.LogRecord("isis_report_lib", logging.INFO, __file__, 1, "%s", ("\x1b[2Ja\u2028b",), None)
    LogEncodingFilter().filter(record)
    assert record.getMessage() == "\\x1b[2Ja\\u2028b"


def test_filter_tolerates_malformed_format_args():
    record = logging.LogRecord("isis_report_lib", logging.INFO, __file__, 1, "bad %s %s", ("only-one",), None)
    assert LogEncodingFilter().filter(record) is True


def test_get_logger_installs_the_filter_once():
    logger = get_logger()
    before = sum(isinstance(f, LogEncodingFilter) for f in logger.filters)
    get_logger()
    after = sum(isinstance(f, LogEncodingFilter) for f in logger.filters)
    assert before == 1
    assert after == before


def test_logger_emits_one_line_for_injected_values():
    logger = get_logger()
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    old_level, old_propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        logger.info("host=%s", log_value("evil\nINJECTED"))
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        logger.propagate = old_propagate

    output = stream.getvalue()
    assert len(output.splitlines()) == 1
    assert "host=evil\\nINJECTED" in output
