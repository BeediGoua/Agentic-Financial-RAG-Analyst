import pytest

from app.evaluation.compare import paired_bootstrap
from app.evaluation.corpus import build_corpus_manifest


def test_snapshot_identity_changes_with_corpus(tmp_path):
    first_document = tmp_path / "first.pdf"
    second_document = tmp_path / "second.pdf"
    first_document.write_bytes(b"synthetic document A")
    second_document.write_bytes(b"synthetic document B")
    first = build_corpus_manifest(documents=[first_document], strategies=["recursive_fixed"])
    second = build_corpus_manifest(documents=[second_document], strategies=["recursive_fixed"])
    assert first["snapshot_id"] != second["snapshot_id"]
    assert first["documents_count"] == 1
    assert len(first["document_hashes"][0]) == 64


def test_paired_bootstrap_is_seeded_and_reports_interval():
    first = paired_bootstrap([0.1, 0.2, 0.3], [0.2, 0.3, 0.4], repetitions=200, seed=42)
    second = paired_bootstrap([0.1, 0.2, 0.3], [0.2, 0.3, 0.4], repetitions=200, seed=42)
    assert first == second
    assert first["ci95_low"] is not None
    assert first["ci95_high"] is not None
