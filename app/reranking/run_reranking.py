from __future__ import annotations

import argparse
from pathlib import Path

from app.reranking.supervisor import RerankingSupervisor


def find_latest_retrieval_run(
    retrieval_runs_dir: str = "data/retrieval/runs",
) -> Path | None:
    runs_dir = Path(retrieval_runs_dir)

    if not runs_dir.exists():
        return None

    files = sorted(
        runs_dir.glob("retrieval_run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return files[0] if files else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 8 - Reranking des résultats retrieval"
    )

    parser.add_argument(
        "--retrieval-run",
        type=str,
        default=None,
        help="Chemin vers un fichier data/retrieval/runs/retrieval_run_*.json",
    )

    parser.add_argument(
        "--model",
        type=str,
        default="mini_cross_encoder",
        help="mini_cross_encoder ou tiny_cross_encoder",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Nombre de chunks finaux après reranking.",
    )

    args = parser.parse_args()

    retrieval_run_path = args.retrieval_run

    if retrieval_run_path is None:
        latest = find_latest_retrieval_run()

        if latest is None:
            raise FileNotFoundError(
                "Aucun retrieval_run_*.json trouvé dans data/retrieval/runs. "
                "Lance d'abord la phase 7."
            )

        retrieval_run_path = str(latest)

    supervisor = RerankingSupervisor()

    report = supervisor.run(
        retrieval_run_path=retrieval_run_path,
        reranking_model=args.model,
        top_k=args.top_k,
    )

    print("\nRERANKING TERMINÉ")
    print("=" * 60)
    print(f"Status global     : {report['overall_status']}")
    print(f"Retrieval run     : {report['retrieval_run_path']}")
    print(f"Reranking model   : {report['reranking_model']}")
    print(f"Top K             : {report['top_k']}")
    print(f"Rapport           : {report['report_path']}")
    print("-" * 60)

    q = report["quality"]

    print(f"Runs traités      : {q['total_runs']}")
    print(f"Succès            : {q['success_runs']}")
    print(f"Vides             : {q['empty_runs']}")
    print(f"Erreurs           : {q['error_runs']}")
    print(f"Résultats finaux  : {q['total_reranked_results']}")
    print("-" * 60)

    for run in report["runs"]:
        print(
            f"{run['retrieval_method']} | "
            f"{run['chunking_strategy']} | "
            f"{run['embedding_model']} | "
            f"{run['status']} | "
            f"results={run['reranked_results_count']}"
        )

        for result in run.get("results", [])[:3]:
            text = result.get("text", "").replace("\n", " ")
            print(
                f"  #{result['rank']} "
                f"rerank_score={result['reranking_score']:.4f} "
                f"old_rank={result.get('original_rank')} "
                f"page={result.get('page_start')} "
                f"section={result.get('section')} "
                f"text={text[:180]}..."
            )

        print("-" * 60)

    if report["overall_status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()