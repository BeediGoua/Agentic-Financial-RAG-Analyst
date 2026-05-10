from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from app.chunking.schemas import TextChunk
from app.chunking.utils import (
    group_pages_by_document,
    load_jsonl,
    make_chunk_id,
    matches_filter,
    recursive_split_text,
    write_jsonl,
)


class SemanticChunking:
    """
    Semantic chunking simple.
    Si sentence-transformers n'est pas installé, fallback vers recursive_split.
    """

    def __init__(
        self,
        processed_pages_dir: str = "data/processed/pages",
        output_dir: str = "data/chunks/semantic",
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        similarity_threshold: float = 0.55,
        max_words: int = 260,
    ):
        self.processed_pages_dir = Path(processed_pages_dir)
        self.output_dir = Path(output_dir)
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.max_words = max_words
        self.strategy = "semantic"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.model = None

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name)
        except Exception:
            self.model = None

    def split_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [s.strip() for s in sentences if s.strip()]

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def semantic_split(self, text: str) -> list[str]:
        sentences = self.split_sentences(text)

        if len(sentences) <= 2 or self.model is None:
            return recursive_split_text(text, chunk_size=1400, chunk_overlap=150)

        embeddings = self.model.encode(sentences, normalize_embeddings=True)

        chunks = []
        current = [sentences[0]]

        for i in range(1, len(sentences)):
            similarity = self.cosine(embeddings[i - 1], embeddings[i])
            current_words = len(" ".join(current).split())

            if similarity < self.similarity_threshold or current_words > self.max_words:
                chunks.append(" ".join(current).strip())
                current = [sentences[i]]
            else:
                current.append(sentences[i])

        if current:
            chunks.append(" ".join(current).strip())

        return [c for c in chunks if c]

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
        grouped = group_pages_by_document(pages)

        for source_pdf, doc_pages in grouped.items():
            index = 0

            for page in doc_pages:
                text = page.get("cleaned_text") or page.get("text") or ""
                page_number = int(page.get("page_number"))

                parts = self.semantic_split(text)

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
            "semantic_model_loaded": self.model is not None,
        }

    def run(self, companies=None, years=None, force: bool = False) -> list[dict]:
        files = list(self.processed_pages_dir.rglob("*.clean_pages.jsonl"))
        return [self.run_file(f, companies, years, force) for f in files]