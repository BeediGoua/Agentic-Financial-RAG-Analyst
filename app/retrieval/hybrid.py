from __future__ import annotations

from app.retrieval.bm25 import BM25Retriever
from app.retrieval.dense import DenseRetriever
from app.retrieval.schemas import RetrievalResult


class HybridRetriever:
    """
    Combine Dense Retrieval + BM25.

    Score final simple :
    dense_score_normalisé * dense_weight
    +
    bm25_score_normalisé * bm25_weight
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever | None = None,
        bm25_retriever: BM25Retriever | None = None,
        dense_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ):
        self.dense_retriever = dense_retriever or DenseRetriever()
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight

    def normalize_scores(self, results: list[RetrievalResult]) -> dict[str, float]:
        if not results:
            return {}

        scores = [r.score for r in results]
        min_score = min(scores)
        max_score = max(scores)

        normalized = {}

        for result in results:
            if max_score == min_score:
                normalized[result.chunk_id] = 1.0
            else:
                normalized[result.chunk_id] = (
                    (result.score - min_score) / (max_score - min_score)
                )

        return normalized

    def search(
        self,
        query: str,
        strategy: str,
        model_key: str,
        top_k: int = 5,
        retrieval_pool: int = 20,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> list[RetrievalResult]:
        dense_results = self.dense_retriever.search(
            query=query,
            strategy=strategy,
            model_key=model_key,
            top_k=retrieval_pool,
        )

        bm25_results = self.bm25_retriever.search(
            query=query,
            strategy=strategy,
            top_k=retrieval_pool,
            companies=companies,
            years=years,
        )

        dense_norm = self.normalize_scores(dense_results)
        bm25_norm = self.normalize_scores(bm25_results)

        by_chunk: dict[str, RetrievalResult] = {}

        for result in dense_results + bm25_results:
            if result.chunk_id not in by_chunk:
                by_chunk[result.chunk_id] = result

        scored = []

        for chunk_id, result in by_chunk.items():
            score = (
                self.dense_weight * dense_norm.get(chunk_id, 0.0)
                + self.bm25_weight * bm25_norm.get(chunk_id, 0.0)
            )

            result.score = float(score)
            result.retrieval_method = "hybrid"

            scored.append(result)

        scored = sorted(scored, key=lambda x: x.score, reverse=True)[:top_k]

        for rank, result in enumerate(scored, start=1):
            result.rank = rank

        return scored