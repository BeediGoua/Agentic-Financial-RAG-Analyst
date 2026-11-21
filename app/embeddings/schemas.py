from pydantic import BaseModel, model_validator

from app.core.document_hash import sha256_file


class EmbeddingRecord(BaseModel):
    chunk_id: str
    chunking_strategy: str
    embedding_model: str
    vector_dimension: int
    embedding: list[float]

    source_pdf: str
    document_sha256: str | None = None
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

    @model_validator(mode="after")
    def attach_verified_document_hash(self):
        if self.document_sha256:
            return self
        try:
            self.document_sha256 = sha256_file(self.source_pdf)
        except (FileNotFoundError, OSError):
            return self
        return self