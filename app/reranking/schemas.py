from pydantic import BaseModel


class RerankedResult(BaseModel):
    rank: int
    original_rank: int | None = None

    retrieval_score: float | None = None
    reranking_score: float
    final_score: float

    retrieval_method: str
    reranking_model: str

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


class RerankingRun(BaseModel):
    query: str
    retrieval_run_path: str
    reranking_model: str
    top_k: int
    results: list[RerankedResult]