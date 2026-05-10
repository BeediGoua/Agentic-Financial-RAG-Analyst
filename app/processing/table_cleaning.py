from __future__ import annotations

import json
import re
from pathlib import Path

from app.processing.schemas import CleanedTable


class TableCleaningAgent:
    """
    Agent déterministe.
    Rôle :
    - lire les tables extraites ;
    - nettoyer les cellules ;
    - supprimer les lignes entièrement vides ;
    - conserver les métadonnées.
    """

    def __init__(
        self,
        extracted_tables_dir: str = "data/extracted/tables",
        processed_tables_dir: str = "data/processed/tables",
    ):
        self.extracted_tables_dir = Path(extracted_tables_dir)
        self.processed_tables_dir = Path(processed_tables_dir)
        self.processed_tables_dir.mkdir(parents=True, exist_ok=True)

    def clean_cell(self, cell: str | None) -> str | None:
        if cell is None:
            return None

        cell = str(cell)
        cell = cell.replace("\x00", " ")
        cell = cell.replace("\u00a0", " ")
        cell = cell.replace("\n", " ")
        cell = re.sub(r"\s+", " ", cell)

        cleaned = cell.strip()
        return cleaned if cleaned else None

    def clean_rows(self, rows: list[list[str | None]]) -> list[list[str | None]]:
        cleaned_rows = []

        for row in rows:
            cleaned_row = [self.clean_cell(cell) for cell in row]

            if any(cell is not None for cell in cleaned_row):
                cleaned_rows.append(cleaned_row)

        return cleaned_rows

    def build_output_path(self, input_path: Path) -> Path:
        relative = input_path.relative_to(self.extracted_tables_dir)
        output_path = self.processed_tables_dir / relative.with_suffix(".clean_tables.jsonl")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def matches_filter(
        self,
        record: dict,
        companies: list[str] | None,
        years: list[str] | None,
    ) -> bool:
        company = str(record.get("company") or "").lower()
        year = str(record.get("year") or "")

        if companies:
            if not any(c.lower() in company for c in companies):
                return False

        if years:
            if year not in years:
                return False

        return True

    def clean_tables_file(
        self,
        input_path: Path,
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> dict:
        output_path = self.build_output_path(input_path)

        if output_path.exists() and not force:
            return {
                "status": "already_exists",
                "input_path": str(input_path),
                "output_path": str(output_path),
            }

        records_count = 0

        try:
            with input_path.open("r", encoding="utf-8") as f_in, output_path.open(
                "w",
                encoding="utf-8",
            ) as f_out:
                for line in f_in:
                    if not line.strip():
                        continue

                    record = json.loads(line)

                    if not self.matches_filter(record, companies, years):
                        continue

                    rows = record.get("rows") or []
                    cleaned_rows = self.clean_rows(rows)

                    column_count = max([len(row) for row in cleaned_rows], default=0)

                    cleaned_table = CleanedTable(
                        source_pdf=record.get("source_pdf"),
                        source_url=record.get("source_url"),
                        company=record.get("company"),
                        year=str(record.get("year")) if record.get("year") else None,
                        document_type=record.get("document_type"),
                        language=record.get("language"),
                        page_number=int(record.get("page_number")),
                        table_index=int(record.get("table_index")),
                        rows=rows,
                        cleaned_rows=cleaned_rows,
                        row_count=len(cleaned_rows),
                        column_count=column_count,
                        content_type="table",
                    )

                    f_out.write(cleaned_table.model_dump_json() + "\n")
                    records_count += 1

            return {
                "status": "success",
                "input_path": str(input_path),
                "output_path": str(output_path),
                "records_count": records_count,
            }

        except Exception as e:
            return {
                "status": "error",
                "input_path": str(input_path),
                "error": str(e),
            }

    def run(
        self,
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> list[dict]:
        files = list(self.extracted_tables_dir.rglob("*.tables.jsonl"))
        results = []

        for input_path in files:
            results.append(
                self.clean_tables_file(
                    input_path=input_path,
                    companies=companies,
                    years=years,
                    force=force,
                )
            )

        return results