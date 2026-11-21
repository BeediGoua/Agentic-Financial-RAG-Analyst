import pytest

from app.evaluation.evidence import evidence_matches_chunk, normalize_evidence_text


def test_normalization_preserves_numbers_and_units():
    assert normalize_evidence_text("  1\u00a0000   FCFA\n2024 ") == "1 000 FCFA 2024"


def test_strict_document_page_and_quote_matching():
    evidence = {
        "document_sha256": "a" * 64,
        "page_start": 4,
        "page_end": 5,
        "quote": "Résultat net 101 FCFA",
    }
    assert evidence_matches_chunk(evidence, {
        "document_sha256": "A" * 64,
        "page_start": 5,
        "page_end": 5,
        "text": "Tableau: Résultat net 101 FCFA",
    })
    assert not evidence_matches_chunk(evidence, {
        "document_sha256": "b" * 64,
        "page_start": 5,
        "page_end": 5,
        "text": "Résultat net 101 FCFA",
    })
    assert not evidence_matches_chunk(evidence, {
        "document_sha256": "a" * 64,
        "page_start": 7,
        "page_end": 7,
        "text": "Résultat net 101 FCFA",
    })


def test_different_number_unit_and_table_column_are_rejected():
    evidence = {
        "document_sha256": "a" * 64,
        "page_start": 4,
        "page_end": 4,
        "quote": "Résultat net 101 FCFA",
    }
    assert not evidence_matches_chunk(evidence, {
        "document_sha256": "a" * 64,
        "page_start": 4,
        "page_end": 4,
        "text": "Résultat net 102 FCFA",
    })
    assert not evidence_matches_chunk(evidence, {
        "document_sha256": "a" * 64,
        "page_start": 4,
        "page_end": 4,
        "text": "Résultat net 101 USD",
    })
