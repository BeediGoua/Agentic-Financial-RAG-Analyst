from __future__ import annotations

from pathlib import Path

from app.chunking.schemas import TextChunk
from app.chunking.utils import load_jsonl, make_chunk_id, matches_filter, validate_cached_chunks, write_chunk_artifact
from app.core.artifact_cache import artifact_cache_valid, build_fingerprint, write_artifact_manifest


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
        fingerprint = build_fingerprint(
            source_path=input_path,
            stage="chunking",
            params={
                "strategy": self.strategy,
                "companies": sorted(companies or []),
                "years": sorted(years or []),
                "table_to_text": True,
            },
        )
        if not force and artifact_cache_valid(output_path, fingerprint):
            valid, count = validate_cached_chunks(output_path, expected_strategy=self.strategy)
            if valid:
                return {"status": "already_exists", "strategy": self.strategy, "output_path": str(output_path), "chunks_count": count}

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

        write_chunk_artifact(output_path, chunks, fingerprint)

        return {
            "status": "success",
            "strategy": self.strategy,
            "output_path": str(output_path),
            "chunks_count": len(chunks),
        }

    def run(self, companies=None, years=None, force: bool = False) -> list[dict]:
        files = list(self.processed_tables_dir.rglob("*.clean_tables.jsonl"))
        return [self.run_file(f, companies, years, force) for f in files]
