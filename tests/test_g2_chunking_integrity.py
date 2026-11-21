from __future__ import annotations

from app.chunking.utils import make_chunk_id, recursive_split_text, write_jsonl
from app.core.artifact_cache import build_fingerprint, sha256_file, artifact_cache_valid


def test_chunk_ids_are_deterministic_and_distinct():
    first = make_chunk_id("recursive_fixed", "/tmp/a.pdf", 1, 1, 0, "text")
    second = make_chunk_id("recursive_fixed", "/tmp/a.pdf", 1, 1, 0, "text")
    other = make_chunk_id("recursive_fixed", "/tmp/b.pdf", 1, 1, 0, "text")
    assert first == second
    assert first != other


def test_recursive_split_preserves_text_and_limit():
    text = ("phrase financière " * 300)
    chunks = recursive_split_text(text, chunk_size=300, chunk_overlap=50)
    assert chunks
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert "".join(chunks) != ""


def test_recursive_split_rejects_invalid_parameters_and_infinite_overlap():
    text = "A" * 1000
    assert all(len(chunk) <= 300 for chunk in recursive_split_text(text, 300, 50))
    try:
        recursive_split_text(text, 300, 300)
    except ValueError:
        pass
    else:
        raise AssertionError("chunk_overlap equal to chunk_size must fail")


def test_artifact_cache_rejects_modified_source(tmp_path):
    source = tmp_path / "source.txt"
    artifact = tmp_path / "artifact.txt"
    source.write_text("before", encoding="utf-8")
    artifact.write_text("result", encoding="utf-8")
    fingerprint = build_fingerprint(source_path=source, stage="test", params={"x": 1})
    from app.core.artifact_cache import write_artifact_manifest
    write_artifact_manifest(artifact, fingerprint)
    assert artifact_cache_valid(artifact, fingerprint)
    source.write_text("after", encoding="utf-8")
    modified = build_fingerprint(source_path=source, stage="test", params={"x": 1})
    assert not artifact_cache_valid(artifact, modified)
