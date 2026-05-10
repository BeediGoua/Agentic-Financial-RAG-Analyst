from __future__ import annotations

import argparse

from app.embeddings.supervisor import EmbeddingSupervisor
from app.ingest.utils import parse_csv_filter, parse_year_filter


DEFAULT_MODELS = ["mini_lm_multilingual", "e5_small"]

DEFAULT_STRATEGIES = [
    "recursive_fixed",
    "page_aware",
    "section_aware",
]


def parse_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default

    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 5 - Génération des embeddings"
    )

    parser.add_argument("--companies", type=str, default=None)
    parser.add_argument("--years", type=str, default=None)

    parser.add_argument(
        "--models",
        type=str,
        default=None,
        help="Exemple: mini_lm_multilingual,e5_small",
    )

    parser.add_argument(
        "--strategies",
        type=str,
        default=None,
        help="Exemple: recursive_fixed,page_aware,section_aware",
    )

    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()

    companies = parse_csv_filter(args.companies)
    years = parse_year_filter(args.years)

    models = parse_list(args.models, DEFAULT_MODELS)
    strategies = parse_list(args.strategies, DEFAULT_STRATEGIES)

    supervisor = EmbeddingSupervisor()

    report = supervisor.run(
        models=models,
        strategies=strategies,
        companies=companies,
        years=years,
        force=args.force,
    )

    print("\nEMBEDDINGS TERMINÉS")
    print("=" * 60)
    print(f"Status global : {report['overall_status']}")
    print(f"Modèles       : {', '.join(report['models'])}")
    print(f"Stratégies    : {', '.join(report['strategies'])}")
    print(f"Entreprises   : {report['companies']}")
    print(f"Années        : {report['years']}")
    print(f"Rapport       : {report['report_path']}")
    print("-" * 60)

    for model_key, quality in report["model_quality"].items():
        print(
            f"{model_key} | {quality['status']} | "
            f"records={quality['total_records']} | "
            f"dims={quality['dimensions']} | "
            f"errors={quality['error_files']}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()


# python -m app.embeddings.run_embeddings --companies "ORANGE CI" --years "2025"