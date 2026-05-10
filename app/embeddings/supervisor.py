from __future__ import annotations

import json
import time
from pathlib import Path

from app.embeddings.embedder import ChunkEmbedder
from app.embeddings.quality import EmbeddingQuality


class EmbeddingSupervisor:
    def __init__(self, quality_dir: str = "data/embeddings/quality"):
        self.quality_dir = Path(quality_dir)
        self.quality_dir.mkdir(parents=True, exist_ok=True)

        self.embedder = ChunkEmbedder()
        self.quality = EmbeddingQuality()

    def save_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.quality_dir / f"embeddings_run_{timestamp}.json"

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def run(
        self,
        models: list[str],
        strategies: list[str],
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        model_results = {}
        model_quality = {}

        for model_key in models:
            results = self.embedder.run(
                model_key=model_key,
                strategies=strategies,
                companies=companies,
                years=years,
                force=force,
            )

            model_results[model_key] = results
            model_quality[model_key] = self.quality.evaluate(results)

        overall_status = "PASS"

        if any(q["status"] == "FAIL" for q in model_quality.values()):
            overall_status = "FAIL"
        elif any(q["status"] == "WARNING" for q in model_quality.values()):
            overall_status = "WARNING"

        report = {
            "overall_status": overall_status,
            "models": models,
            "strategies": strategies,
            "companies": companies or "all",
            "years": years or "all",
            "model_quality": model_quality,
            "model_results": model_results,
        }

        report_path = self.save_report(report)
        report["report_path"] = str(report_path)

        return report