from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from app.retrieval.bm25 import BM25Retriever
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.quality import RetrievalQuality


class RetrievalSupervisor:
    """
    Orchestration Retrieval.

    Méthodes supportées :
    - dense
    - bm25
    - hybrid
    """

    def __init__(
        self,
        output_dir: str = "data/retrieval/runs",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.dense = DenseRetriever()
        self.bm25 = BM25Retriever()
        self.hybrid = HybridRetriever(
            dense_retriever=self.dense,
            bm25_retriever=self.bm25,
        )
        self.quality = RetrievalQuality()

    def save_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        run_id = report.get("run_id") or uuid.uuid4().hex
        report["run_id"] = run_id
        path = self.output_dir / f"retrieval_run_{timestamp}_{run_id}.json"
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)

        return path

    def _status_for_error(self, exc: Exception) -> tuple[str, str]:
        message = str(exc)
        if isinstance(exc, FileNotFoundError) or "missing_corpus" in message:
            return "missing_corpus", message
        if (
            "invalid_index" in message
            or "Unable to read FAISS" in message
            or "Rejected invalid" in message
            or "mismatched FAISS" in message
        ):
            return "invalid_index", message
        if "model unavailable" in message.lower() or "sentence_transformer" in message.lower():
            return "model_unavailable", message
        return "error", message

    def run_one(
        self,
        query: str,
        method: str,
        strategy: str,
        model_key: str,
        top_k: int,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> dict:
        try:
            if method == "dense":
                results = self.dense.search(
                    query=query,
                    strategy=strategy,
                    model_key=model_key,
                    top_k=top_k,
                    companies=companies,
                    years=years,
                )

            elif method == "bm25":
                results = self.bm25.search(
                    query=query,
                    strategy=strategy,
                    top_k=top_k,
                    companies=companies,
                    years=years,
                )

            elif method == "hybrid":
                results = self.hybrid.search(
                    query=query,
                    strategy=strategy,
                    model_key=model_key,
                    top_k=top_k,
                    companies=companies,
                    years=years,
                )

            else:
                raise ValueError(f"Unknown retrieval method: {method}")

            return {
                "status": "success" if results else "empty",
                "query": query,
                "method": method,
                "strategy": strategy,
                "model": model_key,
                "top_k": top_k,
                "results_count": len(results),
                "results": [r.model_dump() for r in results],
            }

        except Exception as e:
            status, error = self._status_for_error(e)
            return {
                "status": status,
                "query": query,
                "method": method,
                "strategy": strategy,
                "model": model_key,
                "top_k": top_k,
                "results_count": 0,
                "error": str(e),
            }

    def run(
        self,
        query: str,
        methods: list[str],
        strategies: list[str],
        models: list[str],
        top_k: int = 5,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> dict:
        runs = []

        for method in methods:
            for strategy in strategies:
                if method == "bm25":
                    runs.append(
                        self.run_one(
                            query=query,
                            method=method,
                            strategy=strategy,
                            model_key="none",
                            top_k=top_k,
                            companies=companies,
                            years=years,
                        )
                    )
                else:
                    for model_key in models:
                        runs.append(
                            self.run_one(
                                query=query,
                                method=method,
                                strategy=strategy,
                                model_key=model_key,
                                top_k=top_k,
                                companies=companies,
                                years=years,
                            )
                        )

        quality = self.quality.evaluate(runs)

        report = {
            "overall_status": quality["status"],
            "query": query,
            "methods": methods,
            "strategies": strategies,
            "models": models,
            "top_k": top_k,
            "quality": quality,
            "runs": runs,
        }

        path = self.save_report(report)
        report["report_path"] = str(path)

        return report