from __future__ import annotations


class VectorDBQuality:
    """
    Contrôle qualité simple pour l'indexation vectorielle.
    """

    def evaluate(self, results: list[dict]) -> dict:
        total_files = len(results)

        success_files = sum(
            1 for r in results if r.get("status") in {"success", "already_exists"}
        )

        empty_files = sum(1 for r in results if r.get("status") == "empty")
        error_files = sum(1 for r in results if r.get("status") == "error")

        total_vectors = sum(int(r.get("vectors_count") or 0) for r in results)

        dimensions = sorted(
            set(
                int(r.get("vector_dimension"))
                for r in results
                if r.get("vector_dimension")
            )
        )

        indexed_pairs = sorted(
            set(
                f"{r.get('strategy')}::{r.get('model')}"
                for r in results
                if r.get("strategy") and r.get("model")
            )
        )

        status = "PASS"

        if total_files == 0:
            status = "FAIL"

        elif total_vectors == 0 and success_files == 0:
            status = "FAIL"

        elif error_files > 0:
            status = "WARNING"

        return {
            "status": status,
            "total_files": total_files,
            "success_files": success_files,
            "empty_files": empty_files,
            "error_files": error_files,
            "total_vectors": total_vectors,
            "dimensions": dimensions,
            "indexed_pairs": indexed_pairs,
        }
