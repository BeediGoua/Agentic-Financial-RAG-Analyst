from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import requests
import urllib3

from app.ingest.schemas import ReportDocument
from app.ingest.utils import slugify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


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
        self.session.verify = False

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
        output_path = self.build_path(report)

        if output_path.exists() and output_path.stat().st_size > 0:
            return output_path

        response = self.session.get(report.pdf_url, timeout=60)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        if "pdf" not in content_type and not report.pdf_url.lower().endswith(".pdf"):
            raise RuntimeError(f"Réponse non PDF probable: {content_type}")

        output_path.write_bytes(response.content)

        return output_path

    def save_metadata(
        self,
        report: ReportDocument,
        local_path: str | Path,
        checksum: str,
        status: str,
    ) -> Path:
        local_path = Path(local_path)

        metadata = {
            **report.model_dump(),
            "local_path": str(local_path),
            "checksum_sha256": checksum,
            "status": status,
            "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        manifest_path = local_path.with_suffix(".manifest.json")

        manifest_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return manifest_path

    def load_existing_checksums(self) -> set[str]:
        checksums: set[str] = set()

        for manifest in self.root_dir.rglob("*.manifest.json"):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
                checksum = data.get("checksum_sha256")

                if checksum:
                    checksums.add(checksum)

            except Exception:
                continue

        return checksums

    def save_run_log(self, results: list[dict]) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_path = self.logs_dir / f"ingestion_run_{timestamp}.json"

        log_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return log_path