"""Cross-layer contract models for passage practice.

This package will grow incrementally through WP-01. T01.1 provides exact-time
value objects; later tasks add identity, diagnostics, and passage containers.
"""

from .time import (
    SCORE_INTERVAL_SCHEMA_VERSION,
    SCORE_POSITION_SCHEMA_VERSION,
    ScoreInterval,
    ScorePosition,
    fraction_from_json,
    fraction_to_json,
)

__all__ = [
    "SCORE_INTERVAL_SCHEMA_VERSION",
    "SCORE_POSITION_SCHEMA_VERSION",
    "ScoreInterval",
    "ScorePosition",
    "fraction_from_json",
    "fraction_to_json",
]
