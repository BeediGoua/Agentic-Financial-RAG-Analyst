from __future__ import annotations

import numpy as np
import pytest

from app.embeddings.embedder import ChunkEmbedder
from app.embeddings.models import get_model_config


class FakeSentenceTransformer:
    created = []

    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs
        self.created.append((model_name, kwargs))

    def encode(self, texts, **kwargs):
        vectors = np.zeros((len(texts), 384), dtype=np.float32)
        for index in range(len(texts)):
            vectors[index, index % 384] = 1.0
        return vectors


def test_model_config_and_fake_encoder_preserve_revision(monkeypatch, tmp_path):
    import app.embeddings.embedder as module
    FakeSentenceTransformer.created = []
    monkeypatch.setattr(module, "SentenceTransformer", FakeSentenceTransformer)
    chunks_dir = tmp_path / "chunks"
    chunk_file = chunks_dir / "recursive_fixed" / "sample.chunks.jsonl"
    chunk_file.parent.mkdir(parents=True)
    import json
    chunk_file.write_text(
        json.dumps({
            "chunk_id": "one",
            "chunking_strategy": "recursive_fixed",
            "source_pdf": "/tmp/sample.pdf",
            "company": "ORANGE CI",
            "year": "2025",
            "text": "résultat net",
        }) + "\n",
        encoding="utf-8",
    )
    embedder = ChunkEmbedder(str(chunks_dir), str(tmp_path / "embeddings"))
    result = embedder.embed_file(chunk_file, "e5_small", force=True)
    assert result["status"] == "success"
    assert FakeSentenceTransformer.created[0][1]["revision"]


def test_e5_config_prefixes_are_documented():
    config = get_model_config("e5_small")
    assert config["query_prefix"] == "query: "
    assert config["passage_prefix"] == "passage: "
