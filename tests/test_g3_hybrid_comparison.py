from app.retrieval.hybrid import HybridRetriever
from app.retrieval.schemas import RetrievalResult


class Retriever:
    def __init__(self, results):
        self.results = results

    def search(self, **kwargs):
        return self.results


def result(chunk_id, score, company="ORANGE CI", year="2024"):
    return RetrievalResult(
        rank=1,
        score=score,
        retrieval_method="dense",
        chunk_id=chunk_id,
        chunking_strategy="recursive_fixed",
        source_pdf=f"/tmp/{chunk_id}.pdf",
        company=company,
        year=year,
        text=chunk_id,
    )


def test_hybrid_filters_and_deterministic_ties():
    dense = Retriever([
        result("orac2024", 0.9),
        result("cie2024", 0.8, "CIE CI"),
    ])
    bm25 = Retriever([
        result("orac2024", 0.7),
        result("sonatel2025", 0.6, "SONATEL", "2025"),
    ])
    hybrid = HybridRetriever(dense, bm25, dense_weight=0.5, bm25_weight=0.5)
    ranked = hybrid.search(
        "résultat",
        "recursive_fixed",
        "mini_lm_multilingual",
        top_k=5,
        companies=["ORAC"],
        years=["2024"],
    )
    assert [item.chunk_id for item in ranked] == ["orac2024"]
    assert ranked[0].retrieval_method == "hybrid"


def test_hybrid_rejects_negative_weights():
    try:
        HybridRetriever(dense_weight=-0.1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative hybrid weights must be rejected")
