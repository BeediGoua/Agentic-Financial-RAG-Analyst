from __future__ import annotations

import json
import time
from pathlib import Path

from app.generation.citation_builder import CitationBuilder
from app.generation.ollama_generator import OllamaGenerator
from app.generation.quality import GenerationQuality
from app.generation.schemas import GeneratedAnswer


class GenerationSupervisor:
    """
    Orchestration génération contrôlée.
    """

    def __init__(
        self,
        output_dir: str = "data/generation/runs",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.citation_builder = CitationBuilder()
        self.quality = GenerationQuality()

    def load_reranking_run(
        self,
        path: Path,
    ) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def save_report(
        self,
        report: dict,
    ) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        output_path = (
            self.output_dir
            / f"generation_run_{timestamp}.json"
        )

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return output_path

    def run(
        self,
        reranking_run_path: str,
        provider: str = "ollama",
        model_name: str = "qwen2.5:7b",
    ) -> dict:
        path = Path(reranking_run_path)

        if not path.exists():
            raise FileNotFoundError(path)

        reranking_report = self.load_reranking_run(path)

        runs = reranking_report.get("runs", [])

        if not runs:
            raise ValueError("No reranking runs found.")

        first_run = runs[0]

        query = first_run["query"]
        reranked_results = first_run["results"]

        contexts = [
            item.get("text", "")
            for item in reranked_results
        ]

        generator = OllamaGenerator(
            model_name=model_name,
        )

        answer = generator.generate(
            query=query,
            contexts=contexts,
        )

        citations = self.citation_builder.build(
            reranked_results
        )

        quality = self.quality.evaluate(
            answer=answer,
            citations_count=len(citations),
        )

        generated = GeneratedAnswer(
            query=query,
            answer=answer,
            status="answered"
            if answer != "Information not found in the provided documents."
            else "not_found",
            confidence=0.80,
            provider=provider,
            model=model_name,
            retrieval_method=first_run.get("retrieval_method"),
            reranking_model=first_run.get("reranking_model"),
            citations=citations,
            used_chunks=len(reranked_results),
        )

        report = {
            "overall_status": quality["status"],
            "quality": quality,
            "generated_answer": generated.model_dump(),
        }

        report_path = self.save_report(report)

        report["report_path"] = str(report_path)

        return report