"""Tests for S6.6 sequence/repetition heuristic v1."""

from __future__ import annotations

from fractions import Fraction

import pytest

from passage_practice.semantics.sequence import detect_sequence_repetition
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from passage_practice.models.source import SourceKind, SourceRef


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, measure_number="1", offset_in_measure=q)


def _score_from_notes(notes):
    """notes: list of (midi, onset, duration)"""
    class Note:
        def __init__(self, nid, midi, onset, dur, order):
            self.note_id = nid
            self.pitch_midi = midi
            self.onset = onset
            self.duration = dur
            self.xml_order = order

    note_objs = [Note(f"n{i}", midi, onset, dur, i) for i, (midi, onset, dur) in enumerate(notes)]
    refs = tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in note_objs)
    max_end = max((onset + dur for _, onset, dur in notes), default=Fraction(4))
    passage = Passage(
        passage_id="test.seq@[0,4)/seq",
        score_id="test.seq",
        start=_pos(Fraction(0)),
        end=_pos(max_end if max_end > Fraction(0) else Fraction(4)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=refs,
    )
    class Score:
        logical_notes = note_objs
        measures = []
        written_notes = []
        directions = []
    return passage, Score()


def test_transposed_sequence():
    # Motif C D E at 0, transposed to D E F# at 3
    notes = [
        (60, Fraction(0), Fraction(1)),  # C
        (62, Fraction(1), Fraction(1)),  # D
        (64, Fraction(2), Fraction(1)),  # E
        (62, Fraction(3), Fraction(1)),  # D (transposed +2)
        (64, Fraction(4), Fraction(1)),  # E
        (66, Fraction(5), Fraction(1)),  # F#
    ]
    passage, score = _score_from_notes(notes)
    cands, diags = detect_sequence_repetition(passage, score)
    assert len(cands) >= 1
    # First candidate should be transposed by +2
    assert any(c.transposition_semitones == 2 and not c.is_exact for c in cands)


def test_exact_repetition():
    notes = [
        (60, Fraction(0), Fraction(1)),
        (62, Fraction(1), Fraction(1)),
        (64, Fraction(2), Fraction(1)),
        (60, Fraction(3), Fraction(1)),
        (62, Fraction(4), Fraction(1)),
        (64, Fraction(5), Fraction(1)),
    ]
    passage, score = _score_from_notes(notes)
    cands, diags = detect_sequence_repetition(passage, score)
    assert len(cands) >= 1
    assert any(c.is_exact for c in cands)


def test_similar_rhythm_different_contour():
    # Same rhythm (quarter each) but different intervals: C D E vs C Eb G
    notes = [
        (60, Fraction(0), Fraction(1)),  # C
        (62, Fraction(1), Fraction(1)),  # D
        (64, Fraction(2), Fraction(1)),  # E
        (60, Fraction(3), Fraction(1)),  # C
        (63, Fraction(4), Fraction(1)),  # Eb (different interval)
        (67, Fraction(5), Fraction(1)),  # G
    ]
    passage, score = _score_from_notes(notes)
    cands, diags = detect_sequence_repetition(passage, score)
    assert len(cands) == 0
    assert any(d.code == "similar_rhythm_different_contour" for d in diags)


def test_too_short_negative():
    notes = [
        (60, Fraction(0), Fraction(1)),
        (62, Fraction(1), Fraction(1)),
    ]
    passage, score = _score_from_notes(notes)
    cands, diags = detect_sequence_repetition(passage, score)
    assert len(cands) == 0
    assert any(d.code == "too_short_for_sequence" for d in diags)
