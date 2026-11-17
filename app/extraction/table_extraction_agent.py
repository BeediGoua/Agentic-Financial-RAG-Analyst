from __future__ import annotations

import json
from pathlib import Path

import fitz
import pdfplumber

from app.core.atomic import atomic_text_writer
from app.extraction.schemas import ExtractedTable


class TableExtractionAgent:
    """
    Agent déterministe.
    Rôle : extraire les tableaux simples avec pdfplumber.
    """

    def __init__(
        self,
        raw_dir: str = "data/raw/reports",
        output_dir: str = "data/extracted/tables",
    ):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_manifest(self, pdf_path: Path) -> dict:
        manifest_path = pdf_path.with_suffix(".manifest.json")

        if not manifest_path.exists():
            return {}

        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid PDF manifest {manifest_path}: {exc}") from exc

    def build_output_path(self, pdf_path: Path) -> Path:
        relative = pdf_path.relative_to(self.raw_dir)
        output_path = self.output_dir / relative.with_suffix(".tables.jsonl")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def extract_tables(self, pdf_path: Path, force: bool = False) -> dict:
        output_path = self.build_output_path(pdf_path)

        if output_path.exists() and not force:
            try:
                if output_path.stat().st_mtime >= pdf_path.stat().st_mtime:
                    with fitz.open(pdf_path) as cached_pdf:
                        if (
                            not cached_pdf.is_pdf
                            or cached_pdf.needs_pass
                            or cached_pdf.page_count < 1
                        ):
                            raise ValueError("Source PDF is encrypted or empty")
                        page_count = cached_pdf.page_count
                    rows = [
                        json.loads(line)
                        for line in output_path.read_text(encoding="utf-8").splitlines()
                        if line.strip()
                    ]
                    if all(
                        isinstance(row, dict)
                        and 1 <= int(row["page_number"]) <= page_count
                        and isinstance(row["rows"], list)
                        and int(row["row_count"]) == len(row["rows"])
                        and int(row["column_count"]) >= 0
                        for row in rows
                    ):
                        return {
                            "status": "already_exists",
                            "source_pdf": str(pdf_path),
                            "tables_output": str(output_path),
                            "tables_count": len(rows),
                        }
            except (OSError, ValueError, KeyError, TypeError, fitz.FileDataError):
                pass

        manifest = self.load_manifest(pdf_path)
        tables_count = 0

        try:
            with fitz.open(pdf_path) as source_pdf:
                if (
                    not source_pdf.is_pdf
                    or source_pdf.needs_pass
                    or source_pdf.page_count < 1
                ):
                    raise ValueError("PDF is encrypted or contains no pages")
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    raise ValueError("PDF contains no pages")
                with atomic_text_writer(output_path) as output:
                    for page_index, page in enumerate(pdf.pages):
                        tables = page.extract_tables() or []

                        for table_index, table in enumerate(tables):
                            clean_rows = [
                                [
                                    str(cell).strip() if cell is not None else None
                                    for cell in row
                                ]
                                for row in table
                            ]

                            column_count = max(
                                (len(row) for row in clean_rows), default=0
                            )

                            extracted_table = ExtractedTable(
                                source_pdf=str(pdf_path),
                                source_url=manifest.get("source_url"),
                                company=manifest.get("company"),
                                year=str(manifest.get("year"))
                                if manifest.get("year")
                                else None,
                                document_type=manifest.get("document_type"),
                                language=manifest.get("language"),
                                page_number=page_index + 1,
                                table_index=table_index,
                                rows=clean_rows,
                                row_count=len(clean_rows),
                                column_count=column_count,
                            )

                            output.write(extracted_table.model_dump_json() + "\n")
                            tables_count += 1

            return {
                "status": "success",
                "source_pdf": str(pdf_path),
                "tables_output": str(output_path),
                "tables_count": tables_count,
            }

        except Exception as e:
            return {
                "status": "error",
                "source_pdf": str(pdf_path),
                "error": str(e),
            }

    def run(
        self,
        companies: list[str] | None = None,
        years: list[str] | None = None,
        force: bool = False,
    ) -> list[dict]:
        pdf_files = list(self.raw_dir.rglob("*.pdf"))
        results = []

        for pdf_path in pdf_files:
            manifest = self.load_manifest(pdf_path)

            company = str(manifest.get("company") or "").lower()
            year = str(manifest.get("year") or "")

            if companies:
                if not any(c.lower() in company for c in companies):
                    continue

            if years:
                if year not in years:
                    continue

            results.append(self.extract_tables(pdf_path, force=force))

        return results