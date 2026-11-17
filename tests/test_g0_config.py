"""G0 self-tests: use no external data, GPU, model downloads or network."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys
import subprocess

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


def test_all_hugging_face_models_have_pinned_revisions():
    models = check_env.configured_hf_models()
    assert set(models) == {
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "intfloat/multilingual-e5-small",
        "cross-encoder/ms-marco-MiniLM-L-6-v2",
        "cross-encoder/ms-marco-TinyBERT-L-2-v2",
    }
    assert all(len(revision) == 40 for revision in models.values())


def test_ollama_example_agrees_with_current_generator_default():
    from app.generation.ollama_generator import OllamaGenerator
    assert 'OLLAMA_MODEL=qwen2.5:7b' in (ROOT / '.env.example').read_text(encoding='utf-8')
    assert "OLLAMA_MODEL_DIGEST=" in (ROOT / '.env.example').read_text(encoding='utf-8')
    generator = OllamaGenerator()
    assert generator.model_name == 'qwen2.5:7b'


def test_one_command_and_venv_bootstrap_exist():
    for path in ('scripts/bootstrap.sh', 'scripts/test.sh', 'scripts/lock.sh', 'scripts/check_env.py'):
        assert (ROOT / path).is_file()
    assert 'pytest -q tests' in (ROOT / 'scripts/test.sh').read_text()
    assert 'python3.11' in (ROOT / 'scripts/bootstrap.sh').read_text()
    assert '.venv uses Python' in (ROOT / 'scripts/bootstrap.sh').read_text()


def test_bootstrap_rejects_existing_venv_with_wrong_python(tmp_path):
    project = tmp_path / "project"
    scripts = project / "scripts"
    fake_python = project / ".venv" / "bin" / "python"
    scripts.mkdir(parents=True)
    fake_python.parent.mkdir(parents=True)
    shutil.copy(ROOT / "scripts/bootstrap.sh", scripts / "bootstrap.sh")
    fake_python.write_text(
        "#!" + sys.executable + "\n"
        "import sys\n"
        "class VersionInfo(tuple):\n"
        "    major = property(lambda self: self[0])\n"
        "    minor = property(lambda self: self[1])\n"
        "sys.version_info = VersionInfo((3, 12, 0, 'final', 0))\n"
        "exec(compile(sys.stdin.read(), '<venv-check>', 'exec'))\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    environment = os.environ | {"PYTHON_BIN": sys.executable}

    result = subprocess.run(
        ["bash", str(scripts / "bootstrap.sh"), "--no-tests"],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode != 0
    assert ".venv uses Python 3.12" in result.stderr
