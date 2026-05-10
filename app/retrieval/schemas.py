from pydantic import BaseModel


class RetrievalResult(BaseModel):
    rank: int
    score: float
    retrieval_method: str

    chunk_id: str
    chunking_strategy: str
    embedding_model: str | None = None

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

    text: str


class RetrievalRun(BaseModel):
    query: str
    method: str
    strategy: str | None = None
    model: str | None = None
    top_k: int
    results: list[RetrievalResult]