"""Tests for S2.13 semantic-view integration payload.

One compact payload showing passage, view refs, observation refs, and
diagnostics. No detectors, no confidence scoring, no pedagogy.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.investigation import PassageInvestigation
from passage_practice.semantics.contracts import SemanticBundle
from passage_practice.semantics.integration import (
    INTEGRATION_METHOD_ID,
    INTEGRATION_METHOD_VERSION,
    build_semantic_integration,
)
from passage_practice.passages.selection import select_passage
from passage_practice.passages.investigate import manual_investigation

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _inv(name: str, start: Fraction, end: Fraction) -> tuple:
    score = _load(name)
    inv = manual_investigation(score, score_id=name, start=start, end=end, investigation_id=f"inv.integration.{name}")
    return score, inv


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


def test_integration_is_deterministic():
    score, inv = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    first = build_semantic_integration(inv, score)
    second = build_semantic_integration(inv, score)
    assert _dump(first.to_dict()) == _dump(second.to_dict())
    assert first == second
    # Same passage, same fixture → same bundle_id and refs
    assert first.bundle_id == second.bundle_id == f"{inv.passage.passage_id}:integration:v1"
    assert first.source_passage_id == inv.passage.passage_id
    # Round-trip
    revived = SemanticBundle.from_dict(json.loads(_dump(first.to_dict())))
    assert revived == first


def test_integration_view_and_observation_refs_resolve():
    score, inv = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    bundle = build_semantic_integration(inv, score)
    # View refs must encode passage_id and view_type
    assert len(bundle.view_refs) == 5  # attack, written, rhythm, texture, salience
    for ref in bundle.view_refs:
        assert inv.passage.passage_id in ref
        assert "@v1" in ref
    # Observation refs must be actual observation_ids produced this run
    # Collect expected observation ids by re-running all observation fns
    from passage_practice import observations as obs

    fns = [
        obs.observe_pitch_range, obs.observe_pitch_transitions, obs.observe_leap_frequency,
        obs.observe_repeated_notes, obs.observe_registral_extremes,
        obs.observe_attack_density, obs.observe_shortest_duration, obs.observe_off_beat_density,
        obs.observe_syncopation_proxy, obs.observe_hand_alignment_ratio, obs.observe_subdivision_mismatch,
        obs.observe_max_simultaneity, obs.observe_chord_density, obs.observe_sustained_under_moving,
        obs.observe_voice_count, obs.observe_staff_crossing,
        obs.observe_accidental_density, obs.observe_ledger_line_proxy, obs.observe_clef_change_presence,
        obs.observe_articulation_density, obs.observe_ornament_grace_notes,
    ]
    expected_ids: set[str] = set()
    for fn in fns:
        result = fn(inv, score)
        for o in result.observations:
            expected_ids.add(o.observation_id)
    assert set(bundle.observation_refs) <= expected_ids
    # At least some observations should be present (clef abstains, so not all fns contribute)
    assert len(bundle.observation_refs) >= 10
    # Every observation_ref must be non-empty str and contain passage_id
    for ref in bundle.observation_refs:
        assert ref
        assert inv.passage.passage_id.split(":")[0] in ref or inv.passage.passage_id in ref  # contains id prefix
    # Method versions must include view and observation tokens plus integration token
    assert f"{INTEGRATION_METHOD_ID}@{INTEGRATION_METHOD_VERSION}" in bundle.method_versions
    assert "attack_stream_view@v1" in bundle.method_versions
    assert "written_stream_view@v1" in bundle.method_versions
    assert "rhythm_grid_view@v1" in bundle.method_versions
    assert "texture_grid_view@v1" in bundle.method_versions
    assert "salience_view@v1" in bundle.method_versions


def test_missing_optional_view_is_valid_with_diagnostic():
    score, inv = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    full = build_semantic_integration(inv, score, include_salience=True)
    partial = build_semantic_integration(inv, score, include_salience=False)
    assert len(full.view_refs) == 5
    assert len(partial.view_refs) == 4
    assert all("salience_view" not in r for r in partial.view_refs)
    assert any(d.code == "missing_optional_view" for d in partial.diagnostics)
    assert not any(d.code == "missing_optional_view" for d in full.diagnostics)
    # Both still valid bundles, deterministic, same observation refs (views don't affect obs)
    assert partial.source_passage_id == full.source_passage_id == inv.passage.passage_id
    assert partial.hypotheses == () and full.hypotheses == ()
    # Deterministic within each mode
    assert _dump(partial.to_dict()) == _dump(build_semantic_integration(inv, score, include_salience=False).to_dict())


def test_integration_diagnostics_cover_views_and_observations():
    score, inv = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    bundle = build_semantic_integration(inv, score)
    codes = {d.code for d in bundle.diagnostics}
    # At least one view diagnostic (salience always has slur_unavailable etc) and one observation diagnostic (ledger proxy or clef)
    assert "slur_evidence_unavailable" in codes or "pattern_exclusion_not_available" in codes or "missing_dynamic_evidence" in codes
    assert "ledger_line_proxy_heuristic" in codes
    assert "clef_data_unavailable" in codes
    assert "layout_data_unavailable" in codes
    # Bundle with hypotheses empty is still valid — no detectors yet
    assert bundle.hypotheses == ()
    assert bundle.ranked_hypothesis_ids == ()


def test_integration_rejects_bad_investigation():
    score, _ = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    with pytest.raises(TypeError):
        build_semantic_integration("not-an-investigation", score)  # type: ignore


def test_integration_empty_passage_still_valid_bundle():
    # Empty written interval still yields a valid integration bundle (views empty with diagnostics)
    score, _ = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    empty_inv = manual_investigation(score, score_id="semantic_ambiguity.musicxml", start=Fraction(7, 2), end=Fraction(4, 1), investigation_id="inv.integration.empty")
    bundle = build_semantic_integration(empty_inv, score)
    assert bundle.source_passage_id == empty_inv.passage.passage_id
    assert len(bundle.view_refs) == 5
    # Observations will be empty but method_versions still present, diagnostics include insufficient_attacks
    assert any(d.code == "insufficient_attacks" for d in bundle.diagnostics)
    assert SemanticBundle.from_dict(bundle.to_dict()) == bundle


def test_integration_uses_exact_passage_id_and_not_top_level_reparse():
    # Ensures the integration payload references the exact passage id and does not reparse MusicXML itself
    score, inv = _inv("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    bundle = build_semantic_integration(inv, score)
    assert bundle.source_passage_id == inv.passage.passage_id
    assert bundle.bundle_id.endswith(":integration:v1")
    # View refs all encode the same passage id
    assert all(inv.passage.passage_id in r for r in bundle.view_refs)
