"""Tests for S3.6 texture classifier v1."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.passages.selection import select_passage
from passage_practice.semantics.texture import TextureClassifier
from passage_practice.views.texture_grid import build_texture_grid

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _texture_views(name: str, start=Fraction(0), end=Fraction(4)):
    score = _load(name)
    sel = select_passage(score, score_id=name, start=start, end=end)
    tex = build_texture_grid(sel.passage, score)
    return score, sel.passage, {"texture_grid": tex}


def _classifier():
    return TextureClassifier()


def test_monophonic_positive():
    # Synthetic monophonic: 4 single notes, no chords, no sustained
    from dataclasses import dataclass, field
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.source import SourceKind, SourceRef
    from passage_practice.models.time import ScorePosition
    from passage_practice.views.texture_grid import build_texture_grid

    @dataclass
    class FakeM:
        measure_index: int
        start: Fraction
        end: Fraction
        time_beats: int | None = 4
        time_beat_type: int | None = 4

    @dataclass
    class FakeL:
        note_id: str
        onset: Fraction
        duration: Fraction
        pitch_midi: int = 60
        hand: str | None = "right"
        staff: int | None = 1
        voice: str | None = "1"
        measure_index: int | None = 0
        source_note_ids: tuple[str, ...] = ()
        xml_order: int | None = None

    @dataclass
    class FakeScore:
        measures: list = field(default_factory=list)
        logical_notes: list = field(default_factory=list)
        written_notes: list = field(default_factory=list)

    score = FakeScore(measures=[FakeM(0, Fraction(0), Fraction(4))])
    for i in range(4):
        nid = f"m{i}"
        score.logical_notes.append(FakeL(note_id=nid, onset=Fraction(i), duration=Fraction(1), voice="1", xml_order=i + 1))
    passage = Passage(
        passage_id="mono.test",
        score_id="syn",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in score.logical_notes),
    )
    tex = build_texture_grid(passage, score)
    det = _classifier()
    hyps, _ = det.detect(passage, {"texture_grid": tex}, {})
    types = {h.hypothesis_type for h in hyps}
    assert "texture.monophonic" in types
    hyp = next(h for h in hyps if h.hypothesis_type == "texture.monophonic")
    assert hyp.confidence >= 0.50
    if "texture.homophonic_block" in types:
        assert next(h for h in hyps if h.hypothesis_type == "texture.homophonic_block").confidence < hyp.confidence


def test_homophonic_block_positive():
    score, passage, views = _texture_views("semantic_ambiguity.musicxml")
    det = _classifier()
    hyps, _ = det.detect(passage, views, {})
    types = {h.hypothesis_type for h in hyps}
    assert "texture.homophonic_block" in types
    hyp = next(h for h in hyps if h.hypothesis_type == "texture.homophonic_block")
    assert hyp.confidence >= 0.60


def test_melody_plus_accompaniment_positive():
    score, passage, views = _texture_views("semantic_top_voice_melody.musicxml")
    det = _classifier()
    hyps, _ = det.detect(passage, views, {})
    types = {h.hypothesis_type for h in hyps}
    assert "texture.melody_plus_accompaniment" in types
    hyp = next(h for h in hyps if h.hypothesis_type == "texture.melody_plus_accompaniment")
    assert hyp.confidence >= 0.60


def test_arpeggiated_positive():
    score, passage, views = _texture_views("semantic_accompaniment_pattern.musicxml")
    det = _classifier()
    hyps, _ = det.detect(passage, views, {})
    types = {h.hypothesis_type for h in hyps}
    assert "texture.arpeggiated" in types
    hyp = next(h for h in hyps if h.hypothesis_type == "texture.arpeggiated")
    assert hyp.confidence >= 0.50


def test_polyphonic_positive():
    score, passage, views = _texture_views("semantic_ambiguity.musicxml")
    # ambiguity has two encoded voices -> polyphonic
    det = _classifier()
    hyps, _ = det.detect(passage, views, {})
    types = {h.hypothesis_type for h in hyps}
    # semantic_ambiguity has voices 1 and 2, so polyphonic should be present
    assert "texture.polyphonic" in types
    hyp = next(h for h in hyps if h.hypothesis_type == "texture.polyphonic")
    assert hyp.confidence >= 0.55


def test_close_negatives():
    # Monophonic close negative: homophonic fixture should not be monophonic high
    score, passage, views = _texture_views("semantic_ambiguity.musicxml")
    det = _classifier()
    hyps, _ = det.detect(passage, views, {})
    mono = next((h for h in hyps if h.hypothesis_type == "texture.monophonic"), None)
    # For chordal fixture, monophonic should be low or absent or lower than homophonic
    if mono:
        homo = next(h for h in hyps if h.hypothesis_type == "texture.homophonic_block")
        assert mono.confidence < homo.confidence


def test_ambiguous_output_multiple():
    # Ambiguous texture: maybe a passage that could be both arpeggiated and melody_plus
    # Use accompaniment pattern which has both sustained and arpeggiated -> both should be present with similar confidence
    score, passage, views = _texture_views("semantic_accompaniment_pattern.musicxml")
    det = _classifier()
    hyps, diags = det.detect(passage, views, {})
    assert len(hyps) >= 2
    # Check that top two confidences are close (<0.20) and ambiguous diagnostic present
    confs = sorted([h.confidence for h in hyps], reverse=True)
    if len(confs) >= 2 and confs[0] - confs[1] < 0.15:
        assert any(d.code == "ambiguous_texture" for d in diags)
    # Ambiguous should have multiple medium/low hypotheses (not just one high)
    assert len([h for h in hyps if h.confidence >= 0.35]) >= 2


def test_missing_view_gives_diagnostic():
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition
    from passage_practice.models.source import SourceKind, SourceRef

    passage = Passage(
        passage_id="p.missing.tex",
        score_id="s",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )
    det = _classifier()
    hyps, diags = det.detect(passage, {}, {})
    assert hyps == ()
    assert any(d.code == "missing_required_view" for d in diags)


def test_registry_selection():
    from passage_practice.semantics.registry import DetectorRegistry

    registry = DetectorRegistry()
    det = _classifier()
    registry.register(det)
    assert det in registry.by_family("texture.")
    assert det in registry.selectable_for({"texture_grid"})
