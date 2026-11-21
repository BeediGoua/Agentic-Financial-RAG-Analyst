from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from pydantic import ValidationError

from app.evaluation.schemas import GoldQuestion


PLACEHOLDERS = {"SHA256_REEL_DU_DOCUMENT", "PASSAGE_VERIFIE_DU_DOCUMENT"}


def normalize_unicode(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def load_questions(path: str | Path) -> list[GoldQuestion]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Questions file absent: {source}")
    questions: list[GoldQuestion] = []
    seen: set[str] = set()
    with source.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_number}: {exc}") from exc
            try:
                question = GoldQuestion.model_validate(raw)
            except ValidationError as exc:
                raise ValueError(f"Invalid question at line {line_number}: {exc}") from exc
            if question.question_id in seen:
                raise ValueError(f"Duplicate question_id: {question.question_id}")
            seen.add(question.question_id)
            validate_question(question)
            questions.append(question)
    return questions


def validate_question(question: GoldQuestion) -> None:
    if not question.question_id or not question.question:
        raise ValueError("question_id and question are required")
    if question.answerability == "answerable" and not question.evidence_groups:
        raise ValueError(
            f"Answerable question {question.question_id} has no evidence groups"
        )
    if question.answerability == "unanswerable":
        if question.evidence_groups:
            raise ValueError(
                f"Unanswerable question {question.question_id} has evidence"
            )
        if not question.exclusion_reason:
            raise ValueError(
                f"Unanswerable question {question.question_id} lacks exclusion_reason"
            )
    if question.annotation_status == "verified":
        if question.answerability == "answerable" and not question.evidence_groups:
            raise ValueError("Verified answerable question lacks evidence")
        evidence_ids: set[str] = set()
        for group in question.evidence_groups:
            if not group.group_id:
                raise ValueError("Evidence group_id is required")
            if not group.alternatives:
                raise ValueError(
                    f"Evidence group {group.group_id} has no alternatives"
                )
            for evidence in group.alternatives:
                if evidence.evidence_id in evidence_ids:
                    raise ValueError(f"Duplicate evidence_id: {evidence.evidence_id}")
                evidence_ids.add(evidence.evidence_id)
                if evidence.document_sha256 in PLACEHOLDERS:
                    raise ValueError("Verified annotation contains placeholder SHA-256")
                if evidence.quote in PLACEHOLDERS:
                    raise ValueError("Verified annotation contains placeholder quote")
                if evidence.page_end < evidence.page_start:
                    raise ValueError("Evidence page_end precedes page_start")
