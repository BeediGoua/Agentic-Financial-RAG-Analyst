from __future__ import annotations

import argparse

from app.chunking.supervisor import ChunkingSupervisor
from app.ingest.utils import parse_csv_filter, parse_year_filter


DEFAULT_STRATEGIES = [
    "recursive_fixed",
    "page_aware",
    "section_aware",
]


ALL_STRATEGIES = [
    "recursive_fixed",
    "page_aware",
    "section_aware",
    "table_aware",
    "semantic",
    "markdown_aware",
    "hierarchical",
]


def parse_strategies(value: str | None, all_flag: bool = False) -> list[str]:
    if all_flag:
        return ALL_STRATEGIES

    if not value:
        return DEFAULT_STRATEGIES

    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 4 - Chunking multi-stratégies"
    )

    parser.add_argument("--companies", type=str, default=None)
    parser.add_argument("--years", type=str, default=None)
    parser.add_argument("--strategies", type=str, default=None)
    parser.add_argument("--all-strategies", action="store_true")
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()

    companies = parse_csv_filter(args.companies)
    years = parse_year_filter(args.years)
    strategies = parse_strategies(args.strategies, args.all_strategies)

    supervisor = ChunkingSupervisor()

    report = supervisor.run(
        strategies=strategies,
        companies=companies,
        years=years,
        force=args.force,
    )

    print("\nCHUNKING TERMINÉ")
    print("=" * 60)
    print(f"Status global : {report['overall_status']}")
    print(f"Stratégies    : {', '.join(report['strategies'])}")
    print(f"Entreprises   : {report['companies']}")
    print(f"Années        : {report['years']}")
    print(f"Rapport       : {report['report_path']}")
    print("-" * 60)

    for strategy, quality in report["strategy_quality"].items():
        print(
            f"{strategy} | {quality['status']} | "
            f"chunks={quality['total_chunks']} | "
            f"errors={quality['errors']}"
        )

    print("=" * 60)


if __name__ == "__main__":
    main()