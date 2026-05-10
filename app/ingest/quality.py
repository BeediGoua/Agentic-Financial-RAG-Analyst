from __future__ import annotations

from pathlib import Path

from app.ingest.utils import sha256_file


class QualityAgent:
    """Validates downloaded reports and detects duplicates."""

    def validate_pdf(self, path: str | Path) -> tuple[bool, str]:
        file_path = Path(path)

        if not file_path.exists():
            return False, "file_not_found"

        if file_path.stat().st_size < 1_000:
            return False, "file_too_small"

        with file_path.open("rb") as f:
            header = f.read(5)

        if header != b"%PDF-":
            return False, "invalid_pdf_header"

        return True, "ok"

    def file_hash(self, path: str | Path) -> str:
        return sha256_file(path)

    def is_duplicate(self, checksum: str, existing_checksums: set[str]) -> bool:
        return checksum in existing_checksums
