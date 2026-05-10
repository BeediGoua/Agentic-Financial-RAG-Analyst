from __future__ import annotations


class RetrievalQuality:
    """
    Validation simple avant vraie évaluation retrieval.

    La vraie évaluation Recall@K / MRR viendra avec un dataset de questions annotées.
    """

    def evaluate(self, results: list[dict]) -> dict:
        total_runs = len(results)

        success_runs = sum(
            1 for r in results if r.get("status") == "success"
        )

        empty_runs = sum(
            1 for r in results if r.get("status") == "empty"
        )

        error_runs = sum(
            1 for r in results if r.get("status") == "error"
        )

        total_results = sum(
            int(r.get("results_count") or 0) for r in results
        )

        status = "PASS"

        if total_runs == 0 or total_results == 0:
            status = "FAIL"
        elif error_runs > 0:
            status = "WARNING"

        return {
            "status": status,
            "total_runs": total_runs,
            "success_runs": success_runs,
            "empty_runs": empty_runs,
            "error_runs": error_runs,
            "total_results": total_results,
        }