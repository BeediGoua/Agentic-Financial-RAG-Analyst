from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from app.vector_db.faiss_index import FaissIndexBuilder


def make_record(chunk_id: str, vector: list[float], company="ORANGE CI", year="2025"):
    return {
        "chunk_id": chunk_id,
        "chunking_strategy": "recursive_fixed",
        "embedding_model": "mini_lm_multilingual",
        "vector_dimension": len(vector),
        "embedding": vector,
        "source_pdf": f"/tmp/{chunk_id}.pdf",
        "source_url": "https://www.brvm.org/report",
        "company": company,
        "year": year,
        "document_type": "annual_report",
        "language": "fr",
        "page_start": 1,
        "page_end": 1,
        "section": "performance",
        "parent_id": None,
        "content_type": "text",
        "char_count": 20,
        "word_count": 4,
        "text": f"Passage financier {chunk_id}",
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_distinct_embedding_files_have_distinct_indexes(tmp_path):
    source = tmp_path / "embeddings"
    directory = source / "recursive_fixed" / "mini_lm_multilingual" / "brvm" / "2025"
    directory.mkdir(parents=True)
    first = directory / "first.embeddings.jsonl"
    second = directory / "second.embeddings.jsonl"
    builder = FaissIndexBuilder(str(source), str(tmp_path / "faiss"))
    assert builder.build_output_paths(first) != builder.build_output_paths(second)


def test_invalid_embedding_does_not_create_index(tmp_path):
    source = tmp_path / "embeddings"
    embedding_file = (
        source / "recursive_fixed" / "mini_lm_multilingual"
        / "brvm" / "invalid.embeddings.jsonl"
    )
    write_jsonl(
        embedding_file,
        [
            make_record("good", [1.0] + [0.0] * 383),
            make_record("bad", []),
        ],
    )
    builder = FaissIndexBuilder(str(source), str(tmp_path / "faiss"))
    result = builder.build_index_for_file(embedding_file, force=True)
    assert result["status"] == "error"
    index_path, metadata_path = builder.build_output_paths(embedding_file)
    assert not index_path.exists()
    assert not metadata_path.exists()


def test_vector_ids_match_faiss_positions(tmp_path):
    source = tmp_path / "embeddings"
    embedding_file = (
        source / "recursive_fixed" / "mini_lm_multilingual"
        / "brvm" / "valid.embeddings.jsonl"
    )
    write_jsonl(
        embedding_file,
        [
            make_record("a", [1.0] + [0.0] * 383),
            make_record("b", [0.0, 1.0] + [0.0] * 382),
        ],
    )
    builder = FaissIndexBuilder(str(source), str(tmp_path / "faiss"))
    result = builder.build_index_for_file(embedding_file, force=True)
    assert result["status"] == "success"
    index_path, metadata_path = builder.build_output_paths(embedding_file)
    index = faiss.read_index(str(index_path))
    metadata = [json.loads(line) for line in metadata_path.read_text().splitlines()]
    assert index.ntotal == len(metadata) == 2
    assert [row["vector_id"] for row in metadata] == [0, 1]
    assert [row["chunk_id"] for row in metadata] == ["a", "b"]


def test_nan_duplicate_and_dimension_errors(tmp_path):
    source = tmp_path / "embeddings"
    embedding_file = source / "recursive_fixed" / "mini_lm_multilingual" / "brvm" / "bad.embeddings.jsonl"
    cases = [
        [make_record("a", [float("nan")] + [0.0] * 383)],
        [make_record("a", [1.0] * 383)],
        [make_record("a", [1.0] + [0.0] * 383), make_record("a", [0.0, 1.0] + [0.0] * 382)],
    ]
    builder = FaissIndexBuilder(str(source), str(tmp_path / "faiss"))
    for rows in cases:
        write_jsonl(embedding_file, rows)
        assert builder.build_index_for_file(embedding_file, force=True)["status"] == "error"
