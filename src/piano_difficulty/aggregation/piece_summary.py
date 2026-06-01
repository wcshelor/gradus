"""Piece-level aggregation helpers.

Feature extractors should produce localizable raw facts. This module should
eventually summarize those facts at the whole-piece level without destroying the
underlying traceability metadata.
"""

from __future__ import annotations

from collections import defaultdict

from piano_difficulty.features.base import FeatureRecord


def summarize_piece(features: list[FeatureRecord]) -> dict[str, object]:
    """Aggregate raw feature records into a piece-level summary payload."""

    grouped: dict[str, list[FeatureRecord]] = defaultdict(list)
    for feature in features:
        if feature.scope != "measure":
            grouped[feature.feature_id].append(feature)

    return {
        "feature_count": len(features),
        "features": {
            feature_id: _summarize_records(records)
            for feature_id, records in sorted(grouped.items())
        },
    }


def _summarize_records(records: list[FeatureRecord]) -> object:
    if (
        len(records) == 1
        and records[0].scope == "piece"
        and records[0].scope_ref == "all"
    ):
        return {
            "value": records[0].value,
            "units": records[0].units,
            "reliability": records[0].reliability,
        }

    return [
        {
            "scope": record.scope,
            "scope_ref": record.scope_ref,
            "value": record.value,
            "units": record.units,
            "reliability": record.reliability,
        }
        for record in records
    ]
