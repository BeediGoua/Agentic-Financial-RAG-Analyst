from __future__ import annotations

import argparse
from pathlib import Path

from app.generation.supervisor import GenerationSupervisor


def find_latest_reranking_run(
    reranking_dir: str = "data/reranking/runs",
) -> Path | None:
    path = Path(reranking_dir)

    if not path.exists():
        return None

    files = sorted(
        path.glob("reranking_run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return files[0] if files else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 9 - Generation contrôlée"
    )

    parser.add_argument(
        "--reranking-run",
        type=str,
        default=None,
    )

    parser.add_argument(
        "--provider",
        type=str,
        default="ollama",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="qwen2.5:7b",
    )

    args = parser.parse_args()

    reranking_run = args.reranking_run

    if reranking_run is None:
        latest = find_latest_reranking_run()

        if latest is None:
            raise FileNotFoundError(
                "No reranking run found."
            )

        reranking_run = str(latest)

    supervisor = GenerationSupervisor()

    report = supervisor.run(
        reranking_run_path=reranking_run,
        provider=args.provider,
        model_name=args.model,
    )

    print("\nGENERATION TERMINÉE")
    print("=" * 60)

    generated = report["generated_answer"]

    print(f"Status            : {generated['status']}")
    print(f"Provider          : {generated['provider']}")
    print(f"Model             : {generated['model']}")
    print(f"Used chunks       : {generated['used_chunks']}")
    print("-" * 60)

    print("QUESTION")
    print(generated["query"])
    print("-" * 60)

    print("ANSWER")
    print(generated["answer"])
    print("-" * 60)

    print("CITATIONS")

    for citation in generated["citations"]:
        print(
            f"{citation['company']} | "
            f"page={citation['page_start']} | "
            f"section={citation['section']}"
        )

    print("-" * 60)

    print(f"Report: {report['report_path']}")


if __name__ == "__main__":
    main()
