from __future__ import annotations


class ProcessingQualityAgent:
    """
    Agent déterministe.
    Rôle :
    - mesurer la qualité des pages et tables nettoyées ;
    - décider si la phase 3 est exploitable.
    """

    def evaluate_text_cleaning(self, text_results: list[dict]) -> dict:
        total_files = len(text_results)
        success_files = sum(
            1 for r in text_results if r.get("status") in {"success", "already_exists"}
        )
        error_files = sum(1 for r in text_results if r.get("status") == "error")
        total_records = sum(int(r.get("records_count") or 0) for r in text_results)

        status = "PASS"

        if total_files == 0 or total_records == 0:
            status = "FAIL"
        elif error_files > 0:
            status = "WARNING"

        return {
            "status": status,
            "total_files": total_files,
            "success_files": success_files,
            "error_files": error_files,
            "total_records": total_records,
        }

    def evaluate_table_cleaning(self, table_results: list[dict]) -> dict:
        total_files = len(table_results)
        success_files = sum(
            1 for r in table_results if r.get("status") in {"success", "already_exists"}
        )
        error_files = sum(1 for r in table_results if r.get("status") == "error")
        total_records = sum(int(r.get("records_count") or 0) for r in table_results)

        status = "PASS"

        if error_files > 0:
            status = "WARNING"

        return {
            "status": status,
            "total_files": total_files,
            "success_files": success_files,
            "error_files": error_files,
            "total_records": total_records,
        }

    def decide_overall_status(
        self,
        text_quality: dict,
        table_quality: dict,
        metadata_quality: dict,
    ) -> str:
        if text_quality["status"] == "FAIL" or metadata_quality["status"] == "FAIL":
            return "FAIL"

        if (
            text_quality["status"] == "WARNING"
            or table_quality["status"] == "WARNING"
            or metadata_quality["status"] == "WARNING"
        ):
            return "WARNING"

        return "PASS"