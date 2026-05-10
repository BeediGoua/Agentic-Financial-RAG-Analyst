from pydantic import BaseModel


class TextChunk(BaseModel):
    chunk_id: str
    chunking_strategy: str

    source_pdf: str
    source_url: str | None = None
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
    language: str | None = None

    page_start: int
    page_end: int
    section: str | None = None
    parent_id: str | None = None

    content_type: str = "text"
    text: str
    char_count: int
    word_count: int


class ChunkingResult(BaseModel):
    status: str
    strategy: str
    output_path: str | None = None
    chunks_count: int = 0
    error: str | None = None