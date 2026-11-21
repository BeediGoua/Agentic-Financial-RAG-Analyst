from app.evaluation.corpus import build_corpus_manifest
from app.evaluation.runner import BenchmarkRunner, FixtureRetriever
from app.evaluation.schemas import GoldQuestion


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
        "chunk_id": "E1",
        "evidence_id": "E1",
        "rank": 1,
        "score": 1.0,
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
