"""Tests for S3.7 semantic bundle builder."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind
from passage_practice.passages.selection import select_passage
from passage_practice.semantics.bundle_builder import build_semantic_bundle
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.written_stream import build_written_stream

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _bundle_for(name: str):
    score = _load(name)
    sel = select_passage(score, score_id=name, start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    # observations empty for bundle builder (detectors use views)
    observations = {}
    bundle = build_semantic_bundle(sel.passage, views, observations)
    return bundle, sel.passage, score


def test_deterministic_ordering():
    bundle1, _, _ = _bundle_for("semantic_top_voice_melody.musicxml")
    bundle2, _, _ = _bundle_for("semantic_top_voice_melody.musicxml")
    assert bundle1 == bundle2
    # Hypotheses sorted by (-confidence, type, id)
    confs = [h.confidence for h in bundle1.hypotheses]
    assert confs == sorted(confs, reverse=True)
    # Ranked ids follow sorted order
    assert bundle1.ranked_hypothesis_ids == tuple(h.hypothesis_id for h in bundle1.hypotheses)
    # JSON deterministic
    assert json.dumps(bundle1.to_dict(), sort_keys=True) == json.dumps(bundle2.to_dict(), sort_keys=True)


def test_mixed_detector_diagnostics():
    bundle, _, _ = _bundle_for("semantic_ambiguity.musicxml")
    # Should have hypotheses from multiple detectors
    types = {h.hypothesis_type for h in bundle.hypotheses}
    assert "role.melody" in types or "role.bass" in types
    assert "texture." in str(types) or any(t.startswith("texture.") for t in types)
    assert "rhythm." in str(types) or any(t.startswith("rhythm.") for t in types)
    # Diagnostics should include view diagnostics and detector diagnostics
    codes = {d.code for d in bundle.diagnostics}
    assert "slur_evidence_unavailable" in codes or "pattern_exclusion_not_available" in codes
    # Contradictions visible: hypotheses include contradictory_criteria
    assert any(h.contradictory_criteria for h in bundle.hypotheses)


def test_no_supported_hypothesis_case():
    # Empty passage should give no_supported_hypothesis
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition
    from passage_practice.models.source import SourceRef

    score = _load("semantic_top_voice_melody.musicxml")
    empty_passage = None
    # Create empty passage with no refs
    from passage_practice.passages.selection import select_passage

    # Use an empty interval
    sel = select_passage(score, score_id="empty", start=Fraction(7, 2), end=Fraction(4, 1))
    # sel may be empty (no refs)
    passage = sel.passage
    # Build views for empty
    views = {
        "salience_view": build_salience_view(passage, score),
        "texture_grid": build_texture_grid(passage, score),
        "rhythm_grid": build_rhythm_grid(passage, score),
        "attack_stream": build_attack_stream(passage, score),
        "written_stream": build_written_stream(passage, score),
    }
    bundle = build_semantic_bundle(passage, views, {})
    assert bundle.hypotheses == ()
    assert any(d.code == "no_supported_hypothesis" for d in bundle.diagnostics)


def test_bundle_keeps_contradictions_visible():
    bundle, _, _ = _bundle_for("semantic_ambiguity.musicxml")
    # Ambiguous fixture should have at least one hypothesis with contradictory_criteria
    assert any(h.contradictory_criteria for h in bundle.hypotheses)
    # And diagnostics should not hide them
    assert len(bundle.hypotheses) >= 2


def test_bundle_provenance():
    bundle, passage, _ = _bundle_for("semantic_top_voice_melody.musicxml")
    assert bundle.source_passage_id == passage.passage_id
    assert bundle.bundle_id.endswith(":semantic_bundle:v1")
    assert len(bundle.view_refs) >= 4
    assert len(bundle.method_versions) >= 4
    assert all("@" in mv for mv in bundle.method_versions)
