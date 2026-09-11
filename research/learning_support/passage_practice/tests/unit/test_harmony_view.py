"""Tests for S6.1 harmony view contract — empty/insufficient evidence diagnostic."""

from __future__ import annotations

from fractions import Fraction

import pytest

from passage_practice.models.passage import Passage, PassagePurpose, ViewType
from passage_practice.models.time import ScorePosition
from passage_practice.views.harmony_view import HarmonyView, build_harmony_view


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, measure_number="1", offset_in_measure=q)


def _empty_passage():
    return Passage(
        passage_id="test_empty@[0,1)/harmony",
        score_id="test_empty",
        start=_pos(Fraction(0)),
        end=_pos(Fraction(1)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=(),
    )


def _mock_score_empty():
    class Score:
        logical_notes = []
        measures = []
        written_notes = []
        directions = []
    return Score()


def test_empty_harmony_view_has_diagnostic():
    passage = _empty_passage()
    score = _mock_score_empty()
    view = build_harmony_view(passage, score)
    assert view.view_type == ViewType.HARMONY_VIEW
    assert view.pitch_class_counts == tuple(0 for _ in range(12))
    assert any(d.code == "insufficient_harmony_evidence" for d in view.diagnostics)
    # Round-trip
    revived = HarmonyView.from_dict(view.to_dict())
    assert revived == view


def test_normal_harmony_view_from_fixture():
    from pathlib import Path
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir
    from passage_practice.passages.selection import select_passage

    FIX = Path(__file__).resolve().parents[1] / "fixtures"
    score = build_score_ir(load_musicxml_document(FIX / "semantic_top_voice_melody.musicxml"))
    sel = select_passage(score, score_id="semantic_top_voice_melody.musicxml", start=Fraction(0), end=Fraction(4))
    view = build_harmony_view(sel.passage, score)
    assert view.view_type == ViewType.HARMONY_VIEW
    assert sum(view.pitch_class_counts) > 0
    assert len(view.onsets) > 0
    assert view.bass_refs
    # Deterministic
    view2 = build_harmony_view(sel.passage, score)
    assert view.to_dict() == view2.to_dict()


def test_insufficient_notes_diagnostic():
    # Only 1-2 notes should trigger insufficient evidence
    from passage_practice.models.source import SourceKind, SourceRef
    from passage_practice.models.diagnostics import Diagnostic

    # Create a passage with 1 note via synthetic score
    passage = Passage(
        passage_id="test_one@[0,1)/harmony",
        score_id="test_one",
        start=_pos(Fraction(0)),
        end=_pos(Fraction(1)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )

    class Note:
        note_id = "n1"
        pitch_midi = 60
        onset = Fraction(0)
        duration = Fraction(1)
        xml_order = 0

    class Score:
        logical_notes = [Note()]
        measures = []
        written_notes = []
        directions = []

    view = build_harmony_view(passage, Score())
    assert any(d.code == "insufficient_harmony_evidence" for d in view.diagnostics)
