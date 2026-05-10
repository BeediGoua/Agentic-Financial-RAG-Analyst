from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.ingest.utils import parse_csv_filter, parse_year_filter


class ExtractionAuditAgent:
    """
    Agent déterministe.
    Rôle :
    - lire les sorties d'extraction ;
    - contrôler la qualité texte/tables ;
    - produire un rapport d'audit avant de passer à l'étape suivante.
    """

    def __init__(
        self,
        pages_dir: str = "data/extracted/pages",
        tables_dir: str = "data/extracted/tables",
        audit_dir: str = "data/extracted/quality",
    ):
        self.pages_dir = Path(pages_dir)
        self.tables_dir = Path(tables_dir)
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

    def load_jsonl(self, path: Path) -> list[dict]:
        rows = []

        if not path.exists():
            return rows

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

        return rows

    def matches_filter(
        self,
        row: dict,
        companies: list[str] | None,
        years: list[str] | None,
    ) -> bool:
        company = str(row.get("company") or "").lower()
        year = str(row.get("year") or "")

        if companies:
            if not any(c.lower() in company for c in companies):
                return False

        if years:
            if year not in years:
                return False

        return True

    def audit_pages(
        self,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> dict:
        page_files = list(self.pages_dir.rglob("*.pages.jsonl"))

        total_pages = 0
        empty_pages = 0
        low_quality_pages = 0
        ocr_pages = 0
        documents = set()
        examples = []

        for page_file in page_files:
            pages = self.load_jsonl(page_file)

            for page in pages:
                if not self.matches_filter(page, companies, years):
                    continue

                total_pages += 1
                documents.add(page.get("source_pdf"))

                word_count = int(page.get("word_count") or 0)
                quality_status = page.get("quality_status")
                ocr_used = bool(page.get("ocr_used"))

                if word_count == 0:
                    empty_pages += 1

                if quality_status in {
                    "low_text_quality",
                    "low_text_quality_after_ocr",
                    "ocr_failed",
                }:
                    low_quality_pages += 1

                if ocr_used:
                    ocr_pages += 1

                if len(examples) < 5 and word_count > 20:
                    examples.append(
                        {
                            "source_pdf": page.get("source_pdf"),
                            "company": page.get("company"),
                            "year": page.get("year"),
                            "page_number": page.get("page_number"),
                            "word_count": word_count,
                            "quality_status": quality_status,
                            "sample_text": str(page.get("text") or "")[:500],
                        }
                    )

        empty_rate = empty_pages / total_pages if total_pages else 0.0
        low_quality_rate = low_quality_pages / total_pages if total_pages else 0.0
        ocr_rate = ocr_pages / total_pages if total_pages else 0.0

        status = "PASS"

        if total_pages == 0:
            status = "FAIL"
        elif empty_rate > 0.2:
            status = "FAIL"
        elif low_quality_rate > 0.4:
            status = "WARNING"

        return {
            "status": status,
            "documents_count": len(documents),
            "total_pages": total_pages,
            "empty_pages": empty_pages,
            "low_quality_pages": low_quality_pages,
            "ocr_pages": ocr_pages,
            "empty_rate": empty_rate,
            "low_quality_rate": low_quality_rate,
            "ocr_rate": ocr_rate,
            "examples": examples,
        }

    def audit_tables(
        self,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> dict:
        table_files = list(self.tables_dir.rglob("*.tables.jsonl"))

        total_tables = 0
        total_rows = 0
        total_columns = 0
        documents = set()
        examples = []

        for table_file in table_files:
            tables = self.load_jsonl(table_file)

            for table in tables:
                if not self.matches_filter(table, companies, years):
                    continue

                total_tables += 1
                documents.add(table.get("source_pdf"))

                row_count = int(table.get("row_count") or 0)
                column_count = int(table.get("column_count") or 0)

                total_rows += row_count
                total_columns += column_count

                if len(examples) < 5 and row_count > 1 and column_count > 1:
                    examples.append(
                        {
                            "source_pdf": table.get("source_pdf"),
                            "company": table.get("company"),
                            "year": table.get("year"),
                            "page_number": table.get("page_number"),
                            "row_count": row_count,
                            "column_count": column_count,
                            "sample_rows": table.get("rows", [])[:5],
                        }
                    )

        avg_rows = total_rows / total_tables if total_tables else 0.0
        avg_columns = total_columns / total_tables if total_tables else 0.0

        status = "PASS"

        if total_tables == 0:
            status = "WARNING"

        return {
            "status": status,
            "documents_count": len(documents),
            "total_tables": total_tables,
            "avg_rows": avg_rows,
            "avg_columns": avg_columns,
            "examples": examples,
        }

    def run(
        self,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> dict:
        pages_audit = self.audit_pages(companies=companies, years=years)
        tables_audit = self.audit_tables(companies=companies, years=years)

        overall_status = "PASS"

        if pages_audit["status"] == "FAIL":
            overall_status = "FAIL"
        elif pages_audit["status"] == "WARNING" or tables_audit["status"] == "WARNING":
            overall_status = "WARNING"

        report = {
            "overall_status": overall_status,
            "companies": companies or "all",
            "years": years or "all",
            "pages_audit": pages_audit,
            "tables_audit": tables_audit,
        }

        output_path = self.audit_dir / "latest_extraction_audit.json"
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        report["audit_path"] = str(output_path)

        return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit qualité des sorties d'extraction texte + tables"
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

    args = parser.parse_args()

    companies = parse_csv_filter(args.companies)
    years = parse_year_filter(args.years)

    audit_agent = ExtractionAuditAgent()
    report = audit_agent.run(companies=companies, years=years)

    print("\nAUDIT EXTRACTION")
    print("=" * 60)
    print(f"Status global       : {report['overall_status']}")
    print(f"Entreprises         : {report['companies']}")
    print(f"Années              : {report['years']}")
    print("-" * 60)
    print(f"Documents texte     : {report['pages_audit']['documents_count']}")
    print(f"Pages totales       : {report['pages_audit']['total_pages']}")
    print(f"Pages vides         : {report['pages_audit']['empty_pages']}")
    print(f"Pages faible qualité: {report['pages_audit']['low_quality_pages']}")
    print(f"Pages OCR           : {report['pages_audit']['ocr_pages']}")
    print(f"Taux pages vides    : {report['pages_audit']['empty_rate']:.1%}")
    print(f"Taux faible qualité : {report['pages_audit']['low_quality_rate']:.1%}")
    print("-" * 60)
    print(f"Documents tables    : {report['tables_audit']['documents_count']}")
    print(f"Tables totales      : {report['tables_audit']['total_tables']}")
    print(f"Lignes moyennes     : {report['tables_audit']['avg_rows']:.1f}")
    print(f"Colonnes moyennes   : {report['tables_audit']['avg_columns']:.1f}")
    print("-" * 60)
    print(f"Rapport audit       : {report['audit_path']}")
    print("=" * 60)

    if report["overall_status"] == "FAIL":
        print("\nDécision : NE PAS passer à l'étape suivante.")
    elif report["overall_status"] == "WARNING":
        print("\nDécision : vérifier manuellement quelques exemples avant de continuer.")
    else:
        print("\nDécision : extraction suffisante pour passer à l'étape suivante.")


if __name__ == "__main__":
    main()

# python -m app.extraction.extraction_audit --companies "ORANGE CI" --years "2025"