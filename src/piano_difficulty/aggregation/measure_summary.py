"""Measure-level aggregation helpers.

The repository should expose local difficulty structure, not just whole-piece
descriptors. This module should eventually build stable per-measure views from
raw feature records and score context.
"""

from __future__ import annotations

from collections import defaultdict

from piano_difficulty.features.base import FeatureRecord


def summarize_measures(features: list[FeatureRecord]) -> list[dict[str, object]]:
    """Aggregate feature records into measure-scoped summaries."""

    by_measure: dict[int, list[FeatureRecord]] = defaultdict(list)
    for feature in features:
        measure_index = _single_measure_index(feature)
        if measure_index is not None:
            by_measure[measure_index].append(feature)

    return [
        {
            "measure_index": measure_index,
            "features": [
                {
                    "feature_id": feature.feature_id,
                    "scope": feature.scope,
                    "scope_ref": feature.scope_ref,
                    "value": feature.value,
                    "units": feature.units,
                    "reliability": feature.reliability,
                }
                for feature in sorted(
                    records,
                    key=lambda record: (
                        record.feature_id,
                        record.scope,
                        record.scope_ref,
                    ),
                )
            ],
        }
        for measure_index, records in sorted(by_measure.items())
    ]


def _single_measure_index(feature: FeatureRecord) -> int | None:
    if feature.scope == "measure":
        try:
            return int(feature.scope_ref)
        except ValueError:
            return None

    start = feature.source_span.get("measure_start")
    end = feature.source_span.get("measure_end")
    if start is not None and start == end:
        return start
    return None
