from __future__ import annotations

import argparse

from app.vector_db.supervisor import VectorDBSupervisor


def parse_list(value: str | None) -> list[str] | None:
    if not value:
        return None

    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 6 - Construction des index FAISS"
    )

    parser.add_argument(
        "--strategies",
        type=str,
        default=None,
        help="Exemple: recursive_fixed,page_aware,section_aware",
    )

    parser.add_argument(
        "--models",
        type=str,
        default=None,
        help="Exemple: mini_lm_multilingual,e5_small",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Reconstruit les index même s'ils existent déjà.",
    )

    args = parser.parse_args()

    strategies = parse_list(args.strategies)
    models = parse_list(args.models)

    supervisor = VectorDBSupervisor()

    report = supervisor.run(
        strategies=strategies,
        models=models,
        force=args.force,
    )

    print("\nVECTOR DB INDEXING TERMINÉ")
    print("=" * 60)
    print(f"Status global : {report['overall_status']}")
    print(f"Stratégies    : {report['strategies']}")
    print(f"Modèles       : {report['models']}")
    print(f"Rapport       : {report['report_path']}")
    print("-" * 60)

    q = report["quality"]

    print(f"Fichiers traités : {q['total_files']}")
    print(f"Succès           : {q['success_files']}")
    print(f"Vides            : {q['empty_files']}")
    print(f"Erreurs          : {q['error_files']}")
    print(f"Vecteurs indexés : {q['total_vectors']}")
    print(f"Dimensions       : {q['dimensions']}")
    print("-" * 60)

    print("Index créés :")
    for pair in q["indexed_pairs"]:
        print(f"- {pair}")

    print("=" * 60)

    if report["overall_status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
