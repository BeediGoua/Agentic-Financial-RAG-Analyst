from __future__ import annotations

import math


def dcg_at_k(grades: list[int], k: int) -> float:
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")
    if any(type(grade) is not int or not 0 <= grade <= 3 for grade in grades):
        raise ValueError("Invalid relevance grade")
    return sum(
        (2 ** grade - 1) / math.log2(rank + 2)
        for rank, grade in enumerate(grades[:k])
    )


def evaluate_ranked_query(
    ranked_ids: list[str],
    qrels: dict[str, int],
    k: int,
    relevant_threshold: int = 2,
) -> dict:
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")
    if type(relevant_threshold) is not int or relevant_threshold <= 0:
        raise ValueError("Invalid relevance threshold")
    if any(type(grade) is not int or not 0 <= grade <= 3 for grade in qrels.values()):
        raise ValueError("Invalid relevance grade")
    if len(ranked_ids) != len(set(ranked_ids)):
        raise ValueError("Duplicate result identifiers")

    relevant_ids = {
        identifier
        for identifier, grade in qrels.items()
        if grade >= relevant_threshold
    }
    if not relevant_ids:
        raise ValueError("No positive relevance judgments: use the unanswerable-question protocol")

    top = ranked_ids[:k]
    relevant_found = [identifier for identifier in top if identifier in relevant_ids]
    first_relevant_rank = next(
        (
            index + 1
            for index, identifier in enumerate(top)
            if identifier in relevant_ids
        ),
        None,
    )
    observed_grades = [qrels.get(identifier, 0) for identifier in top]
    ideal_grades = sorted(qrels.values(), reverse=True)[:k]
    dcg = dcg_at_k(observed_grades, k)
    ideal_dcg = dcg_at_k(ideal_grades, k)
    unjudged = [identifier for identifier in top if identifier not in qrels]

    return {
        "hit": float(bool(relevant_found)),
        "recall": len(relevant_found) / len(relevant_ids),
        "precision": len(relevant_found) / k,
        "reciprocal_rank": (
            1.0 / first_relevant_rank
            if first_relevant_rank is not None
            else 0.0
        ),
        "ndcg": dcg / ideal_dcg if ideal_dcg > 0 else None,
        "judged_fraction": (
            (len(top) - len(unjudged)) / len(top)
            if top
            else 0.0
        ),
        "unjudged_count": len(unjudged),
        "provisional": bool(unjudged),
    }


def evidence_coverage(
    ranked_ids: list[str],
    evidence_groups: dict[str, set[str]],
) -> dict:
    retrieved = set(ranked_ids)
    covered = sum(bool(retrieved.intersection(alternatives)) for alternatives in evidence_groups.values())
    total = len(evidence_groups)
    if total == 0:
        return {"evidence_coverage": 0.0, "all_evidence": 0.0}
    coverage = covered / total
    return {
        "evidence_coverage": coverage,
        "all_evidence": float(covered == total),
    }


def aggregate_metrics(rows: list[dict], metric_names: list[str]) -> dict:
    output = {}
    for name in metric_names:
        values = [
            float(row[name])
            for row in rows
            if name in row and row[name] is not None
        ]
        output[name] = sum(values) / len(values) if values else None
    return output
