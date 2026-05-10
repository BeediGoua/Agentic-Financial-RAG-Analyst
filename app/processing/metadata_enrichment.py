from __future__ import annotations

import json
from pathlib import Path


class MetadataEnrichmentAgent:
    """
    Agent déterministe.
    Rôle :
    - vérifier que les métadonnées critiques sont présentes ;
    - produire un rapport de complétude metadata.
    """

    REQUIRED_FIELDS = [
        "source_pdf",
        "company",
        "year",
        "document_type",
        "page_number",
        "content_type",
    ]

    def __init__(
        self,
        processed_pages_dir: str = "data/processed/pages",
        processed_tables_dir: str = "data/processed/tables",
    ):
        self.processed_pages_dir = Path(processed_pages_dir)
        self.processed_tables_dir = Path(processed_tables_dir)

    def load_jsonl(self, path: Path) -> list[dict]:
        rows = []

        if not path.exists():
            return rows

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))

        return rows

    def check_record(self, record: dict) -> dict:
        missing = []

        for field in self.REQUIRED_FIELDS:
            value = record.get(field)

            if value is None or value == "":
                missing.append(field)

        return {
            "is_complete": len(missing) == 0,
            "missing_fields": missing,
        }

    def run(self) -> dict:
        files = list(self.processed_pages_dir.rglob("*.clean_pages.jsonl"))
        files += list(self.processed_tables_dir.rglob("*.clean_tables.jsonl"))

        total_records = 0
        incomplete_records = 0
        missing_fields_counter: dict[str, int] = {}

        examples = []

        for file_path in files:
            rows = self.load_jsonl(file_path)

            for record in rows:
                total_records += 1
                check = self.check_record(record)

                if not check["is_complete"]:
                    incomplete_records += 1

                    for field in check["missing_fields"]:
                        missing_fields_counter[field] = missing_fields_counter.get(field, 0) + 1

                    if len(examples) < 10:
                        examples.append(
                            {
                                "file": str(file_path),
                                "source_pdf": record.get("source_pdf"),
                                "page_number": record.get("page_number"),
                                "missing_fields": check["missing_fields"],
                            }
                        )

        completeness_rate = (
            1 - incomplete_records / total_records if total_records else 0.0
        )

        status = "PASS"

        if total_records == 0:
            status = "FAIL"
        elif completeness_rate < 0.95:
            status = "WARNING"

        return {
            "status": status,
            "total_records": total_records,
            "incomplete_records": incomplete_records,
            "completeness_rate": completeness_rate,
            "missing_fields_counter": missing_fields_counter,
            "examples": examples,
        }