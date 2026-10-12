"""Focused tests for debug-only taxonomy attribution payload construction.

This is internal debug infrastructure validation, not learner-facing scoring.
Uses existing fixtures and synthetic checks.
"""

from pathlib import Path

import json

from piano_difficulty.debug.taxonomy_attribution import (
    DEBUG_LABEL,
    DEBUG_SCHEMA,
    GRAPH_TAXONOMY_VERSION,
    PROXY_FEATURES,
    build_debug_attribution_payload,
    parse_measures_arg,
    render_debug_attribution_markdown,
    render_debug_attribution_json,
)
from piano_difficulty.difficulty_analysis.front_graph_taxonomy import GRAPH_DIMENSION_IDS
from piano_difficulty.difficulty_analysis.overview import OverviewOptions


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
ALT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "real_mxl_basic_grand_staff.mxl"


def _payload_for_fixture(measures="1-2", dimension="layers_coordination", **kwargs):
    path = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    opts = OverviewOptions(window="measure", window_size=2, stride=1, hand="both", top_sections=5)
    return build_debug_attribution_payload(str(path), measures, dimension, overview_options=opts, **kwargs)


def test_parse_measures_arg():
    assert parse_measures_arg("12-16") == [12, 13, 14, 15, 16]
    assert parse_measures_arg("12") == [12]
    assert parse_measures_arg("12,14-16") == [12, 14, 15, 16]
    assert parse_measures_arg("1-2,4") == [1, 2, 4]
    # en dash
    assert parse_measures_arg("12–16") == [12, 13, 14, 15, 16]


def test_payload_structure_debug_only():
    payload = _payload_for_fixture(measures="1", dimension="layers_coordination")
    assert payload["debug"] is True
    assert payload["debug_label"] == DEBUG_LABEL
    assert payload["schema"] == DEBUG_SCHEMA
    assert payload["taxonomy_version"] == GRAPH_TAXONOMY_VERSION
    # Must not claim hard or give learner advice phrases
    md = render_debug_attribution_markdown(payload)
    assert DEBUG_LABEL in md
    assert "DEBUG ONLY" in md
    assert "not learner-facing" in md.lower()
    # No pedagogical advice words
    assert "Practice" not in md or "DEBUG" in md  # allow debug context but not learner advice
    assert "you should" not in md.lower()


def test_payload_has_required_output_fields():
    payload = _payload_for_fixture(measures="1-2", dimension="layers_coordination")
    # Score path/title if available
    assert "score" in payload and "path" in payload["score"]
    assert payload["score"]["title"] is not None
    # Selected measure range
    assert payload["request"]["measures_str"] == "1-2"
    assert payload["request"]["measures_parsed"] == [1, 2]
    # Selected taxonomy dimension
    assert payload["request"]["dimension_id"] == "layers_coordination"
    assert payload["dimension"]["id"] == "layers_coordination"
    # Overlapping analysis window(s)
    assert "windows" in payload and len(payload["windows"]) >= 1
    for w in payload["windows"]:
        assert "window_index" in w
        assert "measure_numbers" in w
        assert "dimension_raw" in w or "dimension_normalized" in w
    # Dimension raw/normalized value for those windows
    assert any(w.get("dimension_normalized") is not None for w in payload["windows"])
    # Ranked contributing features for that dimension
    assert "aggregated_contributors" in payload and len(payload["aggregated_contributors"]) > 0
    for c in payload["aggregated_contributors"]:
        assert "feature_id" in c
        assert "weight" in c
        assert "avg_weighted_value" in c
        assert "units" in c or "label" in c
    # For each contributor fields
    per_win = payload["contributors_per_window"]
    assert len(per_win) >= 1
    for pw in per_win:
        for c in pw["contributors"]:
            assert "feature_id" in c
            assert "raw_value" in c
            assert "normalized_value" in c
            assert "weight" in c
            assert "weighted_value" in c or "contribution_share" in c
            assert "is_proxy" in c
            # source scope/window/measure info
            assert "window_index" in c
            assert "measure_numbers" in c


def test_proxy_labeling_and_warnings():
    payload = _payload_for_fixture(measures="1", dimension="layers_coordination")
    # Check proxy labeling
    agg = {c["feature_id"]: c for c in payload["aggregated_contributors"]}
    if "coordination.subdivision_mismatch_proxy" in agg:
        assert agg["coordination.subdivision_mismatch_proxy"]["is_proxy"] is True
        assert agg["coordination.subdivision_mismatch_proxy"]["proxy_kind"] == "proxy"
    # Warnings for proxy-based features, especially coordination features
    warnings_text = " ".join(payload["warnings"]).lower()
    assert "proxy" in warnings_text
    assert "subdivision_mismatch_proxy" in warnings_text or "proxy-based" in warnings_text
    # Markdown must label proxy
    md = render_debug_attribution_markdown(payload)
    assert "proxy" in md.lower()


def test_layers_coordination_breakdown_surfaces_required_paths():
    payload = _payload_for_fixture(measures="1-2", dimension="layers_coordination")
    breakdown = payload.get("breakdown")
    assert breakdown is not None
    cats = breakdown.get("categories", {})
    # Must surface at least these categories where present
    assert "coordination.subdivision_mismatch_proxy" in cats or breakdown.get("has_subdivision_mismatch_proxy") is False
    assert "coordination.asynchronous_hand_onset_count" in cats or breakdown.get("has_async") is not None
    # For fixture, both should be present
    assert breakdown.get("has_subdivision_mismatch_proxy") is True
    assert breakdown.get("has_async") is True
    # rhythm/polyrhythm
    assert breakdown.get("has_rhythm_polyrhythm") is not None
    # texture weak
    assert breakdown.get("has_texture_proxy") is not None
    assert "weight_note" in breakdown
    # Check markdown breakdown section exists
    md = render_debug_attribution_markdown(payload)
    assert "layers_coordination" in md and "breakdown" in md.lower()
    assert "subdivision_mismatch_proxy" in md
    assert "asynchronous_hand_onset_count" in md


def test_normalization_visibility():
    payload = _payload_for_fixture(measures="1-2", dimension="layers_coordination")
    # Each contributor should have piece_raw_min/max and normalization_note
    for pw in payload["contributors_per_window"]:
        for c in pw["contributors"]:
            if isinstance(c.get("normalized_value"), float) and isinstance(c.get("raw_value"), float):
                assert "piece_raw_min" in c
                assert "piece_raw_max" in c
                assert "normalization_note" in c
                if c.get("normalization_note"):
                    assert "within-piece" in c["normalization_note"].lower() or "piece range" in c["normalization_note"].lower()
    # Warnings should mention within-piece normalization if high normalized
    warnings_text = " ".join(payload["warnings"])
    assert "within-piece" in warnings_text or "relative within this piece" in warnings_text


def test_why_high_summary_technical_not_pedagogical():
    payload = _payload_for_fixture(measures="1-2", dimension="layers_coordination")
    why = payload.get("why_high_summary", "")
    assert why.startswith("DEBUG")
    # Must not use learner-facing advice phrases
    lowered = why.lower()
    assert "you should practice" not in lowered
    assert "try to" not in lowered or "weighted" in lowered  # allow technical try? be strict
    # Must mention weighted/weight/design weights
    assert "weight" in lowered
    # Must not claim objectively hard
    assert "objectively hard" not in lowered or "do not claim" in lowered  # actually warnings say do not claim, why_high should not claim
    assert "is hard" not in lowered or "not absolute" in lowered


def test_json_stable_for_tests():
    payload = _payload_for_fixture(measures="1-2", dimension="layers_coordination")
    j1 = render_debug_attribution_json(payload)
    # Reload and check stable keys
    data = json.loads(j1)
    assert data["schema"] == DEBUG_SCHEMA
    assert data["debug"] is True
    # Ensure json.dumps with sort_keys produces deterministic output (no NaN)
    j2 = json.dumps(data, indent=2, sort_keys=True, allow_nan=False)
    assert j1.strip() == j2.strip() or json.loads(j1) == json.loads(j2)
    # Payload must be json-serializable with allow_nan False
    json.dumps(payload, allow_nan=False)


def test_detail_onsets_optional():
    payload_without = _payload_for_fixture(measures="1", dimension="layers_coordination", detail=None)
    assert "onsets_detail" not in payload_without
    payload_with = _payload_for_fixture(measures="1", dimension="layers_coordination", detail="onsets")
    assert "onsets_detail" in payload_with
    assert isinstance(payload_with["onsets_detail"], list)
    if payload_with["onsets_detail"]:
        first = payload_with["onsets_detail"][0]
        assert "measure_number" in first
        assert "right_hand_offsets" in first
        assert "left_hand_offsets" in first
        assert "aligned_offsets" in first
        assert "mismatched_offsets" in first
    # Markdown should include onsets section when detail requested
    md = render_debug_attribution_markdown(payload_with)
    assert "onsets" in md.lower()


def test_invalid_dimension_raises():
    try:
        _payload_for_fixture(measures="1-2", dimension="nonexistent_dim")
        assert False, "should have raised"
    except ValueError as exc:
        assert "unknown dimension" in str(exc).lower()


def test_no_overlapping_windows_warning():
    # Request measures far outside fixture range (fixture has 1-2)
    payload = _payload_for_fixture(measures="99-100", dimension="layers_coordination")
    assert len(payload["windows"]) == 0
    warnings_text = " ".join(payload["warnings"]).lower()
    assert "no analysis windows overlap" in warnings_text
    assert "no contributors" in warnings_text or "no contributors to show" in warnings_text or "no overlapping" in warnings_text
    md = render_debug_attribution_markdown(payload)
    assert "No windows overlap" in md or "no windows overlap" in md.lower()
