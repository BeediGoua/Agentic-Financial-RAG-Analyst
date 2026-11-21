from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from app.retrieval.dense import DenseRetriever
from app.retrieval.filters import matches_retrieval_filters
from app.core.artifact_cache import sha256_file, write_artifact_manifest


def make_metadata(chunk_id, company, year, vector_id):
    return {
        "vector_id": vector_id,
        "chunk_id": chunk_id,
        "chunking_strategy": "recursive_fixed",
        "embedding_model": "mini_lm_multilingual",
        "source_pdf": f"/tmp/{chunk_id}.pdf",
        "company": company,
        "year": year,
        "text": f"texte {chunk_id}",
        "page_start": 1,
        "page_end": 1,
    }


def test_shared_filter_supports_exact_company_aliases():
    assert matches_retrieval_filters(
        {"company": "ORANGE COTE D'IVOIRE", "year": "2024"},
        companies=["ORANGE CI"],
        years=["2024"],
    )
    assert matches_retrieval_filters(
        {"company": "CIE CI", "year": "2024"},
        companies=["CIEC"],
    )
    assert matches_retrieval_filters(
        {"company": "SONATEL", "year": "2024"},
        companies=["SNTS"],
    )
    assert matches_retrieval_filters(
        {"company": "ORANGE COTE D'IVOIRE", "year": "2024"},
        companies=["ORAC"],
    )
    assert matches_retrieval_filters(
        {"company": "CIE CI", "year": "2024"},
        companies=["CIEC"],
    )
    assert matches_retrieval_filters(
        {"company": "SONATEL SENEGAL", "year": "2024"},
        companies=["SNTS"],
    )


def test_shared_filter_rejects_substring_lookalikes():
    for company in ("ORANGE FINANCE SERVICES", "ORANGE CIEL"):
        assert not matches_retrieval_filters(
            {"company": company, "year": "2024"},
            companies=["ORAC"],
        )
    assert not matches_retrieval_filters(
        {"company": "CIE SERVICES EXTERNES", "year": "2024"},
        companies=["CIEC"],
    )
    for company in ("SONATEL INTERNATIONAL", "SONATEL HOLDING", "ORANGE TELECOM AFRICA"):
        assert not matches_retrieval_filters(
            {"company": company, "year": "2024"},
            companies=["SNTS"] if company.startswith("SONATEL") else ["ORAC"],
        )


def test_dense_rejects_mixed_faiss_generations_with_same_count_and_dimension(tmp_path):
    root = tmp_path / "faiss" / "recursive_fixed" / "mini_lm_multilingual" / "mixed"
    root.mkdir(parents=True)
    index = faiss.IndexFlatIP(384)
    vectors = np.array([
    [1.0] + [0.0] * 383,
    [0.0, 1.0] + [0.0] * 382,
    ], dtype=np.float32)
    index.add(vectors)
    faiss.write_index(index, str(root / "index.faiss"))

    first_generation = [
    make_metadata("generation-a-1", "ORANGE CI", "2025", 0),
    make_metadata("generation-a-2", "CIE CI", "2025", 1),
    ]
    (root / "metadata.jsonl").write_text(
    "".join(json.dumps(row) + "\n" for row in first_generation),
    encoding="utf-8",
    )
    fingerprint = {
    "schema_version": 1,
    "stage": "faiss_index",
    "params": {
        "strategy": "recursive_fixed",
        "model": "mini_lm_multilingual",
        "model_revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
    },
    "model_revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
    }
    manifest_path = write_artifact_manifest(root / "index.faiss", fingerprint)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["metadata_sha256"] = sha256_file(root / "metadata.jsonl")
    manifest["metadata_size"] = (root / "metadata.jsonl").stat().st_size
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    second_generation = [
    make_metadata("generation-b-1", "SONATEL", "2024", 0),
    make_metadata("generation-b-2", "ECOBANK CI", "2024", 1),
    ]
    (root / "metadata.jsonl").write_text(
    "".join(json.dumps(row) + "\n" for row in second_generation),
    encoding="utf-8",
    )

    retriever = DenseRetriever(str(tmp_path / "faiss"))
    retriever.embed_query = lambda query, model_key: np.array(
        [[1.0] + [0.0] * 383],
        dtype=np.float32,
    )
    try:
        retriever.search(
            "résultat",
            "recursive_fixed",
            "mini_lm_multilingual",
            top_k=1,
        )
    except ValueError as exc:
        assert "mismatched FAISS artifact pair" in str(exc)
    else:
        raise AssertionError("A mixed FAISS generation pair must be rejected")


def test_dense_progressively_filters_and_rejects_mismatched_index(tmp_path):
    root = tmp_path / "faiss" / "recursive_fixed" / "mini_lm_multilingual"
    root.mkdir(parents=True)
    vectors = np.array([
        [1.0, 0.0, 0.0, 0.0],
        [0.99, 0.01, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
    ], dtype=np.float32)
    index = faiss.IndexFlatIP(384)
    padded = np.pad(vectors, ((0, 0), (0, 380)))
    index.add(padded)
    (root / "index.faiss").parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(root / "index.faiss"))
    metadata = [
        make_metadata("cie", "CIE CI", "2025", 0),
        make_metadata("orange2025", "ORANGE CI", "2025", 1),
        make_metadata("orange2024", "ORANGE CI", "2024", 2),
        make_metadata("sonatel", "SONATEL", "2025", 3),
    ]
    (root / "metadata.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in metadata),
        encoding="utf-8",
    )
    fingerprint = {
        "schema_version": 1,
        "stage": "faiss_index",
        "params": {
            "strategy": "recursive_fixed",
            "model": "mini_lm_multilingual",
            "model_revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
        },
        "model_revision": "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
    }
    manifest_path = write_artifact_manifest(root / "index.faiss", fingerprint)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["metadata_sha256"] = sha256_file(root / "metadata.jsonl")
    manifest["metadata_size"] = (root / "metadata.jsonl").stat().st_size
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    retriever = DenseRetriever(str(tmp_path / "faiss"))
    retriever.embed_query = lambda query, model_key: np.pad(
        np.array([[0.0, 1.0, 0.0, 0.0]], dtype=np.float32),
        ((0, 0), (0, 380)),
    )
    results = retriever.search(
        "résultat net",
        "recursive_fixed",
        "mini_lm_multilingual",
        top_k=1,
        companies=["ORANGE CI"],
        years=["2024"],
    )
    assert len(results) == 1
    assert results[0].company == "ORANGE CI"
    assert results[0].year == "2024"
