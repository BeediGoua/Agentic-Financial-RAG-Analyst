from pydantic import BaseModel


class Citation(BaseModel):
    company: str | None = None
    year: str | None = None
    document_type: str | None = None

    source_pdf: str
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None


class GeneratedAnswer(BaseModel):
    query: str

    answer: str
    status: str

    confidence: float

    provider: str
    model: str

    retrieval_method: str | None = None
    reranking_model: str | None = None

    citations: list[Citation]
    used_chunks: int
