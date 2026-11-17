from __future__ import annotations

import json
import time
from pathlib import Path

from app.core.atomic import atomic_text_writer
from app.extraction.extraction_quality_agent import ExtractionQualityAgent
from app.extraction.pdf_text_agent import PDFTextExtractionAgent
from app.extraction.table_extraction_agent import TableExtractionAgent


class ExtractionSupervisorAgent:
    """
    Agent superviseur déterministe.
    Rôle : orchestrer extraction texte + extraction tables + rapport qualité.
    """

    def __init__(
        self,
        text_agent: PDFTextExtractionAgent,
        table_agent: TableExtractionAgent,
        quality_agent: ExtractionQualityAgent,
        quality_dir: str = "data/extracted/quality",
    ):
        self.text_agent = text_agent
        self.table_agent = table_agent
        self.quality_agent = quality_agent
        self.quality_dir = Path(quality_dir)
        self.quality_dir.mkdir(parents=True, exist_ok=True)

    def save_quality_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.quality_dir / f"extraction_run_{timestamp}.json"

        with atomic_text_writer(output_path) as output:
            json.dump(report, output, indent=2, ensure_ascii=False)

        return output_path

    def run(
        self,
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        text_results = self.text_agent.run(
            companies=companies,
            years=years,
            force=force,
        )

        table_results = self.table_agent.run(
            companies=companies,
            years=years,
            force=force,
        )

        text_quality = self.quality_agent.evaluate_text_results(text_results)
        table_quality = self.quality_agent.evaluate_table_results(table_results)

        severity = {"HEALTHY": 0, "DEGRADED": 1, "UNHEALTHY": 2}
        overall_status = max(
            (text_quality["status"], table_quality["status"]),
            key=lambda status: severity.get(status, 2),
        )

        report = {
            "overall_status": overall_status,
            "text_quality": text_quality,
            "table_quality": table_quality,
            "text_results": text_results,
            "table_results": table_results,
        }

        quality_report_path = self.save_quality_report(report)
        report["quality_report_path"] = str(quality_report_path)

        return report
