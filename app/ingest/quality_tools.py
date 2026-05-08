from __future__ import annotations
import hashlib
import json
from pathlib import Path
from smolagents import tool


@tool
def validate_pdf_file(path: str) -> str:
    """
    Validate that a local file exists and is probably a PDF.
    Args:
        path: Local path of the downloaded file.
    Returns:
        JSON string with validation status.
    """
    file_path = Path(path)
    if not file_path.exists():
        return json.dumps({"valid": False, "reason": "file_not_found"})
    if file_path.stat().st_size < 1_000:
        return json.dumps({"valid": False, "reason": "file_too_small"})
    with file_path.open("rb") as f:
        header = f.read(5)
    if header != b"%PDF-":
        return json.dumps({"valid": False, "reason": "invalid_pdf_header"})
    return json.dumps({"valid": True, "reason": "ok"})


@tool
def compute_file_checksum(path: str) -> str:
    """
    Compute SHA256 checksum of a local file.
    Args:
        path: Local file path.
    Returns:
        SHA256 checksum string.
    """
    file_path = Path(path)
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
