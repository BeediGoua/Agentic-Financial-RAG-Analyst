from __future__ import annotations

import json
import time
from pathlib import Path

from app.chunking.hierarchical import HierarchicalChunking
from app.chunking.markdown_aware import MarkdownAwareChunking
from app.chunking.page_aware import PageAwareChunking
from app.chunking.quality import ChunkQuality
from app.chunking.recursive_fixed import RecursiveFixedChunking
from app.chunking.section_aware import SectionAwareChunking
from app.chunking.semantic import SemanticChunking
from app.chunking.table_aware import TableAwareChunking


class ChunkingSupervisor:
    def __init__(self, quality_dir: str = "data/chunks/quality"):
        self.quality_dir = Path(quality_dir)
        self.quality_dir.mkdir(parents=True, exist_ok=True)
        self.quality = ChunkQuality()

        self.strategies = {
            "recursive_fixed": RecursiveFixedChunking(),
            "page_aware": PageAwareChunking(),
            "section_aware": SectionAwareChunking(),
            "table_aware": TableAwareChunking(),
            "semantic": SemanticChunking(),
            "markdown_aware": MarkdownAwareChunking(),
            "hierarchical": HierarchicalChunking(),
        }

    def save_report(self, report: dict) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = self.quality_dir / f"chunking_run_{timestamp}.json"

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def run(
        self,
        strategies: list[str],
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        strategy_results: dict[str, list[dict]] = {}

        for strategy in strategies:
            if strategy not in self.strategies:
                raise ValueError(
                    f"Unknown strategy: {strategy}. Available: {list(self.strategies)}"
                )

            strategy_results[strategy] = self.strategies[strategy].run(
                companies=companies,
                years=years,
                force=force,
            )

        strategy_quality = self.quality.evaluate_by_strategy(strategy_results)

        overall_status = "PASS"

        if any(q["status"] == "FAIL" for q in strategy_quality.values()):
            overall_status = "FAIL"
        elif any(q["status"] == "WARNING" for q in strategy_quality.values()):
            overall_status = "WARNING"

        report = {
            "overall_status": overall_status,
            "strategies": strategies,
            "companies": companies or "all",
            "years": years or "all",
            "strategy_quality": strategy_quality,
            "strategy_results": strategy_results,
        }

        report_path = self.save_report(report)
        report["report_path"] = str(report_path)

        return report