from __future__ import annotations

import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.retrieval.filters import matches_retrieval_filters
from app.retrieval.schemas import RetrievalResult


class BM25Retriever:
    """
    Retrieval lexical BM25.

    Il lit directement les chunks JSONL.
    Utile pour retrouver les termes exacts :
    EBITDA, IFRS, dividende, dette, trésorerie, etc.
    """

    def __init__(
        self,
        chunks_dir: str = "data/chunks",
    ):
        self.chunks_dir = Path(chunks_dir)

    def tokenize(self, text: str) -> list[str]:
        text = text.lower()
        text = re.sub(r"[^a-zA-ZÀ-ÿ0-9]+", " ", text)
        return [tok for tok in text.split() if tok]

    def load_chunks(
        self,
        strategy: str,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> list[dict]:
        strategy_dir = self.chunks_dir / strategy

        if not strategy_dir.exists():
            raise FileNotFoundError(
                f"missing_corpus: chunk strategy directory absent: {strategy_dir}"
            )

        chunks = []

        for path in strategy_dir.rglob("*.chunks.jsonl"):
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    item = json.loads(line)

                    if not matches_retrieval_filters(
                        item,
                        companies=companies,
                        years=years,
                    ):
                        continue
                    chunks.append(item)

        return chunks

    def search(
        self,
        query: str,
        strategy: str,
        top_k: int = 5,
        companies: list[str] | None = None,
        years: list[str] | None = None,
    ) -> list[RetrievalResult]:
        chunks = self.load_chunks(strategy=strategy, companies=companies, years=years)

        if not chunks:
            return []

        corpus = [self.tokenize(chunk.get("text") or "") for chunk in chunks]
        bm25 = BM25Okapi(corpus)

        query_tokens = self.tokenize(query)
        scores = bm25.get_scores(query_tokens)

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        results = []

        for rank, (idx, score) in enumerate(ranked, start=1):
            item = chunks[idx]

            results.append(
                RetrievalResult(
                    rank=rank,
                    score=float(score),
                    retrieval_method="bm25",
                    chunk_id=item["chunk_id"],
                    chunking_strategy=item["chunking_strategy"],
                    embedding_model=None,
                    source_pdf=item["source_pdf"],
                    source_url=item.get("source_url"),
                    document_sha256=item.get("document_sha256"),
                    source_sha256=item.get("source_sha256"),
                    company=item.get("company"),
                    year=item.get("year"),
                    document_type=item.get("document_type"),
                    language=item.get("language"),
                    page_start=item.get("page_start"),
                    page_end=item.get("page_end"),
                    section=item.get("section"),
                    parent_id=item.get("parent_id"),
                    content_type=item.get("content_type"),
                    text=item.get("text") or "",
                )
            )

        return results