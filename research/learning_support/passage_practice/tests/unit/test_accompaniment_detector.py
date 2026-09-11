"""Tests for S3.4 accompaniment-pattern detector v1.

Covers clear positives, scalar negative, too-short pattern low confidence,
repeated-note ambiguity. Uses semantic fixtures + synthetic cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScorePosition
from passage_practice.passages.selection import select_passage
from passage_practice.semantics.accompaniment import AccompanimentPatternDetector
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
    tex = build_texture_grid(sel.passage, score)
    sal = build_salience_view(sel.passage, score)
    return score, sel.passage, {"texture_grid": tex, "salience_view": sal}


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


def _synthetic_passage(pitches: list[int], onsets: list[Fraction], pid="syn.test", durations=None):
    if durations is None:
        durations = [Fraction(1)] * len(pitches)
    score = FakeScore(measures=[FakeMeasure(0, Fraction(0), Fraction(4))])
    for i, (p, o, d) in enumerate(zip(pitches, onsets, durations)):
        nid = f"n{i}"
        score.logical_notes.append(FakeLogical(note_id=nid, onset=o, duration=d, pitch_midi=p, xml_order=i + 1))
        score.written_notes.append(FakeWritten(note_id=nid, pitch_midi=p, onset=o, duration=d, xml_order=i + 1))
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


# --- Clear positives ---

def test_clear_positive_accompaniment_pattern():
    score, passage, views = _views_for("semantic_accompaniment_pattern.musicxml")
    det = AccompanimentPatternDetector()
    hyps, diags = det.detect(passage, views, {})
    assert len(hyps) == 1
    hyp = hyps[0]
    assert hyp.hypothesis_type in ("role.accompaniment", "texture.arpeggiated", "texture.ostinato", "texture.block_chord")
    assert hyp.confidence >= 0.60
    assert "sustained_under_moving" in hyp.satisfied_criteria or "arpeggiated_range_and_leaps" in hyp.satisfied_criteria
    # Deterministic
    hyps2, _ = det.detect(passage, views, {})
    assert hyps[0] == hyps2[0]


def test_block_chord_support_positive():
    # Ambiguity fixture has block chords (chordal_onset_count 4, max_chord 2) — should be considered block chord support
    score, passage, views = _views_for("semantic_ambiguity.musicxml")
    det = AccompanimentPatternDetector()
    hyps, _ = det.detect(passage, views, {})
    assert len(hyps) == 1
    assert hyps[0].confidence >= 0.50
    assert "block_chord_support" in hyps[0].satisfied_criteria


# --- Scalar negative ---

def test_scalar_negative_no_accompaniment():
    # Scalar stepwise 60,62,64,65 — not accompaniment
    score, passage = _synthetic_passage([60, 62, 64, 65], [Fraction(0), Fraction(1), Fraction(2), Fraction(3)], pid="scalar")
    sal = build_salience_view(passage, score)
    tex = build_texture_grid(passage, score)
    det = AccompanimentPatternDetector()
    hyps, diags = det.detect(passage, {"texture_grid": tex, "salience_view": sal}, {})
    assert hyps == ()
    assert any(d.code == "no_supported_accompaniment" for d in diags)
    assert any("scalar_stepwise" in c for c in diags[0].message) or any(d.code == "no_supported_accompaniment" for d in diags)


# --- Too-short pattern low confidence ---

def test_too_short_pattern_low_confidence():
    # Only 2 onsets
    score, passage = _synthetic_passage([60, 67], [Fraction(0), Fraction(1)], pid="short")
    # Adjust passage end to 2 quarters
    from passage_practice.models.time import ScorePosition
    passage = Passage(
        passage_id="short.test",
        score_id="syn",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(2), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=passage.event_refs,
    )
    sal = build_salience_view(passage, score)
    tex = build_texture_grid(passage, score)
    det = AccompanimentPatternDetector()
    hyps, diags = det.detect(passage, {"texture_grid": tex, "salience_view": sal}, {})
    # Too short should either give no hyp or low confidence hyp
    assert any(d.code == "too_short_pattern" for d in diags)
    if hyps:
        assert hyps[0].confidence < 0.50
    else:
        assert any(d.code == "no_supported_accompaniment" for d in diags)


# --- Repeated-note ambiguity ---

def test_repeated_note_ambiguity():
    score, passage = _synthetic_passage([60, 60, 60, 60], [Fraction(0), Fraction(1), Fraction(2), Fraction(3)], pid="repeat")
    sal = build_salience_view(passage, score)
    tex = build_texture_grid(passage, score)
    det = AccompanimentPatternDetector()
    hyps, diags = det.detect(passage, {"texture_grid": tex, "salience_view": sal}, {})
    # Repeated notes ambiguous — should give diagnostic, and either no hyp or low confidence with contradictory
    assert any(d.code == "repeated_note_ambiguity" for d in diags)
    if hyps:
        assert "repeated_note_ambiguity" in hyps[0].contradictory_criteria
        assert hyps[0].confidence < 0.60
    else:
        assert any(d.code == "no_supported_accompaniment" for d in diags)


def test_missing_required_view_gives_diagnostic():
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition

    passage = Passage(
        passage_id="p.missing.acc",
        score_id="s",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )
    det = AccompanimentPatternDetector()
    hyps, diags = det.detect(passage, {}, {})
    assert hyps == ()
    assert any(d.code == "missing_required_view" for d in diags)
    assert any(d.code == "unsupported_view" for d in diags)


def test_registry_selection_and_family():
    from passage_practice.semantics.registry import DetectorRegistry

    registry = DetectorRegistry()
    det = AccompanimentPatternDetector()
    registry.register(det)
    assert det in registry.by_family("role.accompaniment")
    assert det in registry.by_family("texture.")
    assert det in registry.selectable_for({"texture_grid"})
    assert registry.selectable_for(set()) == []


def test_transposition_preserves_accompaniment():
    score, passage, views = _views_for("semantic_accompaniment_pattern.musicxml")
    det = AccompanimentPatternDetector()
    hyps, _ = det.detect(passage, views, {})
    # Transpose +3 semitones
    import copy
    trans_score = copy.deepcopy(score)
    for n in trans_score.logical_notes:
        object.__setattr__(n, "pitch_midi", n.pitch_midi + 3)
    for w in trans_score.written_notes:
        object.__setattr__(w, "pitch_midi", w.pitch_midi + 3)
    from passage_practice.views.salience_view import build_salience_view as bsv
    from passage_practice.views.texture_grid import build_texture_grid as btg
    sal_t = bsv(passage, trans_score)
    tex_t = btg(passage, trans_score)
    hyps_t, _ = det.detect(passage, {"texture_grid": tex_t, "salience_view": sal_t}, {})
    assert len(hyps) == len(hyps_t) == 1
    assert hyps[0].hypothesis_type == hyps_t[0].hypothesis_type
    assert abs(hyps[0].confidence - hyps_t[0].confidence) < 1e-9
