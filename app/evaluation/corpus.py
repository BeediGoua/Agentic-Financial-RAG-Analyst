from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def normalize_document_path(path: str | Path) -> str:
    """Normalize Linux and Windows PDF paths for identity matching."""
    text = str(path).strip().replace("\\", "/")
    if len(text) >= 2 and text[1] == ":":
        text = text[0].upper() + text[1:]
    return str(Path(text)) if not text.startswith(("C:/", "D:/")) else text


def build_document_registry(
    manifest_payloads: Iterable[dict | str | Path] = (),
    *,
    corpus_manifest: dict | None = None,
) -> dict:
    """Build source_pdf -> verified SHA-256 registry from G1/corpus manifests."""
    records: dict[str, str] = {}
    ambiguous: set[str] = set()
    missing: set[str] = set()

    payloads: list[dict] = []
    for payload in manifest_payloads:
        if isinstance(payload, dict):
            payloads.append(payload)
            continue
        path = Path(payload)
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    payloads.append(loaded)
            except (OSError, json.JSONDecodeError):
                continue

    if isinstance(corpus_manifest, dict):
        payloads.append(corpus_manifest)
        for record in corpus_manifest.get("document_records", []):
            if isinstance(record, dict):
                payloads.append({
                    "local_path": record.get("source_pdf"),
                    "checksum_sha256": record.get("document_sha256"),
                })

    for payload in payloads:
        source_pdf = payload.get("local_path") or payload.get("source_pdf")
        expected = str(
            payload.get("checksum_sha256")
            or payload.get("document_sha256")
            or ""
        ).lower()
        if not source_pdf:
            continue
        normalized = normalize_document_path(source_pdf)
        if len(expected) != 64:
            missing.add(normalized)
            continue
        existing = records.get(normalized)
        if existing and existing != expected:
            ambiguous.add(normalized)
        else:
            records[normalized] = expected

    basename_map: dict[str, set[str]] = {}
    for source in records:
        basename = source.rstrip("/").rsplit("/", 1)[-1].lower()
        basename_map.setdefault(basename, set()).add(source)
    for source in list(records):
        basename = source.rstrip("/").rsplit("/", 1)[-1].lower()
        if len(basename_map[basename]) > 1:
            ambiguous.update(basename_map[basename])

    return {
        "records": records,
        "ambiguous_paths": sorted(ambiguous),
        "missing_paths": sorted(missing),
    }


def resolve_document_sha256(
    source_pdf: str | None,
    registry: dict,
) -> tuple[str | None, str]:
    """Resolve and verify a PDF identity, returning (SHA-256, status)."""
    if not source_pdf:
        return None, "missing_provenance"
    normalized = normalize_document_path(source_pdf)
    records = registry.get("records", {})
    if normalized in records:
        return records[normalized], "verified"
    if normalized in registry.get("ambiguous_paths", []):
        return None, "ambiguous_provenance"
    basename = normalized.rstrip("/").rsplit("/", 1)[-1].lower()
    matches = [
        (path, sha)
        for path, sha in records.items()
        if path.rstrip("/").rsplit("/", 1)[-1].lower() == basename
    ]
    if len(matches) == 1:
        return matches[0][1], "verified"
    if len(matches) > 1:
        return None, "ambiguous_provenance"
    return None, "missing_provenance"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_manifest_files(paths: Iterable[Path]) -> list[str]:
    return sorted(
        sha256_file(path)
        for path in paths
        if Path(path).is_file()
    )


def build_corpus_manifest(
    *,
    documents: Iterable[Path],
    chunk_manifests: Iterable[Path] = (),
    faiss_manifests: Iterable[Path] = (),
    embedding_models: Iterable[str] = (),
    strategies: Iterable[str] = (),
    document_metadata: Iterable[dict] = (),
) -> dict:
    document_paths = sorted({Path(path) for path in documents if Path(path).is_file()})
    document_hashes = _hash_manifest_files(document_paths)
    records_by_hash: dict[str, dict] = {}
    for record in document_metadata:
        if not isinstance(record, dict):
            continue
        sha = str(record.get("document_sha256") or "").lower()
        if len(sha) == 64:
            records_by_hash[sha] = dict(record)
    for path in document_paths:
        sha = sha256_file(path)
        records_by_hash.setdefault(sha, {
            "source_pdf": str(path),
            "document_sha256": sha,
        })
    chunk_paths = sorted({
        Path(path)
        for path in chunk_manifests
        if Path(path).is_file()
    })
    faiss_paths = sorted({
        Path(path)
        for path in faiss_manifests
        if Path(path).is_file()
    })
    chunks_count = 0
    for path in chunk_paths:
        if path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as stream:
                chunks_count += sum(1 for line in stream if line.strip())
        elif path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    chunks_count += len(payload)
            except (json.JSONDecodeError, OSError):
                pass
    vectors_count = 0
    for path in faiss_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                vectors_count += int(payload.get("ntotal") or payload.get("vectors_count") or payload.get("count") or 0)
            elif isinstance(payload, list):
                vectors_count += len(payload)
        except (json.JSONDecodeError, OSError, ValueError):
            pass
    identity = json.dumps(
        {
            "documents": document_hashes,
            "chunks": _hash_manifest_files(chunk_paths),
            "faiss": _hash_manifest_files(faiss_paths),
            "embedding_models": sorted(set(embedding_models)),
            "strategies": sorted(set(strategies)),
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    return {
        "schema_version": 1,
        "snapshot_id": hashlib.sha256(identity).hexdigest(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents_count": len(document_paths),
        "chunk_files_count": len(chunk_paths),
        "chunks_count": chunks_count,
        "faiss_indexes_count": len(faiss_paths),
        "vectors_count": vectors_count,
        "document_hashes": document_hashes,
        "document_records": [records_by_hash[sha] for sha in sorted(records_by_hash)],
        "chunk_manifest_hashes": _hash_manifest_files(chunk_paths),
        "faiss_manifest_hashes": _hash_manifest_files(faiss_paths),
        "embedding_models": sorted(set(embedding_models)),
        "strategies": sorted(set(strategies)),
    }
