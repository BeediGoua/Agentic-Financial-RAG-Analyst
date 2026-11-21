from __future__ import annotations

from app.retrieval.hybrid import HybridRetriever
from app.retrieval.schemas import RetrievalResult


class StubRetriever:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return [item.model_copy(deep=True) for item in self.results]


def make_result(chunk_id, company="ORANGE CI", year="2024", score=0.8):
    return RetrievalResult(
        rank=1,
        score=score,
        retrieval_method="dense",
        chunk_id=chunk_id,
        chunking_strategy="recursive_fixed",
        embedding_model="mini_lm_multilingual",
        source_pdf=f"/tmp/{chunk_id}.pdf",
        company=company,
        year=year,
        text=f"text {chunk_id}",
    )


def test_hybrid_passes_filters_copies_results_and_is_deterministic():
    dense = StubRetriever([make_result("a"), make_result("outside", "CIE CI", "2025")])
    bm25 = StubRetriever([make_result("a")])
    retriever = HybridRetriever(dense, bm25, dense_weight=0.6, bm25_weight=0.4)
    first = retriever.search(
        "question",
        "recursive_fixed",
        "mini_lm_multilingual",
        top_k=5,
        companies=["ORANGE CI"],
        years=["2024"],
    )
    second = retriever.search(
        "question",
        "recursive_fixed",
        "mini_lm_multilingual",
        top_k=5,
        companies=["ORANGE CI"],
        years=["2024"],
    )
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert all(item.company == "ORANGE CI" and item.year == "2024" for item in first)
    assert all(item.rank == rank for rank, item in enumerate(first, start=1))
    assert dense.calls[0]["companies"] == ["ORANGE CI"]
    assert bm25.calls[0]["years"] == ["2024"]
    assert dense.results[0].score == 0.8
