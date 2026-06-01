"""Hand-assignment helpers for piano score analysis.

This subsystem should remain conservative in the first implementation. Many
later features depend on hand labels, so v0 should prefer explicit and
explainable staff-based logic plus confidence flags instead of aggressive
cross-staff inference.
"""

from __future__ import annotations

from piano_difficulty.normalize.schema import LogicalNoteIR, RestEventIR, WrittenNoteIR


def _assign_staff_hand(event: WrittenNoteIR | LogicalNoteIR | RestEventIR) -> None:
    if event.staff == 1:
        event.hand = "right"
        event.hand_confidence = "staff"
    elif event.staff == 2:
        event.hand = "left"
        event.hand_confidence = "staff"
    elif event.staff is not None:
        event.hand = None
        event.hand_confidence = "unknown_staff"


def assign_hands_to_written_notes(
    notes: list[WrittenNoteIR],
) -> list[WrittenNoteIR]:
    """Populate hand labels on written notes.

    The final implementation should start with grand-staff information and only
    introduce stronger heuristics when those heuristics can be tested well.
    """

    for note in notes:
        _assign_staff_hand(note)
    return notes


def assign_hands_to_logical_notes(
    notes: list[LogicalNoteIR],
) -> list[LogicalNoteIR]:
    """Populate hand labels on logical notes."""

    for note in notes:
        _assign_staff_hand(note)
    return notes


def assign_hands_to_rests(rests: list[RestEventIR]) -> list[RestEventIR]:
    """Populate hand labels on rest events."""

    for rest in rests:
        _assign_staff_hand(rest)
    return rests
