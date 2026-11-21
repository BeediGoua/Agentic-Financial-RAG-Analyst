from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable

from app.evaluation.adapters import run_adapter_search
from app.evaluation.metrics import aggregate_metrics, evaluate_ranked_query
from app.evaluation.schemas import GoldQuestion


class FixtureRetriever:
    def __init__(self, ranked_by_query: dict[str, list[dict]]) -> None:
        self.ranked_by_query = ranked_by_query

    def search(self, query: str, **kwargs) -> list[dict]:
        return self.ranked_by_query.get(query, [])


class BenchmarkRunner:
    def __init__(
        self,
        *,
        retrievers: dict[str, object],
        corpus_snapshot: dict,
        seed: int = 42,
        synthetic: bool = True,
    ) -> None:
        self.retrievers = retrievers
        self.corpus_snapshot = corpus_snapshot
        self.seed = seed
        self.synthetic = synthetic
        self.run_id = uuid.uuid4().hex

    def run(
        self,
        questions: Iterable[GoldQuestion],
        *,
        strategies: list[str],
        models: list[str],
        methods: list[str],
        top_k: int,
        relevant_threshold: int = 2,
    ) -> dict:
        per_query: list[dict] = []
        for question in questions:
            if question.answerability == "unanswerable":
                continue
            evidence_groups: dict[str, set[str]] = {}
            qrels: dict[str, int] = {}
            for group in question.evidence_groups:
                alternatives = {alternative.evidence_id for alternative in group.alternatives}
                evidence_groups[group.group_id] = alternatives
                for alternative in group.alternatives:
                    qrels[alternative.evidence_id] = alternative.grade
            for method in methods:
                model_keys = ["none"] if method == "bm25" else models
                for strategy in strategies:
                    for model_key in model_keys:
                        retriever_key = method
                        retriever = self.retrievers.get(retriever_key)
                        if retriever is None:
                            raise ValueError(f"Retriever unavailable: {retriever_key}")
                        configuration_id = (
                            f"{method}_{strategy}_{model_key}"
                            if method != "bm25"
                            else f"{method}_{strategy}"
                        )
                        ranked, status, error, latency = run_adapter_search(
                            retriever,
                            query=question.question,
                            method=method,
                            strategy=strategy,
                            model_key=None if method == "bm25" else model_key,
                            top_k=top_k,
                            companies=question.company_tickers,
                            years=question.years,
                        )
                        ranked_ids = [
                            str(item.get("evidence_id") or item.get("chunk_id"))
                            for item in ranked
                        ]
                        if len(ranked_ids) != len(set(ranked_ids)):
                            raise ValueError("Duplicate candidate identifiers")
                        metrics = {}
                        if status == "success":
                            metrics = evaluate_ranked_query(
                                ranked_ids,
                                qrels,
                                k=top_k,
                                relevant_threshold=relevant_threshold,
                            )
                        per_query.append(
                            {
                                "question_id": question.question_id,
                                "configuration_id": configuration_id,
                                "status": status,
                                "query": question.question,
                                "top_k": top_k,
                                "retrieved_ids": ranked_ids,
                                "retrieved_evidence_ids": ranked_ids,
                                "metrics": metrics,
                                "latency_ms": latency,
                                "error": error,
                                "ranked_results": ranked,
                            }
                        )
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "seed": self.seed,
            "synthetic": self.synthetic,
            "corpus_snapshot": self.corpus_snapshot,
            "per_query": per_query,
        }
