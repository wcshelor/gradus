"""JSON export helpers.

JSON should be the canonical output format for early development because it can
preserve detailed structure, diagnostics, and localizable feature metadata.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR

CORE_FEATURE_SCHEMA_VERSION = "core_features.v1"
PAYLOAD_SCHEMA = "piano_difficulty.score_payload"
PAYLOAD_SCHEMA_VERSION = "score_payload.v1"


def to_json_payload(
    score: ScoreIR,
    *,
    features: list[FeatureRecord] | None = None,
    piece_summary: dict[str, object] | None = None,
    measure_summaries: list[dict[str, object]] | None = None,
    analysis_profiles: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Convert normalized extraction results into a JSON-serializable payload."""

    feature_records = features or []
    return {
        "schema": PAYLOAD_SCHEMA,
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "core_feature_schema_version": CORE_FEATURE_SCHEMA_VERSION,
        "source": {
            "path": str(score.source_path) if score.source_path is not None else None,
        },
        "score": {
            "title": score.title,
            "composer": score.composer,
            "measure_count": len(score.measures),
            "written_note_count": len(score.written_notes),
            "logical_note_count": len(score.logical_notes),
        },
        "features": [_feature_to_payload(feature) for feature in feature_records],
        "piece_summary": piece_summary or {},
        "measure_summaries": measure_summaries or [],
        "analysis_profiles": analysis_profiles or [],
        "diagnostics": [
            {
                "code": diagnostic.code,
                "severity": diagnostic.severity,
                "message": diagnostic.message,
                "measure_start": diagnostic.measure_start,
                "measure_end": diagnostic.measure_end,
            }
            for diagnostic in score.diagnostics
        ],
    }


def _feature_to_payload(feature: FeatureRecord) -> dict[str, object]:
    return {
        "feature_id": feature.feature_id,
        "scope": feature.scope,
        "scope_ref": feature.scope_ref,
        "value": feature.value,
        "units": feature.units,
        "reliability": feature.reliability,
        "source_span": feature.source_span,
        "diagnostics": feature.diagnostics,
    }
