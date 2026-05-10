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
    source_url: str | None = None
    language: str | None = None


class IngestionResult(BaseModel):
    """Result of one ingestion run (compatible avec enterprise tracing)."""
    
    status: str  # 'success', 'duplicate', 'invalid_pdf', 'error', 'skipped'
    pdf_url: str | None = None 
    local_path: str | None = None 
    manifest_path: str | None = None
    checksum_sha256: str | None = None  # SHA256 du fichier
    file_size_bytes: int | None = None
    error: str | None = None
    reason: str | None = None  # Raison détaillée du statut
    downloaded_at: str | None = None  # ISO format UTC
    validation_checks: dict | None = None  # {"pdf_header": ok, "min_size": ok, ...}
    