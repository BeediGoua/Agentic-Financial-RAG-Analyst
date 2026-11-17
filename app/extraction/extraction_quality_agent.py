from __future__ import annotations

import json
from pathlib import Path


class ExtractionQualityAgent:
    """
    Agent déterministe.
    Rôle : produire un diagnostic qualité simple sur l'extraction.
    """

    def evaluate_text_results(self, text_results: list[dict]) -> dict:
        normalized_results = []
        for result in text_results:
            if result.get("status") != "already_exists":
                normalized_results.append(result)
                continue

            enriched = dict(result)
            output_path = Path(result.get("pages_output") or "")
            try:
                rows = [
                    json.loads(line)
                    for line in output_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
                expected_pages = int(result.get("pages_count") or len(rows))
                if (
                    expected_pages < 1
                    or len(rows) != expected_pages
                    or any(not isinstance(row, dict) for row in rows)
                    or [int(row["page_number"]) for row in rows]
                    != list(range(1, expected_pages + 1))
                ):
                    raise ValueError("Missing or invalid pages cache")
                enriched["pages_count"] = len(rows)
                enriched["empty_pages"] = sum(
                    int(row.get("word_count") or 0) == 0 for row in rows
                )
                enriched["ocr_pages"] = sum(bool(row.get("ocr_used")) for row in rows)
                enriched["low_quality_pages"] = sum(
                    row.get("quality_status")
                    in {
                        "low_text_quality",
                        "low_text_quality_after_ocr",
                        "ocr_failed",
                    }
                    for row in rows
                )
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                enriched["status"] = "error"
            normalized_results.append(enriched)
        text_results = normalized_results
        total_files = len(text_results)

        success_files = sum(
            1 for r in text_results if r.get("status") in {"success", "already_exists"}
        )

        error_files = sum(
            1
            for result in text_results
            if result.get("status") not in {"success", "already_exists"}
        )

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
        if total_files == 0 or total_pages == 0 or error_files > 0:
            status = "UNHEALTHY"
        elif empty_page_rate > 0.5:
            status = "UNHEALTHY"
        elif low_quality_rate > 0.4:
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

        error_files = sum(
            1
            for result in table_results
            if result.get("status") not in {"success", "already_exists"}
        )

        total_tables = sum(int(r.get("tables_count") or 0) for r in table_results)

        status = (
            "UNHEALTHY"
            if total_files == 0 or error_files > 0
            else "HEALTHY"
        )

        return {
            "total_files": total_files,
            "success_files": success_files,
            "error_files": error_files,
            "total_tables": total_tables,
            "status": status,
        }