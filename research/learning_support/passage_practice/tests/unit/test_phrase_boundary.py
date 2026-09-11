"""Tests for S6.5 phrase-boundary heuristic v1."""

from __future__ import annotations

from fractions import Fraction

import pytest

from passage_practice.semantics.phrase import detect_phrase_boundaries
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from passage_practice.models.source import SourceKind, SourceRef


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, measure_number="1", offset_in_measure=q)


def _score_with_notes_and_rests(notes, rests=None, measures=None):
    class Note:
        def __init__(self, nid, midi, onset, dur, order):
            self.note_id = nid
            self.pitch_midi = midi
            self.onset = onset
            self.duration = dur
            self.xml_order = order

    class Rest:
        def __init__(self, rid, onset, dur):
            self.rest_id = rid
            self.onset = onset
            self.duration = dur

    class Measure:
        def __init__(self, start, end, bt=4):
            self.start = start
            self.end = end
            self.time_beat_type = bt
            self.time_beats = 4

    note_objs = [Note(f"n{i}", midi, onset, dur, i) for i, (midi, onset, dur) in enumerate(notes)]
    rest_objs = [Rest(f"r{i}", onset, dur) for i, (onset, dur) in enumerate(rests or [])]
    measure_objs = [Measure(Fraction(s), Fraction(e), bt) for s, e, bt in (measures or [(0, 8, 4)])]
    refs = tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in note_objs)
    max_end = max((onset + dur for _, onset, dur in notes), default=Fraction(4))
    # Passage end at max_end + gap for rest
    passage_end = max_end + Fraction(1)
    passage = Passage(
        passage_id="test.phrase@[0,8)/phrase",
        score_id="test.phrase",
        start=_pos(Fraction(0)),
        end=_pos(passage_end),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=refs,
    )
    class Score:
        logical_notes = note_objs
        rests = rest_objs
        measures = measure_objs
        written_notes = []
        directions = []
    return passage, Score()


def test_clear_boundary_with_rest_and_long_note():
    # Long note (2 quarters) at 0, rest at 2, next onset at 4 on downbeat -> boundary at 4
    notes = [
        (60, Fraction(0), Fraction(2)),  # long C
        (62, Fraction(4), Fraction(1)),  # D at next measure
    ]
    rests = [(Fraction(2), Fraction(2))]  # rest filling gap
    measures = [(0, 4, 4), (4, 8, 4)]
    passage, score = _score_with_notes_and_rests(notes, rests, measures)
    boundaries, diags = detect_phrase_boundaries(passage, score)
    assert any(b.onset == Fraction(4) for b in boundaries)
    assert any(b.confidence >= 0.6 for b in boundaries if b.onset == Fraction(4))


def test_tie_over_boundary_negative():
    # Note starting at 0 with duration 4 sustains over onset 2, so boundary at 2 should not be detected
    notes = [
        (60, Fraction(0), Fraction(4)),  # sustains over 2
        (62, Fraction(2), Fraction(1)),  # D at 2, but tie sustains over
    ]
    passage, score = _score_with_notes_and_rests(notes, rests=[], measures=[(0, 4, 4), (4, 8, 4)])
    boundaries, diags = detect_phrase_boundaries(passage, score)
    # Boundary at 2 should be blocked by tie_over
    assert not any(b.onset == Fraction(2) for b in boundaries)


def test_phrase_continuation_ambiguity():
    # Repeated motif C D E, C D E -> ambiguity, should produce low confidence or ambiguity diagnostic
    notes = [
        (60, Fraction(0), Fraction(1)),  # C
        (62, Fraction(1), Fraction(1)),  # D
        (64, Fraction(2), Fraction(1)),  # E
        (60, Fraction(3), Fraction(1)),  # C repeat
        (62, Fraction(4), Fraction(1)),  # D
        (64, Fraction(5), Fraction(1)),  # E
    ]
    passage, score = _score_with_notes_and_rests(notes, rests=[], measures=[(0, 4, 4), (4, 8, 4)])
    boundaries, diags = detect_phrase_boundaries(passage, score)
    # Should have ambiguity diagnostic due to repeated motif
    assert any(d.code in ("phrase_continuation_ambiguity", "repeated_motif_ambiguity") or "repeated" in d.code for d in diags) or any(b.confidence < 0.6 for b in boundaries)
    # At least not a strong clear boundary at 3
    # If boundaries exist, they should be low confidence
    for b in boundaries:
        if b.onset == Fraction(3):
            assert b.confidence < 0.80


def test_slur_unavailable_diagnostic():
    notes = [(60, Fraction(0), Fraction(1)), (62, Fraction(1), Fraction(1))]
    passage, score = _score_with_notes_and_rests(notes)
    _, diags = detect_phrase_boundaries(passage, score)
    assert any(d.code == "slur_evidence_unavailable" for d in diags)
