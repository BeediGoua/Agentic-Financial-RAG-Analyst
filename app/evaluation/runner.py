from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Iterable

from app.evaluation.adapters import run_adapter_search
from app.evaluation.evidence import evidence_matches_chunk
from app.evaluation.metrics import aggregate_metrics, evaluate_ranked_query, evidence_coverage
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
        k_values: list[int] | None = None,
    ) -> dict:
        per_query: list[dict] = []
        answerable_count = 0
        unanswerable_count = 0
        ignored_count = 0
        technical_errors: dict[str, int] = {}
        for question in questions:
            if question.answerability == "unanswerable":
                unanswerable_count += 1
                per_query.append({
                    "question_id": question.question_id,
                    "configuration_id": "unanswerable",
                    "split": question.split,
                    "status": "unanswerable",
                    "query": question.question,
                    "top_k": top_k,
                    "retrieved_ids": [],
                    "retrieved_evidence_ids": [],
                    "metrics": {},
                    "latency_ms": None,
                    "error": question.exclusion_reason,
                    "ranked_results": [],
                    "answerability": "unanswerable",
                })
                continue
            answerable_count += 1
            if question.annotation_status != "verified":
                ignored_count += 1
                per_query.append({
                    "question_id": question.question_id,
                    "configuration_id": "ignored",
                    "split": question.split,
                    "status": "ignored",
                    "query": question.question,
                    "top_k": top_k,
                    "retrieved_ids": [],
                    "retrieved_evidence_ids": [],
                    "metrics": {},
                    "latency_ms": None,
                    "error": "annotation_status_is_not_verified",
                    "ranked_results": [],
                    "answerability": "answerable",
                })
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
                        matched_evidence_ids: list[str] = []
                        matched_group_ids: list[str] = []
                        enriched_ranked: list[dict] = []
                        for item in ranked:
                            chunk_id = str(item.get("chunk_id") or "")
                            item_matches: list[str] = []
                            item_groups: list[str] = []
                            if not chunk_id:
                                item = dict(item)
                                item["matched_evidence_ids"] = []
                                item["matched_group_ids"] = []
                                item["provenance_status"] = "missing_provenance"
                                enriched_ranked.append(item)
                                continue
                            chunk_document_sha = str(
                                item.get("document_sha256")
                                or item.get("source_sha256")
                                or ""
                            ).lower()
                            if not chunk_document_sha:
                                item = dict(item)
                                item["matched_evidence_ids"] = []
                                item["matched_group_ids"] = []
                                item["provenance_status"] = "missing_provenance"
                                enriched_ranked.append(item)
                                continue
                            for group in question.evidence_groups:
                                for alternative in group.alternatives:
                                    evidence = alternative.model_dump()
                                    if evidence_matches_chunk(evidence, dict(item)):
                                        if evidence["evidence_id"] not in item_matches:
                                            item_matches.append(evidence["evidence_id"])
                                        if group.group_id not in item_groups:
                                            item_groups.append(group.group_id)
                                        if evidence["evidence_id"] not in matched_evidence_ids:
                                            matched_evidence_ids.append(evidence["evidence_id"])
                                        if group.group_id not in matched_group_ids:
                                            matched_group_ids.append(group.group_id)
                            item = dict(item)
                            item["matched_evidence_ids"] = item_matches
                            item["matched_group_ids"] = item_groups
                            item["provenance_status"] = (
                                "verified" if item_matches else "verified_document_not_matching"
                            )
                            enriched_ranked.append(item)
                        ranked_ids = matched_evidence_ids
                        metrics = {}
                        if status in ("success", "empty"):
                            metrics = evaluate_ranked_query(
                                ranked_ids,
                                qrels,
                                k=top_k,
                                relevant_threshold=relevant_threshold,
                            )
                            coverage = evidence_coverage(ranked_ids, evidence_groups)
                            metrics.update(coverage)
                            for k in sorted(set((k_values or [top_k]))):
                                if k <= 0:
                                    continue
                                k_metrics = evaluate_ranked_query(
                                    ranked_ids,
                                    qrels,
                                    k=k,
                                    relevant_threshold=relevant_threshold,
                                )
                                metrics[f"hit@{k}"] = k_metrics["hit"]
                                metrics[f"recall@{k}"] = k_metrics["recall"]
                                metrics[f"mrr@{k}"] = k_metrics["reciprocal_rank"]
                                metrics[f"ndcg@{k}"] = k_metrics["ndcg"]
                                k_coverage = evidence_coverage(ranked_ids[:k], evidence_groups)
                                metrics[f"evidence_coverage@{k}"] = k_coverage["evidence_coverage"]
                                metrics[f"all_evidence@{k}"] = k_coverage["all_evidence"]
                        else:
                            technical_errors[status] = technical_errors.get(status, 0) + 1
                        per_query.append(
                            {
                                "question_id": question.question_id,
                                "configuration_id": configuration_id,
                                "split": question.split,
                                "status": status,
                                "query": question.question,
                                "top_k": top_k,
                                "retrieved_ids": ranked_ids,
                                "retrieved_evidence_ids": matched_evidence_ids,
                                "matched_group_ids": matched_group_ids,
                                "metrics": metrics,
                                "latency_ms": latency,
                                "error": error,
                                "ranked_results": enriched_ranked,
                                "answerability": "answerable",
                                "corpus_snapshot": str(self.corpus_snapshot.get("snapshot_id") or ""),
                            }
                        )
        total_technical = sum(technical_errors.values())
        total_rows = len(per_query)
        technical_count = technical_errors
        technical_percent = {
            status: (count / total_rows * 100.0 if total_rows else 0.0)
            for status, count in technical_count.items()
        }
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "seed": self.seed,
            "synthetic": self.synthetic,
            "corpus_snapshot": self.corpus_snapshot,
            "per_query": per_query,
            "counts": {
                "answerable": answerable_count,
                "unanswerable": unanswerable_count,
                "ignored": ignored_count,
                "evaluated": sum(
                    1 for row in per_query
                    if row["status"] in ("success", "empty")
                ),
                "technical_errors": total_technical,
            },
            "technical_errors": technical_count,
            "technical_error_percentages": technical_percent,
        }
