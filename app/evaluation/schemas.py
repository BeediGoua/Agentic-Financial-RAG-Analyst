from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class Evidence(BaseModel):
    evidence_id: str
    document_sha256: str
    page_start: int
    page_end: int
    quote: str
    grade: int = Field(ge=0, le=3)

    @field_validator("document_sha256")
    @classmethod
    def validate_sha(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
            raise ValueError("document_sha256 must be a lowercase or uppercase hexadecimal SHA-256")
        return value.lower()

    @field_validator("page_start", "page_end")
    @classmethod
    def validate_page(cls, value: int) -> int:
        if value < 1:
            raise ValueError("pages must be positive")
        return value


class EvidenceAlternative(BaseModel):
    evidence_id: str
    document_sha256: str
    page_start: int
    page_end: int
    quote: str
    grade: int = Field(ge=0, le=3)

    @field_validator("document_sha256")
    @classmethod
    def validate_sha(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
            raise ValueError("document_sha256 must be a 64-character hexadecimal SHA-256")
        return value.lower()

    @field_validator("page_start", "page_end")
    @classmethod
    def validate_page(cls, value: int) -> int:
        if value < 1:
            raise ValueError("pages must be positive")
        return value


class EvidenceGroup(BaseModel):
    group_id: str
    alternatives: list[EvidenceAlternative]


class GoldQuestion(BaseModel):
    question_id: str
    question: str
    language: str = "fr"
    task_type: str
    company_tickers: list[str] = Field(default_factory=list)
    years: list[str] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    answerability: Literal["answerable", "unanswerable"]
    split: Literal["dev", "test"]
    annotation_status: Literal["draft", "candidate", "verified"]
    evidence_groups: list[EvidenceGroup] = Field(default_factory=list)
    annotation_date: str | None = None
    annotation_version: str | None = None
    exclusion_reason: str | None = None

    @model_validator(mode="after")
    def validate_answerability(self):
        if self.answerability == "answerable" and not self.evidence_groups:
            raise ValueError("Answerable question must contain evidence; no evidence groups")
        if self.answerability == "unanswerable":
            if self.evidence_groups:
                raise ValueError("Unanswerable question cannot contain evidence")
            if not self.exclusion_reason:
                raise ValueError("Unanswerable question requires exclusion_reason")
        return self


class RetrievalResultRecord(BaseModel):
    question_id: str
    configuration_id: str
    status: Literal[
        "success",
        "empty",
        "missing_corpus",
        "invalid_index",
        "model_unavailable",
        "error",
    ]
    query: str
    top_k: int
    retrieved_ids: list[str] = Field(default_factory=list)
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    latency_ms: float | None = None
    error: str | None = None
    ranked_results: list[dict] = Field(default_factory=list)
