"""Pipeline de geração de relatório: Obter -> Tratar -> HTML -> PDF.

Equivalente ao ``BaseReportService`` + ``SharedReportService`` do POC,
sem dependência do Robyn.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, final

logger = logging.getLogger("isis_report_lib")


class BaseReportService(ABC):
    """Define o ciclo de vida de geração; ``execute`` garante a ordem."""

    @final
    async def execute(self, payload: dict[str, Any]) -> bytes:
        service_name = self.__class__.__name__
        try:
            logger.info("Iniciando processamento do relatório: %s", service_name)
            raw_data = await self._obter_dados(payload)
            processed_data = await self._tratar_dados(raw_data, payload)
            html_content = await self._gerar_html(processed_data, payload)
            pdf_bytes = await self._gerar_pdf(html_content)
            logger.info("Relatório %s gerado com sucesso.", service_name)
            return pdf_bytes
        except Exception:
            logger.exception("Falha no pipeline do serviço %s", service_name)
            raise

    @abstractmethod
    async def _obter_dados(self, payload: dict[str, Any]) -> Any:
        """Recupera dados brutos do payload."""

    @abstractmethod
    async def _tratar_dados(self, data: Any, payload: dict[str, Any]) -> Any:
        """Aplica layout/conversão de dados."""

    @abstractmethod
    async def _gerar_html(self, data: Any, payload: dict[str, Any]) -> str:
        """Renderiza o template Jinja2."""

    @abstractmethod
    async def _gerar_pdf(self, html: str) -> bytes:
        """Converte HTML em PDF."""


class TabularReportService(BaseReportService):
    """Implementação tabular padrão (equivale ao SharedReportService do POC)."""

    def __init__(self, pdf_options: dict[str, Any] | None = None) -> None:
        from isis_report_lib import pdf as _pdf

        self._pdf_options = pdf_options or {}
        self._pdf_module = _pdf

    async def _obter_dados(self, payload: dict[str, Any]) -> Any:
        return payload.get("data", [])

    async def _tratar_dados(self, data: Any, payload: dict[str, Any]) -> dict[str, Any]:
        from isis_report_lib.layout import convert_data, convert_layout, infer_layout, is_template_format

        meta = payload.get("meta", {})
        layout_raw = payload.get("layout")

        if layout_raw:
            layout = convert_layout(layout_raw)
            ds_items = convert_data(data, layout_raw)
        else:
            layout = infer_layout(data)
            # O template itera `data.fields`: embrulha registros crus.
            if is_template_format(data):
                ds_items = {"groups": data}
            else:
                ds_items = {"groups": [{"fields": r} if isinstance(r, dict) else {"fields": {"value": r}} for r in data]}

        void = is_template_format  # mantém referência p/ paridade com o POC
        _ = void
        return {"ds_items": ds_items, "layout": layout, "meta": meta}

    async def _gerar_html(self, data: dict[str, Any], payload: dict[str, Any]) -> str:
        from isis_report_lib.rendering import arender_report_html

        return await arender_report_html(
            ds_items=data["ds_items"],
            layout=data["layout"],
            meta=data["meta"],
        )

    async def _gerar_pdf(self, html: str) -> bytes:
        return await self._pdf_module.get_pdf_from_html(html, **self._pdf_options)
