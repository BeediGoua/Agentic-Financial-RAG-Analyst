from __future__ import annotations


class EmbeddingQuality:
    def evaluate(self, results: list[dict]) -> dict:
        total_files = len(results)

        success_files = sum(
            1 for r in results if r.get("status") in {"success", "already_exists"}
        )

        empty_files = sum(1 for r in results if r.get("status") == "empty")
        error_files = sum(1 for r in results if r.get("status") == "error")

        total_records = sum(int(r.get("records_count") or 0) for r in results)

        dimensions = sorted(
            set(
                int(r.get("vector_dimension"))
                for r in results
                if r.get("vector_dimension")
            )
        )

        status = "PASS"

        if total_records == 0:
            status = "FAIL"
        elif error_files > 0:
            status = "WARNING"

        return {
            "status": status,
            "total_files": total_files,
            "success_files": success_files,
            "empty_files": empty_files,
            "error_files": error_files,
            "total_records": total_records,
            "dimensions": dimensions,
        }