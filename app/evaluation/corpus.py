from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


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
) -> dict:
    document_paths = sorted({Path(path) for path in documents if Path(path).is_file()})
    document_hashes = _hash_manifest_files(document_paths)
    chunk_paths = [Path(path) for path in chunk_manifests]
    faiss_paths = [Path(path) for path in faiss_manifests]
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
        "chunks_count": len(chunk_paths),
        "document_hashes": document_hashes,
        "chunk_manifest_hashes": _hash_manifest_files(chunk_paths),
        "faiss_manifest_hashes": _hash_manifest_files(faiss_paths),
        "embedding_models": sorted(set(embedding_models)),
        "strategies": sorted(set(strategies)),
    }
