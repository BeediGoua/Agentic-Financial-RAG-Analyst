from __future__ import annotations

import json
import time
from pathlib import Path

from app.processing.metadata_enrichment import MetadataEnrichmentAgent
from app.processing.processing_quality import ProcessingQualityAgent
from app.processing.table_cleaning import TableCleaningAgent
from app.processing.text_cleaning import TextCleaningAgent


class ProcessingSupervisorAgent:
    """
    Agent superviseur déterministe.
    Rôle :
    - orchestrer nettoyage texte ;
    - orchestrer nettoyage tables ;
    - vérifier metadata ;
    - générer rapport qualité.
    """

    def __init__(
        self,
        text_agent: TextCleaningAgent,
        table_agent: TableCleaningAgent,
        metadata_agent: MetadataEnrichmentAgent,
        quality_agent: ProcessingQualityAgent,
        quality_dir: str = "data/processed/quality",
    ):
        self.text_agent = text_agent
        self.table_agent = table_agent
        self.metadata_agent = metadata_agent
        self.quality_agent = quality_agent

        self.quality_dir = Path(quality_dir)
        self.quality_dir.mkdir(parents=True, exist_ok=True)

    def save_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.quality_dir / f"processing_run_{timestamp}.json"

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

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

        metadata_quality = self.metadata_agent.run()

        text_quality = self.quality_agent.evaluate_text_cleaning(text_results)
        table_quality = self.quality_agent.evaluate_table_cleaning(table_results)

        overall_status = self.quality_agent.decide_overall_status(
            text_quality=text_quality,
            table_quality=table_quality,
            metadata_quality=metadata_quality,
        )

        report = {
            "overall_status": overall_status,
            "companies": companies or "all",
            "years": years or "all",
            "text_quality": text_quality,
            "table_quality": table_quality,
            "metadata_quality": metadata_quality,
            "text_results": text_results,
            "table_results": table_results,
        }

        report_path = self.save_report(report)
        report["report_path"] = str(report_path)

        return report