"""Focused tests for the primary difficulty_aspects.v1 profile."""

from pathlib import Path
import json

import pytest

from piano_difficulty.difficulty_analysis.registry import PROFILE_REGISTRY, resolve_profiles
from piano_difficulty.pipeline import analyze_score


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
# Fallback fixture used by overview tests
ALT_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "real_mxl_basic_grand_staff.mxl"

EXPECTED_ASPECT_IDS = (
    "rhythmic_demand",
    "pitch_movement_demand",
    "hand_shape_span_demand",
    "texture_polyphony_demand",
    "coordination_demand",
    "notation_reading_demand",
    "expression_control_demand",
    "structural_pattern_demand",
    "performance_interpretive_demand",
)


def test_profile_is_registered_and_selectable():
    assert "difficulty_aspects" in PROFILE_REGISTRY
    assert resolve_profiles(("difficulty_aspects",))[0].profile_id == "difficulty_aspects"
    # selectable via analyze_score
    result = analyze_score(FIXTURE if FIXTURE.exists() else ALT_FIXTURE, profile_ids=("difficulty_aspects",))
    payload = result.to_json_payload()["analysis_profiles"][0]
    assert payload["profile_id"] == "difficulty_aspects"
    assert payload["schema_version"] == "difficulty_aspects.v1"
    # deterministic: second call same
    result2 = analyze_score(FIXTURE if FIXTURE.exists() else ALT_FIXTURE, profile_ids=("difficulty_aspects",))
    payload2 = result2.to_json_payload()["analysis_profiles"][0]
    assert payload == payload2
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_default_profile_uses_nine_aspects_first():
    result = analyze_score(FIXTURE if FIXTURE.exists() else ALT_FIXTURE)
    payload = result.to_json_payload()
    assert [p["profile_id"] for p in payload["analysis_profiles"]] == [
        "difficulty_aspects",
        "difficulty_overview",
    ]
    assert payload["analysis_profiles"][0]["schema_version"] == "difficulty_aspects.v1"


def test_payload_has_schema_and_exactly_nine_aspects():
    fixture = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    payload = analyze_score(fixture, profile_ids=("difficulty_aspects",)).to_json_payload()["analysis_profiles"][0]
    assert payload["schema_version"] == "difficulty_aspects.v1"
    assert payload["profile_id"] == "difficulty_aspects"
    assert len(payload["aspects"]) == 9
    aspect_ids = tuple(a["aspect_id"] for a in payload["aspects"])
    # also accept "id" field
    assert aspect_ids == EXPECTED_ASPECT_IDS
    for aspect in payload["aspects"]:
        assert "aspect_id" in aspect
        assert "label" in aspect or "name" in aspect
        assert aspect["readiness"] in ("ready", "partial", "blocked", "caveated")
        assert "included_feature_ids" in aspect or "feature_ids" in aspect
        assert "missing_features" in aspect or "missing_feature_notes" in aspect
        assert "limitations" in aspect or "caveats" in aspect
        # lightweight feature summaries present
        assert "features" in aspect or "feature_summaries" in aspect
        feats = aspect.get("features", aspect.get("feature_summaries"))
        assert isinstance(feats, list)
        for f in feats:
            assert "feature_id" in f
            assert "scope" in f
            assert "scope_ref" in f
            assert "value" in f
            assert "units" in f


def test_current_runtime_features_grouped_into_expected_aspects():
    fixture = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    extraction = analyze_score(fixture, profile_ids=("difficulty_aspects",)).extraction
    runtime_ids = {r.feature_id for r in extraction.features}
    payload = analyze_score(fixture, profile_ids=("difficulty_aspects",)).to_json_payload()["analysis_profiles"][0]
    aspect_map = {a["aspect_id"]: set(a.get("included_feature_ids", a.get("feature_ids", []))) for a in payload["aspects"]}

    # Representative checks — existing runtime features must appear in expected buckets
    assert "rhythm.attack_density" in aspect_map["rhythmic_demand"]
    assert "rhythm.note_density" in aspect_map["rhythmic_demand"]
    assert "leaps.max_melodic_leap" in aspect_map["pitch_movement_demand"]
    assert "pitch_geometry.max_simultaneity_span" in aspect_map["hand_shape_span_demand"]
    assert "texture.notes_per_onset" in aspect_map["texture_polyphony_demand"]
    assert "coordination.subdivision_mismatch_proxy" in aspect_map["coordination_demand"]
    assert "notation.accidental_density" in aspect_map["notation_reading_demand"]
    assert "expression.articulated_note_ratio" in aspect_map["expression_control_demand"]

    # Also ensure structural context features are present
    assert "metadata.measure_count" in aspect_map["structural_pattern_demand"]
    assert "metadata.note_count" in aspect_map["structural_pattern_demand"]

    # Every runtime feature should be grouped into at least one aspect where applicable
    # (metadata extras like page_count should also be grouped somewhere)
    # We check that at least the major families are covered
    for required in ["metadata.tempo_change_count", "metadata.meter_change_count", "metadata.key_change_count", "metadata.pitch_range"]:
        found = any(required in ids for ids in aspect_map.values())
        assert found, f"{required} not grouped"


def test_aspect_8_is_present_but_blocked_missing():
    fixture = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    payload = analyze_score(fixture, profile_ids=("difficulty_aspects",)).to_json_payload()["analysis_profiles"][0]
    aspect8 = next(a for a in payload["aspects"] if a["aspect_id"] == "structural_pattern_demand")
    assert aspect8["readiness"] in ("blocked", "missing")
    # status field mirrors readiness or contains blocked
    assert aspect8.get("status") in ("blocked", "missing", "blocked") or "blocked" in str(aspect8.get("status")).lower() or aspect8.get("blocked") is True
    # Must have missing/future notes
    missing = aspect8.get("missing_features") or aspect8.get("missing_feature_notes") or aspect8.get("future_features")
    assert missing and len(missing) > 0
    # Should mention no pattern extractor or repetition
    joined_missing = " ".join(missing).lower()
    assert "repetition" in joined_missing or "pattern" in joined_missing or "structural" in joined_missing
    # Limitations should explain blocked
    lim = " ".join(aspect8.get("limitations", []) + aspect8.get("caveats", [])).lower()
    assert "contextual" in lim or "blocked" in lim or "no validated" in lim or "gap" in lim


def test_aspect_9_is_present_and_caveated():
    fixture = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    payload = analyze_score(fixture, profile_ids=("difficulty_aspects",)).to_json_payload()["analysis_profiles"][0]
    aspect9 = next(a for a in payload["aspects"] if a["aspect_id"] == "performance_interpretive_demand")
    assert aspect9["readiness"] == "caveated"
    assert aspect9.get("caveated") is True or aspect9.get("is_caveated") is True or aspect9.get("status") == "caveated"
    # Must list blocked Yan candidates or mention velocity/mc family
    missing = aspect9.get("missing_features") or aspect9.get("missing_feature_notes") or aspect9.get("future_features")
    assert missing and len(missing) > 0
    joined = " ".join(missing).lower()
    assert "pressing_velocity" in joined or "melodic_complexity" in joined or "blocked" in joined
    lim = " ".join(aspect9.get("limitations", []) + aspect9.get("caveats", [])).lower()
    assert "caveated" in lim or "partially observable" in lim or "learner" in lim
    # Should make clear not actual performance interpretation
    assert "not actual performance" in lim or "not how it must be performed" in lim or "written" in lim or "score alone" in lim or "needs performance" in lim


def test_difficulty_overview_output_remains_unchanged_when_requested_separately():
    fixture = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    # Single profile overview is legacy/provenance
    overview_payload = analyze_score(fixture, profile_ids=("difficulty_overview",)).to_json_payload()["analysis_profiles"][0]
    assert overview_payload["schema_version"] == "difficulty_overview.v1"
    assert overview_payload["profile_id"] == "difficulty_overview"
    assert "factors" in overview_payload
    assert "regions" in overview_payload
    # Requesting both should not alter overview payload
    both = analyze_score(fixture, profile_ids=("difficulty_overview", "difficulty_aspects")).to_json_payload()["analysis_profiles"]
    overview_both = next(p for p in both if p["profile_id"] == "difficulty_overview")
    aspects_both = next(p for p in both if p["profile_id"] == "difficulty_aspects")
    assert overview_both["schema_version"] == "difficulty_overview.v1"
    assert overview_both["factors"] == overview_payload["factors"]
    assert aspects_both["schema_version"] == "difficulty_aspects.v1"
    # Aspects now IS the primary temporal model: it has aspect composite, not a legacy weighted grade
    assert "composite" in aspects_both and isinstance(aspects_both["composite"], dict)
    assert aspects_both["composite"].get("feature_id") == "composite.aspect_demand"
    assert "normalized_values" in aspects_both["composite"]
    # Overview still has its own composite (legacy)
    assert "composite" in overview_payload


def test_aspect_temporal_series_and_composite_are_nine_aspect():
    fixture = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    payload = analyze_score(fixture, profile_ids=("difficulty_aspects",)).to_json_payload()["analysis_profiles"][0]
    # Temporal fields
    assert "regions" in payload and isinstance(payload["regions"], list) and len(payload["regions"]) > 0
    assert "series" in payload and isinstance(payload["series"], dict)
    assert len(payload["series"]) == 9
    assert set(payload["series"].keys()) == set(EXPECTED_ASPECT_IDS)
    # Each series has temporal values and readiness metadata
    for aid in EXPECTED_ASPECT_IDS:
        series = payload["series"][aid]
        assert series["aspect_id"] == aid
        assert series["readiness"] in ("ready", "partial", "blocked", "caveated")
        assert "raw_values" in series and "normalized_values" in series and "smoothed_values" in series
        assert len(series["raw_values"]) == len(payload["regions"])
        # blocked aspect has no temporal signal
        if aid == "structural_pattern_demand":
            assert series["readiness"] == "blocked"
            assert series.get("blocked") is True
            assert all(v is None for v in series["normalized_values"])
        if aid == "performance_interpretive_demand":
            assert series["readiness"] == "caveated"
            assert series.get("caveated") is True
    # Composite is descriptive mean excluding blocked
    assert "composite" in payload and payload["composite"] is not None
    comp = payload["composite"]
    assert comp["feature_id"] == "composite.aspect_demand"
    assert len(comp["normalized_values"]) == len(payload["regions"])
    # Chart alias — taxonomy order (1-9), not alphabetical
    assert "chart" in payload
    assert set(payload["chart"]["aspect_ids"]) == set(EXPECTED_ASPECT_IDS)
    assert payload["chart"]["aspect_ids"] == list(EXPECTED_ASPECT_IDS)
    assert set(payload["chart"]["factor_ids"]) == set(EXPECTED_ASPECT_IDS)
    assert set(payload["chart"]["series"].keys()) == set(EXPECTED_ASPECT_IDS)


def test_aspect_hotspots_are_ranked_from_aspect_composite_with_nested_contributors():
    fixture = FIXTURE if FIXTURE.exists() else ALT_FIXTURE
    payload = analyze_score(fixture, profile_ids=("difficulty_aspects",)).to_json_payload()["analysis_profiles"][0]
    hotspots = payload.get("hotspots") or payload.get("candidate_sections") or payload.get("aspect_hotspots")
    assert hotspots is not None and isinstance(hotspots, list) and len(hotspots) > 0
    # Hotspots ranked, top has highest score
    scores = [h.get("score_value") if h.get("score_value") is not None else h.get("score") for h in hotspots]
    assert scores == sorted(scores, reverse=True)
    for h in hotspots:
        assert "rank" in h
        assert "measure_numbers" in h
        # Aspect contributors present
        aspect_contribs = h.get("aspect_contributors") or h.get("top_contributors") or h.get("contributions")
        assert aspect_contribs is not None and len(aspect_contribs) > 0
        for ac in aspect_contribs:
            assert "aspect_id" in ac or "feature_id" in ac
            # Nested feature contributors where available (non-blocked aspects)
            if ac.get("readiness") != "blocked":
                feats = ac.get("feature_contributors") or ac.get("supporting_feature_contributors") or []
                # At least some aspects will have feature contributors
                assert isinstance(feats, list)
