from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

import yaml

from app.evaluation.corpus import (
    build_corpus_manifest,
    build_document_registry,
    sha256_file,
)
from app.evaluation.qrels import load_questions
from app.evaluation.reporting import (
    write_csv_atomic,
    write_json_atomic,
    write_markdown,
)
from app.evaluation.runner import BenchmarkRunner, FixtureRetriever
from app.evaluation.schemas import GoldQuestion
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.dense import DenseRetriever
from app.retrieval.hybrid import HybridRetriever


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


def validate_config(config: dict) -> dict:
    benchmark = config.get("benchmark")
    retrieval = config.get("retrieval")
    if not isinstance(benchmark, dict) or not isinstance(retrieval, dict):
        raise ValueError("Invalid G3 config: benchmark and retrieval sections are required")
    k_values = benchmark.get("k_values")
    splits = benchmark.get("splits")
    strategies = retrieval.get("strategies")
    methods = retrieval.get("methods")
    models = retrieval.get("embedding_models")
    if not isinstance(k_values, list) or not k_values or any(type(k) is not int or k < 1 for k in k_values):
        raise ValueError("Invalid k_values")
    if not isinstance(splits, list) or not set(splits).issubset({"dev", "test"}):
        raise ValueError("Invalid benchmark splits")
    if not isinstance(strategies, list) or not strategies:
        raise ValueError("Invalid retrieval strategies")
    if not isinstance(methods, list) or not set(methods).issubset({"bm25", "dense", "hybrid"}):
        raise ValueError("Invalid retrieval methods")
    if not isinstance(models, list) or not models:
        raise ValueError("Invalid embedding_models")
    return config


def resolve_benchmark_top_k(config: dict, cli_top_k: int | None) -> tuple[int, list[int]]:
    """Keep every reported @K within the effective retrieval cutoff."""
    k_values = list(config["benchmark"]["k_values"])
    if cli_top_k is not None:
        if cli_top_k <= 0:
            raise ValueError("--top-k must be a positive integer")
        effective_k_values = sorted({
            k for k in k_values
            if k <= cli_top_k
        } | {cli_top_k})
        return cli_top_k, effective_k_values
    top_k = max(k_values)
    return top_k, sorted(set(k_values))


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
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Override YAML k_values for the retrieval cutoff (YAML k_values remain reported)",
    )
    parser.add_argument("--allow-model-download", action="store_true")
    parser.add_argument("--chunks-dir", default="data/chunks")
    parser.add_argument("--vector-db-dir", default="data/vector_db/faiss")
    args = parser.parse_args()

    try:
        config = validate_config(load_config(args.config))
        top_k, k_values = resolve_benchmark_top_k(config, args.top_k)
        output_dir = Path(args.output_dir)
        if args.mode == "fixtures":
            questions = build_fixture_questions()
            ranked = {
                questions[0].question: [
                    {"chunk_id": "recursive_fixed_abc123", "rank": 1, "score": 1.0,
                     "document_sha256": "a" * 64, "source_pdf": "synthetic_report.pdf",
                     "page_start": 1, "page_end": 1,
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
                strategies=config["retrieval"]["strategies"],
                models=config["retrieval"]["embedding_models"],
                methods=config["retrieval"]["methods"],
                top_k=top_k,
                relevant_threshold=int(config["benchmark"].get("relevance_threshold", 2)),
                k_values=k_values,
            )
            report["synthetic"] = True
            report["mode"] = "fixtures"
        else:
            missing: list[str] = []
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
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:
                    missing.append(f"invalid corpus manifest: {exc}")
                    manifest = {}
                if manifest.get("documents_count", 0) <= 0:
                    missing.append("corpus manifest contains no documents")
                if manifest.get("status") == "template_only":
                    missing.append("corpus snapshot is template_only")
                document_hashes = manifest.get("document_hashes", [])
                if document_hashes and any(len(str(value)) != 64 for value in document_hashes):
                    missing.append("corpus manifest contains invalid document SHA-256")
                document_records = manifest.get("document_records", [])
                if isinstance(document_records, list):
                    if len(document_records) != int(manifest.get("documents_count", 0)):
                        missing.append("corpus manifest document records do not match documents_count")
                for record in manifest.get("document_records", []):
                    source_pdf = record.get("source_pdf")
                    expected_sha = str(record.get("document_sha256") or "").lower()
                    if not source_pdf or not Path(source_pdf).is_file():
                        missing.append(f"missing document artifact: {source_pdf}")
                        continue
                    actual_sha = sha256_file(source_pdf)
                    if not expected_sha or actual_sha != expected_sha:
                        missing.append(f"document SHA-256 mismatch: {source_pdf}")
            if 'manifest' in locals() and isinstance(manifest, dict):
                registry = build_document_registry([], corpus_manifest=manifest)
                known_hashes = {
                    str(value).lower()
                    for value in manifest.get("document_hashes", [])
                } | set(registry.get("records", {}).values())
                for question in (questions if 'questions' in locals() else []):
                    if question.annotation_status != "verified":
                        continue
                    for evidence_group in question.evidence_groups:
                        for alternative in evidence_group.alternatives:
                            if alternative.document_sha256 not in known_hashes:
                                missing.append(
                                    f"evidence provenance unavailable: "
                                    f"{alternative.evidence_id}"
                                )
                if registry.get("ambiguous_paths"):
                    missing.append(
                        "ambiguous document paths: "
                        + ", ".join(registry["ambiguous_paths"])
                    )
            if missing:
                report = {
                    "status": "REAL_BENCHMARK_NOT_READY",
                    "missing": missing,
                    "synthetic": False,
                    "run_id": uuid4().hex,
                }
                write_json_atomic(output_dir / "summary.json", report)
                write_markdown(output_dir / "report.md", report)
                print(json.dumps(report, indent=2, ensure_ascii=False))
                return 2
            bm25 = BM25Retriever(chunks_dir=args.chunks_dir)
            dense = DenseRetriever(
                vector_db_dir=args.vector_db_dir,
                allow_model_download=args.allow_model_download,
            )
            hybrid = HybridRetriever(
                dense_retriever=dense,
                bm25_retriever=bm25,
            )
            retrievers = {"bm25": bm25, "dense": dense, "hybrid": hybrid}
            runner = BenchmarkRunner(
                retrievers=retrievers,
                corpus_snapshot=manifest,
                seed=args.seed,
                synthetic=False,
                document_registry=registry,
            )
            report = runner.run(
                questions,
                strategies=config["retrieval"]["strategies"],
                models=config["retrieval"]["embedding_models"],
                methods=config["retrieval"]["methods"],
                top_k=top_k,
                relevant_threshold=int(config["benchmark"].get("relevance_threshold", 2)),
                k_values=k_values,
            )
            report["synthetic"] = False
            report["mode"] = "real"
            report["allow_model_download"] = bool(args.allow_model_download)

        report["counts"]["by_split"] = {
            split: sum(1 for row in report.get("per_query", []) if row.get("split") == split)
            for split in ("dev", "test")
        }

        run_output_dir = output_dir / str(report["run_id"])
        write_json_atomic(run_output_dir / "summary.json", report)
        write_csv_atomic(
            run_output_dir / "per_query.csv",
            report.get("per_query", []),
        )
        write_markdown(run_output_dir / "report.md", report)
        print(json.dumps({
            "status": "success",
            "run_id": report["run_id"],
            "output_dir": str(run_output_dir),
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
