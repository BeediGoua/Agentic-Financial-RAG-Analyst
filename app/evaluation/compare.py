from __future__ import annotations

import random
from collections import defaultdict


def align_results(rows_a: list[dict], rows_b: list[dict], *, metric: str) -> tuple[list[dict], list[dict]]:
    def index(rows: list[dict]) -> dict[tuple[str, str, str], dict]:
        result = {}
        for row in rows:
            key = (
                str(row.get("question_id")),
                str(row.get("split")),
                str(row.get("corpus_snapshot")),
            )
            value = row.get("metrics", {}).get(metric)
            if value is not None:
                result[key] = row
        return result
    index_a = index(rows_a)
    index_b = index(rows_b)
    common = sorted(set(index_a).intersection(index_b))
    if not common:
        raise ValueError("No aligned question/split/corpus_snapshot samples")
    aligned_a = [index_a[key] for key in common]
    aligned_b = [index_b[key] for key in common]
    return aligned_a, aligned_b


def paired_bootstrap(
    values_a: list[float],
    values_b: list[float],
    *,
    repetitions: int = 1000,
    seed: int = 42,
) -> dict:
    if len(values_a) != len(values_b):
        raise ValueError("Paired samples must have equal lengths")
    if not values_a:
        return {"mean_delta": None, "ci95_low": None, "ci95_high": None}
    rng = random.Random(seed)
    deltas = []
    for _ in range(repetitions):
        sample = [rng.randrange(len(values_a)) for _ in values_a]
        mean_a = sum(values_a[index] for index in sample) / len(sample)
        mean_b = sum(values_b[index] for index in sample) / len(sample)
        deltas.append(mean_b - mean_a)
    deltas.sort()
    low_index = int(0.025 * (len(deltas) - 1))
    high_index = int(0.975 * (len(deltas) - 1))
    return {
        "mean_delta": (
            sum(values_b) / len(values_b) - sum(values_a) / len(values_a)
        ),
        "ci95_low": deltas[low_index],
        "ci95_high": deltas[high_index],
    }
