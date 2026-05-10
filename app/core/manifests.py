import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any

def create_manifest(file_path: str, source_url: str, source_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    path = Path(file_path)
    checksum = ""
    file_size = 0
    if path.exists():
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
    
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_file
