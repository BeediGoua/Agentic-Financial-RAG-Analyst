from pydantic import BaseModel


class VectorMetadata(BaseModel):
    vector_id: int
    chunk_id: str
    chunking_strategy: str
    embedding_model: str

    source_pdf: str
    source_url: str | None = None
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
    language: str | None = None

    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    parent_id: str | None = None
    content_type: str | None = None

    char_count: int | None = None
    word_count: int | None = None

    text: str


class IndexingResult(BaseModel):
    status: str
    strategy: str
    model: str
    input_path: str
    index_path: str | None = None
    metadata_path: str | None = None
    vectors_count: int = 0
    vector_dimension: int | None = None
    error: str | None = None