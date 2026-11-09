"""Modelos de dados da lib (extraídos do POC isis_report)."""

from typing import Any

from pydantic import BaseModel, Field


class MetaInfo(BaseModel):
    """Metadados do relatório."""

    title: str
    sub_title: str | None = None
    company: str | None = None
    mode: str = "exact"


class ReportPayload(BaseModel):
    """Payload de relatório: metadados + layout hierárquico opcional + dados."""

    meta: MetaInfo
    layout: dict[str, Any] | None = None
    data: list[Any] = Field(default_factory=list)
