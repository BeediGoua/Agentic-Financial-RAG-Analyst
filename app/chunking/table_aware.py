from __future__ import annotations

from pathlib import Path

from app.chunking.schemas import TextChunk
from app.chunking.utils import load_jsonl, make_chunk_id, matches_filter, write_jsonl


class TableAwareChunking:
    def __init__(
        self,
        processed_tables_dir: str = "data/processed/tables",
        output_dir: str = "data/chunks/table_aware",
    ):
        self.processed_tables_dir = Path(processed_tables_dir)
        self.output_dir = Path(output_dir)
        self.strategy = "table_aware"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_output_path(self, input_path: Path) -> Path:
        relative = input_path.relative_to(self.processed_tables_dir)
        return self.output_dir / relative.with_suffix(".chunks.jsonl")

    def table_to_text(self, rows: list[list[str | None]]) -> str:
        lines = []

        for row in rows:
            cleaned = [cell if cell is not None else "" for cell in row]
            lines.append(" | ".join(cleaned))

        return "\n".join(lines).strip()

    def run_file(self, input_path: Path, companies=None, years=None, force: bool = False) -> dict:
        output_path = self.build_output_path(input_path)

        if output_path.exists() and not force:
            return {"status": "already_exists", "strategy": self.strategy, "output_path": str(output_path)}

        tables = [
            table for table in load_jsonl(input_path)
            if matches_filter(table, companies, years)
        ]

        chunks: list[TextChunk] = []

        for index, table in enumerate(tables, start=1):
            rows = table.get("cleaned_rows") or table.get("rows") or []
            text = self.table_to_text(rows)

            if not text:
                continue

            page_number = int(table.get("page_number"))
            source_pdf = table.get("source_pdf")

            chunks.append(
                TextChunk(
                    chunk_id=make_chunk_id(
                        self.strategy,
                        source_pdf,
                        page_number,
                        page_number,
                        index,
                        text,
                    ),
                    chunking_strategy=self.strategy,
                    source_pdf=source_pdf,
                    source_url=table.get("source_url"),
                    company=table.get("company"),
                    year=table.get("year"),
                    document_type=table.get("document_type"),
                    language=table.get("language"),
                    page_start=page_number,
                    page_end=page_number,
                    section="table",
                    content_type="table",
                    text=text,
                    char_count=len(text),
                    word_count=len(text.split()),
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
        files = list(self.processed_tables_dir.rglob("*.clean_tables.jsonl"))
        return [self.run_file(f, companies, years, force) for f in files]
