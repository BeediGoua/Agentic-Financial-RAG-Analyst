import pytest

from app.evaluation.metrics import (
    aggregate_metrics,
    dcg_at_k,
    evidence_coverage,
    evaluate_ranked_query,
)


def test_reference_ranking_metrics():
    result = evaluate_ranked_query(
        ["X", "A", "B"],
        {"X": 0, "A": 3, "B": 2},
        k=3,
    )
    assert result["hit"] == 1.0
    assert result["recall"] == 1.0
    assert result["precision"] == pytest.approx(2 / 3)
    assert result["reciprocal_rank"] == 0.5
    assert result["ndcg"] == pytest.approx(0.6653152460429406, abs=1e-10)
    assert result["provisional"] is False


def test_metrics_at_two_and_relevance_after_k():
    result = evaluate_ranked_query(["X", "A", "B"], {"X": 0, "A": 3, "B": 2}, k=2)
    assert result["recall"] == 0.5
    assert result["reciprocal_rank"] == 0.5
    assert result["ndcg"] == pytest.approx(0.4966392596877323, abs=1e-10)
    assert evaluate_ranked_query(["X", "A"], {"X": 0, "A": 3}, k=1)["hit"] == 0.0


@pytest.mark.parametrize("ranked,qrels,k", [
    (["A", "A"], {"A": 3}, 2),
    (["A"], {"A": 0}, 1),
    (["A"], {"A": 3}, 0),
])
def test_invalid_or_negative_metrics_are_rejected(ranked, qrels, k):
    with pytest.raises(ValueError):
        evaluate_ranked_query(ranked, qrels, k=k)


def test_empty_and_unjudged_results():
    assert evaluate_ranked_query([], {"A": 3}, k=5)["precision"] == 0.0
    provisional = evaluate_ranked_query(["A", "X"], {"A": 3}, k=2)
    assert provisional["provisional"] is True
    assert provisional["unjudged_count"] == 1
    assert provisional["judged_fraction"] == 0.5


def test_evidence_coverage_and_macro_aggregation():
    coverage = evidence_coverage(
        ["E1", "E3"],
        {"G1": {"E1", "E2"}, "G2": {"E3"}},
    )
    assert coverage == {"evidence_coverage": 1.0, "all_evidence": 1.0}
    partial = evidence_coverage(["E1"], {"G1": {"E1"}, "G2": {"E2"}, "G3": {"E3"}})
    assert partial["evidence_coverage"] == pytest.approx(1 / 3)
    assert partial["all_evidence"] == 0.0
    assert aggregate_metrics([{"hit": 1.0}, {"hit": 0.0}], ["hit"])["hit"] == 0.5


def test_dcg_and_invalid_grades():
    assert dcg_at_k([3, 2, 0], 3) > dcg_at_k([2, 3, 0], 3)
    with pytest.raises(ValueError):
        dcg_at_k([4], 1)
