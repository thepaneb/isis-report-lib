"""Data models of the library."""

from typing import Any

from pydantic import BaseModel, Field


class MetaInfo(BaseModel):
    """Report metadata."""

    title: str
    sub_title: str | None = None
    company: str | None = None
    mode: str = "exact"


class ReportPayload(BaseModel):
    """Report payload: metadata + optional hierarchical layout + data."""

    meta: MetaInfo
    layout: dict[str, Any] | None = None
    data: list[Any] = Field(default_factory=list)
