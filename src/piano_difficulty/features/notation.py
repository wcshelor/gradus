"""Notation and reading-complexity descriptors.

This family should eventually operate on written-note tokens and measure context
rather than logical attack events. Early direct features include accidental
density, clef changes, cross-staff notation counts, and ledger-line burden.
"""

from __future__ import annotations

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import feature_record
from piano_difficulty.normalize.schema import ClefIR, ScoreIR, WrittenNoteIR

_STEP_INDEX = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
_CLEF_ANCHORS = {
    "G": ("G", 4, 2),
    "F": ("F", 3, 4),
    "C": ("C", 4, 3),
}
_DEFAULT_PIANO_CLEFS = {
    1: ("G", 2),
    2: ("F", 4),
}


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract notation-sensitive descriptors from written score objects."""

    metrics = compute_reference_metrics(score)
    accidental_count = sum(1 for note in score.written_notes if note.accidental)
    accidental_density = (
        accidental_count / len(score.written_notes) if score.written_notes else 0.0
    )
    cross_staff_notes = [
        note for note in score.written_notes if _is_explicit_cross_staff(note)
    ]
    ledger_burden, ledger_diagnostics = _ledger_line_burden(score)

    records = [
        feature_record(
            "notation.accidental_density",
            value=accidental_density,
            units="ratio",
            events=score.written_notes,
        ),
        feature_record(
            "notation.clef_change_count",
            value=_clef_change_count(score.clefs),
            units="changes",
            events=score.clefs,
        ),
        feature_record(
            "notation.cross_staff_note_count",
            value=len(cross_staff_notes),
            units="notes",
            events=score.written_notes,
            diagnostics=[
                "Counts only explicit hand/staff conflicts available in ScoreIR."
            ],
        ),
        feature_record(
            "notation.ledger_line_burden",
            value=ledger_burden,
            units="ledger_lines",
            events=score.written_notes,
            diagnostics=ledger_diagnostics,
        ),
    ]
    for hand, hand_metrics in metrics.hand_metrics.items():
        records.extend(
            [
                feature_record(
                    "notation.accidental_count",
                    value=hand_metrics.accidental_count,
                    units="notes",
                    events=list(hand_metrics.notes),
                    scope="hand",
                    scope_ref=hand,
                ),
                feature_record(
                    "notation.accidental_ratio",
                    value=hand_metrics.accidental_ratio,
                    units="percent",
                    events=list(hand_metrics.notes),
                    scope="hand",
                    scope_ref=hand,
                ),
            ]
        )
        for measure_index, count in hand_metrics.accidental_measure_counts.items():
            records.append(
                feature_record(
                    "notation.accidental_count",
                    value=count,
                    units="notes",
                    events=[
                        note
                        for note in hand_metrics.notes
                        if note.measure_index == measure_index and note.accidental
                    ],
                    scope="measure",
                    scope_ref=str(measure_index),
                )
            )
    return records


def _clef_change_count(clefs: list[ClefIR]) -> int:
    changes = 0
    previous_by_staff: dict[int | None, tuple[str, int | None]] = {}
    for clef in sorted(clefs, key=lambda c: (c.measure_index or 0, c.clef_id)):
        current = (clef.sign, clef.line)
        previous = previous_by_staff.get(clef.staff)
        if previous is not None and current != previous:
            changes += 1
        previous_by_staff[clef.staff] = current
    return changes


def _is_explicit_cross_staff(note: WrittenNoteIR) -> bool:
    return (
        (note.staff == 1 and note.hand == "left")
        or (note.staff == 2 and note.hand == "right")
    )


def _ledger_line_burden(score: ScoreIR) -> tuple[int, list[str]]:
    diagnostics: list[str] = []
    if not score.clefs:
        diagnostics.append("No clef declarations found; assumed standard piano clefs.")

    clefs_by_staff: dict[int | None, list[ClefIR]] = {}
    for clef in score.clefs:
        clefs_by_staff.setdefault(clef.staff, []).append(clef)

    for clefs in clefs_by_staff.values():
        clefs.sort(key=lambda c: (c.measure_index or 0, c.clef_id))

    burden = 0
    for note in score.written_notes:
        clef = _active_clef(note, clefs_by_staff)
        burden += _ledger_lines_for_note(note, clef)

    return burden, diagnostics


def _active_clef(
    note: WrittenNoteIR,
    clefs_by_staff: dict[int | None, list[ClefIR]],
) -> tuple[str, int | None]:
    default_clef = _DEFAULT_PIANO_CLEFS.get(note.staff or 0, ("G", 2))
    active = default_clef
    for clef in clefs_by_staff.get(note.staff, []):
        if note.measure_index is not None and clef.measure_index is not None:
            if clef.measure_index > note.measure_index:
                break
        active = (clef.sign, clef.line)
    return active


def _ledger_lines_for_note(
    note: WrittenNoteIR,
    clef: tuple[str, int | None],
) -> int:
    if note.pitch_step not in _STEP_INDEX or note.pitch_octave is None:
        return 0

    sign, line = clef
    anchor = _CLEF_ANCHORS.get(sign)
    if anchor is None:
        return 0

    anchor_step, anchor_octave, default_line = anchor
    clef_line = line or default_line
    anchor_position = 2 * (clef_line - 1)
    note_index = _diatonic_index(note.pitch_step, note.pitch_octave)
    anchor_index = _diatonic_index(anchor_step, anchor_octave)
    staff_position = anchor_position + (note_index - anchor_index)

    if staff_position < 0:
        return -staff_position // 2
    if staff_position > 8:
        return (staff_position - 8) // 2
    return 0


def _diatonic_index(step: str, octave: int) -> int:
    return octave * 7 + _STEP_INDEX[step]
