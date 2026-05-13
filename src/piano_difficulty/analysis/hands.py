"""Hand-assignment helpers for piano score analysis.

This subsystem should remain conservative in the first implementation. Many
later features depend on hand labels, so v0 should prefer explicit and
explainable staff-based logic plus confidence flags instead of aggressive
cross-staff inference.
"""

from __future__ import annotations

from piano_difficulty.normalize.schema import LogicalNoteIR, WrittenNoteIR


def assign_hands_to_written_notes(
    notes: list[WrittenNoteIR],
) -> list[WrittenNoteIR]:
    """Populate hand labels on written notes.

    The final implementation should start with grand-staff information and only
    introduce stronger heuristics when those heuristics can be tested well.
    """

    raise NotImplementedError("Written-note hand assignment is not implemented yet.")


def assign_hands_to_logical_notes(
    notes: list[LogicalNoteIR],
) -> list[LogicalNoteIR]:
    """Populate hand labels on logical notes."""

    raise NotImplementedError("Logical-note hand assignment is not implemented yet.")

