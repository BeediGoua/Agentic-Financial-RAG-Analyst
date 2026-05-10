from __future__ import annotations

import io
import json
from pathlib import Path

import fitz
import pytesseract
from PIL import Image

from app.extraction.schemas import ExtractedPage


class PDFTextExtractionAgent:
    """
    Agent déterministe.
    Rôle :
    - extraire le texte page par page avec PyMuPDF ;
    - détecter les pages de faible qualité ;
    - appliquer OCR seulement si nécessaire.
    """

    def __init__(
        self,
        raw_dir: str = "data/raw/reports",
        output_dir: str = "data/extracted/pages",
        min_words_per_page: int = 20,
        enable_ocr: bool = True,
        ocr_language: str = "fra+eng",
    ):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.min_words_per_page = min_words_per_page
        self.enable_ocr = enable_ocr
        self.ocr_language = ocr_language

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_manifest(self, pdf_path: Path) -> dict:
        manifest_path = pdf_path.with_suffix(".manifest.json")

        if not manifest_path.exists():
            return {}

        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def build_output_path(self, pdf_path: Path) -> Path:
        relative = pdf_path.relative_to(self.raw_dir)
        output_path = self.output_dir / relative.with_suffix(".pages.jsonl")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    def is_low_quality_text(self, text: str) -> bool:
        words = text.split()
        return len(words) < self.min_words_per_page

    def ocr_page(self, page: fitz.Page) -> str:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.open(io.BytesIO(pix.tobytes("png")))

        return pytesseract.image_to_string(
            image,
            lang=self.ocr_language,
        ).strip()

    def extract_page_text(self, page: fitz.Page) -> tuple[str, str, bool, str]:
        text = page.get_text("text").strip()

        if not self.is_low_quality_text(text):
            return text, "pymupdf", False, "ok"

        if not self.enable_ocr:
            return text, "pymupdf", False, "low_text_quality"

        try:
            ocr_text = self.ocr_page(page)

            if len(ocr_text.split()) > len(text.split()):
                quality_status = (
                    "ocr_recovered"
                    if len(ocr_text.split()) >= self.min_words_per_page
                    else "low_text_quality_after_ocr"
                )
                return ocr_text, "ocr_tesseract", True, quality_status

            return text, "pymupdf", False, "low_text_quality"

        except Exception:
            return text, "pymupdf", False, "ocr_failed"

    def extract_pdf(self, pdf_path: Path, force: bool = False) -> dict:
        output_path = self.build_output_path(pdf_path)

        if output_path.exists() and not force:
            return {
                "status": "already_exists",
                "source_pdf": str(pdf_path),
                "pages_output": str(output_path),
            }

        manifest = self.load_manifest(pdf_path)

        try:
            doc = fitz.open(pdf_path)
            pages: list[ExtractedPage] = []

            with output_path.open("w", encoding="utf-8") as f:
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    text, method, ocr_used, quality_status = self.extract_page_text(page)

                    extracted_page = ExtractedPage(
                        source_pdf=str(pdf_path),
                        source_url=manifest.get("source_url"),
                        company=manifest.get("company"),
                        year=str(manifest.get("year")) if manifest.get("year") else None,
                        document_type=manifest.get("document_type"),
                        language=manifest.get("language"),
                        page_number=page_index + 1,
                        text=text,
                        char_count=len(text),
                        word_count=len(text.split()),
                        extraction_method=method,
                        ocr_used=ocr_used,
                        quality_status=quality_status,
                    )

                    pages.append(extracted_page)
                    f.write(extracted_page.model_dump_json() + "\n")

            return {
                "status": "success",
                "source_pdf": str(pdf_path),
                "pages_output": str(output_path),
                "pages_count": len(pages),
                "empty_pages": sum(1 for page in pages if page.word_count == 0),
                "ocr_pages": sum(1 for page in pages if page.ocr_used),
                "low_quality_pages": sum(
                    1
                    for page in pages
                    if page.quality_status
                    in {"low_text_quality", "low_text_quality_after_ocr", "ocr_failed"}
                ),
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

            results.append(self.extract_pdf(pdf_path, force=force))

        return results