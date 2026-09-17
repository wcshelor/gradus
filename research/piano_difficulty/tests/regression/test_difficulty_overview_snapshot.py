"""Compact public contract example; musical behavior has separate unit tests."""

import json
from pathlib import Path

from piano_difficulty.pipeline import analyze_score


def contract_example(profile):
    section = profile["candidate_sections"][0]
    return {
        "schema_version": profile["schema_version"],
        "factor_registry_version": profile["factor_registry_version"],
        "top_level_fields": sorted(profile),
        "region_fields": sorted(profile["regions"][0]),
        "factor_fields": sorted(profile["factors"][0]),
        "first_section": {
            "rank": section["rank"],
            "region": {key: value for key, value in section["region"].items() if key != "score_id"},
            "score": section["score"],
            "supporting_factor_ids": section["supporting_factor_ids"],
            "supporting_window_indices": section["supporting_window_indices"],
            "contribution_scope": section["contribution_scope"],
            "contributions": section["contributions"],
        },
    }


def test_overview_versioned_contract_example():
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
    profiles = analyze_score(fixture, profile_ids=("difficulty_overview",)).to_json_payload()["analysis_profiles"]
    profile = profiles[0]
    expected = json.loads(Path(__file__).with_name("difficulty_overview_contract.json").read_text())
    assert contract_example(profile) == expected
