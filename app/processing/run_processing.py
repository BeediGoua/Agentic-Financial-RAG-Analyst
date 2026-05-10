from __future__ import annotations

import argparse

from app.ingest.utils import parse_csv_filter, parse_year_filter
from app.processing.metadata_enrichment import MetadataEnrichmentAgent
from app.processing.processing_quality import ProcessingQualityAgent
from app.processing.processing_supervisor import ProcessingSupervisorAgent
from app.processing.table_cleaning import TableCleaningAgent
from app.processing.text_cleaning import TextCleaningAgent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 3 - Nettoyage + Metadata Enrichment"
    )

    parser.add_argument(
        "--companies",
        type=str,
        default=None,
        help='Entreprises séparées par virgule. Exemple: "ORANGE CI,SONATEL"',
    )

    parser.add_argument(
        "--years",
        type=str,
        default=None,
        help='Années séparées par virgule. Exemple: "2024,2025"',
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Recrée les fichiers processed même s'ils existent déjà.",
    )

    args = parser.parse_args()

    companies = parse_csv_filter(args.companies)
    years = parse_year_filter(args.years)

    text_agent = TextCleaningAgent()
    table_agent = TableCleaningAgent()
    metadata_agent = MetadataEnrichmentAgent()
    quality_agent = ProcessingQualityAgent()

    supervisor = ProcessingSupervisorAgent(
        text_agent=text_agent,
        table_agent=table_agent,
        metadata_agent=metadata_agent,
        quality_agent=quality_agent,
    )

    report = supervisor.run(
        companies=companies,
        years=years,
        force=args.force,
    )

    print("\n Processing terminé!")
    print("=" * 60)
    print(f"État général        : {report['overall_status']}")
    print(f"Fichiers texte      : {report['text_quality']['success_files']}")
    print(f"Pages nettoyées     : {report['text_quality']['total_records']}")
    print(f"Fichiers tables     : {report['table_quality']['success_files']}")
    print(f"Tables nettoyées    : {report['table_quality']['total_records']}")
    print(f"Complétude metadata : {report['metadata_quality']['completeness_rate']:.1%}")
    print(f"Rapport qualité     : {report['report_path']}")
    print("=" * 60)

    if report["overall_status"] == "FAIL":
        print("Décision : NE PAS passer à l'étape suivante.")
    elif report["overall_status"] == "WARNING":
        print("Décision : vérifier les warnings avant de continuer.")
    else:
        print("Décision : processing suffisant pour passer à la phase suivante.")


if __name__ == "__main__":
    main()