from __future__ import annotations

import argparse

from app.extraction.extraction_quality_agent import ExtractionQualityAgent
from app.extraction.extraction_supervisor import ExtractionSupervisorAgent
from app.extraction.pdf_text_agent import PDFTextExtractionAgent
from app.extraction.table_extraction_agent import TableExtractionAgent
from app.ingest.utils import parse_csv_filter, parse_year_filter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 2 - Extraction texte + tables depuis les PDF RAW"
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
        help="Recrée les fichiers extraits même s'ils existent déjà.",
    )

    parser.add_argument(
        "--disable-ocr",
        action="store_true",
        help="Désactive OCR fallback.",
    )

    args = parser.parse_args()

    companies = parse_csv_filter(args.companies)
    years = parse_year_filter(args.years)

    text_agent = PDFTextExtractionAgent(
        enable_ocr=not args.disable_ocr,
    )

    table_agent = TableExtractionAgent()
    quality_agent = ExtractionQualityAgent()

    supervisor = ExtractionSupervisorAgent(
        text_agent=text_agent,
        table_agent=table_agent,
        quality_agent=quality_agent,
    )

    report = supervisor.run(
        companies=companies,
        years=years,
        force=args.force,
    )

    print("\n✅ Extraction terminée!")
    print("=" * 60)
    print(f"État général       : {report['overall_status']}")
    print(f"Fichiers texte     : {report['text_quality']['success_files']}")
    print(f"Pages extraites    : {report['text_quality']['total_pages']}")
    print(f"Pages vides        : {report['text_quality']['empty_pages']}")
    print(f"Pages OCR          : {report['text_quality']['ocr_pages']}")
    print(f"Pages faible qualité: {report['text_quality']['low_quality_pages']}")
    print(f"Taux pages vides   : {report['text_quality']['empty_page_rate']:.1%}")
    print(f"Taux OCR           : {report['text_quality']['ocr_rate']:.1%}")
    print(f"Fichiers tables    : {report['table_quality']['success_files']}")
    print(f"Tables extraites   : {report['table_quality']['total_tables']}")
    print(f"Rapport qualité    : {report['quality_report_path']}")
    print("=" * 60)


if __name__ == "__main__":
    main()