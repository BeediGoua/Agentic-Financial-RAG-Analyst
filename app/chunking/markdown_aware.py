from __future__ import annotations

import re
from pathlib import Path

from app.chunking.schemas import TextChunk
from app.chunking.utils import load_jsonl, make_chunk_id, matches_filter, recursive_split_text, write_jsonl


class MarkdownAwareChunking:
    """
    Version simple :
    - transforme les pages en pseudo-Markdown ;
    - détecte des titres probables ;
    - découpe par blocs Markdown.
    """

    def __init__(
        self,
        processed_pages_dir: str = "data/processed/pages",
        output_dir: str = "data/chunks/markdown_aware",
        chunk_size: int = 1600,
        overlap: int = 150,
    ):
        self.processed_pages_dir = Path(processed_pages_dir)
        self.output_dir = Path(output_dir)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.strategy = "markdown_aware"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def looks_like_heading(self, line: str) -> bool:
        line = line.strip()

        if not line:
            return False

        if len(line) > 90:
            return False

        if re.match(r"^\d+(\.\d+)*\s+[A-ZÉÈÀÂÎÔÛA-Z]", line):
            return True

        if line.isupper() and len(line.split()) <= 10:
            return True

        keywords = [
            "risque",
            "performance",
            "gouvernance",
            "strategie",
            "perspectives",
            "resultats",
            "revenus",
            "dette",
            "tresorerie",
        ]

        lower = line.lower()
        return any(k in lower for k in keywords) and len(line.split()) <= 8

    def to_markdown_blocks(self, text: str) -> list[tuple[str | None, str]]:
        lines = text.splitlines()
        blocks = []
        current_title = None
        current_lines = []

        for line in lines:
            stripped = line.strip()

            if self.looks_like_heading(stripped):
                if current_lines:
                    blocks.append((current_title, "\n".join(current_lines).strip()))
                    current_lines = []

                current_title = stripped
            else:
                current_lines.append(stripped)

        if current_lines:
            blocks.append((current_title, "\n".join(current_lines).strip()))

        return [(title, block) for title, block in blocks if block]

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
            source_pdf = page.get("source_pdf")
            page_number = int(page.get("page_number"))

            blocks = self.to_markdown_blocks(text)

            if not blocks:
                blocks = [(None, text)]

            for title, block in blocks:
                parts = recursive_split_text(block, self.chunk_size, self.overlap)

                for part in parts:
                    index += 1
                    section = title.lower().replace(" ", "_") if title else None

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
                            section=section,
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