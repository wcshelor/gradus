"""Helpers for constructing reusable score views.

Most feature extractors should not perform raw regrouping every time they run.
This module is intended to centralize common indexing and grouping operations so
extractors can stay small and deterministic.
"""

from __future__ import annotations

from piano_difficulty.normalize.schema import LogicalNoteIR, OnsetGroupIR, WrittenNoteIR


def group_onsets(notes: list[LogicalNoteIR]) -> list[OnsetGroupIR]:
    """Group logical notes that begin at the same onset.

    The eventual implementation should support both global grouping and
    hand-specific grouping derived from the same normalized note stream.
    """

    raise NotImplementedError("Onset grouping is not implemented yet.")


def index_written_notes_by_measure(
    notes: list[WrittenNoteIR],
) -> dict[int, list[WrittenNoteIR]]:
    """Return written notes grouped by measure index."""

    raise NotImplementedError("Measure indexing is not implemented yet.")


def index_logical_notes_by_hand(
    notes: list[LogicalNoteIR],
) -> dict[str, list[LogicalNoteIR]]:
    """Return logical notes grouped by inferred or assigned hand."""

    raise NotImplementedError("Hand indexing is not implemented yet.")

