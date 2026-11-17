from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path

import requests

from app.core.atomic import atomic_text_writer
from app.ingest.quality import QualityAgent
from app.ingest.schemas import ReportDocument
from app.ingest.url_security import (
    configured_pdf_hosts,
    get_trusted_response,
    validate_https_url,
)
from app.ingest.utils import slugify


class StorageAgent:
    """
    Agent déterministe.
    Rôle :
    - télécharger les PDF ;
    - organiser le stockage RAW ;
    - sauvegarder les manifests ;
    - sauvegarder les logs.
    """

    def __init__(self, root_dir: str = "data/raw/reports"):
        self.root_dir = Path(root_dir)
        self.metadata_dir = Path("data/metadata")
        self.logs_dir = Path("data/logs")

        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()

    def build_path(self, report: ReportDocument) -> Path:
        source = slugify(report.source or "unknown_source")
        company = slugify(report.company or "unknown_company")
        year = report.year or "unknown_year"
        document_type = report.document_type or "other_report"

        short_hash = hashlib.md5(report.pdf_url.encode("utf-8")).hexdigest()[:8]
        base_name = f"{company}_{year}_{document_type}_{short_hash}"
        base_name = re.sub(r'[<>:"/\\|?*\s]+', "_", base_name)

        filename = f"{base_name}.pdf"

        output_dir = self.root_dir / source / company / year / document_type
        output_dir.mkdir(parents=True, exist_ok=True)

        return output_dir / filename

    def download(self, report: ReportDocument) -> Path:
        allowed_hosts = configured_pdf_hosts()
        validate_https_url(
            report.pdf_url,
            allowed_hosts=allowed_hosts,
        )
        output_path = self.build_path(report)
        quality_agent = QualityAgent()

        if output_path.exists():
            valid, _, _ = quality_agent.validate_pdf(output_path)
            if valid:
                return output_path
            output_path.unlink()
            output_path.with_suffix(".manifest.json").unlink(missing_ok=True)

        temporary_path: Path | None = None
        try:
            with get_trusted_response(
                self.session,
                report.pdf_url,
                allowed_hosts=allowed_hosts,
                timeout=(10, 60),
                stream=True,
            ) as response:
                response.raise_for_status()

                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > quality_agent.max_pdf_size:
                    raise ValueError("Downloaded file exceeds the maximum PDF size")

                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=output_path.parent,
                    prefix=f".{output_path.name}.",
                    suffix=".part",
                    delete=False,
                ) as temporary_file:
                    temporary_path = Path(temporary_file.name)
                    total_size = 0
                    for chunk in response.iter_content(chunk_size=65_536):
                        if not chunk:
                            continue
                        total_size += len(chunk)
                        if total_size > quality_agent.max_pdf_size:
                            raise ValueError("Downloaded file exceeds the maximum PDF size")
                        temporary_file.write(chunk)

            valid, reason, _ = quality_agent.validate_pdf(temporary_path)
            if not valid:
                raise ValueError(f"Downloaded file is not a valid PDF: {reason}")

            os.replace(temporary_path, output_path)
            temporary_path = None
            return output_path
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def save_metadata(
        self,
        report: ReportDocument,
        local_path: str | Path,
        checksum: str,
        status: str,
    ) -> Path:
        local_path = Path(local_path)
        quality_agent = QualityAgent()
        valid, reason, _ = quality_agent.validate_pdf(local_path)
        if not valid:
            raise ValueError(f"Refusing success manifest for invalid PDF: {reason}")
        actual_checksum = quality_agent.file_hash(local_path)
        if checksum != actual_checksum:
            raise ValueError("Refusing success manifest with a mismatched PDF checksum")

        metadata = {
            **report.model_dump(),
            "local_path": str(local_path),
            "checksum_sha256": checksum,
            "file_size_bytes": local_path.stat().st_size,
            "status": status,
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        manifest_path = local_path.with_suffix(".manifest.json")
        with atomic_text_writer(manifest_path) as output:
            json.dump(metadata, output, indent=2, ensure_ascii=False)

        return manifest_path

    def has_valid_success_manifest(
        self,
        local_path: str | Path,
        checksum: str,
    ) -> bool:
        """Check that a PDF has a coherent persisted success manifest."""
        local_path = Path(local_path)
        manifest_path = local_path.with_suffix(".manifest.json")

        try:
            metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict):
                return False
            if metadata.get("status") != "success":
                return False
            persisted_path = Path(metadata.get("local_path", ""))
            if persisted_path.resolve(strict=True) != local_path.resolve(strict=True):
                return False
            if metadata.get("checksum_sha256") != checksum:
                return False

            file_size = local_path.stat().st_size
            if (
                metadata.get("file_size_bytes") is not None
                and metadata["file_size_bytes"] != file_size
            ):
                return False

            quality_agent = QualityAgent()
            valid, _, _ = quality_agent.validate_pdf(local_path)
            if not valid or quality_agent.file_hash(local_path) != checksum:
                return False
            return True
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return False

    def load_existing_checksums(self) -> set[str]:
        checksums: set[str] = set()
        quality_agent = QualityAgent()
        logger = logging.getLogger(__name__)
        root = self.root_dir.resolve()

        for manifest in self.root_dir.rglob("*.manifest.json"):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                if data.get("status") != "success":
                    continue
                local_path = Path(data["local_path"])
                if not local_path.resolve().is_relative_to(root):
                    logger.warning(
                        "Ignoring manifest outside RAW storage: %s", manifest
                    )
                    continue
                checksum = data.get("checksum_sha256")
                valid, reason, _ = quality_agent.validate_pdf(local_path)
                if (
                    not valid
                    or not checksum
                    or quality_agent.file_hash(local_path) != checksum
                ):
                    logger.warning(
                        "Ignoring inconsistent success manifest %s (%s)",
                        manifest,
                        reason if not valid else "checksum mismatch",
                    )
                    continue
                checksums.add(checksum)
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
                logger.warning("Ignoring unreadable manifest %s: %s", manifest, exc)

        return checksums

    def save_run_log(self, results: list[dict]) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_path = self.logs_dir / f"ingestion_run_{timestamp}.json"

        with atomic_text_writer(log_path) as output:
            json.dump(results, output, indent=2, ensure_ascii=False)

        return log_path