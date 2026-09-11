"""Tests for S3.5 rhythm-layer detector v1."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScorePosition
from passage_practice.passages.selection import select_passage
from passage_practice.semantics.rhythm import RhythmLayerDetector
from passage_practice.views.rhythm_grid import build_rhythm_grid

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _rhythm_views(name: str, start=Fraction(0), end=Fraction(4)):
    score = _load(name)
    sel = select_passage(score, score_id=name, start=start, end=end)
    rg = build_rhythm_grid(sel.passage, score)
    return score, sel.passage, {"rhythm_grid": rg}


# Helpers for synthetic

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
    pitch_midi: int = 60
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


def _synthetic_passage(pitches, onsets, hands, pid="syn.rhythm"):
    score = FakeScore(measures=[FakeMeasure(0, Fraction(0), Fraction(4))])
    for i, (p, o, h) in enumerate(zip(pitches, onsets, hands)):
        nid = f"n{i}"
        score.logical_notes.append(FakeLogical(note_id=nid, onset=o, duration=Fraction(1), pitch_midi=p, hand=h, xml_order=i + 1))
        score.written_notes.append(FakeWritten(note_id=nid, pitch_midi=p, onset=o, duration=Fraction(1), hand=h, xml_order=i + 1))
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.source import SourceKind, SourceRef
    from passage_practice.models.time import ScorePosition

    passage = Passage(
        passage_id=pid,
        score_id="syn",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in score.logical_notes),
    )
    return score, passage


def test_aligned_hands_negative_no_independent():
    # Aligned hands: both hands attack together at each onset
    # Create synthetic with paired onsets: 2 notes per onset (left+right) for 3 onsets
    score_a = FakeScore(measures=[FakeMeasure(0, Fraction(0), Fraction(4))])
    for onset in [Fraction(0), Fraction(1), Fraction(2)]:
        for hand, pitch in [("left", 48), ("right", 72)]:
            nid = f"a{onset}_{hand}"
            score_a.logical_notes.append(FakeLogical(note_id=nid, onset=onset, duration=Fraction(1), pitch_midi=pitch, hand=hand, xml_order=len(score_a.logical_notes) + 1))
            score_a.written_notes.append(FakeWritten(note_id=nid, pitch_midi=pitch, onset=onset, duration=Fraction(1), hand=hand, xml_order=len(score_a.written_notes) + 1))
    passage_a = Passage(
        passage_id="aligned.test",
        score_id="syn",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in score_a.logical_notes),
    )
    from passage_practice.views.rhythm_grid import build_rhythm_grid

    rg = build_rhythm_grid(passage_a, score_a)
    det = RhythmLayerDetector()
    hyps, _ = det.detect(passage_a, {"rhythm_grid": rg}, {})
    # Aligned hands should produce common_attack_skeleton but NOT independent_hands
    types = {h.hypothesis_type for h in hyps}
    assert "rhythm.common_attack_skeleton" in types
    assert "rhythm.independent_hands" not in types


def test_syncopated_melody():
    score, passage, views = _rhythm_views("semantic_syncopation.musicxml")
    det = RhythmLayerDetector()
    hyps, _ = det.detect(passage, views, {})
    types = {h.hypothesis_type for h in hyps}
    assert "rhythm.syncopated_layer" in types
    # Syncopated fixture has off_beat at 2.5
    hyp = next(h for h in hyps if h.hypothesis_type == "rhythm.syncopated_layer")
    assert hyp.confidence >= 0.50
    assert "off_beat_density" in hyp.satisfied_criteria or "syncopation_proxy" in hyp.satisfied_criteria


def test_staggered_accompaniment():
    score, passage, views = _rhythm_views("semantic_accompaniment_pattern.musicxml")
    det = RhythmLayerDetector()
    hyps, _ = det.detect(passage, views, {})
    types = {h.hypothesis_type for h in hyps}
    assert "rhythm.independent_hands" in types
    hyp = next(h for h in hyps if h.hypothesis_type == "rhythm.independent_hands")
    assert hyp.confidence >= 0.55


def test_mixed_subdivision():
    # Synthetic mixed: one onset with two notes different durations
    score = FakeScore(measures=[FakeMeasure(0, Fraction(0), Fraction(4))])
    # Onset 0: left quarter, right half -> mixed
    score.logical_notes.append(FakeLogical(note_id="a1", onset=Fraction(0), duration=Fraction(1), pitch_midi=48, hand="left", xml_order=1))
    score.logical_notes.append(FakeLogical(note_id="a2", onset=Fraction(0), duration=Fraction(2), pitch_midi=72, hand="right", xml_order=2))
    score.written_notes.extend([
        FakeWritten(note_id="a1", pitch_midi=48, onset=Fraction(0), duration=Fraction(1), hand="left", xml_order=1),
        FakeWritten(note_id="a2", pitch_midi=72, onset=Fraction(0), duration=Fraction(2), hand="right", xml_order=2),
    ])
    for i, onset in enumerate([Fraction(1), Fraction(2)]):
        nid = f"b{i}"
        score.logical_notes.append(FakeLogical(note_id=nid, onset=onset, duration=Fraction(1), pitch_midi=60 + i, hand="left", xml_order=10 + i))
        score.written_notes.append(FakeWritten(note_id=nid, pitch_midi=60 + i, onset=onset, duration=Fraction(1), hand="left", xml_order=10 + i))
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.source import SourceKind, SourceRef
    from passage_practice.models.time import ScorePosition

    passage = Passage(
        passage_id="mixed.test",
        score_id="syn",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in score.logical_notes),
    )
    rg = build_rhythm_grid(passage, score)
    det = RhythmLayerDetector()
    hyps, _ = det.detect(passage, {"rhythm_grid": rg}, {})
    # Mixed subdivision should prevent stable_accompaniment, but independent may still be there
    types = {h.hypothesis_type for h in hyps}
    # Stable accompaniment should not be high confidence due to mixed
    if "rhythm.stable_accompaniment" in types:
        hyp = next(h for h in hyps if h.hypothesis_type == "rhythm.stable_accompaniment")
        assert hyp.confidence < 0.75 or "mixed_subdivision" in hyp.contradictory_criteria


def test_missing_required_view():
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition

    passage = Passage(
        passage_id="p.missing.rhythm",
        score_id="s",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )
    det = RhythmLayerDetector()
    hyps, diags = det.detect(passage, {}, {})
    assert hyps == ()
    assert any(d.code == "missing_required_view" for d in diags)


def test_registry_selection():
    from passage_practice.semantics.registry import DetectorRegistry

    registry = DetectorRegistry()
    det = RhythmLayerDetector()
    registry.register(det)
    assert det in registry.by_family("rhythm.")
    assert det in registry.selectable_for({"rhythm_grid"})
    assert registry.selectable_for(set()) == []
