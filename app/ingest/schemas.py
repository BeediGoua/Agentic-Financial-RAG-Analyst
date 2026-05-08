from pydantic import BaseModel


class ReportDocument(BaseModel):
    source: str
    title: str
    page_url: str
    pdf_url: str
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
