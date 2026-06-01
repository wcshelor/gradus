"""Helpers for constructing reusable score views.

Most feature extractors should not perform raw regrouping every time they run.
This module is intended to centralize common indexing and grouping operations so
extractors can stay small and deterministic.
"""

from __future__ import annotations

from collections import defaultdict

from piano_difficulty.normalize.schema import LogicalNoteIR, OnsetGroupIR, WrittenNoteIR


def group_onsets(notes: list[LogicalNoteIR]) -> list[OnsetGroupIR]:
    """Group logical notes that begin at the same onset.

    The eventual implementation should support both global grouping and
    hand-specific grouping derived from the same normalized note stream.
    """

    grouped: dict[object, list[LogicalNoteIR]] = defaultdict(list)
    for note in notes:
        grouped[note.onset].append(note)

    return [
        OnsetGroupIR(
            onset=onset,
            hand=None,
            note_ids=tuple(note.note_id for note in sorted(group, key=_note_order)),
            measure_index=min(
                (note.measure_index for note in group if note.measure_index is not None),
                default=None,
            ),
        )
        for onset, group in sorted(grouped.items(), key=lambda item: item[0])
    ]


def group_onsets_by_hand(notes: list[LogicalNoteIR]) -> list[OnsetGroupIR]:
    """Group logical notes by exact onset and assigned hand."""

    grouped: dict[tuple[object, str], list[LogicalNoteIR]] = defaultdict(list)
    for note in notes:
        if note.hand is None:
            continue
        grouped[(note.onset, note.hand)].append(note)

    return [
        OnsetGroupIR(
            onset=onset,
            hand=hand,
            note_ids=tuple(note.note_id for note in sorted(group, key=_note_order)),
            measure_index=min(
                (note.measure_index for note in group if note.measure_index is not None),
                default=None,
            ),
        )
        for (onset, hand), group in sorted(grouped.items(), key=lambda item: item[0])
    ]


def index_written_notes_by_measure(
    notes: list[WrittenNoteIR],
) -> dict[int, list[WrittenNoteIR]]:
    """Return written notes grouped by measure index."""

    result: dict[int, list[WrittenNoteIR]] = defaultdict(list)
    for note in notes:
        if note.measure_index is not None:
            result[note.measure_index].append(note)
    return {
        measure_index: sorted(group, key=_note_order)
        for measure_index, group in sorted(result.items())
    }


def index_logical_notes_by_hand(
    notes: list[LogicalNoteIR],
) -> dict[str, list[LogicalNoteIR]]:
    """Return logical notes grouped by inferred or assigned hand."""

    result: dict[str, list[LogicalNoteIR]] = defaultdict(list)
    for note in notes:
        if note.hand is not None:
            result[note.hand].append(note)
    return {
        hand: sorted(group, key=_note_order)
        for hand, group in sorted(result.items())
    }


def _note_order(note: WrittenNoteIR | LogicalNoteIR) -> tuple[object, int]:
    return note.onset, note.xml_order or 0
