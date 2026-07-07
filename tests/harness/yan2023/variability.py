"""Shared variability formula bank for Yan 2023 feature experiments."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

VariabilityFormulaName = Literal[
    "adjacent_normalized",
    "coefficient_of_variation",
    "normalized_range",
    "mean_absolute_step",
]

DEFAULT_VARIABILITY_FORMULA: VariabilityFormulaName = "adjacent_normalized"
VARIABILITY_FORMULA_NAMES: tuple[VariabilityFormulaName, ...] = (
    "adjacent_normalized",
    "coefficient_of_variation",
    "normalized_range",
    "mean_absolute_step",
)


def compute_variability(values: Sequence[float | int], formula: VariabilityFormulaName) -> float:
    """Compute one variability candidate for a numeric sequence."""

    normalized_values = [float(value) for value in values]
    if formula == "adjacent_normalized":
        return _adjacent_normalized_variability(normalized_values)
    if formula == "coefficient_of_variation":
        return _coefficient_of_variation(normalized_values)
    if formula == "normalized_range":
        return _normalized_range(normalized_values)
    if formula == "mean_absolute_step":
        return _mean_absolute_step_variability(normalized_values)
    raise ValueError(f"Unsupported variability formula {formula!r}.")


def compute_variability_candidates(
    values: Sequence[float | int],
) -> dict[VariabilityFormulaName, float]:
    """Return all current variability candidates for a numeric sequence."""

    normalized_values = [float(value) for value in values]
    return {
        "adjacent_normalized": _adjacent_normalized_variability(normalized_values),
        "coefficient_of_variation": _coefficient_of_variation(normalized_values),
        "normalized_range": _normalized_range(normalized_values),
        "mean_absolute_step": _mean_absolute_step_variability(normalized_values),
    }


def _adjacent_normalized_variability(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    terms: list[float] = []
    for left, right in zip(values, values[1:]):
        denominator = (abs(left) + abs(right)) / 2
        if denominator == 0:
            continue
        terms.append(abs(left - right) / denominator)
    return _mean(terms)


def _coefficient_of_variation(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean_value = _mean(values)
    if mean_value == 0:
        return 0.0
    return _population_stddev(values) / abs(mean_value)


def _normalized_range(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean_value = abs(_mean(values))
    if mean_value == 0:
        return 0.0
    return (max(values) - min(values)) / mean_value


def _mean_absolute_step_variability(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = abs(_mean(values))
    if mean_value == 0:
        return 0.0
    diffs = [abs(left - right) for left, right in zip(values, values[1:])]
    return _mean(diffs) / mean_value


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _population_stddev(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean_value = _mean(values)
    return (sum((value - mean_value) ** 2 for value in values) / len(values)) ** 0.5
