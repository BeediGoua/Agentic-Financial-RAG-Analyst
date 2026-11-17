"""G0 self-tests: use no external data, GPU, model downloads or network."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_env


def test_all_runtime_and_dev_dependencies_are_exact_pins():
    runtime = check_env.pinned_requirements(ROOT / "requirements.txt")
    dev = check_env.pinned_requirements(ROOT / "requirements-dev.txt")
    assert runtime["faiss-cpu"] == "1.12.0"
    assert runtime["sentence-transformers"] == "5.1.2"
    assert dev["pytest"] == "9.0.2"
    assert not (runtime.keys() & dev.keys())
    assert "chromadb" not in runtime  # Currently no ChromaDB backend


def test_embedders_have_expected_dimensions_and_default_model():
    from app.embeddings.models import EMBEDDING_MODELS
    assert EMBEDDING_MODELS["mini_lm_multilingual"]["dimension"] == 384
    assert EMBEDDING_MODELS["e5_small"]["query_prefix"] == "query: "


def test_reranker_catalog_has_tiny_and_mini_baselines():
    from app.reranking.models import RERANKING_MODELS
    assert "tiny_cross_encoder" in RERANKING_MODELS
    assert "mini_cross_encoder" in RERANKING_MODELS


def test_ollama_example_agrees_with_current_generator_default():
    from app.generation.ollama_generator import OllamaGenerator
    assert 'OLLAMA_MODEL=qwen2.5:7b' in (ROOT / '.env.example').read_text(encoding='utf-8')
    generator = OllamaGenerator()
    assert generator.model_name == 'qwen2.5:7b'


def test_one_command_and_venv_bootstrap_exist():
    for path in ('scripts/bootstrap.sh', 'scripts/test.sh', 'scripts/lock.sh', 'scripts/check_env.py'):
        assert (ROOT / path).is_file()
    assert 'pytest -q tests' in (ROOT / 'scripts/test.sh').read_text()
    assert 'python3.11' in (ROOT / 'scripts/bootstrap.sh').read_text()
