from __future__ import annotations

from pathlib import Path

from piano_difficulty.difficulty_analysis.markdown import render_markdown_report
from piano_difficulty.difficulty_analysis.scoreanalyzer_reference import (
    mark_chords,
    mark_displacement,
    mark_harmony,
    mark_length,
    mark_rhythm,
    mark_speed,
    mark_tonality,
)
from piano_difficulty.pipeline import analyze_score

FEATURE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"


def test_scoreanalyzer_reference_threshold_boundaries() -> None:
    assert mark_speed(20) == 1
    assert mark_speed(20.01) == 2
    assert mark_speed(50) == 2
    assert mark_speed(50.01) == 3
    assert mark_speed(80) == 3
    assert mark_speed(80.01) == 4

    assert mark_displacement(5, 10) == 1
    assert mark_displacement(6, 11) == 3
    assert mark_displacement(11, 21) == 4

    assert mark_chords(10, 10) == 1
    assert mark_chords(11, 11) == 3
    assert mark_chords(31, 31) == 4

    assert mark_harmony(5, 5) == 1
    assert mark_harmony(6, 6) == 2
    assert mark_harmony(21, 21) == 4

    assert mark_rhythm(0) == 1
    assert mark_rhythm(20) == 2
    assert mark_rhythm(60) == 3
    assert mark_rhythm(60.01) == 4

    assert mark_length(2) == 1
    assert mark_length(4) == 2
    assert mark_length(6) == 3
    assert mark_length(7) == 4

    assert mark_tonality(1) == 1
    assert mark_tonality(3) == 2
    assert mark_tonality(5) == 3
    assert mark_tonality(6) == 4


def test_analyze_score_emits_scoreanalyzer_reference_payload(tmp_path: Path) -> None:
    payload = analyze_score(FEATURE_FIXTURE_PATH, profile_ids=("scoreanalyzer_reference",)).to_json_payload()

    assert payload["analysis_profiles"]
    profile = payload["analysis_profiles"][0]
    assert profile["profile_id"] == "scoreanalyzer_reference"
    assert profile["overall_score"] == 2.0
    assert profile["scoreanalyzer_legacy_grade"] == "intermediate"
    assert [dimension["dimension_id"] for dimension in profile["dimensions"]] == [
        "speed",
        "displacement",
        "chords",
        "harmony",
        "rhythm",
        "length",
        "tonality",
    ]
    assert profile["dimensions"][0]["summary"].startswith("Estimated speed ratio")
    assert profile["dimensions"][0]["legacy_label"] == "intermediate"


def test_markdown_report_renders_from_saved_payload(tmp_path: Path) -> None:
    payload = analyze_score(FEATURE_FIXTURE_PATH, profile_ids=("scoreanalyzer_reference",)).to_json_payload()
    report = render_markdown_report(payload, profile_id="scoreanalyzer_reference")

    assert "## Overview" in report
    assert "## Speed" in report
    assert "## Displacement" in report
    assert "## Chords" in report
    assert "## Harmony" in report
    assert "## Rhythm" in report
    assert "## Length" in report
    assert "## Tonality" in report
    assert "## Notable Measures" in report
    assert "## Diagnostics" in report
