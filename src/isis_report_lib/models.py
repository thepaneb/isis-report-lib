"""Data models of the library."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetaInfo(BaseModel):
    """Report metadata."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    sub_title: str | None = None
    company: str | None = None
    mode: str = "exact"
    page: dict[str, Any] | None = None
    locale: str | None = None
    currency: str | None = None
    accent_color: str | None = None
    logo: str | None = None
    watermark: Any = None
    printed_at: Any = None
    summary_side: Any = None
    source_note: Any = None
    empty_text: Any = None
    limits: Any = None


class ReportPayload(BaseModel):
    """Report payload: metadata + optional hierarchical layout + data."""

    model_config = ConfigDict(extra="forbid")

    meta: MetaInfo | None = None
    layout: dict[str, Any] | None = None
    data: list[Any] = Field(default_factory=list)
    sections: list[dict[str, Any]] | None = None
