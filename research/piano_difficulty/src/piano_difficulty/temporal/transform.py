"""Normalization and smoothing helpers for temporal feature series."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import mean, median
from typing import Any, Literal

NormalizationMethod = Literal["none", "min_max", "z_score", "robust"]
SmoothingMethod = Literal["none", "moving_average", "trailing_moving_average"]


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    method: NormalizationMethod = "none"


@dataclass(frozen=True, slots=True)
class SmoothingConfig:
    method: SmoothingMethod = "none"
    window_size: int = 3
    centered: bool = True


def normalize_series(
    values: list[float | None],
    config: NormalizationConfig,
) -> tuple[list[float | None], dict[str, Any]]:
    numeric_values = [value for value in values if value is not None and isfinite(value)]
    if config.method == "none":
        return [None if value is None else float(value) for value in values], {"method": "none"}
    if not numeric_values:
        return [None for _ in values], {"method": config.method, "empty": True}

    if config.method == "min_max":
        minimum = min(numeric_values)
        maximum = max(numeric_values)
        if maximum == minimum:
            return [0.0 if value is not None else None for value in values], {
                "method": "min_max",
                "minimum": minimum,
                "maximum": maximum,
                "constant_series": True,
            }
        scale = maximum - minimum
        return [
            None if value is None else (float(value) - minimum) / scale
            for value in values
        ], {"method": "min_max", "minimum": minimum, "maximum": maximum, "constant_series": False}

    if config.method == "z_score":
        mean_value = mean(numeric_values)
        variance = sum((value - mean_value) ** 2 for value in numeric_values) / len(numeric_values)
        standard_deviation = variance ** 0.5
        if standard_deviation == 0:
            return [0.0 if value is not None else None for value in values], {
                "method": "z_score",
                "mean": mean_value,
                "standard_deviation": standard_deviation,
                "constant_series": True,
            }
        return [
            None if value is None else (float(value) - mean_value) / standard_deviation
            for value in values
        ], {"method": "z_score", "mean": mean_value, "standard_deviation": standard_deviation, "constant_series": False}

    if config.method == "robust":
        center = median(numeric_values)
        q1 = _quantile(numeric_values, 0.25)
        q3 = _quantile(numeric_values, 0.75)
        iqr = q3 - q1
        if iqr == 0:
            return [0.0 if value is not None else None for value in values], {
                "method": "robust",
                "median": center,
                "iqr": iqr,
                "constant_series": True,
            }
        return [
            None if value is None else (float(value) - center) / iqr
            for value in values
        ], {"method": "robust", "median": center, "iqr": iqr, "constant_series": False}

    raise ValueError(f"Unsupported normalization method {config.method!r}.")


def smooth_series(
    values: list[float | None],
    config: SmoothingConfig,
) -> tuple[list[float | None], dict[str, Any]]:
    if config.method == "none":
        return list(values), {"method": "none"}
    if config.window_size <= 0:
        raise ValueError("Smoothing window size must be positive.")
    if not values:
        return [], {"method": config.method, "empty": True}

    smoothed: list[float | None] = []
    for index in range(len(values)):
        if config.method == "moving_average" and config.centered:
            half_window = config.window_size // 2
            start = max(0, index - half_window)
            end = min(len(values), index + half_window + 1)
        else:
            start = max(0, index - config.window_size + 1)
            end = index + 1
        window = [value for value in values[start:end] if value is not None]
        smoothed.append(sum(window) / len(window) if window else None)
    return smoothed, {
        "method": config.method,
        "window_size": config.window_size,
        "centered": config.centered,
        "edge_handling": "truncate",
    }


def _quantile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - lower_index
    return ordered[lower_index] * (1 - fraction) + ordered[upper_index] * fraction
