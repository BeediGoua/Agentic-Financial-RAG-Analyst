from __future__ import annotations


class ExtractionQualityAgent:
    """
    Agent déterministe.
    Rôle : produire un diagnostic qualité simple sur l'extraction.
    """

    def evaluate_text_results(self, text_results: list[dict]) -> dict:
        total_files = len(text_results)

        success_files = sum(
            1 for r in text_results if r.get("status") in {"success", "already_exists"}
        )

        error_files = sum(1 for r in text_results if r.get("status") == "error")

        total_pages = sum(int(r.get("pages_count") or 0) for r in text_results)
        empty_pages = sum(int(r.get("empty_pages") or 0) for r in text_results)
        ocr_pages = sum(int(r.get("ocr_pages") or 0) for r in text_results)
        low_quality_pages = sum(
            int(r.get("low_quality_pages") or 0) for r in text_results
        )

        empty_page_rate = empty_pages / total_pages if total_pages else 0.0
        low_quality_rate = low_quality_pages / total_pages if total_pages else 0.0
        ocr_rate = ocr_pages / total_pages if total_pages else 0.0

        status = "HEALTHY"

        if error_files > 0:
            status = "DEGRADED"

        if total_pages > 0 and empty_page_rate > 0.5:
            status = "UNHEALTHY"

        if total_pages > 0 and low_quality_rate > 0.4:
            status = "DEGRADED"

        return {
            "total_files": total_files,
            "success_files": success_files,
            "error_files": error_files,
            "total_pages": total_pages,
            "empty_pages": empty_pages,
            "ocr_pages": ocr_pages,
            "low_quality_pages": low_quality_pages,
            "empty_page_rate": empty_page_rate,
            "ocr_rate": ocr_rate,
            "low_quality_rate": low_quality_rate,
            "status": status,
        }

    def evaluate_table_results(self, table_results: list[dict]) -> dict:
        total_files = len(table_results)

        success_files = sum(
            1 for r in table_results if r.get("status") in {"success", "already_exists"}
        )

        error_files = sum(1 for r in table_results if r.get("status") == "error")

        total_tables = sum(int(r.get("tables_count") or 0) for r in table_results)

        status = "HEALTHY"

        if error_files > 0:
            status = "DEGRADED"

        return {
            "total_files": total_files,
            "success_files": success_files,
            "error_files": error_files,
            "total_tables": total_tables,
            "status": status,
        }