"""Converters from parser-native score objects into the repository IR.

This module should eventually contain the most parser-specific logic that still
belongs inside the normalization layer. Its job is to interpret parser objects
once and convert them into reusable repository-native structures.
"""

from __future__ import annotations

from typing import Any

from piano_difficulty.normalize.schema import (
    DirectionIR,
    LogicalNoteIR,
    MeasureIR,
    ScoreIR,
    WrittenNoteIR,
)


def build_score_ir(parsed_score: Any) -> ScoreIR:
    """Build the top-level normalized score object from parser-native data."""

    raise NotImplementedError("Score normalization is not implemented yet.")


def normalize_measures(parsed_score: Any) -> list[MeasureIR]:
    """Extract normalized measures with stable timing and numbering."""

    raise NotImplementedError("Measure normalization is not implemented yet.")


def normalize_written_notes(parsed_score: Any) -> list[WrittenNoteIR]:
    """Extract written-note tokens suitable for notation-aware features."""

    raise NotImplementedError("Written note normalization is not implemented yet.")


def normalize_directions(parsed_score: Any) -> list[DirectionIR]:
    """Extract normalized score directions and control markings."""

    raise NotImplementedError("Direction normalization is not implemented yet.")


def collapse_ties(written_notes: list[WrittenNoteIR]) -> list[LogicalNoteIR]:
    """Collapse tied written notes into logical attack events.

    This helper is a major boundary in the data model because many direct
    descriptors should operate on logical attacks rather than written fragments.
    """

    raise NotImplementedError("Tie collapsing is not implemented yet.")

