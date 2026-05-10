from pydantic import BaseModel


class CleanedPage(BaseModel):
    source_pdf: str
    source_url: str | None = None
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
    language: str | None = None

    page_number: int
    text: str
    cleaned_text: str
    char_count: int
    word_count: int

    extraction_method: str | None = None
    ocr_used: bool = False
    quality_status: str | None = None

    content_type: str = "text"


class CleanedTable(BaseModel):
    source_pdf: str
    source_url: str | None = None
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
    language: str | None = None

    page_number: int
    table_index: int
    rows: list[list[str | None]]
    cleaned_rows: list[list[str | None]]
    row_count: int
    column_count: int

    content_type: str = "table"


class ProcessingResult(BaseModel):
    status: str
    input_path: str
    output_path: str | None = None
    records_count: int = 0
    error: str | None = None