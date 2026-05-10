from __future__ import annotations

import json
import re
from pathlib import Path

from app.processing.schemas import CleanedPage


class TextCleaningAgent:
    """
    Agent déterministe.
    Rôle :
    - lire les pages extraites ;
    - nettoyer le texte ;
    - conserver les métadonnées ;
    - produire des pages propres.
    """

    def __init__(
        self,
        extracted_pages_dir: str = "data/extracted/pages",
        processed_pages_dir: str = "data/processed/pages",
    ):
        self.extracted_pages_dir = Path(extracted_pages_dir)
        self.processed_pages_dir = Path(processed_pages_dir)
        self.processed_pages_dir.mkdir(parents=True, exist_ok=True)

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.replace("\x00", " ")
        text = text.replace("\u00a0", " ")
        text = text.replace("\ufeff", " ")

        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" +\n", "\n", text)
        text = re.sub(r"\n +", "\n", text)

        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]

        return "\n".join(lines).strip()

    def build_output_path(self, input_path: Path) -> Path:
        relative = input_path.relative_to(self.extracted_pages_dir)
        output_path = self.processed_pages_dir / relative.with_suffix(".clean_pages.jsonl")
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

    def clean_pages_file(
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

                    raw_text = str(record.get("text") or "")
                    cleaned_text = self.clean_text(raw_text)

                    cleaned_page = CleanedPage(
                        source_pdf=record.get("source_pdf"),
                        source_url=record.get("source_url"),
                        company=record.get("company"),
                        year=str(record.get("year")) if record.get("year") else None,
                        document_type=record.get("document_type"),
                        language=record.get("language"),
                        page_number=int(record.get("page_number")),
                        text=raw_text,
                        cleaned_text=cleaned_text,
                        char_count=len(cleaned_text),
                        word_count=len(cleaned_text.split()),
                        extraction_method=record.get("extraction_method"),
                        ocr_used=bool(record.get("ocr_used", False)),
                        quality_status=record.get("quality_status"),
                        content_type="text",
                    )

                    f_out.write(cleaned_page.model_dump_json() + "\n")
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
        files = list(self.extracted_pages_dir.rglob("*.pages.jsonl"))
        results = []

        for input_path in files:
            results.append(
                self.clean_pages_file(
                    input_path=input_path,
                    companies=companies,
                    years=years,
                    force=force,
                )
            )

        return results