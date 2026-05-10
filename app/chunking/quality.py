from __future__ import annotations


class ChunkQuality:
    REQUIRED_FIELDS = [
        "chunk_id",
        "chunking_strategy",
        "source_pdf",
        "company",
        "year",
        "document_type",
        "page_start",
        "page_end",
        "content_type",
        "text",
    ]

    def evaluate_results(self, results: list[dict]) -> dict:
        total_outputs = len(results)
        success_outputs = sum(
            1 for r in results if r.get("status") in {"success", "already_exists"}
        )
        errors = sum(1 for r in results if r.get("status") == "error")
        total_chunks = sum(int(r.get("chunks_count") or 0) for r in results)

        status = "PASS"

        if total_outputs == 0 or total_chunks == 0:
            status = "FAIL"
        elif errors > 0:
            status = "WARNING"

        return {
            "status": status,
            "total_outputs": total_outputs,
            "success_outputs": success_outputs,
            "errors": errors,
            "total_chunks": total_chunks,
        }

    def evaluate_by_strategy(self, strategy_results: dict[str, list[dict]]) -> dict:
        return {
            strategy: self.evaluate_results(results)
            for strategy, results in strategy_results.items()
        }