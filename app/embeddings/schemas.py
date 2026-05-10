from pydantic import BaseModel


class EmbeddingRecord(BaseModel):
    chunk_id: str
    chunking_strategy: str
    embedding_model: str
    vector_dimension: int
    embedding: list[float]

    source_pdf: str
    source_url: str | None = None
    company: str | None = None
    year: str | None = None
    document_type: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    content_type: str | None = None
    text: str