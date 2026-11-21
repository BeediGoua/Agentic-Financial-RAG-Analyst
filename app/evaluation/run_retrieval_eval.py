from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from app.evaluation.corpus import build_corpus_manifest
from app.evaluation.qrels import load_questions
from app.evaluation.reporting import (
    write_csv_atomic,
    write_json_atomic,
    write_markdown,
)
from app.evaluation.runner import BenchmarkRunner, FixtureRetriever
from app.evaluation.schemas import GoldQuestion


def load_config(path: str | None) -> dict:
    if not path:
        return {
            "benchmark": {"seed": 42, "k_values": [1, 5, 10], "relevance_threshold": 2},
            "retrieval": {
                "strategies": ["recursive_fixed", "page_aware", "section_aware"],
                "embedding_models": ["mini_lm_multilingual", "e5_small"],
                "methods": ["bm25", "dense", "hybrid"],
            },
        }
    config_path = Path(path)
    if not config_path.is_file():
        raise FileNotFoundError(f"Configuration absent: {config_path}")
    return yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}


def build_fixture_questions() -> list[GoldQuestion]:
    return [
        GoldQuestion(
            question_id="SYNTH-Q0001",
            question="Quel est le résultat net synthétique d'ORANGE CI en 2024?",
            language="fr",
            task_type="financial_fact",
            company_tickers=["ORAC"],
            years=["2024"],
            document_types=["annual_report"],
            answerability="answerable",
            split="dev",
            annotation_status="verified",
            evidence_groups=[
                {
                    "group_id": "G1",
                    "alternatives": [
                        {
                            "evidence_id": "SYNTH-E1",
                            "document_sha256": "a" * 64,
                            "page_start": 1,
                            "page_end": 1,
                            "quote": "Le résultat net synthétique vaut 101 FCFA.",
                            "grade": 3,
                        }
                    ],
                }
            ],
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="G3 retrieval evaluation")
    parser.add_argument("--mode", choices=["fixtures", "real"], default="fixtures")
    parser.add_argument("--questions", default="data/evaluation/gold/questions.jsonl")
    parser.add_argument("--corpus-manifest", default="data/evaluation/corpus/manifest.json")
    parser.add_argument("--config", default="config/evaluation_g3.yaml")
    parser.add_argument("--output-dir", default="data/evaluation/runs/fixture_smoke")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--allow-model-download", action="store_true")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        output_dir = Path(args.output_dir)
        if args.mode == "fixtures":
            questions = build_fixture_questions()
            ranked = {
                questions[0].question: [
                    {"chunk_id": "SYNTH-E1", "evidence_id": "SYNTH-E1", "rank": 1, "score": 1.0,
                     "text": "Le résultat net synthétique vaut 101 FCFA."}
                ]
            }
            retrievers = {
                "bm25": FixtureRetriever(ranked),
                "dense": FixtureRetriever(ranked),
                "hybrid": FixtureRetriever(ranked),
            }
            snapshot = build_corpus_manifest(
                documents=[],
                embedding_models=["mini_lm_multilingual"],
                strategies=["recursive_fixed"],
            )
            snapshot["fixture_only"] = True
            runner = BenchmarkRunner(
                retrievers=retrievers,
                corpus_snapshot=snapshot,
                seed=args.seed,
                synthetic=True,
            )
            report = runner.run(
                questions,
                strategies=["recursive_fixed"],
                models=["mini_lm_multilingual"],
                methods=["bm25", "dense", "hybrid"],
                top_k=args.top_k,
            )
            report["synthetic"] = True
            report["mode"] = "fixtures"
        else:
            missing: list[str] = []
            if not args.allow_model_download:
                missing.append("real model downloads not requested")
            question_path = Path(args.questions)
            manifest_path = Path(args.corpus_manifest)
            if not question_path.is_file():
                missing.append(f"missing questions: {question_path}")
            else:
                questions = load_questions(question_path)
                verified = [q for q in questions if q.annotation_status == "verified"]
                if not verified:
                    missing.append("no verified annotations")
            if not manifest_path.is_file():
                missing.append(f"missing corpus manifest: {manifest_path}")
            else:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest.get("documents_count", 0) <= 0:
                    missing.append("corpus manifest contains no documents")
            if missing:
                report = {
                    "status": "REAL_BENCHMARK_NOT_READY",
                    "missing": missing,
                    "synthetic": False,
                }
                write_json_atomic(output_dir / "summary.json", report)
                write_markdown(output_dir / "report.md", report)
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 2
            raise RuntimeError(
                "The real benchmark runner requires verified corpus artifacts "
                "and real retriever adapters; no fabricated execution was performed"
            )

        write_json_atomic(output_dir / "summary.json", report)
        write_csv_atomic(
            output_dir / "per_query.csv",
            report.get("per_query", []),
        )
        write_markdown(output_dir / "report.md", report)
        print(json.dumps({
            "status": "success",
            "run_id": report["run_id"],
            "output_dir": str(output_dir),
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
