import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any

from app.core.atomic import atomic_text_writer

def create_manifest(file_path: str, source_url: str, source_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Cannot create a success manifest for missing or empty data: {path}")
    file_size = path.stat().st_size
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    checksum = h.hexdigest()

    return {
        "source": source_name,
        "source_url": source_url,
        "local_path": str(file_path),
        "checksum_sha256": checksum,
        "file_size_bytes": file_size,
        "status": "success",
        "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": params or {}
    }

def write_manifest(manifest: Dict[str, Any], out_dir: str) -> Path:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    local_path = Path(manifest["local_path"])
    manifest_file = out_path / f"{local_path.name}.manifest.json"
    if not local_path.is_file() or local_path.stat().st_size != manifest["file_size_bytes"]:
        raise ValueError(f"Manifest data changed before writing: {local_path}")
    with local_path.open("rb") as data_file:
        actual_hash = hashlib.sha256()
        for chunk in iter(lambda: data_file.read(8192), b""):
            actual_hash.update(chunk)
    if actual_hash.hexdigest() != manifest["checksum_sha256"]:
        raise ValueError(f"Manifest checksum no longer matches: {local_path}")
    with atomic_text_writer(manifest_file) as output:
        json.dump(manifest, output, indent=2, ensure_ascii=False)
    return manifest_file
