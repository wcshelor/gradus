"""Compatibility imports; implementation is owned by piano_difficulty.difficulty_analysis.dynamics.core."""

from piano_difficulty.difficulty_analysis.dynamics.core import *  # noqa: F401,F403
from piano_difficulty.difficulty_analysis.dynamics.core import (
    _build_feature_series,
    _build_composite_series,
    _collect_peak_passages,
    _build_hotspots,
    _series_value_at,
    _attribution_value,
    _build_peak_passage,
    _resolve_feature_record,
    _slice_score_to_region,
    _feature_provenance,
    _human_feature_name,
    _score_identifier,
    _percentile_threshold,
    _is_local_maximum,
    _build_regions,
)
