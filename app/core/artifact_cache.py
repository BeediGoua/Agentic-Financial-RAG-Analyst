from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.atomic import atomic_text_writer


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metadata_path_for(artifact_path: str | Path) -> Path:
    return Path(str(Path(artifact_path)) + ".build.json")


def build_fingerprint(
    *,
    source_path: str | Path,
    stage: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    source_path = Path(source_path)
    return {
        "schema_version": 1,
        "stage": stage,
        "source_path": str(source_path.resolve()),
        "source_sha256": sha256_file(source_path),
        "params": params,
    }


def write_artifact_manifest(
    artifact_path: str | Path,
    fingerprint: dict[str, Any],
) -> Path:
    artifact_path = Path(artifact_path)
    manifest = {
        **fingerprint,
        "artifact_sha256": sha256_file(artifact_path),
        "artifact_size": artifact_path.stat().st_size,
    }
    manifest_path = metadata_path_for(artifact_path)
    with atomic_text_writer(manifest_path) as output:
        json.dump(manifest, output, ensure_ascii=False, indent=2, sort_keys=True)
    return manifest_path


def artifact_cache_valid(
    artifact_path: str | Path,
    expected_fingerprint: dict[str, Any],
) -> bool:
    artifact_path = Path(artifact_path)
    manifest_path = metadata_path_for(artifact_path)
    if not artifact_path.is_file() or not manifest_path.is_file():
        return False
    try:
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key, expected in expected_fingerprint.items():
            if metadata.get(key) != expected:
                return False
        if metadata.get("artifact_size") != artifact_path.stat().st_size:
            return False
        if metadata.get("artifact_sha256") != sha256_file(artifact_path):
            return False
        return True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
