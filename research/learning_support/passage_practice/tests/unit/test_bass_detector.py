"""Tests for S3.3 bass-anchor detector v1.

Covers ordinary bass, walking bass, pedal point, melodic left-hand
negative, ambiguous low voice. Uses S2.3 fixtures + synthetic cases.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import copy
from dataclasses import dataclass, field

import pytest

from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScorePosition
from passage_practice.passages.selection import select_passage
from passage_practice.semantics.bass import BassAnchorDetector
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


# --- Helpers for synthetic walking/pedal ---

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
    hand: str | None = "left"
    staff: int | None = 2
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
    staff: int | None = 2
    voice: str | None = None
    hand: str | None = "left"
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


def _synthetic_passage(score: FakeScore, pid="synthetic.bass"):
    refs = tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in score.logical_notes)
    return Passage(
        passage_id=pid,
        score_id="synthetic",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=refs,
    )


# --- Ordinary bass ---

def test_ordinary_bass_anchor():
    score, passage, views = _views_for("semantic_top_voice_melody.musicxml")
    det = BassAnchorDetector()
    hyps, diags = det.detect(passage, views, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    assert hyp.hypothesis_type == "role.bass"
    assert hyp.confidence >= 0.60
    # Ordinary bass is the sustained left n5 (lowest, longest)
    assert "n5" in {r.id for r in hyp.covered_event_ids}
    assert "lowest_voice" in hyp.satisfied_criteria
    # Deterministic
    hyps2, _ = det.detect(passage, views, {})
    assert hyps[0] == hyps2[0]


# --- Walking bass ---

def test_walking_bass():
    score = FakeScore(measures=[FakeMeasure(0, Fraction(0), Fraction(4))])
    pitches = [48, 50, 52, 53]  # stepwise walking
    for i, (pitch, onset) in enumerate(zip(pitches, [Fraction(0), Fraction(1), Fraction(2), Fraction(3)])):
        nid = f"w{i+1}"
        score.logical_notes.append(FakeLogical(note_id=nid, onset=onset, duration=Fraction(1), pitch_midi=pitch, hand="left", staff=2, xml_order=i+1))
        score.written_notes.append(FakeWritten(note_id=nid, pitch_midi=pitch, onset=onset, duration=Fraction(1), hand="left", staff=2, xml_order=i+1))
    passage = _synthetic_passage(score, pid="walking.test")
    sal = build_salience_view(passage, score)
    tex = build_texture_grid(passage, score)
    det = BassAnchorDetector()
    hyps, _ = det.detect(passage, {"salience_view": sal, "texture_grid": tex}, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    assert hyp.hypothesis_type == "role.bass"
    assert hyp.confidence >= 0.50
    # All walking notes should be covered
    assert {r.id for r in hyp.covered_event_ids} == {"w1", "w2", "w3", "w4"}
    # Walking is stepwise but still bass anchor via lowest + on_beat
    assert "lowest_voice" in hyp.satisfied_criteria or "on_beat" in hyp.satisfied_criteria


# --- Pedal point ---

def test_pedal_point():
    score = FakeScore(measures=[FakeMeasure(0, Fraction(0), Fraction(4))])
    for i, onset in enumerate([Fraction(0), Fraction(1), Fraction(2), Fraction(3)]):
        nid = f"p{i+1}"
        score.logical_notes.append(FakeLogical(note_id=nid, onset=onset, duration=Fraction(1), pitch_midi=48, hand="left", staff=2, xml_order=i+1))
        score.written_notes.append(FakeWritten(note_id=nid, pitch_midi=48, onset=onset, duration=Fraction(1), hand="left", staff=2, xml_order=i+1))
    passage = _synthetic_passage(score, pid="pedal.test")
    sal = build_salience_view(passage, score)
    tex = build_texture_grid(passage, score)
    det = BassAnchorDetector()
    hyps, _ = det.detect(passage, {"salience_view": sal, "texture_grid": tex}, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    assert hyp.confidence >= 0.65  # pedal with recurrence should be high
    assert "pitch_class_recurrence" in hyp.satisfied_criteria


# --- Melodic left hand negative ---

def test_melodic_left_hand_negative():
    score, passage, views = _views_for("semantic_left_hand_melody.musicxml")
    det = BassAnchorDetector()
    hyps, diags = det.detect(passage, views, {})
    # Should either abstain or give low confidence (<0.50) with anchor-evidence missing
    if not hyps:
        assert any(d.code == "no_supported_bass" for d in diags)
    else:
        hyp = hyps[0]
        assert hyp.confidence < 0.55
        assert "no_anchor_evidence_longest_or_recurrence" in hyp.contradictory_criteria or "low_pitch_class_stability" in hyp.contradictory_criteria
        assert any(d.code == "low_confidence_bass" for d in diags)


# --- Ambiguous low voice ---

def test_ambiguous_low_voice():
    score, passage, views = _views_for("semantic_ambiguity.musicxml")
    det = BassAnchorDetector()
    hyps, diags = det.detect(passage, views, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    # Ambiguous fixture has two voices both with similar low register and chordal
    # Expect lower confidence and ambiguous diagnostics
    assert hyp.confidence < 0.65
    assert any(c in hyp.contradictory_criteria for c in ("low_pitch_class_stability", "inner_chord_tone_not_bass", "multiple_candidates_same_onset")) or any(d.code == "low_confidence_bass" for d in diags)


def test_transposition_preserves_bass():
    score, passage, views = _views_for("semantic_top_voice_melody.musicxml")
    det = BassAnchorDetector()
    hyps, _ = det.detect(passage, views, {})
    # Transpose +5 semitones
    trans_score = copy.deepcopy(score)
    for n in trans_score.logical_notes:
        object.__setattr__(n, "pitch_midi", n.pitch_midi + 5)
    for w in trans_score.written_notes:
        object.__setattr__(w, "pitch_midi", w.pitch_midi + 5)
    sal_t = build_salience_view(passage, trans_score)
    tex_t = build_texture_grid(passage, trans_score)
    hyps_t, _ = det.detect(passage, {"salience_view": sal_t, "texture_grid": tex_t}, {})
    assert len(hyps) == len(hyps_t) == 1
    assert {r.id for r in hyps[0].covered_event_ids} == {r.id for r in hyps_t[0].covered_event_ids}
    assert abs(hyps[0].confidence - hyps_t[0].confidence) < 1e-9


def test_missing_required_view_gives_diagnostic():
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition

    passage = Passage(
        passage_id="p.missing.bass",
        score_id="s",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )
    det = BassAnchorDetector()
    hyps, diags = det.detect(passage, {}, {})
    assert hyps == ()
    assert any(d.code == "missing_required_view" for d in diags)
    assert any(d.code == "unsupported_view" for d in diags)


def test_registry_selection_and_family():
    from passage_practice.semantics.registry import DetectorRegistry

    registry = DetectorRegistry()
    det = BassAnchorDetector()
    registry.register(det)
    assert det in registry.by_family("role.bass")
    assert det in registry.by_family("role.")
    assert det in registry.selectable_for({"salience_view"})
    assert registry.selectable_for(set()) == []
