from app.retrieval.schemas import RetrievalResult
from app.retrieval.supervisor import RetrievalSupervisor


class FakeDense:
    def __init__(self):
        self.kwargs = None

    def search(self, **kwargs):
        self.kwargs = kwargs
        return [
            RetrievalResult(
                rank=1,
                score=1.0,
                retrieval_method="dense",
                chunk_id="orac2024",
                chunking_strategy=kwargs["strategy"],
                source_pdf="/tmp/orac2024.pdf",
                company="ORANGE CI",
                year="2024",
                text="Résultat net 2024",
            )
        ]


class FakeBM25:
    def __init__(self):
        self.kwargs = None

    def search(self, **kwargs):
        self.kwargs = kwargs
        return [
            RetrievalResult(
                rank=1,
                score=1.0,
                retrieval_method="bm25",
                chunk_id="orac2024",
                chunking_strategy=kwargs["strategy"],
                source_pdf="/tmp/orac2024.pdf",
                company="ORANGE CI",
                year="2024",
                text="Résultat net 2024",
            )
        ]


class FakeHybrid:
    def __init__(self):
        self.kwargs = None

    def search(self, **kwargs):
        self.kwargs = kwargs
        return [
            RetrievalResult(
                rank=1,
                score=1.0,
                retrieval_method="hybrid",
                chunk_id="orac2024",
                chunking_strategy=kwargs["strategy"],
                source_pdf="/tmp/orac2024.pdf",
                company="ORANGE CI",
                year="2024",
                text="Résultat net 2024",
            )
        ]


def test_supervisor_transmits_same_filters_to_all_methods():
    supervisor = RetrievalSupervisor()
    supervisor.dense = FakeDense()
    supervisor.bm25 = FakeBM25()
    supervisor.hybrid = FakeHybrid()
    for method in ("dense", "bm25", "hybrid"):
        run = supervisor.run_one(
            query="résultat net",
            method=method,
            strategy="recursive_fixed",
            model_key="mini_lm_multilingual",
            top_k=5,
            companies=["ORAC"],
            years=["2024"],
        )
        assert run["status"] == "success"
        retriever = getattr(supervisor, method)
        assert retriever.kwargs["companies"] == ["ORAC"]
        assert retriever.kwargs["years"] == ["2024"]
        assert all(r["company"] == "ORANGE CI" for r in run["results"])
        assert all(r["year"] == "2024" for r in run["results"])


def test_supervisor_distinguishes_empty_missing_and_error(tmp_path):
    supervisor = RetrievalSupervisor(output_dir=str(tmp_path))

    class Empty:
        def search(self, **kwargs):
            return []

    class Missing:
        def search(self, **kwargs):
            raise FileNotFoundError("missing_corpus")

    class Broken:
        def search(self, **kwargs):
            raise ValueError("Rejected invalid or mismatched FAISS artifact pair")

    supervisor.dense = Empty()
    assert supervisor.run_one("x", "dense", "recursive_fixed", "mini_lm_multilingual", 5)["status"] == "empty"
    supervisor.dense = Missing()
    assert supervisor.run_one("x", "dense", "recursive_fixed", "mini_lm_multilingual", 5)["status"] == "missing_corpus"
    supervisor.dense = Broken()
    assert supervisor.run_one("x", "dense", "recursive_fixed", "mini_lm_multilingual", 5)["status"] == "invalid_index"
