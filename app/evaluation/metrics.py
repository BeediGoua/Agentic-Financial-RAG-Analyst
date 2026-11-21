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
    judged_count = len(top) - len(unjudged)
    grade0_count = sum(
        1
        for identifier in top
        if identifier in qrels and qrels[identifier] == 0
    )

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
        "judged_count": judged_count,
        "grade0_count": grade0_count,
        "judged_fraction": judged_count / len(top) if top else 0.0,
        "unjudged_count": len(unjudged),
        "provisional": bool(unjudged),
    }


def evaluate_ranked_results(
    ranked_results: list[dict],
    evidence_groups: dict[str, set[str]],
    qrels: dict[str, int],
    k: int,
    relevant_threshold: int = 2,
) -> dict:
    """Evaluate chunk positions while deduplicating evidence alternatives by group.

    Hit, MRR and nDCG are computed on ranked chunks.  Recall and evidence
    coverage are computed on indispensable evidence groups, not on duplicate
    chunks or duplicate alternatives.
    """
    if type(k) is not int or k <= 0:
        raise ValueError("k must be a positive integer")
    if type(relevant_threshold) is not int or relevant_threshold <= 0:
        raise ValueError("Invalid relevance threshold")

    top = ranked_results[:k]
    relevant_groups: dict[str, int] = {}
    for group_id, alternatives in evidence_groups.items():
        grades = [qrels.get(evidence_id, 0) for evidence_id in alternatives]
        group_grade = max(grades, default=0)
        if group_grade >= relevant_threshold:
            relevant_groups[group_id] = group_grade

    if not relevant_groups:
        raise ValueError("No positive relevance judgments: use the unanswerable-question protocol")

    covered: set[str] = set()
    all_covered: set[str] = set()
    observed_grades: list[int] = []
    first_relevant_rank = None
    unjudged_count = 0
    judged_count = 0
    grade0_count = 0
    relevant_chunk_count = 0
    for rank, item in enumerate(top, start=1):
        matched_ids = set(item.get("matched_evidence_ids") or [])
        matched_groups = set(item.get("matched_group_ids") or [])
        if not matched_ids and not matched_groups:
            unjudged_count += 1
        else:
            judged_count += 1
            matched_grades = [
                qrels[evidence_id]
                for evidence_id in matched_ids
                if evidence_id in qrels
            ]
            if matched_grades and all(grade == 0 for grade in matched_grades):
                grade0_count += 1

        newly_relevant = matched_groups.intersection(relevant_groups).difference(covered)
        if newly_relevant and first_relevant_rank is None:
            first_relevant_rank = rank
        covered.update(newly_relevant)
        all_covered.update(matched_groups.intersection(relevant_groups))
        if newly_relevant:
            relevant_chunk_count += 1
        observed_grades.append(
            max((relevant_groups[group_id] for group_id in newly_relevant), default=0)
        )

    ideal_grades = sorted(relevant_groups.values(), reverse=True)[:k]
    dcg = dcg_at_k(observed_grades, k)
    ideal_dcg = dcg_at_k(ideal_grades, k)
    unjudged = unjudged_count
    top_count = len(top)

    return {
        "hit": float(first_relevant_rank is not None),
        "recall": len(covered) / len(relevant_groups),
        "precision": relevant_chunk_count / k,
        "reciprocal_rank": 1.0 / first_relevant_rank if first_relevant_rank else 0.0,
        "ndcg": dcg / ideal_dcg if ideal_dcg > 0 else 0.0,
        "judged_count": judged_count,
        "grade0_count": grade0_count,
        "judged_fraction": judged_count / top_count if top_count else 0.0,
        "unjudged_count": unjudged,
        "provisional": bool(unjudged),
        "evidence_coverage": len(all_covered) / len(relevant_groups) if relevant_groups else 0.0,
        "all_evidence": float(bool(relevant_groups) and len(all_covered) == len(relevant_groups)),
        "metric_units": {
            "hit": "ranked_chunk",
            "recall": "indispensable_evidence_group",
            "mrr": "ranked_chunk",
            "ndcg": "ranked_chunk_with_unique_evidence_groups",
            "evidence_coverage": "evidence_group",
            "all_evidence": "evidence_group",
        },
    }


def evidence_coverage(
    ranked_ids: list[str],
    evidence_groups: dict[str, set[str]],
    qrels: dict[str, int] | None = None,
    relevant_threshold: int = 2,
) -> dict:
    retrieved = set(ranked_ids)
    relevant_groups = evidence_groups
    if qrels is not None:
        relevant_groups = {
            group_id: alternatives
            for group_id, alternatives in evidence_groups.items()
            if max((qrels.get(evidence_id, 0) for evidence_id in alternatives), default=0)
            >= relevant_threshold
        }
    covered = sum(
        bool(retrieved.intersection(alternatives))
        for alternatives in relevant_groups.values()
    )
    total = len(relevant_groups)
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
