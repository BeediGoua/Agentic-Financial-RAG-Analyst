from __future__ import annotations

from pydantic import BaseModel, Field


class ReportDocument(BaseModel):
    """Metadata describing one financial report discovered online."""

    source: str = Field(default="BRVM")
    title: str
    page_url: str
    pdf_url: str
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
