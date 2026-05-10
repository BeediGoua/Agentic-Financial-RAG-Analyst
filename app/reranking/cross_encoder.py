from __future__ import annotations

import json
from pathlib import Path

from sentence_transformers import CrossEncoder
from tqdm import tqdm

from app.reranking.models import get_reranking_model_config
from app.reranking.schemas import RerankedResult


class CrossEncoderReranker:
    """
    Reranker basé sur CrossEncoder.

    Rôle :
    - lire les résultats retrieval ;
    - scorer chaque paire (question, chunk) ;
    - réordonner les chunks ;
    - produire un top-k final.
    """

    def __init__(
        self,
        model_key: str = "mini_cross_encoder",
        batch_size: int = 16,
    ):
        self.model_key = model_key
        self.batch_size = batch_size

        config = get_reranking_model_config(model_key)
        self.model_name = config["model_name"]
        self.model = CrossEncoder(self.model_name)

    def load_retrieval_run(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def rerank_results(
        self,
        query: str,
        retrieval_results: list[dict],
        top_k: int = 5,
    ) -> list[RerankedResult]:
        if not retrieval_results:
            return []

        pairs = [
            (query, str(item.get("text") or ""))
            for item in retrieval_results
        ]

        scores = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        reranked = []

        for item, score in zip(retrieval_results, scores):
            original_rank = item.get("rank")
            retrieval_score = item.get("score")

            reranked.append(
                RerankedResult(
                    rank=0,
                    original_rank=original_rank,
                    retrieval_score=float(retrieval_score) if retrieval_score is not None else None,
                    reranking_score=float(score),
                    final_score=float(score),

                    retrieval_method=item.get("retrieval_method", "unknown"),
                    reranking_model=self.model_key,

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

        reranked = sorted(
            reranked,
            key=lambda x: x.final_score,
            reverse=True,
        )[:top_k]

        for rank, item in enumerate(reranked, start=1):
            item.rank = rank

        return reranked

    def rerank_retrieval_run(
        self,
        retrieval_run_path: Path,
        top_k: int = 5,
    ) -> list[dict]:
        retrieval_report = self.load_retrieval_run(retrieval_run_path)
        query = retrieval_report["query"]

        reranking_outputs = []

        for run in tqdm(retrieval_report.get("runs", []), desc="Reranking runs"):
            if run.get("status") != "success":
                continue

            retrieval_results = run.get("results", [])

            reranked_results = self.rerank_results(
                query=query,
                retrieval_results=retrieval_results,
                top_k=top_k,
            )

            reranking_outputs.append(
                {
                    "status": "success" if reranked_results else "empty",
                    "query": query,
                    "retrieval_method": run.get("method"),
                    "chunking_strategy": run.get("strategy"),
                    "embedding_model": run.get("model"),
                    "reranking_model": self.model_key,
                    "top_k": top_k,
                    "input_results_count": len(retrieval_results),
                    "reranked_results_count": len(reranked_results),
                    "results": [item.model_dump() for item in reranked_results],
                }
            )

        return reranking_outputs