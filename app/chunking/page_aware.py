from __future__ import annotations

from pathlib import Path

from app.chunking.schemas import TextChunk
from app.chunking.utils import (
    load_jsonl,
    make_chunk_id,
    matches_filter,
    recursive_split_text,
    write_jsonl,
)


class PageAwareChunking:
    def __init__(
        self,
        processed_pages_dir: str = "data/processed/pages",
        output_dir: str = "data/chunks/page_aware",
        max_page_chunk_size: int = 1800,
        overlap: int = 150,
    ):
        self.processed_pages_dir = Path(processed_pages_dir)
        self.output_dir = Path(output_dir)
        self.max_page_chunk_size = max_page_chunk_size
        self.overlap = overlap
        self.strategy = "page_aware"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_output_path(self, input_path: Path) -> Path:
        relative = input_path.relative_to(self.processed_pages_dir)
        return self.output_dir / relative.with_suffix(".chunks.jsonl")

    def run_file(self, input_path: Path, companies=None, years=None, force: bool = False) -> dict:
        output_path = self.build_output_path(input_path)

        if output_path.exists() and not force:
            return {"status": "already_exists", "strategy": self.strategy, "output_path": str(output_path)}

        pages = [
            page for page in load_jsonl(input_path)
            if matches_filter(page, companies, years)
        ]

        chunks: list[TextChunk] = []
        index = 0

        for page in pages:
            text = page.get("cleaned_text") or page.get("text") or ""
            page_number = int(page.get("page_number"))
            source_pdf = page.get("source_pdf")

            if len(text) <= self.max_page_chunk_size:
                parts = [text.strip()] if text.strip() else []
            else:
                parts = recursive_split_text(
                    text=text,
                    chunk_size=self.max_page_chunk_size,
                    chunk_overlap=self.overlap,
                )

            for part in parts:
                index += 1

                chunks.append(
                    TextChunk(
                        chunk_id=make_chunk_id(
                            self.strategy,
                            source_pdf,
                            page_number,
                            page_number,
                            index,
                            part,
                        ),
                        chunking_strategy=self.strategy,
                        source_pdf=source_pdf,
                        source_url=page.get("source_url"),
                        company=page.get("company"),
                        year=page.get("year"),
                        document_type=page.get("document_type"),
                        language=page.get("language"),
                        page_start=page_number,
                        page_end=page_number,
                        section=None,
                        content_type="text",
                        text=part,
                        char_count=len(part),
                        word_count=len(part.split()),
                    )
                )

        write_jsonl(output_path, chunks)

        return {
            "status": "success",
            "strategy": self.strategy,
            "output_path": str(output_path),
            "chunks_count": len(chunks),
        }

    def run(self, companies=None, years=None, force: bool = False) -> list[dict]:
        files = list(self.processed_pages_dir.rglob("*.clean_pages.jsonl"))
        return [self.run_file(f, companies, years, force) for f in files]