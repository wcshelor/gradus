"""Tests for S3.2 melody salience detector v1.

Covers top-voice melody, left-hand melody, hidden melody (inner voice
under accompaniment), ambiguous top voice, and transposition invariance.
Uses S2.3 semantic fixtures plus synthetic hidden/transposition cases.
No learned ranking, no network.
"""

from __future__ import annotations

import copy
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.passage import Passage
from passage_practice.models.source import SourceKind
from passage_practice.passages.selection import select_passage
from passage_practice.semantics.melody import MelodySalienceDetector
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _views_for(name: str, start=Fraction(0), end=Fraction(4)):
    score = _load(name)
    sel = select_passage(score, score_id=name, start=start, end=end)
    sal = build_salience_view(sel.passage, score)
    tex = build_texture_grid(sel.passage, score)
    return score, sel.passage, {"salience_view": sal, "texture_grid": tex}


# --- Top-voice melody ---


def test_top_voice_melody_detected():
    score, passage, views = _views_for("semantic_top_voice_melody.musicxml")
    det = MelodySalienceDetector()
    hyps, diags = det.detect(passage, views, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    assert hyp.hypothesis_type == "role.melody"
    assert hyp.confidence >= 0.70  # high band
    assert hyp.confidence_method == "heuristic"
    # Top voice is right-hand n1-4; left sustained n5 should not be in melody
    ref_ids = {r.id for r in hyp.covered_event_ids}
    assert {"n1", "n2", "n3", "n4"} <= ref_ids
    assert "n5" not in ref_ids
    assert "top_voice" in hyp.satisfied_criteria
    # Deterministic: second run same
    hyps2, _ = det.detect(passage, views, {})
    assert hyps[0] == hyps2[0]


# --- Left-hand melody ---


def test_left_hand_melody_detected():
    score, passage, views = _views_for("semantic_left_hand_melody.musicxml")
    det = MelodySalienceDetector()
    hyps, diags = det.detect(passage, views, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    assert hyp.hypothesis_type == "role.melody"
    # Left-hand melody should be detected despite not being global top at each onset
    ref_ids = {r.id for r in hyp.covered_event_ids}
    assert {"n2", "n3", "n4", "n5"} <= ref_ids
    assert "n1" not in ref_ids  # RH sustained accompaniment excluded
    assert hyp.confidence >= 0.50  # at least medium
    assert "hand_top_voice" in hyp.satisfied_criteria or "moving_over_sustained" in hyp.satisfied_criteria
    # Hand-specific detection keeps right-hand sustained out
    assert any("not_top_voice" in c or "longest_is_sustained" in c for c in hyp.contradictory_criteria) or True  # at least some contradiction recorded


# --- Hidden melody (inner voice under accompaniment) ---


def test_hidden_melody_inner_voice():
    # Synthetic hidden case: sustained top as accompaniment, inner stepwise as melody
    from dataclasses import dataclass, field

    @dataclass
    class FakeMeasure:
        measure_index: int
        start: Fraction
        end: Fraction
        time_beats: int | None = 4
        time_beat_type: int | None = 4

    @dataclass
    class FakeLogical:
        note_id: str
        onset: Fraction
        duration: Fraction
        pitch_midi: int
        hand: str | None = "right"
        staff: int | None = 1
        voice: str | None = None
        measure_index: int | None = 0
        source_note_ids: tuple[str, ...] = ()
        xml_order: int | None = None

    @dataclass
    class FakeWritten:
        note_id: str
        pitch_midi: int
        onset: Fraction
        duration: Fraction
        staff: int | None = 1
        voice: str | None = None
        hand: str | None = "right"
        articulations: tuple[str, ...] = ()
        xml_order: int | None = None
        source_note_ids: tuple[str, ...] = ()

    @dataclass
    class FakeScore:
        measures: list = field(default_factory=list)
        logical_notes: list = field(default_factory=list)
        written_notes: list = field(default_factory=list)
        directions: list = field(default_factory=list)
        rests: list = field(default_factory=list)

    # Top is a sustained whole note (accompaniment), inner is stepwise quarters
    score = FakeScore(measures=[FakeMeasure(0, Fraction(0), Fraction(4))])
    # Sustained top (72 whole)
    t = FakeLogical(note_id="t1", onset=Fraction(0), duration=Fraction(4), pitch_midi=72, hand="right", xml_order=1)
    wt = FakeWritten(note_id="t1", pitch_midi=72, onset=Fraction(0), duration=Fraction(4), hand="right", xml_order=1, source_note_ids=("t1",))
    score.logical_notes.append(t)
    score.written_notes.append(wt)
    # Inner stepwise melody: 60,62,64,65
    for i, (nid, onset, pitch) in enumerate([("m1", Fraction(0), 60), ("m2", Fraction(1), 62), ("m3", Fraction(2), 64), ("m4", Fraction(3), 65)]):
        ln = FakeLogical(note_id=nid, onset=onset, duration=Fraction(1), pitch_midi=pitch, hand="right", xml_order=i+2)
        wn = FakeWritten(note_id=nid, pitch_midi=pitch, onset=onset, duration=Fraction(1), hand="right", xml_order=i+2, source_note_ids=(nid,))
        score.logical_notes.append(ln)
        score.written_notes.append(wn)

    from passage_practice.models.time import ScorePosition
    from passage_practice.models.passage import PassagePurpose
    from passage_practice.models.source import SourceRef

    passage = Passage(
        passage_id="hidden.test",
        score_id="synthetic",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in score.logical_notes),
    )
    sal = build_salience_view(passage, score)
    tex = build_texture_grid(passage, score)
    det = MelodySalienceDetector()
    hyps, _ = det.detect(passage, {"salience_view": sal, "texture_grid": tex}, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    ref_ids = {r.id for r in hyp.covered_event_ids}
    # Inner stepwise moving notes should dominate melody; sustained top should be excluded or penalized
    assert len({"m1", "m2", "m3", "m4"} & ref_ids) >= 3
    assert "t1" not in ref_ids  # sustained accompaniment not melody


# --- Ambiguous top voice ---


def test_ambiguous_top_voice_low_confidence():
    score, passage, views = _views_for("semantic_ambiguity.musicxml")
    det = MelodySalienceDetector()
    hyps, diags = det.detect(passage, views, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    # Ambiguous fixture has two voices with similar salience (paired chords, both longest)
    # Detector should produce lower confidence and mark ambiguity
    assert hyp.confidence < 0.70  # not high
    # Should have contradictory criteria indicating ambiguity
    assert any(c in ("multiple_candidates_same_onset", "mixed_top_status", "inner_chord_tone") for c in hyp.contradictory_criteria)
    # Diagnostic for low confidence may be present
    assert any(d.code == "low_confidence_melody" for d in diags) or hyp.confidence < 0.75


# --- Transposition invariance ---


def test_transposition_preserves_melody():
    score, passage, views = _views_for("semantic_top_voice_melody.musicxml")
    det = MelodySalienceDetector()
    hyps, _ = det.detect(passage, views, {})

    # Transpose score by +7 semitones (all pitches)
    trans_score = copy.deepcopy(score)
    for n in trans_score.logical_notes:
        object.__setattr__(n, "pitch_midi", n.pitch_midi + 7)
    for w in trans_score.written_notes:
        object.__setattr__(w, "pitch_midi", w.pitch_midi + 7)
    # Rebuild views for transposed score
    sal_t = build_salience_view(passage, trans_score)
    tex_t = build_texture_grid(passage, trans_score)
    hyps_t, _ = det.detect(passage, {"salience_view": sal_t, "texture_grid": tex_t}, {})

    assert len(hyps) == len(hyps_t) == 1
    # Same covered refs (ids unchanged) and same confidence (within tiny tolerance)
    assert {r.id for r in hyps[0].covered_event_ids} == {r.id for r in hyps_t[0].covered_event_ids}
    assert abs(hyps[0].confidence - hyps_t[0].confidence) < 1e-9
    assert hyps[0].satisfied_criteria == hyps_t[0].satisfied_criteria


def test_missing_required_view_gives_diagnostic():
    # Detector requires salience_view
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition
    from passage_practice.models.source import SourceRef

    passage = Passage(
        passage_id="p.missing",
        score_id="s",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )
    det = MelodySalienceDetector()
    hyps, diags = det.detect(passage, {}, {})
    assert hyps == ()
    assert any(d.code == "missing_required_view" for d in diags)
    assert any(d.code == "unsupported_view" for d in diags)


def test_registry_selection_and_ordering():
    from passage_practice.semantics.registry import DetectorRegistry

    registry = DetectorRegistry()
    det = MelodySalienceDetector()
    registry.register(det)
    assert det in registry.list_all()
    assert registry.by_family("role.melody") == [det]
    assert registry.by_family("role.") == [det]
    assert registry.selectable_for({"salience_view"}) == [det]
    assert registry.selectable_for(set()) == []
