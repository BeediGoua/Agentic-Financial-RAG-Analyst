from __future__ import annotations

import argparse

from app.ingest.utils import parse_csv_filter, parse_year_filter
from app.retrieval.supervisor import RetrievalSupervisor


DEFAULT_METHODS = ["dense", "bm25", "hybrid"]
DEFAULT_STRATEGIES = ["recursive_fixed", "page_aware", "section_aware"]
DEFAULT_MODELS = ["mini_lm_multilingual"]


def parse_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default

    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 7 - Retrieval dense, BM25 et hybride"
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Question utilisateur ou requête de recherche.",
    )

    parser.add_argument("--companies", type=str, default=None)
    parser.add_argument("--years", type=str, default=None)

    parser.add_argument(
        "--methods",
        type=str,
        default=None,
        help="dense,bm25,hybrid",
    )

    parser.add_argument(
        "--strategies",
        type=str,
        default=None,
        help="recursive_fixed,page_aware,section_aware",
    )

    parser.add_argument(
        "--models",
        type=str,
        default=None,
        help="mini_lm_multilingual,e5_small",
    )

    parser.add_argument("--top-k", type=int, default=5)

    args = parser.parse_args()

    companies = parse_csv_filter(args.companies)
    years = parse_year_filter(args.years)

    methods = parse_list(args.methods, DEFAULT_METHODS)
    strategies = parse_list(args.strategies, DEFAULT_STRATEGIES)
    models = parse_list(args.models, DEFAULT_MODELS)

    supervisor = RetrievalSupervisor()

    report = supervisor.run(
        query=args.query,
        methods=methods,
        strategies=strategies,
        models=models,
        top_k=args.top_k,
        companies=companies,
        years=years,
    )

    print("\nRETRIEVAL TERMINÉ")
    print("=" * 60)
    print(f"Status global : {report['overall_status']}")
    print(f"Query         : {report['query']}")
    print(f"Methods       : {', '.join(report['methods'])}")
    print(f"Strategies    : {', '.join(report['strategies'])}")
    print(f"Models        : {', '.join(report['models'])}")
    print(f"Top K         : {report['top_k']}")
    print(f"Rapport       : {report['report_path']}")
    print("-" * 60)

    for run in report["runs"]:
        print(
            f"{run['method']} | {run['strategy']} | {run['model']} | "
            f"{run['status']} | results={run['results_count']}"
        )

        for result in run.get("results", [])[:3]:
            text = result.get("text", "").replace("\n", " ")
            print(
                f"  #{result['rank']} score={result['score']:.4f} "
                f"page={result.get('page_start')} "
                f"section={result.get('section')} "
                f"text={text[:180]}..."
            )

        print("-" * 60)

    if report["overall_status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()