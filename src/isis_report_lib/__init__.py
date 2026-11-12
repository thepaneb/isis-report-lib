"""isis_report_lib — generate tabular PDFs from dicts or `.toon` text."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from isis_report_lib.api import (
    agenerate_csv,
    agenerate_csv_from_toon,
    agenerate_pdf,
    agenerate_pdf_from_toon,
    agenerate_xlsx,
    agenerate_xlsx_from_toon,
    arender_html,
    generate_csv,
    generate_csv_from_toon,
    generate_pdf,
    generate_pdf_from_toon,
    generate_xlsx,
    generate_xlsx_from_toon,
    render_html,
    render_html_from_toon,
)
from isis_report_lib.export import collect_tables
from isis_report_lib.formatting import format_value, formatter_for
from isis_report_lib.inputs import from_csv, from_dataframe, from_json, payload_schema
from isis_report_lib.layout import (
    build_report,
    convert_data,
    convert_layout,
    infer_layout,
    is_template_format,
    template_header_layout,
)
from isis_report_lib.models import MetaInfo, ReportPayload
from isis_report_lib.service import BaseReportService, TabularReportService
from isis_report_lib.toon import ToonParser, parse_toon

try:
    __version__ = _pkg_version("isis-report-lib")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "MetaInfo",
    "ReportPayload",
    "ToonParser",
    "parse_toon",
    "format_value",
    "formatter_for",
    "from_csv",
    "from_dataframe",
    "from_json",
    "payload_schema",
    "convert_layout",
    "convert_data",
    "build_report",
    "infer_layout",
    "is_template_format",
    "template_header_layout",
    "BaseReportService",
    "TabularReportService",
    "agenerate_pdf",
    "generate_pdf",
    "agenerate_pdf_from_toon",
    "generate_pdf_from_toon",
    "agenerate_xlsx",
    "generate_xlsx",
    "agenerate_xlsx_from_toon",
    "generate_xlsx_from_toon",
    "agenerate_csv",
    "generate_csv",
    "agenerate_csv_from_toon",
    "generate_csv_from_toon",
    "collect_tables",
    "arender_html",
    "render_html",
    "render_html_from_toon",
    "__version__",
]
