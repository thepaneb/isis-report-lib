"""isis_report_lib — gere PDFs tabulares a partir de dict ou texto `.toon`."""

from isis_report_lib.api import (
    agenerate_pdf,
    agenerate_pdf_from_toon,
    arender_html,
    generate_pdf,
    generate_pdf_from_toon,
    render_html,
    render_html_from_toon,
)
from isis_report_lib.formatting import format_value
from isis_report_lib.layout import convert_data, convert_layout, infer_layout, is_template_format
from isis_report_lib.models import MetaInfo, ReportPayload
from isis_report_lib.service import BaseReportService, TabularReportService
from isis_report_lib.toon import ToonParser, parse_toon

__version__ = "0.1.0"

__all__ = [
    "MetaInfo",
    "ReportPayload",
    "ToonParser",
    "parse_toon",
    "format_value",
    "convert_layout",
    "convert_data",
    "infer_layout",
    "is_template_format",
    "BaseReportService",
    "TabularReportService",
    "agenerate_pdf",
    "generate_pdf",
    "agenerate_pdf_from_toon",
    "generate_pdf_from_toon",
    "arender_html",
    "render_html",
    "render_html_from_toon",
    "__version__",
]
