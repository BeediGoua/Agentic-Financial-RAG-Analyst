from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from app.retrieval.dense import DenseRetriever
from app.retrieval.filters import matches_retrieval_filters


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


def test_shared_filter_supports_partial_company_and_year():
    assert matches_retrieval_filters(
        {"company": "ORANGE COTE D'IVOIRE", "year": "2024"},
        companies=["ORANGE CI"],
        years=["2024"],
    )


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
