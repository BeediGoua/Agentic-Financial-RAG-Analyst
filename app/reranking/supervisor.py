from __future__ import annotations

import json
import time
from pathlib import Path

from app.reranking.cross_encoder import CrossEncoderReranker
from app.reranking.quality import RerankingQuality


class RerankingSupervisor:
    """
    Orchestration de la phase reranking.

    Entrée :
    - un fichier retrieval_run_*.json

    Sortie :
    - un fichier reranking_run_*.json
    """

    def __init__(
        self,
        output_dir: str = "data/reranking/runs",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.quality = RerankingQuality()

    def save_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"reranking_run_{timestamp}.json"

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def run(
        self,
        retrieval_run_path: str,
        reranking_model: str = "mini_cross_encoder",
        top_k: int = 5,
    ) -> dict:
        path = Path(retrieval_run_path)

        if not path.exists():
            raise FileNotFoundError(f"Retrieval run not found: {path}")

        reranker = CrossEncoderReranker(model_key=reranking_model)

        runs = reranker.rerank_retrieval_run(
            retrieval_run_path=path,
            top_k=top_k,
        )

        quality = self.quality.evaluate(runs)

        report = {
            "overall_status": quality["status"],
            "retrieval_run_path": str(path),
            "reranking_model": reranking_model,
            "top_k": top_k,
            "quality": quality,
            "runs": runs,
        }

        report_path = self.save_report(report)
        report["report_path"] = str(report_path)

        return report