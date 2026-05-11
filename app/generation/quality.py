from __future__ import annotations


class GenerationQuality:
    """
    Validation simple de la génération.

    La vraie évaluation :
    - faithfulness
    - groundedness
    - hallucination rate
    viendra plus tard.
    """

    def evaluate(
        self,
        answer: str,
        citations_count: int,
    ) -> dict:
        answer = answer.strip()

        status = "PASS"

        if not answer:
            status = "FAIL"

        elif citations_count == 0:
            status = "WARNING"

        return {
            "status": status,
            "answer_length": len(answer),
            "citations_count": citations_count,
        }