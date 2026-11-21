import numpy as np
import pytest

from app.reranking.cross_encoder import CrossEncoderReranker


def candidate(chunk_id, rank, score, text="texte"):
    return {
        "rank": rank,
        "score": score,
        "retrieval_method": "hybrid",
        "chunk_id": chunk_id,
        "chunking_strategy": "section_aware",
        "source_pdf": f"/tmp/{chunk_id}.pdf",
        "company": "ORANGE CI",
        "year": "2024",
        "text": text,
    }


def reranker_with_scores(scores):
    reranker = CrossEncoderReranker.__new__(CrossEncoderReranker)
    reranker.model_key = "fake"
    reranker.batch_size = 16

    class Model:
        def predict(self, pairs, batch_size, show_progress_bar):
            return np.asarray(scores)

    reranker.model = Model()
    return reranker


def test_score_contract_and_deterministic_equal_scores():
    pool = [candidate("B", 1, 0.9), candidate("A", 2, 0.8)]
    reranker = reranker_with_scores([0.5, 0.5])
    ranked = reranker.rerank_results("question", pool, top_k=5)
    assert [item.chunk_id for item in ranked] == ["B", "A"]
    assert [item.rank for item in ranked] == [1, 2]
    assert all(item.original_rank in (1, 2) for item in ranked)


def test_mismatched_scores_nan_and_duplicate_candidates_are_rejected():
    pool = [candidate("A", 1, 0.9), candidate("B", 2, 0.8)]
    with pytest.raises(ValueError, match="score count mismatch"):
        reranker_with_scores([0.5]).rerank_results("question", pool)
    with pytest.raises(ValueError, match="NaN"):
        reranker_with_scores([np.nan, 0.5]).rerank_results("question", pool)
    with pytest.raises(ValueError, match="Duplicate"):
        reranker_with_scores([0.5, 0.5]).rerank_results(
            "question",
            [candidate("A", 1, 0.9), candidate("A", 2, 0.8)],
        )
