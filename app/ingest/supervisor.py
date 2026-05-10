from __future__ import annotations

from app.ingest.brvm_source import BRVMSourceAgent
from app.ingest.quality import QualityAgent
from app.ingest.storage import StorageAgent


class SupervisorAgent:
    """Orchestrates source discovery, download, validation and metadata writing."""

    def __init__(
        self,
        source_agent: BRVMSourceAgent,
        quality_agent: QualityAgent,
        storage_agent: StorageAgent,
    ):
        self.source_agent = source_agent
        self.quality_agent = quality_agent
        self.storage_agent = storage_agent

    def run(self, limit: int | None = None) -> dict:
        reports = self.source_agent.discover_reports()
        discovered_count = len(reports)

        if limit is not None:
            reports = reports[:limit]

        existing_checksums = self.storage_agent.load_existing_checksums()
        results: list[dict] = []

        for report in reports:
            try:
                local_path = self.storage_agent.download(report)
                valid, reason = self.quality_agent.validate_pdf(local_path)

                if not valid:
                    results.append({
                        "status": "invalid_pdf",
                        "reason": reason,
                        "title": report.title,
                        "pdf_url": report.pdf_url,
                        "local_path": str(local_path),
                    })
                    continue

                checksum = self.quality_agent.file_hash(local_path)

                if self.quality_agent.is_duplicate(checksum, existing_checksums):
                    results.append({
                        "status": "duplicate",
                        "title": report.title,
                        "pdf_url": report.pdf_url,
                        "local_path": str(local_path),
                        "checksum_sha256": checksum,
                    })
                    continue

                existing_checksums.add(checksum)
                manifest_path = self.storage_agent.save_metadata(
                    report=report,
                    local_path=local_path,
                    checksum=checksum,
                    status="success",
                )

                results.append({
                    "status": "success",
                    "title": report.title,
                    "pdf_url": report.pdf_url,
                    "local_path": str(local_path),
                    "manifest_path": str(manifest_path),
                    "checksum_sha256": checksum,
                })

            except Exception as e:
                results.append({
                    "status": "error",
                    "title": report.title,
                    "pdf_url": report.pdf_url,
                    "error": str(e),
                })

        log_path = self.storage_agent.save_run_log(results)

        summary = {
            "discovered_reports": discovered_count,
            "processed_reports": len(results),
            "success": sum(1 for r in results if r["status"] == "success"),
            "duplicates": sum(1 for r in results if r["status"] == "duplicate"),
            "invalid_pdfs": sum(1 for r in results if r["status"] == "invalid_pdf"),
            "errors": sum(1 for r in results if r["status"] == "error"),
            "log_path": str(log_path),
            "results": results,
        }

        return summary
