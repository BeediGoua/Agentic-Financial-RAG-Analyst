from __future__ import annotations

from pathlib import Path
import logging

import fitz

from app.ingest.utils import sha256_file


class QualityAgent:
    """
    Validates downloaded reports with comprehensive checks.
    Inspired by app/evaluation/data_health.py for enterprise-grade validation.
    """

    def __init__(self, min_pdf_size: int = 1_000, max_pdf_size: int = 500_000_000):
        self.min_pdf_size = min_pdf_size  # 1 KB minimum
        self.max_pdf_size = max_pdf_size  # 500 MB maximum
        self.logger = logging.getLogger(__name__)

    def validate_pdf(self, path: str | Path) -> tuple[bool, str, dict]:
        """
        Comprehensive PDF validation with detailed results.
        Returns: (is_valid, reason, checks_dict)
        """
        file_path = Path(path)
        checks = {
            "file_exists": False,
            "file_size": False,
            "pdf_header": False,
            "is_readable": False,
            "pdf_parsable": False,
            "all_passed": False
        }

        # Check 1: File existence
        if not file_path.is_file():
            return False, "file_not_found", checks

        checks["file_exists"] = True

        # Check 2: File size
        try:
            file_size = file_path.stat().st_size
            if file_size < self.min_pdf_size:
                return False, f"file_too_small ({file_size} bytes < {self.min_pdf_size})", checks
            if file_size > self.max_pdf_size:
                return False, f"file_too_large ({file_size} bytes > {self.max_pdf_size})", checks
            checks["file_size"] = True
        except OSError as e:
            return False, f"size_check_failed: {e}", checks

        # Check 3: PDF header
        try:
            with file_path.open("rb") as f:
                header = f.read(5)
            
            if header != b"%PDF-":
                return False, "invalid_pdf_header", checks
            checks["pdf_header"] = True
        except OSError as e:
            return False, f"header_check_failed: {e}", checks

        # Check 4: Readability (try reading more bytes)
        try:
            with file_path.open("rb") as f:
                content = f.read(4096)
                if not content or len(content) < 100:
                    return False, "pdf_content_too_short", checks
            checks["is_readable"] = True
        except OSError as e:
            return False, f"readability_check_failed: {e}", checks

        try:
            with fitz.open(file_path) as document:
                if not document.is_pdf:
                    return False, "not_a_pdf_document", checks
                if document.needs_pass:
                    return False, "encrypted_pdf_requires_password", checks
                if document.page_count < 1:
                    return False, "empty_pdf_document", checks
                for page_number in range(document.page_count):
                    document.load_page(page_number).get_text("text")
            checks["pdf_parsable"] = True
        except Exception as e:
            self.logger.warning("PDF parse validation failed for %s: %s", file_path, e)
            return False, f"unparseable_pdf: {type(e).__name__}", checks

        checks["all_passed"] = True
        return True, "valid_pdf", checks

    def file_hash(self, path: str | Path) -> str:
        """Compute SHA256 hash of file (enterprise traceability)."""
        return sha256_file(path)

    def is_duplicate(self, checksum: str, existing_checksums: set[str]) -> bool:
        """Check if checksum already exists (deduplication)."""
        return checksum in existing_checksums
    
    def get_file_metadata(self, path: str | Path) -> dict:
        """Extract file metadata for comprehensive audit trail."""
        file_path = Path(path)
        try:
            stat = file_path.stat()
            return {
                "file_size_bytes": stat.st_size,
                "file_mtime": stat.st_mtime,
                "file_name": file_path.name,
                "file_path": str(file_path)
            }
        except Exception as e:
            self.logger.warning(f"Could not get metadata for {path}: {e}")
            return {}
