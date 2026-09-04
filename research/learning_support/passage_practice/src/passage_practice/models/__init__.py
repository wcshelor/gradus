"""Cross-layer contract models for passage practice.

This package grows incrementally through WP-01. T01.1 provides exact-time
value objects; T01.2 adds source identity; T01.3 adds diagnostics; T01.4
adds passage/view containers.
"""

from .diagnostics import DIAGNOSTIC_SCHEMA_VERSION, Diagnostic, Severity
from .passage import PASSAGE_SCHEMA_VERSION, VIEW_SCHEMA_VERSION, Passage, PassagePurpose, View, ViewType
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
    "DIAGNOSTIC_SCHEMA_VERSION",
    "Diagnostic",
    "PASSAGE_SCHEMA_VERSION",
    "VIEW_SCHEMA_VERSION",
    "Passage",
    "PassagePurpose",
    "SCORE_INTERVAL_SCHEMA_VERSION",
    "SCORE_POSITION_SCHEMA_VERSION",
    "SOURCE_REF_SCHEMA_VERSION",
    "ScoreInterval",
    "ScorePosition",
    "Severity",
    "SourceKind",
    "SourceRef",
    "View",
    "ViewType",
    "fraction_from_json",
    "fraction_to_json",
    "is_resolvable",
    "refs_for_score",
    "resolve_ref",
]
