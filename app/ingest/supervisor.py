from __future__ import annotations

from app.ingest.brvm_source import BRVMSourceAgent
from app.ingest.quality import QualityAgent
from app.ingest.storage import StorageAgent
from app.ingest.ingestion_health import IngestionHealthMonitor


class SupervisorAgent:
    """Orchestrates source discovery, download, validation and metadata writing."""

    def __init__(
        self,
        source_agent: BRVMSourceAgent,
        quality_agent: QualityAgent,
        storage_agent: StorageAgent,
        verbose: bool = False,
    ):
        self.source_agent = source_agent
        self.quality_agent = quality_agent
        self.storage_agent = storage_agent
        self.verbose = verbose

    def run(self, limit: int | None = None) -> dict:
        if self.verbose:
            print("🔍 Découverte des rapports...")
        reports = self.source_agent.discover_reports()
        discovered_count = len(reports)

        if limit is not None:
            reports = reports[:limit]

        if self.verbose:
            print(f"📊 {discovered_count} rapports découverts, traitement de {len(reports)}")

        existing_checksums = self.storage_agent.load_existing_checksums()
        results: list[dict] = []
        from tqdm import tqdm

        for i, report in enumerate(tqdm(reports, desc="Téléchargement & Validation", unit="pdf")):
            if self.verbose and (i + 1) % 5 == 0:
                tqdm.write(f"📥 Traitement {i + 1}/{len(reports)}: {report.title[:50]}...")

            try:
                local_path = self.storage_agent.download(report)
                valid, reason, validation_checks = self.quality_agent.validate_pdf(local_path)

                if not valid:
                    results.append({
                        "status": "invalid_pdf",
                        "reason": reason,
                        "title": report.title,
                        "pdf_url": report.pdf_url,
                        "local_path": str(local_path),
                        "validation_checks": validation_checks,
                    })
                    continue

                checksum = self.quality_agent.file_hash(local_path)
                file_metadata = self.quality_agent.get_file_metadata(local_path)

                if self.quality_agent.is_duplicate(checksum, existing_checksums):
                    results.append({
                        "status": "duplicate",
                        "title": report.title,
                        "pdf_url": report.pdf_url,
                        "local_path": str(local_path),
                        "checksum_sha256": checksum,
                        "reason": "duplicate_by_checksum",
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
                    "file_size_bytes": file_metadata.get("file_size_bytes"),
                    "validation_checks": {"all_passed": True},
                })

            except Exception as e:
                results.append({
                    "status": "error",
                    "title": report.title,
                    "pdf_url": report.pdf_url,
                    "error": str(e),
                })

        log_path = self.storage_agent.save_run_log(results)

        # Generate health report (inspired by app/evaluation/data_health.py)
        health_monitor = IngestionHealthMonitor()
        health_report = health_monitor.analyze_ingestion_run(results)
        health_path = health_monitor.save_health_report(health_report, str(log_path))

        if self.verbose:
            print("\n✅ Ingestion terminée!")
            health_monitor.print_health_summary(health_report)

        summary = {
            "discovered_reports": discovered_count,
            "processed_reports": len(results),
            "success": sum(1 for r in results if r["status"] == "success"),
            "duplicates": sum(1 for r in results if r["status"] == "duplicate"),
            "invalid_pdfs": sum(1 for r in results if r["status"] == "invalid_pdf"),
            "errors": sum(1 for r in results if r["status"] == "error"),
            "success_rate": health_report["metrics"]["success_rate"],
            "overall_status": health_report["overall_status"],
            "log_path": str(log_path),
            "health_report_path": str(health_path),
            "results": results,
        }

        return summary
