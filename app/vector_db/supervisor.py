from __future__ import annotations

import json
import time
from pathlib import Path

from app.vector_db.faiss_index import FaissIndexBuilder
from app.vector_db.quality import VectorDBQuality


class VectorDBSupervisor:
    """
    Orchestrateur phase 6.
    """

    def __init__(
        self,
        quality_dir: str = "data/vector_db/faiss/quality",
    ):
        self.quality_dir = Path(quality_dir)
        self.quality_dir.mkdir(parents=True, exist_ok=True)

        self.index_builder = FaissIndexBuilder()
        self.quality = VectorDBQuality()

    def save_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.quality_dir / f"vector_db_run_{timestamp}.json"

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def run(
        self,
        strategies: list[str] | None = None,
        models: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        results = self.index_builder.run(
            strategies=strategies,
            models=models,
            force=force,
        )

        quality = self.quality.evaluate(results)

        report = {
            "overall_status": quality["status"],
            "strategies": strategies or "all_available",
            "models": models or "all_available",
            "quality": quality,
            "results": results,
        }

        report_path = self.save_report(report)
        report["report_path"] = str(report_path)

        return report
