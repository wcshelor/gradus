"""Semantic hypothesis contracts for passage practice.

Grows incrementally through the S-track. S1.2/S1.3 provide the minimal
`SemanticHypothesis` and `SemanticBundle` payloads; detectors (S3),
pedagogical bridges (S4), and confidence helpers (S1.5) build on them.
"""

from .confidence import (
    HIGH_FLOOR,
    LOW_FLOOR,
    MEDIUM_FLOOR,
    PRESENTATION_FLOOR,
    ConfidenceBand,
    ConfidenceMethod,
    apply_contradiction_penalty,
    band_for,
    check_confidence,
    parse_method_status,
)
from .contracts import (
    SEMANTIC_BUNDLE_SCHEMA_VERSION,
    SEMANTIC_HYPOTHESIS_SCHEMA_VERSION,
    SemanticBundle,
    SemanticHypothesis,
)

__all__ = [
    "HIGH_FLOOR",
    "LOW_FLOOR",
    "MEDIUM_FLOOR",
    "PRESENTATION_FLOOR",
    "SEMANTIC_BUNDLE_SCHEMA_VERSION",
    "SEMANTIC_HYPOTHESIS_SCHEMA_VERSION",
    "ConfidenceBand",
    "ConfidenceMethod",
    "SemanticBundle",
    "SemanticHypothesis",
    "apply_contradiction_penalty",
    "band_for",
    "check_confidence",
    "parse_method_status",
]
