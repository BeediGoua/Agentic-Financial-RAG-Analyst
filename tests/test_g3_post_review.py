import json

import pytest

from app.chunking.schemas import TextChunk
from app.core.document_hash import _sha256_cached
from app.embeddings.schemas import EmbeddingRecord
from app.evaluation.corpus import build_document_registry, normalize_document_path, sha256_file
from app.evaluation.metrics import evaluate_ranked_results
from app.vector_db.schemas import VectorMetadata


def make_enriched(chunk_id, evidence_ids, group_ids, sha="a" * 64):
    return {
        "chunk_id": chunk_id,
        "document_sha256": sha,
        "matched_evidence_ids": evidence_ids,
        "matched_group_ids": group_ids,
    }


def test_nonrelevant_rank_one_preserves_original_positions():
    results = [
        make_enriched("X", [], []),
        make_enriched("C2", ["E1"], ["G1"]),
    ]
    groups = {"G1": {"E1"}}
    metrics = evaluate_ranked_results(results, groups, {"E1": 3}, k=2)
    assert metrics["reciprocal_rank"] == pytest.approx(0.5)
    assert metrics["ndcg"] == pytest.approx(0.6309297536)


def test_relevant_rank_one_and_relevant_after_k():
    first = evaluate_ranked_results(
        [make_enriched("C1", ["E1"], ["G1"])],
        {"G1": {"E1"}},
        {"E1": 3},
        k=1,
    )
    after_k = evaluate_ranked_results(
        [make_enriched("C1", [], []), make_enriched("C2", ["E1"], ["G1"])],
        {"G1": {"E1"}},
        {"E1": 3},
        k=1,
    )
    assert first["hit"] == 1.0
    assert first["reciprocal_rank"] == 1.0
    assert after_k["hit"] == 0.0


def test_redundancy_and_multi_group_chunk_are_deduplicated():
    results = [
        make_enriched("C1", ["E1", "E2"], ["G1", "G2"]),
        make_enriched("C2", ["E1"], ["G1"]),
        make_enriched("C3", ["E3"], ["G3"]),
    ]
    groups = {
        "G1": {"E1", "E1B"},
        "G2": {"E2"},
        "G3": {"E3"},
    }
    metrics = evaluate_ranked_results(
        results,
        groups,
        {"E1": 3, "E1B": 2, "E2": 2, "E3": 2},
        k=3,
        relevant_threshold=2,
    )
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["evidence_coverage"] == pytest.approx(1.0)
    assert metrics["all_evidence"] == 1.0


def test_unjudged_chunk_visible_and_counted():
    results = [
        make_enriched("C1", [], []),
        make_enriched("C2", ["E1"], ["G1"]),
    ]
    metrics = evaluate_ranked_results(results, {"G1": {"E1"}}, {"E1": 3}, k=2)
    assert metrics["unjudged_count"] == 1
    assert metrics["judged_fraction"] == 0.5
    assert metrics["provisional"] is True


def test_grade_zero_chunk_is_explicitly_judged():
    results = [
        make_enriched("C0", ["E0"], ["G0"]),
        make_enriched("C1", [], []),
    ]
    metrics = evaluate_ranked_results(
        results,
        {"G0": {"E0"}, "G1": {"E1"}},
        {"E0": 0, "E1": 3},
        k=2,
    )
    assert metrics["grade0_count"] == 1
    assert metrics["judged_count"] == 1
    assert metrics["judged_fraction"] == 0.5
    assert metrics["unjudged_count"] == 1


def test_document_registry_and_schema_hash_propagation(tmp_path):
    pdf = tmp_path / "report.pdf"
    pdf.write_bytes(b"%PDF-synthetic")
    _sha256_cached.cache_clear()
    digest = sha256_file(pdf)
    manifest = tmp_path / "report.pdf.manifest.json"
    manifest.write_text(json.dumps({
        "local_path": str(pdf),
        "checksum_sha256": digest,
        "status": "success",
    }))
    registry = build_document_registry([manifest])
    assert registry["records"][normalize_document_path(pdf)] == digest

    chunk = TextChunk(
        chunk_id="CHUNK-DIFFERENT",
        chunking_strategy="page_aware",
        source_pdf=str(pdf),
        page_start=1,
        page_end=1,
        text="passage",
        char_count=7,
        word_count=1,
    )
    embedding = EmbeddingRecord(
        chunk_id=chunk.chunk_id,
        chunking_strategy="page_aware",
        embedding_model="fake",
        vector_dimension=2,
        embedding=[1.0, 0.0],
        source_pdf=str(pdf),
        text="passage",
    )
    vector = VectorMetadata(
        vector_id=0,
        chunk_id=chunk.chunk_id,
        chunking_strategy="page_aware",
        embedding_model="fake",
        source_pdf=str(pdf),
        text="passage",
    )
    assert chunk.document_sha256 == embedding.document_sha256 == vector.document_sha256 == digest
    cache_info = _sha256_cached.cache_info()
    assert cache_info.misses == 1
    assert cache_info.hits >= 3
