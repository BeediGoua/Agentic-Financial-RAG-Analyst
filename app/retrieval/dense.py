from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
import os
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from app.embeddings.models import get_model_config
from app.core.artifact_cache import validate_faiss_artifact
from app.retrieval.filters import matches_retrieval_filters
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
        allow_model_download: bool = False,
    ):
        self.vector_db_dir = Path(vector_db_dir)
        self._model_cache: dict[str, SentenceTransformer] = {}
        self.allow_model_download = allow_model_download

    def load_metadata(self, metadata_path: Path) -> list[dict]:
        rows = []

        with metadata_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

        return rows

    def get_model(self, model_key: str) -> SentenceTransformer:
        if SentenceTransformer is None:
            raise RuntimeError(
                "model_unavailable: sentence_transformers is not installed"
            )
        if model_key not in self._model_cache:
            config = get_model_config(model_key)
            if not self.allow_model_download:
                os.environ["HF_HUB_OFFLINE"] = "1"
            else:
                os.environ.pop("HF_HUB_OFFLINE", None)
            self._model_cache[model_key] = SentenceTransformer(
                config["model_name"],
                revision=config["revision"],
            )

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

    def validate_index_metadata(
        self,
        index,
        metadata: list[dict],
        *,
        expected_dimension: int,
        strategy: str,
        model_key: str,
    ) -> None:
        if index.ntotal != len(metadata):
            raise ValueError(
                f"Index/metadata mismatch: {index.ntotal} vectors versus "
                f"{len(metadata)} metadata rows"
            )
        if index.ntotal <= 0:
            raise ValueError("Empty FAISS index")
        if index.d != expected_dimension:
            raise ValueError(
                f"Invalid FAISS dimension: {index.d} instead of {expected_dimension}"
            )

        seen_chunk_ids: set[str] = set()
        for position, row in enumerate(metadata):
            if row.get("vector_id") != position:
                raise ValueError(f"Misaligned metadata at position {position}")
            if row.get("chunking_strategy") != strategy:
                raise ValueError("Metadata strategy mismatch")
            if row.get("embedding_model") != model_key:
                raise ValueError("Metadata embedding model mismatch")
            chunk_id = str(row.get("chunk_id") or "")
            if not chunk_id:
                raise ValueError("Missing chunk identifier")
            if chunk_id in seen_chunk_ids:
                raise ValueError(f"Duplicate chunk identifier: {chunk_id}")
            seen_chunk_ids.add(chunk_id)
            if not row.get("source_pdf"):
                raise ValueError("Missing document provenance")
            if not str(row.get("text") or "").strip():
                raise ValueError("Missing chunk text")
            page_start = row.get("page_start")
            page_end = row.get("page_end")
            if page_start is not None and int(page_start) < 1:
                raise ValueError("Invalid page_start")
            if page_end is not None and page_start is not None:
                if int(page_end) < int(page_start):
                    raise ValueError("Invalid page range")

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
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []
        config = get_model_config(model_key)
        # The source embedding file is represented by source_sha256 in the manifest.
        # Validate the pair and manifest independently of the source path here.
        try:
            index = faiss.read_index(str(index_path))
        except Exception as exc:
            raise ValueError(f"Unable to read FAISS index {index_path}: {exc}") from exc
        metadata = self.load_metadata(metadata_path)
        valid, _, _ = validate_faiss_artifact(
            index_path,
            metadata_path,
            expected_fingerprint={
                "schema_version": 1,
                "stage": "faiss_index",
                "params": {
                    "strategy": strategy,
                    "model": model_key,
                    "model_revision": config["revision"],
                },
            },
            expected_dimension=int(config["dimension"]),
            expected_strategy=strategy,
            expected_model=model_key,
            expected_revision=str(config["revision"]),
        )
        if not valid:
            raise ValueError(
                f"Rejected invalid or mismatched FAISS artifact pair: "
                f"{index_path.parent}"
            )
        self.validate_index_metadata(
            index,
            metadata,
            expected_dimension=int(config["dimension"]),
            strategy=strategy,
            model_key=model_key,
        )
        query_vector = self.embed_query(query, model_key)
        if query_vector.shape[1] != index.d:
            raise ValueError(
                f"Query dimension mismatch: {query_vector.shape[1]} instead of {index.d}"
            )

        search_size = min(index.ntotal, max(top_k * 4, 32))
        matching: list[tuple[int, float]] = []
        while True:
            scores, ids = index.search(query_vector, search_size)
            matching = []
            for vector_id, score in zip(ids[0], scores[0]):
                if int(vector_id) < 0 or int(vector_id) >= len(metadata):
                    continue
                item = metadata[int(vector_id)]
                if not matches_retrieval_filters(
                    item,
                    companies=companies,
                    years=years,
                ):
                    continue
                matching.append((int(vector_id), float(score)))
            if len(matching) >= top_k or search_size >= index.ntotal:
                break
            search_size = min(index.ntotal, search_size * 2)

        results = []

        matching.sort(key=lambda pair: pair[1], reverse=True)
        for rank, (vector_id, score) in enumerate(matching[:top_k], start=1):
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
                    document_sha256=item.get("document_sha256"),
                    source_sha256=item.get("source_sha256"),
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
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []
        pairs = self.get_index_paths(strategy=strategy, model_key=model_key)
        if not pairs:
            raise FileNotFoundError(
                f"missing_corpus: FAISS index absent for strategy={strategy} "
                f"model={model_key}"
            )

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
                    companies=companies,
                    years=years,
                )
            )

        all_results = sorted(all_results, key=lambda x: x.score, reverse=True)

        final_results = all_results[:top_k]

        for rank, result in enumerate(final_results, start=1):
            result.rank = rank

        return final_results