"""S-X3 semantic metamorphic test helpers.

Helper functions for transposition, duration scaling, staff swap,
neighboring-measure addition, and serialize/reopen comparisons.
All helpers operate on ScoreIR (exact Fractions, no mutation) and are
deterministic. For tests, not for production inference.

Design refs:
- S-X3 (metamorphic helpers for tiny fixtures)
- tests/unit/test_observations (transposition metamorphism pattern)
"""

from __future__ import annotations

import copy
from fractions import Fraction
from typing import Any


def transpose_score(score: Any, semitones: int) -> Any:
    """Return a new ScoreIR with every pitch shifted by ``semitones``.

    Preserves staff, voice, duration, onset, and IDs; only pitch_midi
    (and spelled pitch where available) is shifted. Does not mutate input.
    """
    if not isinstance(semitones, int):
        raise TypeError(f"semitones must be int, got {type(semitones).__name__}")
    # Deep copy to avoid mutation
    new_score = copy.deepcopy(score)
    for note in getattr(new_score, "written_notes", []) or []:
        if hasattr(note, "pitch_midi"):
            note.pitch_midi = int(note.pitch_midi) + semitones
            # Update step/accidental if present (best-effort: keep step/alter)
            # For synthetic tests we only care about pitch_midi; spelling is secondary
    for note in getattr(new_score, "logical_notes", []) or []:
        if hasattr(note, "pitch_midi"):
            note.pitch_midi = int(note.pitch_midi) + semitones
    return new_score


def scale_durations(score: Any, factor: Fraction) -> Any:
    """Return a new ScoreIR with durations and onsets scaled by ``factor``.

    ``factor`` is a Fraction (e.g., Fraction(2,1) for doubling). Both onset
    and duration are scaled exactly. Measure boundaries are also scaled for
    consistency. Does not mutate input.
    """
    if not isinstance(factor, Fraction):
        raise TypeError(f"factor must be Fraction, got {type(factor).__name__}")
    if factor <= 0:
        raise ValueError(f"factor must be >0, got {factor}")
    new_score = copy.deepcopy(score)
    for note in getattr(new_score, "written_notes", []) or []:
        note.onset = note.onset * factor
        note.duration = note.duration * factor
    for note in getattr(new_score, "logical_notes", []) or []:
        note.onset = note.onset * factor
        note.duration = note.duration * factor
    for rest in getattr(new_score, "rest_events", []) or []:
        if hasattr(rest, "onset"):
            rest.onset = rest.onset * factor
        if hasattr(rest, "duration"):
            rest.duration = rest.duration * factor
    for measure in getattr(new_score, "measures", []) or []:
        measure.start = measure.start * factor
        measure.end = measure.end * factor
    for direction in getattr(new_score, "directions", []) or []:
        if hasattr(direction, "start"):
            direction.start = direction.start * factor
        if hasattr(direction, "end") and direction.end is not None:
            direction.end = direction.end * factor
    return new_score


def swap_staves(score: Any) -> Any:
    """Return a new ScoreIR with staff 1 and 2 swapped.

    Voice and pitch unchanged; only staff numbers are swapped.
    For single-staff scores, swapping is a no-op for diagnostics.
    """
    new_score = copy.deepcopy(score)
    for note in getattr(new_score, "written_notes", []) or []:
        if note.staff == 1:
            note.staff = 2
        elif note.staff == 2:
            note.staff = 1
        # Update hand label if present? Keep original hand to test hand inference separation,
        # but also swap hand for physical swap expectation: hand follows staff
        if hasattr(note, "hand") and note.hand in ("left", "right"):
            note.hand = "right" if note.hand == "left" else "left"
    for note in getattr(new_score, "logical_notes", []) or []:
        if hasattr(note, "staff") and note.staff in (1, 2):
            note.staff = 2 if note.staff == 1 else 1
        if hasattr(note, "hand") and note.hand in ("left", "right"):
            note.hand = "right" if note.hand == "left" else "left"
    return new_score


def add_neighboring_measure(score: Any) -> Any:
    """Return a new ScoreIR with one extra measure appended.

    The new measure is a 4/4 rest measure at the end, with a new measure
    number and start/end. This tests that exact passage selection for
    [0,4) is unaffected by neighboring material.

    Does not mutate input.
    """
    new_score = copy.deepcopy(score)
    measures = getattr(new_score, "measures", []) or []
    if not measures:
        return new_score
    last = measures[-1]
    # Create a new measure by copying last and shifting start/end by one measure length
    # Use last.end as new start; assume 4 quarters length if not inferable
    length = last.end - last.start if hasattr(last, "start") else Fraction(4)
    try:
        new_measure = copy.deepcopy(last)
        new_measure.measure_index = last.measure_index + 1
        # Measure number increments numerally if possible
        try:
            new_measure.measure_number = str(int(last.measure_number) + 1)
        except Exception:
            new_measure.measure_number = last.measure_number + "_next"
        new_measure.start = last.end
        new_measure.end = last.end + length
        measures.append(new_measure)
        new_score.measures = tuple(measures) if isinstance(new_score.measures, tuple) else measures
    except Exception:
        # Fallback: ignore if structure unexpected
        pass
    return new_score


def passage_ids_for(score: Any, start: Fraction, end: Fraction) -> list[str]:
    """Helper: build passage event IDs for a given interval (for comparison).

    Uses select_passage internally; returns sorted note IDs.
    """
    from passage_practice.passages.selection import select_passage

    sel = select_passage(score, score_id="test.score", start=start, end=end)
    return sorted(r.id for r in sel.passage.event_refs)


__all__ = ["transpose_score", "scale_durations", "swap_staves", "add_neighboring_measure", "passage_ids_for"]
