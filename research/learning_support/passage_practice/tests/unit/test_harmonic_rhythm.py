"""Tests for S6.3 harmonic rhythm heuristic v1."""

from __future__ import annotations

from fractions import Fraction

import pytest

from passage_practice.views.harmony_view import build_harmony_view, infer_harmonic_rhythm
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from passage_practice.models.source import SourceKind, SourceRef


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, measure_number="1", offset_in_measure=q)


def _score_from_chords(chords: list[tuple[Fraction, list[int], Fraction]]):
    """chords: list of (onset, [midi], duration) where all mids share onset/duration."""
    class Note:
        def __init__(self, nid, midi, onset, dur, order):
            self.note_id = nid
            self.pitch_midi = midi
            self.onset = onset
            self.duration = dur
            self.xml_order = order

    notes = []
    refs = []
    order = 0
    for onset, mids, dur in chords:
        for midi in mids:
            nid = f"n{order}"
            notes.append(Note(nid, midi, onset, dur, order))
            refs.append(SourceRef(id=nid, kind=SourceKind.LOGICAL_NOTE))
            order += 1
    max_end = max((onset + dur for onset, _, dur in chords), default=Fraction(1))
    passage = Passage(
        passage_id="test.hr@[0,8)/harmony",
        score_id="test.hr",
        start=_pos(Fraction(0)),
        end=_pos(max_end if max_end > Fraction(0) else Fraction(1)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=tuple(refs),
    )
    class Score:
        logical_notes = notes
        measures = []
        written_notes = []
        directions = []
    return passage, Score()


def test_once_per_measure_harmony():
    # Two measures: C major chord (C E G) whole, then G major (G B D) whole
    chords = [
        (Fraction(0), [60, 64, 67], Fraction(4)),  # C E G
        (Fraction(4), [67, 71, 62], Fraction(4)),  # G B D
    ]
    passage, score = _score_from_chords(chords)
    view = build_harmony_view(passage, score)
    rhythm = infer_harmonic_rhythm(view)
    assert len(rhythm) == 2
    assert rhythm[0] == Fraction(0)
    assert rhythm[1] == Fraction(4)
    # Sonority points should match harmonic rhythm for this case
    assert view.sonority_points == rhythm


def test_every_beat_changes():
    # Four quarter chords each beat with different root
    chords = [
        (Fraction(0), [60, 64, 67], Fraction(1)),  # C
        (Fraction(1), [62, 65, 69], Fraction(1)),  # D minor approx
        (Fraction(2), [64, 67, 71], Fraction(1)),  # E minor
        (Fraction(3), [65, 69, 72], Fraction(1)),  # F
    ]
    passage, score = _score_from_chords(chords)
    view = build_harmony_view(passage, score)
    rhythm = infer_harmonic_rhythm(view)
    assert len(rhythm) == 4
    assert rhythm == (Fraction(0), Fraction(1), Fraction(2), Fraction(3))


def test_ornamental_non_chord_tone_filtered():
    # C major at 0, passing D 16th at 2 (short ornament), then G major at 4.
    # Harmonic rhythm should be 2 points (0 and 4), not 3, because D is filtered.
    chords = [
        (Fraction(0), [60, 64, 67], Fraction(4)),  # C E G
        (Fraction(2), [62], Fraction(1, 4)),  # D passing 16th (short)
        (Fraction(4), [67, 71, 74], Fraction(4)),  # G B D (new harmony)
    ]
    passage, score = _score_from_chords(chords)
    view = build_harmony_view(passage, score)
    rhythm = infer_harmonic_rhythm(view)
    # Ornamental D should be filtered, leaving 2 points (0 and 4)
    assert len(view.sonority_points) == 2
    assert len(rhythm) == 2
    assert rhythm[0] == Fraction(0)
    assert rhythm[1] == Fraction(4)
    assert Fraction(2) not in view.sonority_points


def test_ornamental_longer_not_filtered():
    # If ornamental tone is longer (quarter), it should count as change
    chords = [
        (Fraction(0), [60, 64, 67], Fraction(2)),  # C
        (Fraction(2), [62, 65, 69], Fraction(1)),  # D quarter (not short)
        (Fraction(4), [60, 64, 67], Fraction(2)),  # C again (but different from D)
    ]
    passage, score = _score_from_chords(chords)
    view = build_harmony_view(passage, score)
    rhythm = infer_harmonic_rhythm(view)
    # Longer D should not be filtered, so 3 points
    assert len(rhythm) == 3
