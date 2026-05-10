from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.embeddings.models import get_model_config
from app.retrieval.schemas import RetrievalResult


class DenseRetriever:
    """
    Retrieval dense avec FAISS.

    Entrées :
    - index.faiss
    - metadata.jsonl

    Sortie :
    - top-k chunks similaires à la question.
    """

    def __init__(
        self,
        vector_db_dir: str = "data/vector_db/faiss",
    ):
        self.vector_db_dir = Path(vector_db_dir)
        self._model_cache: dict[str, SentenceTransformer] = {}

    def load_metadata(self, metadata_path: Path) -> list[dict]:
        rows = []

        with metadata_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

        return rows

    def get_model(self, model_key: str) -> SentenceTransformer:
        if model_key not in self._model_cache:
            config = get_model_config(model_key)
            self._model_cache[model_key] = SentenceTransformer(config["model_name"])

        return self._model_cache[model_key]

    def embed_query(self, query: str, model_key: str) -> np.ndarray:
        config = get_model_config(model_key)
        query_prefix = config.get("query_prefix", "")

        model = self.get_model(model_key)

        vector = model.encode(
            [query_prefix + query],
            normalize_embeddings=True,
        )

        return np.array(vector, dtype="float32")

    def get_index_paths(
        self,
        strategy: str,
        model_key: str,
    ) -> list[tuple[Path, Path]]:
        root = self.vector_db_dir / strategy / model_key

        if not root.exists():
            return []

        pairs = []

        for index_path in root.rglob("index.faiss"):
            metadata_path = index_path.parent / "metadata.jsonl"

            if metadata_path.exists():
                pairs.append((index_path, metadata_path))

        return pairs

    def search_one_index(
        self,
        query: str,
        strategy: str,
        model_key: str,
        index_path: Path,
        metadata_path: Path,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        index = faiss.read_index(str(index_path))
        metadata = self.load_metadata(metadata_path)

        query_vector = self.embed_query(query, model_key)

        scores, ids = index.search(query_vector, top_k)

        results = []

        for rank, (vector_id, score) in enumerate(zip(ids[0], scores[0]), start=1):
            if vector_id < 0 or vector_id >= len(metadata):
                continue

            item = metadata[vector_id]

            results.append(
                RetrievalResult(
                    rank=rank,
                    score=float(score),
                    retrieval_method="dense",
                    chunk_id=item["chunk_id"],
                    chunking_strategy=item["chunking_strategy"],
                    embedding_model=item.get("embedding_model"),
                    source_pdf=item["source_pdf"],
                    source_url=item.get("source_url"),
                    company=item.get("company"),
                    year=item.get("year"),
                    document_type=item.get("document_type"),
                    language=item.get("language"),
                    page_start=item.get("page_start"),
                    page_end=item.get("page_end"),
                    section=item.get("section"),
                    parent_id=item.get("parent_id"),
                    content_type=item.get("content_type"),
                    text=item.get("text") or "",
                )
            )

        return results

    def search(
        self,
        query: str,
        strategy: str,
        model_key: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        pairs = self.get_index_paths(strategy=strategy, model_key=model_key)

        all_results = []

        for index_path, metadata_path in pairs:
            all_results.extend(
                self.search_one_index(
                    query=query,
                    strategy=strategy,
                    model_key=model_key,
                    index_path=index_path,
                    metadata_path=metadata_path,
                    top_k=top_k,
                )
            )

        all_results = sorted(all_results, key=lambda x: x.score, reverse=True)

        final_results = all_results[:top_k]

        for rank, result in enumerate(final_results, start=1):
            result.rank = rank

        return final_results