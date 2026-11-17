"""
Ingestion Health Monitoring
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from app.core.atomic import atomic_text_writer


class IngestionHealthMonitor:
    """Monitor health metrics of PDF report ingestions."""

    def __init__(self, logs_dir: str = "data/logs"):
        self.logs_dir = Path(logs_dir)
        self.logger = logging.getLogger(__name__)

    def analyze_ingestion_run(self, results: list[dict]) -> dict:
        """
        Analyze a complete ingestion run and generate health metrics.
        Returns structured health report similar to data_health.py.
        """
        health_report = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "overall_status": "UNKNOWN",
            "alerts": [],
            "metrics": {
                "total_processed": len(results),
                "successful": sum(1 for r in results if r.get("status") == "success"),
                "duplicates_detected": sum(
                    1 for r in results if r.get("status") == "duplicate"
                ),
                "invalid_pdfs": sum(
                    1 for r in results if r.get("status") == "invalid_pdf"
                ),
                "errors": sum(
                    1
                    for r in results
                    if r.get("status")
                    not in {"success", "duplicate", "invalid_pdf", "error"}
                    or r.get("status") == "error"
                ),
            },
            "validation_summary": {},
            "detailed_results": results
        }

        # Success rate
        total = health_report["metrics"]["total_processed"]
        successful = health_report["metrics"]["successful"]
        duplicates = health_report["metrics"]["duplicates_detected"]
        errors = health_report["metrics"]["errors"]
        invalid_pdfs = health_report["metrics"]["invalid_pdfs"]
        if total > 0:
            health_report["metrics"]["success_rate"] = round(successful / total, 4)
            health_report["metrics"]["available_rate"] = round(
                (successful + duplicates) / total, 4
            )

        else:
            health_report["metrics"]["success_rate"] = 0.0
            health_report["metrics"]["available_rate"] = 0.0
            health_report["alerts"].append("CRITICAL: No reports were processed")

        if errors or invalid_pdfs:
            health_report["alerts"].append(
                f"CRITICAL: {errors} errors and {invalid_pdfs} invalid PDFs"
            )
        elif successful:
            success_rate = health_report["metrics"]["success_rate"]
            if success_rate < 0.5:
                health_report["alerts"].append("CRITICAL: Success rate below 50%")
            elif success_rate < 0.8:
                health_report["alerts"].append("WARNING: Success rate below 80%")
        elif duplicates:
            health_report["alerts"].append(
                "WARNING: Reports were already validated; no new reports were ingested"
            )

        # Validation checks analysis
        validation_statuses = {}
        for result in results:
            if "validation_checks" in result and result["validation_checks"]:
                for check_name, check_result in result["validation_checks"].items():
                    if check_name not in validation_statuses:
                        validation_statuses[check_name] = {"passed": 0, "failed": 0}
                    if check_result:
                        validation_statuses[check_name]["passed"] += 1
                    else:
                        validation_statuses[check_name]["failed"] += 1

        health_report["validation_summary"] = validation_statuses

        # Status determination
        if not health_report["alerts"]:
            health_report["overall_status"] = "HEALTHY"
        elif any("CRITICAL" in alert for alert in health_report["alerts"]):
            health_report["overall_status"] = "CRITICAL"
        else:
            health_report["overall_status"] = "WARNING"

        return health_report

    def save_health_report(self, health_report: dict, log_path: str) -> Path:
        """Save health report alongside ingestion log."""
        log_path = Path(log_path)
        health_path = log_path.with_suffix(".health.json")

        with atomic_text_writer(health_path) as output:
            json.dump(health_report, output, indent=2, ensure_ascii=False)

        self.logger.info(f"Health report saved: {health_path}")
        return health_path

    def print_health_summary(self, health_report: dict):
        """Print human-readable health summary."""
        metrics = health_report["metrics"]
        status = health_report["overall_status"]

        print("\n" + "="*60)
        print(f"📊 INGESTION HEALTH REPORT - {status}")
        print("="*60)
        print(f"Total Processed     : {metrics['total_processed']}")
        print(f"✅ Successful       : {metrics['successful']}")
        print(f"🔄 Duplicates       : {metrics['duplicates_detected']}")
        print(f"❌ Invalid PDFs     : {metrics['invalid_pdfs']}")
        print(f"⚠️  Errors          : {metrics['errors']}")
        print(f"📈 Success Rate     : {metrics['success_rate']*100:.1f}%")

        if health_report["alerts"]:
            print("\n⚠️  ALERTS:")
            for alert in health_report["alerts"]:
                print(f"   - {alert}")

        if health_report["validation_summary"]:
            print("\n✓ VALIDATION CHECKS:")
            for check, results in health_report["validation_summary"].items():
                passed = results["passed"]
                failed = results["failed"]
                total = passed + failed
                rate = (passed / total * 100) if total > 0 else 0
                print(f"   - {check}: {passed}/{total} ({rate:.0f}%)")

        print("="*60 + "\n")
