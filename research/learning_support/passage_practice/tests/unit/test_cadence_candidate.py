"""Tests for S6.4 cadence candidate heuristic v1."""

from __future__ import annotations

from fractions import Fraction

import pytest

from passage_practice.views.harmony_view import build_harmony_view
from passage_practice.semantics.cadence import detect_cadence_candidates
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from passage_practice.models.source import SourceKind, SourceRef


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, measure_number="1", offset_in_measure=q)


def _score_with_measures_and_notes(notes: list[tuple[int, Fraction, Fraction]], measures):
    """notes: list of (midi, onset, duration), measures: list of (start, end, beat_type)"""
    class Note:
        def __init__(self, nid, midi, onset, dur, order):
            self.note_id = nid
            self.pitch_midi = midi
            self.onset = onset
            self.duration = dur
            self.xml_order = order

    class Measure:
        def __init__(self, start, end, beat_type):
            self.start = start
            self.end = end
            self.time_beat_type = beat_type
            self.time_beats = 4

    note_objs = [Note(f"n{i}", midi, onset, dur, i) for i, (midi, onset, dur) in enumerate(notes)]
    measure_objs = [Measure(Fraction(s), Fraction(e), bt) for s, e, bt in measures]
    refs = tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in note_objs)
    max_end = max((onset + dur for _, onset, dur in notes), default=Fraction(4))
    passage = Passage(
        passage_id="test.cad@[0,4)/harmony",
        score_id="test.cad",
        start=_pos(Fraction(0)),
        end=_pos(max_end if max_end > Fraction(0) else Fraction(4)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=refs,
    )
    class Score:
        logical_notes = note_objs
        measures = measure_objs
        written_notes = []
        directions = []
    return passage, Score()


def test_simple_cadence_positive():
    # C major: penultimate G (dominant) at 2, final C at 4 on downbeat, long
    # Provide diatonic context to ensure high key confidence (C major)
    notes = [
        (60, Fraction(0), Fraction(1)),  # C
        (64, Fraction(1), Fraction(1)),  # E
        (67, Fraction(2), Fraction(1)),  # G dominant (penult)
        (60, Fraction(4), Fraction(2)),  # C tonic final, long, downbeat of next measure
        # Add extra diatonic notes to boost C major confidence
        (62, Fraction(0), Fraction(1)),  # D
        (65, Fraction(1), Fraction(1)),  # F
        (69, Fraction(1), Fraction(1)),  # A
        (71, Fraction(2), Fraction(1)),  # B
    ]
    # Measures: 0-4 and 4-8, beat_type 4
    measures = [(0, 4, 4), (4, 8, 4)]
    passage, score = _score_with_measures_and_notes(notes, measures)
    from passage_practice.views.harmony_view import build_harmony_view
    view = build_harmony_view(passage, score)
    # Ensure high key confidence
    assert view.local_key_candidates[0][0] == "C"
    assert view.local_key_candidates[0][1] >= 0.65
    candidates, diags = detect_cadence_candidates(view, passage, score)
    assert len(candidates) == 1
    assert candidates[0].onset == Fraction(4)
    assert candidates[0].confidence >= 0.75


def test_cadence_like_negative_off_beat_or_short():
    # Same pcs but final C is off-beat (4.5) or short duration
    notes = [
        (60, Fraction(0), Fraction(1)),
        (64, Fraction(1), Fraction(1)),
        (67, Fraction(2), Fraction(1)),  # G
        (60, Fraction(4, 1) + Fraction(1, 2), Fraction(1, 4)),  # C off-beat short
        (62, Fraction(0), Fraction(1)),
        (65, Fraction(1), Fraction(1)),
    ]
    measures = [(0, 4, 4), (4, 8, 4)]
    passage, score = _score_with_measures_and_notes(notes, measures)
    view = build_harmony_view(passage, score)
    candidates, diags = detect_cadence_candidates(view, passage, score)
    assert len(candidates) == 0
    assert any(d.code in ("cadence_not_on_downbeat", "cadence_duration_too_short") for d in diags)


def test_low_key_confidence_abstention():
    # Chromatic: all 12 pcs, low key confidence
    notes = [(60 + i, Fraction(i), Fraction(1)) for i in range(12)]
    measures = [(0, 4, 4), (4, 8, 4), (8, 12, 4)]
    passage, score = _score_with_measures_and_notes(notes, measures)
    view = build_harmony_view(passage, score)
    assert view.local_key_candidates[0][1] < 0.65
    candidates, diags = detect_cadence_candidates(view, passage, score)
    assert len(candidates) == 0
    assert any(d.code == "low_key_confidence_abstention" for d in diags)


def test_cadence_with_phrase_boundary_boost():
    notes = [
        (60, Fraction(0), Fraction(1)),
        (64, Fraction(1), Fraction(1)),
        (67, Fraction(2), Fraction(1)),
        (60, Fraction(4), Fraction(2)),
        (62, Fraction(0), Fraction(1)),
        (65, Fraction(1), Fraction(1)),
    ]
    measures = [(0, 4, 4), (4, 8, 4)]
    passage, score = _score_with_measures_and_notes(notes, measures)
    view = build_harmony_view(passage, score)
    candidates_no_phrase, _ = detect_cadence_candidates(view, passage, score)
    candidates_with_phrase, diags = detect_cadence_candidates(view, passage, score, phrase_boundaries=(Fraction(4),))
    assert len(candidates_with_phrase) == 1
    assert candidates_with_phrase[0].confidence > candidates_no_phrase[0].confidence
    assert any(d.code == "phrase_boundary_supports_cadence" for d in diags)
