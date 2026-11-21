import json

import pytest

from app.evaluation.qrels import load_questions
from app.evaluation.schemas import GoldQuestion


def write_questions(tmp_path, rows):
    path = tmp_path / "questions.jsonl"
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def valid_row(question_id="Q1"):
    return {
        "question_id": question_id,
        "question": "Quel est le chiffre synthétique?",
        "language": "fr",
        "task_type": "financial_fact",
        "company_tickers": ["ORAC"],
        "years": ["2024"],
        "document_types": ["annual_report"],
        "answerability": "unanswerable",
        "split": "test",
        "annotation_status": "draft",
        "evidence_groups": [],
        "exclusion_reason": "source_absente",
    }


def test_loads_valid_unanswerable_and_rejects_duplicate(tmp_path):
    path = write_questions(tmp_path, [valid_row(), valid_row()])
    with pytest.raises(ValueError, match="Duplicate"):
        load_questions(path)


def test_invalid_json_and_answerable_without_evidence(tmp_path):
    path = tmp_path / "questions.jsonl"
    path.write_text("{bad\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_questions(path)

    row = valid_row()
    row["answerability"] = "answerable"
    row.pop("exclusion_reason")
    path = write_questions(tmp_path, [row])
    with pytest.raises(ValueError, match="no evidence"):
        load_questions(path)


def test_verified_placeholder_is_rejected(tmp_path):
    row = valid_row()
    row["answerability"] = "answerable"
    row.pop("exclusion_reason")
    row["annotation_status"] = "verified"
    row["evidence_groups"] = [{
        "group_id": "G1",
        "alternatives": [{
            "evidence_id": "E1",
            "document_sha256": "SHA256_REEL_DU_DOCUMENT",
            "page_start": 1,
            "page_end": 1,
            "quote": "PASSAGE_VERIFIE_DU_DOCUMENT",
            "grade": 3,
        }],
    }]
    path = write_questions(tmp_path, [row])
    with pytest.raises(ValueError):
        load_questions(path)


def test_unanswerable_with_evidence_is_rejected():
    with pytest.raises(ValueError):
        GoldQuestion.model_validate({
            **valid_row(),
            "answerability": "unanswerable",
            "annotation_status": "verified",
            "exclusion_reason": "source_absente",
            "evidence_groups": [{
                "group_id": "G1",
                "alternatives": [],
            }],
        })
