"""Measure-level aggregation helpers.

The repository should expose local difficulty structure, not just whole-piece
descriptors. This module should eventually build stable per-measure views from
raw feature records and score context.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord


def summarize_measures(features: list[FeatureRecord]) -> list[dict[str, object]]:
    """Aggregate feature records into measure-scoped summaries."""

    raise NotImplementedError("Measure aggregation is not implemented yet.")

