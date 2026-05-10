from __future__ import annotations

from pathlib import Path

from app.chunking.schemas import TextChunk
from app.chunking.sections import SectionDetection
from app.chunking.utils import group_pages_by_document, load_jsonl, make_chunk_id, matches_filter, recursive_split_text, write_jsonl


class HierarchicalChunking:
    """
    Crée des chunks parents par section/document et des chunks enfants courts.
    """

    def __init__(
        self,
        processed_pages_dir: str = "data/processed/pages",
        output_dir: str = "data/chunks/hierarchical",
        child_chunk_size: int = 1000,
        child_overlap: int = 120,
    ):
        self.processed_pages_dir = Path(processed_pages_dir)
        self.output_dir = Path(output_dir)
        self.child_chunk_size = child_chunk_size
        self.child_overlap = child_overlap
        self.strategy = "hierarchical"
        self.section_detector = SectionDetection()
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

        grouped = group_pages_by_document(pages)
        chunks: list[TextChunk] = []

        for source_pdf, doc_pages in grouped.items():
            current_section = "unknown_section"
            section_pages: dict[str, list[dict]] = {}

            for page in doc_pages:
                detected = self.section_detector.detect_page_section(page)
                if detected:
                    current_section = detected

                section_pages.setdefault(current_section, []).append(page)

            index = 0

            for section, pages_in_section in section_pages.items():
                section_text = "\n\n".join(
                    [p.get("cleaned_text") or p.get("text") or "" for p in pages_in_section]
                ).strip()

                if not section_text:
                    continue

                page_start = min(int(p.get("page_number")) for p in pages_in_section)
                page_end = max(int(p.get("page_number")) for p in pages_in_section)

                parent_id = make_chunk_id(
                    "parent",
                    source_pdf,
                    page_start,
                    page_end,
                    index,
                    section_text,
                )

                chunks.append(
                    TextChunk(
                        chunk_id=parent_id,
                        chunking_strategy=self.strategy,
                        source_pdf=source_pdf,
                        source_url=pages_in_section[0].get("source_url"),
                        company=pages_in_section[0].get("company"),
                        year=pages_in_section[0].get("year"),
                        document_type=pages_in_section[0].get("document_type"),
                        language=pages_in_section[0].get("language"),
                        page_start=page_start,
                        page_end=page_end,
                        section=section,
                        parent_id=None,
                        content_type="parent_text",
                        text=section_text,
                        char_count=len(section_text),
                        word_count=len(section_text.split()),
                    )
                )

                child_parts = recursive_split_text(
                    section_text,
                    chunk_size=self.child_chunk_size,
                    chunk_overlap=self.child_overlap,
                )

                for child_text in child_parts:
                    index += 1

                    chunks.append(
                        TextChunk(
                            chunk_id=make_chunk_id(
                                "child",
                                source_pdf,
                                page_start,
                                page_end,
                                index,
                                child_text,
                            ),
                            chunking_strategy=self.strategy,
                            source_pdf=source_pdf,
                            source_url=pages_in_section[0].get("source_url"),
                            company=pages_in_section[0].get("company"),
                            year=pages_in_section[0].get("year"),
                            document_type=pages_in_section[0].get("document_type"),
                            language=pages_in_section[0].get("language"),
                            page_start=page_start,
                            page_end=page_end,
                            section=section,
                            parent_id=parent_id,
                            content_type="child_text",
                            text=child_text,
                            char_count=len(child_text),
                            word_count=len(child_text.split()),
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