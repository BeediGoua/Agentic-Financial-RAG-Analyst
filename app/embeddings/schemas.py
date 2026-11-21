import hashlib
from pathlib import Path

from pydantic import BaseModel, model_validator


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
        path = Path(self.source_pdf)
        if path.is_file():
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            self.document_sha256 = digest.hexdigest()
        return self