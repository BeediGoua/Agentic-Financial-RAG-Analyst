from __future__ import annotations

import hashlib
import re
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text into a filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_") or "unknown"


def sha256_file(path: str | Path) -> str:
    """Compute SHA256 checksum for a file."""
    file_path = Path(path)
    h = hashlib.sha256()

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)

    return h.hexdigest()


def parse_csv_filter(value: str | None) -> list[str] | None:
    """Parse a comma-separated filter string. Empty means no filter."""
    if not value:
        return None

    values = [x.strip().lower() for x in value.split(",") if x.strip()]
    return values or None
