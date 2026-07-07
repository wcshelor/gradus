from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (_REPO_ROOT, _REPO_ROOT / "src"):
    _candidate_str = str(_candidate)
    if _candidate_str not in sys.path:
        sys.path.insert(0, _candidate_str)

from piano_difficulty.normalize.schema import LogicalNoteIR
from tests.harness.yan2023.leap_measures import compute_hand_leap_proxy


def _note(
    note_id: str,
    pitch_midi: int,
    onset: Fraction,
    duration: Fraction,
    *,
    hand: str,
    staff: int,
) -> LogicalNoteIR:
    return LogicalNoteIR(
        note_id=note_id,
        pitch_midi=pitch_midi,
        onset=onset,
        duration=duration,
        staff=staff,
        voice="1",
        hand=hand,
    )


def test_compute_hand_leap_proxy_uses_gap_weighted_thresholds() -> None:
    notes = [
        _note("n1", 60, Fraction(0), Fraction(1, 2), hand="right", staff=1),
        _note("n2", 70, Fraction(1), Fraction(1, 2), hand="right", staff=1),
        _note("n3", 82, Fraction(2), Fraction(1, 2), hand="right", staff=1),
    ]

    value, diagnostics = compute_hand_leap_proxy(notes, "right")

    assert round(value, 3) == 0.375
    assert "hand_leap_noticeable_count=2" in diagnostics
    assert "hand_leap_difficult_count=1" in diagnostics
    assert "hand_leap_long_rest_filtered=0" in diagnostics


def test_compute_hand_leap_proxy_filters_long_rests() -> None:
    notes = [
        _note("n1", 60, Fraction(0), Fraction(1, 2), hand="left", staff=2),
        _note("n2", 72, Fraction(6), Fraction(1, 2), hand="left", staff=2),
    ]

    value, diagnostics = compute_hand_leap_proxy(notes, "left")

    assert value == 0.0
    assert "hand_leap_long_rest_filtered=1" in diagnostics
