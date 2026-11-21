from pydantic import BaseModel, model_validator

from app.core.document_hash import sha256_file


class TextChunk(BaseModel):
    chunk_id: str
    chunking_strategy: str

    source_pdf: str
    document_sha256: str | None = None
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

    @model_validator(mode="after")
    def attach_verified_document_hash(self):
        if self.document_sha256:
            return self
        try:
            self.document_sha256 = sha256_file(self.source_pdf)
        except (FileNotFoundError, OSError):
            return self
        return self


class ChunkingResult(BaseModel):
    status: str
    strategy: str
    output_path: str | None = None
    chunks_count: int = 0
    error: str | None = None