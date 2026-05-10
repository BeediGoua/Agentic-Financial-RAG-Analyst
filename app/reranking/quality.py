from __future__ import annotations


class RerankingQuality:
    """
    Contrôle qualité simple du reranking.

    La vraie évaluation comparative viendra plus tard avec :
    - Recall@K ;
    - MRR ;
    - citation accuracy ;
    - faithfulness.
    """

    def evaluate(self, runs: list[dict]) -> dict:
        total_runs = len(runs)

        success_runs = sum(
            1 for run in runs if run.get("status") == "success"
        )

        empty_runs = sum(
            1 for run in runs if run.get("status") == "empty"
        )

        error_runs = sum(
            1 for run in runs if run.get("status") == "error"
        )

        total_reranked_results = sum(
            int(run.get("reranked_results_count") or 0)
            for run in runs
        )

        status = "PASS"

        if total_runs == 0 or total_reranked_results == 0:
            status = "FAIL"
        elif error_runs > 0:
            status = "WARNING"

        return {
            "status": status,
            "total_runs": total_runs,
            "success_runs": success_runs,
            "empty_runs": empty_runs,
            "error_runs": error_runs,
            "total_reranked_results": total_reranked_results,
        }