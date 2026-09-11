"""Tests for S4.8 integration report: passage -> pedagogical hypotheses."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.pedagogy.integration import build_pedagogical_report
from passage_practice.semantics.bundle_builder import build_semantic_bundle
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.written_stream import build_written_stream
from passage_practice.passages.selection import select_passage
from passage_practice.passages.investigate import manual_investigation

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _bundle_for(name: str, start: Fraction = Fraction(0), end: Fraction = Fraction(4)):
    score = _load(name)
    sel = select_passage(score, score_id=name, start=start, end=end)
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    return score, sel.passage, bundle


def test_difficulty_context_optional():
    _, _, bundle = _bundle_for("semantic_top_voice_melody.musicxml")
    report = build_pedagogical_report(bundle, difficulty_context_refs=())
    assert report.source_passage_id == bundle.source_passage_id
    assert report.semantic_bundle == bundle
    assert any(d.code == "difficulty_context_optional_empty" for d in report.diagnostics)


def test_semantic_evidence_required():
    _, _, bundle = _bundle_for("semantic_top_voice_melody.musicxml")
    report = build_pedagogical_report(bundle)
    # Semantic evidence is required: report preserves the bundle
    assert report.semantic_bundle.source_passage_id == bundle.source_passage_id
    # At least one pedagogical hypothesis should be produced for this fixture
    assert len(report.pedagogical_hypotheses) >= 1


def test_learner_caveats_retained():
    _, _, bundle = _bundle_for("semantic_top_voice_melody.musicxml")
    report = build_pedagogical_report(bundle)
    # Learner caveats from hypotheses are unioned into report
    assert len(report.learner_caveats) > 0
    # Every hypothesis caveat should be in report caveats
    for hyp in report.pedagogical_hypotheses:
        for cav in hyp.learner_caveats:
            assert cav in report.learner_caveats


def test_user_selected_passage_without_hotspot_succeeds():
    # Use manual_investigation (user_selected) with no DifficultyEvidence
    score = _load("semantic_ambiguity.musicxml")
    inv = manual_investigation(score, score_id="semantic_ambiguity.musicxml", start=Fraction(0), end=Fraction(4), investigation_id="test.user_selected")
    assert inv.selection_origin.value == "user_selected"
    assert inv.difficulty == ()
    # Build bundle from passage
    _, _, bundle = _bundle_for("semantic_ambiguity.musicxml")
    # Provide no difficulty context refs (simulates user-selected without hotspot)
    report = build_pedagogical_report(bundle, difficulty_context_refs=(), passage=inv.passage)
    assert report.source_passage_id == bundle.source_passage_id
    assert report.difficulty_context_refs == ()
    # Should still be valid and deterministic
    report2 = build_pedagogical_report(bundle, difficulty_context_refs=(), passage=inv.passage)
    assert report.to_dict() == report2.to_dict()


def test_report_is_deterministic():
    _, _, bundle = _bundle_for("semantic_top_voice_melody.musicxml")
    r1 = build_pedagogical_report(bundle, accidental_count=2, leap_count=1, hand_alignment_ratio=20)
    r2 = build_pedagogical_report(bundle, accidental_count=2, leap_count=1, hand_alignment_ratio=20)
    assert r1.to_dict() == r2.to_dict()
