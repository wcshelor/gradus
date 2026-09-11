"""Tests for S4.1 pedagogical input boundary.

Verifies contract-level rejection of raw free-text advice and unsupported score
refs, plus acceptance of valid semantic+score-ref inputs.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.pedagogy.boundary import validate_pedagogical_inputs
from passage_practice.passages.selection import select_passage

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def test_rejects_advice_text():
    with pytest.raises(ValueError, match="advice_text"):
        validate_pedagogical_inputs(advice_text="play more musically")


def test_rejects_free_text_diagnosis():
    with pytest.raises(ValueError, match="free_text_diagnosis"):
        validate_pedagogical_inputs(free_text_diagnosis="this looks like a difficult stretch")


def test_rejects_empty_advice_string_as_well():
    with pytest.raises(ValueError, match="advice_text"):
        validate_pedagogical_inputs(advice_text="")


def test_rejects_unsupported_score_ref():
    score = _load("semantic_top_voice_melody.musicxml")
    bad_ref = SourceRef(id="nonexistent-note-999", kind=SourceKind.LOGICAL_NOTE)
    valid, diags = validate_pedagogical_inputs(score=score, covered_event_refs=(bad_ref,))
    assert valid is False
    assert any(d.code == "unresolvable_score_ref" for d in diags)


def test_rejects_empty_covered_event_ids():
    score = _load("semantic_top_voice_melody.musicxml")
    valid, diags = validate_pedagogical_inputs(score=score, covered_event_refs=())
    assert valid is False
    assert any(d.code == "unsupported_passage_ref" for d in diags)


def test_accepts_valid_semantic_and_score_ref():
    score = _load("semantic_top_voice_melody.musicxml")
    sel = select_passage(score, score_id="semantic_top_voice_melody.musicxml", start=Fraction(0), end=Fraction(2))
    # Use a real ref from the passage
    ref = sel.passage.event_refs[0]
    assert ref.kind == SourceKind.LOGICAL_NOTE
    valid, diags = validate_pedagogical_inputs(score=score, passage=sel.passage, covered_event_refs=(ref,))
    assert valid is True
    assert diags == ()


def test_accepts_valid_semantic_bundle_alignment():
    score = _load("semantic_top_voice_melody.musicxml")
    sel = select_passage(score, score_id="semantic_top_voice_melody.musicxml", start=Fraction(0), end=Fraction(4))
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream

    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    valid, diags = validate_pedagogical_inputs(semantic_bundle=bundle, passage=sel.passage)
    assert valid is True
    assert diags == ()


def test_rejects_mismatched_passage_id():
    score = _load("semantic_top_voice_melody.musicxml")
    sel_a = select_passage(score, score_id="semantic_top_voice_melody.musicxml", start=Fraction(0), end=Fraction(2))
    sel_b = select_passage(score, score_id="semantic_top_voice_melody.musicxml", start=Fraction(2), end=Fraction(4))
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream

    views = {
        "salience_view": build_salience_view(sel_a.passage, score),
        "texture_grid": build_texture_grid(sel_a.passage, score),
        "rhythm_grid": build_rhythm_grid(sel_a.passage, score),
        "attack_stream": build_attack_stream(sel_a.passage, score),
        "written_stream": build_written_stream(sel_a.passage, score),
    }
    bundle_a = build_semantic_bundle(sel_a.passage, views, {})
    valid, diags = validate_pedagogical_inputs(semantic_bundle=bundle_a, passage=sel_b.passage)
    assert valid is False
    assert any(d.code == "unsupported_passage_ref" for d in diags)
