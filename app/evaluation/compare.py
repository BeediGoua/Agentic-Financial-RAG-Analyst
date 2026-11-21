from __future__ import annotations

import random


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
