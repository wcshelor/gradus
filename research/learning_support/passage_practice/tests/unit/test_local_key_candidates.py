"""Tests for S6.2 local key candidate heuristic v1."""

from __future__ import annotations

from fractions import Fraction

import pytest

from passage_practice.views.harmony_view import build_harmony_view, rank_local_key_candidates
from passage_practice.models.passage import Passage, PassagePurpose, ViewType
from passage_practice.models.time import ScorePosition
from passage_practice.models.source import SourceKind, SourceRef


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, measure_number="1", offset_in_measure=q)


def _score_from_pitches(pitches: list[tuple[int, Fraction, Fraction]]):
    """Create mock score with given (midi, onset, duration) notes."""
    class Note:
        def __init__(self, nid, midi, onset, dur, order):
            self.note_id = nid
            self.pitch_midi = midi
            self.onset = onset
            self.duration = dur
            self.xml_order = order

    notes = [Note(f"n{i}", midi, onset, dur, i) for i, (midi, onset, dur) in enumerate(pitches)]
    class Score:
        logical_notes = notes
        measures = []
        written_notes = []
        directions = []
    refs = tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in notes)
    max_end = max((onset + dur for _, onset, dur in pitches), default=Fraction(1))
    passage = Passage(
        passage_id="test.key@[0,4)/harmony",
        score_id="test.key",
        start=_pos(Fraction(0)),
        end=_pos(max_end if max_end > Fraction(0) else Fraction(1)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=refs,
    )
    return passage, Score()


def test_clear_diatonic_passage():
    # C major scale: C D E F G A B C (pcs 0,2,4,5,7,9,11)
    pitches = [
        (60, Fraction(0), Fraction(1)),  # C
        (62, Fraction(1), Fraction(1)),  # D
        (64, Fraction(2), Fraction(1)),  # E
        (65, Fraction(3), Fraction(1)),  # F
        (67, Fraction(4), Fraction(1)),  # G
        (69, Fraction(5), Fraction(1)),  # A
        (71, Fraction(6), Fraction(1)),  # B
        (72, Fraction(7), Fraction(1)),  # C
    ]
    passage, score = _score_from_pitches(pitches)
    view = build_harmony_view(passage, score)
    ranked = rank_local_key_candidates(view)
    assert ranked[0][0] == "C"
    assert ranked[0][1] >= 0.85


def test_chromatic_ambiguity():
    # Chromatic scale: all 12 pcs
    pitches = [(60 + i, Fraction(i), Fraction(1)) for i in range(12)]
    passage, score = _score_from_pitches(pitches)
    view = build_harmony_view(passage, score)
    ranked = rank_local_key_candidates(view)
    # Max confidence should be low (<0.65) and diagnostic present
    assert ranked[0][1] < 0.65
    assert any(d.code == "chromatic_ambiguity_low_key_confidence" for d in view.diagnostics)
    assert any(d.code == "atonal_or_chromatic" for d in view.diagnostics)


def test_transposition():
    # D major scale transposed from C: D E F# G A B C# D
    pitches_c = [60, 62, 64, 65, 67, 69, 71, 72]
    pitches_d = [62, 64, 66, 67, 69, 71, 73, 74]  # D major
    passage_c, score_c = _score_from_pitches([(p, Fraction(i), Fraction(1)) for i, p in enumerate(pitches_c)])
    passage_d, score_d = _score_from_pitches([(p, Fraction(i), Fraction(1)) for i, p in enumerate(pitches_d)])
    view_c = build_harmony_view(passage_c, score_c)
    view_d = build_harmony_view(passage_d, score_d)
    ranked_c = rank_local_key_candidates(view_c)
    ranked_d = rank_local_key_candidates(view_d)
    assert ranked_c[0][0] == "C"
    assert ranked_d[0][0] == "D"
    # Confidence should be similar (transposition invariance)
    assert abs(ranked_c[0][1] - ranked_d[0][1]) < 0.05
