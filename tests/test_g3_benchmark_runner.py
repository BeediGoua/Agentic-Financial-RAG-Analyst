import pytest

from app.evaluation.corpus import build_corpus_manifest
from app.evaluation.runner import BenchmarkRunner, FixtureRetriever
from app.evaluation.schemas import GoldQuestion
from app.evaluation.run_retrieval_eval import main, resolve_benchmark_top_k
import sys


def fixture_question():
    return GoldQuestion(
        question_id="SYNTH-Q1",
        question="Quel est le montant synthétique?",
        language="fr",
        task_type="financial_fact",
        company_tickers=["ORAC"],
        years=["2024"],
        answerability="answerable",
        split="dev",
        annotation_status="verified",
        evidence_groups=[{
            "group_id": "G1",
            "alternatives": [{
                "evidence_id": "E1",
                "document_sha256": "a" * 64,
                "page_start": 1,
                "page_end": 1,
                "quote": "Montant synthétique 101 FCFA",
                "grade": 3,
            }],
        }],
    )


def test_fixture_runner_and_technical_status(tmp_path):
    question = fixture_question()
    ranked = {"Quel est le montant synthétique?": [{
        "chunk_id": "recursive_fixed_abc123",
        "evidence_id": "E1",
        "rank": 1,
        "score": 1.0,
        "document_sha256": "a" * 64,
        "page_start": 1,
        "page_end": 1,
        "text": "Montant synthétique 101 FCFA",
    }]}
    retrievers = {name: FixtureRetriever(ranked) for name in ("bm25", "dense", "hybrid")}
    snapshot = build_corpus_manifest(documents=[], embedding_models=["fake"], strategies=["recursive_fixed"])
    runner = BenchmarkRunner(retrievers=retrievers, corpus_snapshot=snapshot)
    report = runner.run(
        [question],
        strategies=["recursive_fixed"],
        models=["mini_lm_multilingual"],
        methods=["bm25", "dense", "hybrid"],
        top_k=5,
    )
    assert report["synthetic"] is True
    assert len(report["per_query"]) == 3
    assert all(row["status"] == "success" for row in report["per_query"])
    assert all(row["metrics"]["recall"] == 1.0 for row in report["per_query"])


def test_empty_valid_search_has_zero_metrics():
    question = fixture_question()
    retriever = FixtureRetriever({"Quel est le montant synthétique?": []})
    snapshot = build_corpus_manifest(documents=[], embedding_models=["fake"], strategies=["recursive_fixed"])
    runner = BenchmarkRunner(
        retrievers={name: retriever for name in ("bm25", "dense", "hybrid")},
        corpus_snapshot=snapshot,
    )
    report = runner.run(
        [question],
        strategies=["recursive_fixed"],
        models=["mini_lm_multilingual"],
        methods=["bm25"],
        top_k=5,
    )
    row = report["per_query"][0]
    assert row["status"] == "empty"
    assert row["metrics"]["hit"] == 0.0
    assert row["metrics"]["recall"] == 0.0
    assert row["metrics"]["precision"] == 0.0
    assert row["metrics"]["ndcg"] == 0.0


@pytest.mark.parametrize(
    ("candidate_count", "top_k", "k_values"),
    [
        (0, 5, [5]),
        (1, 5, [5]),
        (3, 5, [5]),
        (0, 10, [5, 10]),
        (1, 10, [5, 10]),
        (3, 10, [5, 10]),
    ],
)
def test_fewer_candidates_still_produce_at_k_metrics(candidate_count, top_k, k_values):
    question = fixture_question()
    ranked_items = [
        {
            "chunk_id": f"chunk-{index}",
            "evidence_id": "E1",
            "rank": index + 1,
            "score": 1.0,
            "document_sha256": "a" * 64,
            "page_start": 1,
            "page_end": 1,
            "text": "Montant synthétique 101 FCFA",
        }
        for index in range(candidate_count)
    ]
    retriever = FixtureRetriever({
        "Quel est le montant synthétique?": ranked_items,
    })
    runner = BenchmarkRunner(
        retrievers={"bm25": retriever},
        corpus_snapshot=build_corpus_manifest(documents=[]),
    )

    report = runner.run(
        [question],
        strategies=["recursive_fixed"],
        models=["mini_lm_multilingual"],
        methods=["bm25"],
        top_k=top_k,
        k_values=k_values,
    )
    metrics = report["per_query"][0]["metrics"]

    for k in k_values:
        assert metrics[f"recall@{k}"] is not None
        assert metrics[f"evidence_coverage@{k}"] is not None
        assert metrics[f"all_evidence@{k}"] is not None
        assert metrics[f"candidate_count@{k}"] == candidate_count
        assert metrics[f"candidate_shortfall@{k}"] == max(k - candidate_count, 0)


def test_real_mode_without_corpus_is_not_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_retrieval_eval",
            "--mode",
            "real",
            "--output-dir",
            str(tmp_path),
        ],
    )
    assert main() == 2


def test_top_k_contract_never_reports_k_above_cutoff():
    config = {"benchmark": {"k_values": [1, 5, 10, 20]}}
    top_k, k_values = resolve_benchmark_top_k(config, cli_top_k=3)
    assert top_k == 3
    assert k_values == [1, 3]

    top_k, k_values = resolve_benchmark_top_k(config, cli_top_k=None)
    assert top_k == 20
    assert k_values == [1, 5, 10, 20]


def test_runner_rejects_k_values_above_top_k():
    question = fixture_question()
    runner = BenchmarkRunner(
        retrievers={"bm25": FixtureRetriever({})},
        corpus_snapshot=build_corpus_manifest(documents=[]),
    )
    with pytest.raises(ValueError, match="k_value"):
        runner.run(
            [question],
            strategies=["recursive_fixed"],
            models=["mini_lm_multilingual"],
            methods=["bm25"],
            top_k=5,
            k_values=[1, 10],
        )
