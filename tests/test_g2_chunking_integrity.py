from __future__ import annotations

from app.chunking.utils import make_chunk_id, recursive_split_text, write_jsonl
from app.core.artifact_cache import build_fingerprint, sha256_file, artifact_cache_valid
from app.chunking.utils import normalize_text
import pytest
import json

from app.chunking.hierarchical import HierarchicalChunking
from app.chunking.markdown_aware import MarkdownAwareChunking
from app.chunking.page_aware import PageAwareChunking
from app.chunking.recursive_fixed import RecursiveFixedChunking
from app.chunking.section_aware import SectionAwareChunking
from app.chunking.semantic import SemanticChunking
from app.chunking.table_aware import TableAwareChunking


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
    with pytest.raises(ValueError):
        recursive_split_text(text, 300, 300)

    for size, overlap in [(0, 0), (-1, 0), (100, -1), (100, 100), (True, 0), (100, False)]:
        with pytest.raises(ValueError):
            recursive_split_text(text, size, overlap)


def test_recursive_split_paragraph_overlap_and_normalized_coverage():
    text = "A" * 180 + "\n\n" + "B" * 180
    normalized = normalize_text(text)
    chunks = recursive_split_text(normalized, chunk_size=200, chunk_overlap=50)

    assert len(chunks) >= 2
    assert all(len(chunk) <= 200 for chunk in chunks)
    assert chunks[0].startswith("A")
    assert chunks[-1].endswith("B")
    assert "\n\n" in chunks[0] or "\n\n" in chunks[1]
    for previous, current in zip(chunks, chunks[1:]):
        assert previous[-50:] == current[:50]

    end = 0
    for index, chunk in enumerate(chunks):
        start = 0 if index == 0 else end - 50
        assert normalized[start:start + len(chunk)] == chunk
        end = start + len(chunk)
    assert end == len(normalized)


def test_recursive_split_long_sequence_without_spaces():
    text = "X" * 1000
    chunks = recursive_split_text(text, chunk_size=120, chunk_overlap=25)

    assert all(len(chunk) == 120 for chunk in chunks[:-1])
    assert 1 <= len(chunks[-1]) <= 120
    assert chunks[-1]
    for previous, current in zip(chunks, chunks[1:]):
        assert previous[-25:] == current[:25]


def test_recursive_split_small_last_chunk_and_empty_text():
    chunks = recursive_split_text("012345678901234", chunk_size=6, chunk_overlap=2)
    assert all(len(chunk) <= 6 for chunk in chunks)
    assert len(chunks[-1]) < 6
    for previous, current in zip(chunks, chunks[1:]):
        assert previous[-2:] == current[:2]
    assert recursive_split_text("", chunk_size=10, chunk_overlap=2) == []
    assert recursive_split_text("\n\n\n", chunk_size=10, chunk_overlap=2) == []


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


@pytest.mark.parametrize(
    "strategy_name",
    [
        "recursive_fixed",
        "page_aware",
        "section_aware",
        "table_aware",
        "semantic",
        "markdown_aware",
        "hierarchical",
    ],
)
def test_seven_chunking_strategies_invalidate_cache_for_source_and_params(
    tmp_path,
    strategy_name,
):
    if strategy_name == "table_aware":
        source_dir = tmp_path / "processed" / "tables"
        output_dir = tmp_path / "chunks" / "table_aware"
        source_dir.mkdir(parents=True)
        source = source_dir / "sample.clean_tables.jsonl"
        source.write_text(
            json.dumps({
                "cleaned_rows": [["Compte", "Montant"], ["Chiffre d'affaires", "100"]],
                "page_number": 1,
                "source_pdf": "/tmp/report.pdf",
                "source_url": "https://example.test/report.pdf",
                "company": "ORANGE CI",
                "year": "2025",
                "document_type": "annual_report",
                "language": "fr",
            }) + "\n",
            encoding="utf-8",
        )
        chunker = TableAwareChunking(str(source_dir), str(output_dir))
    else:
        source_dir = tmp_path / "processed" / "pages"
        output_dir = tmp_path / "chunks" / strategy_name
        source_dir.mkdir(parents=True)
        source = source_dir / "sample.clean_pages.jsonl"
        source.write_text(
            json.dumps({
                "cleaned_text": "Synthese financière 2025. Le résultat reste stable.",
                "text": "Synthese financière 2025. Le résultat reste stable.",
                "page_number": 1,
                "source_pdf": "/tmp/report.pdf",
                "source_url": "https://example.test/report.pdf",
                "company": "ORANGE CI",
                "year": "2025",
                "document_type": "annual_report",
                "language": "fr",
            }) + "\n",
            encoding="utf-8",
        )
        chunker_classes = {
            "recursive_fixed": RecursiveFixedChunking,
            "page_aware": PageAwareChunking,
            "section_aware": SectionAwareChunking,
            "semantic": SemanticChunking,
            "markdown_aware": MarkdownAwareChunking,
            "hierarchical": HierarchicalChunking,
        }
        chunker = chunker_classes[strategy_name](str(source_dir), str(output_dir))

    first = chunker.run_file(source)
    second = chunker.run_file(source)
    assert first["status"] == "success"
    assert second["status"] == "already_exists"

    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    after_source_change = chunker.run_file(source)
    assert after_source_change["status"] == "success"

    if strategy_name == "recursive_fixed":
        chunker.chunk_size = 900
    elif strategy_name == "page_aware":
        chunker.max_page_chunk_size = 900
    elif strategy_name == "section_aware":
        chunker.chunk_size = 900
    elif strategy_name == "semantic":
        chunker.max_words = 200
    elif strategy_name == "markdown_aware":
        chunker.chunk_size = 900
    elif strategy_name == "hierarchical":
        chunker.child_chunk_size = 900

    after_parameter_change = chunker.run_file(source)
    if strategy_name == "table_aware":
        after_parameter_change = chunker.run_file(source, companies=["ORAC"])
    assert after_parameter_change["status"] == "success"
