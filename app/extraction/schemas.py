from pydantic import BaseModel


class ExtractedPage(BaseModel):
    source_pdf: str
    source_url: str | None = None
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
    language: str | None = None

    page_number: int
    text: str
    char_count: int
    word_count: int

    extraction_method: str = "pymupdf"
    ocr_used: bool = False
    quality_status: str = "unknown"


class ExtractedTable(BaseModel):
    source_pdf: str
    source_url: str | None = None
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
    language: str | None = None

    page_number: int
    table_index: int
    rows: list[list[str | None]]
    row_count: int
    column_count: int


class ExtractionResult(BaseModel):
    status: str
    source_pdf: str
    pages_output: str | None = None
    tables_output: str | None = None
    pages_count: int = 0
    tables_count: int = 0
    empty_pages: int = 0
    ocr_pages: int = 0
    low_quality_pages: int = 0
    error: str | None = None