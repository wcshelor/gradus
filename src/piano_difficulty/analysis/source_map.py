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

    raise NotImplementedError("Source span construction is not implemented yet.")

