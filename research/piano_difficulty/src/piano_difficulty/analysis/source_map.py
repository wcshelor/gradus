"""Source-span helpers for feature traceability.

Every feature should be able to point back to the score region it summarizes.
This module should eventually provide shared utilities for turning note or
direction collections into a stable location descriptor.
"""

from __future__ import annotations

from typing import Protocol


class HasMeasureIndex(Protocol):
    """Minimal protocol for objects that can contribute to a source span."""

    measure_index: int | None


def build_source_span(events: list[HasMeasureIndex]) -> dict[str, int | None]:
    """Build a coarse measure-span mapping from score events."""

    measure_indices = [
        event.measure_index for event in events if event.measure_index is not None
    ]
    if not measure_indices:
        return {"measure_start": None, "measure_end": None}

    return {
        "measure_start": min(measure_indices),
        "measure_end": max(measure_indices),
    }
