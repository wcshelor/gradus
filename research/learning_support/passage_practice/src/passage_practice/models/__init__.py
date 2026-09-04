"""Cross-layer contract models for passage practice.

This package grows incrementally through WP-01. T01.1 provides exact-time
value objects; T01.2 adds stable source identity primitives.
"""

from .source import (
    SOURCE_REF_SCHEMA_VERSION,
    SourceKind,
    SourceRef,
    is_resolvable,
    refs_for_score,
    resolve_ref,
)
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
    "SOURCE_REF_SCHEMA_VERSION",
    "ScoreInterval",
    "ScorePosition",
    "SourceKind",
    "SourceRef",
    "fraction_from_json",
    "fraction_to_json",
    "is_resolvable",
    "refs_for_score",
    "resolve_ref",
]
