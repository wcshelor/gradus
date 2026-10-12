"""Post-processing difficulty-event explanation layer.

Metric-driven segmentation first, selective note inspection second.
Existing difficulty scores unchanged in v1.
"""

from __future__ import annotations

from .labeling import explain_flagged_span
from .models import (
    DIFFICULTY_EVENTS_SCHEMA,
    DIFFICULTY_EVENTS_SCHEMA_VERSION,
    DifficultyEvent,
    MetricEvidence,
    NoteEvidence,
    NoteSummary,
)
from .note_inspection import inspect_span
from .segmentation import SegmentCandidate, segment_by_metrics

__all__ = [
    "DIFFICULTY_EVENTS_SCHEMA",
    "DIFFICULTY_EVENTS_SCHEMA_VERSION",
    "DifficultyEvent",
    "MetricEvidence",
    "NoteEvidence",
    "NoteSummary",
    "SegmentCandidate",
    "explain_flagged_span",
    "inspect_span",
    "segment_by_metrics",
]
