from __future__ import annotations

import argparse
import json

from app.ingest.brvm_source import BRVMSourceAgent
from app.ingest.quality import QualityAgent
from app.ingest.storage import StorageAgent
from app.ingest.supervisor import SupervisorAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Download BRVM financial reports by company and year.")

    parser.add_argument(
        "--companies",
        type=str,
        default="",
        help='Comma-separated company names. Example: "CIE CI,SONATEL". Empty means all companies.',
    )
    parser.add_argument(
        "--years",
        type=str,
        default="",
        help='Comma-separated years. Example: "2023,2024". Empty means all years.',
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=2,  # Réduit de 5 à 2 pour être plus rapide
        help="Number of BRVM listing pages to scan.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of discovered reports to process.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed progress information.",
    )
    parser.add_argument(
        "--root-dir",
        type=str,
        default="data/raw/reports",
        help="Root directory for downloaded reports.",
    )

    args = parser.parse_args()

    source_agent = BRVMSourceAgent(
        companies=args.companies,
        years=args.years,
        max_pages=args.max_pages,
    )
    quality_agent = QualityAgent()
    storage_agent = StorageAgent(root_dir=args.root_dir)

    supervisor = SupervisorAgent(
        source_agent=source_agent,
        quality_agent=quality_agent,
        storage_agent=storage_agent,
        verbose=args.verbose,
    )

    summary = supervisor.run(limit=args.limit)

    print("Résumé ingestion")
    print(f"Entreprises demandées : {args.companies or 'toutes'}")
    print(f"Années demandées      : {args.years or 'toutes'}")
    print(f"Rapports détectés     : {summary['discovered_reports']}")
    print(f"Rapports traités      : {summary['processed_reports']}")
    print(f"Succès                : {summary['success']}")
    print(f"Doublons              : {summary['duplicates']}")
    print(f"PDF invalides         : {summary['invalid_pdfs']}")
    print(f"Erreurs               : {summary['errors']}")
    print(f"Taux de succès        : {summary['success_rate']*100:.1f}%")
    print(f"État général          : {summary['overall_status']}")
    print(f"Log                   : {summary['log_path']}")
    print(f"Health Report         : {summary['health_report_path']}")

    print("\nDétail JSON")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
