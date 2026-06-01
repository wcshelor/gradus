from __future__ import annotations

from pathlib import Path

from piano_difficulty.output.verbose_report import render_verbose_report
from piano_difficulty.pipeline import analyze_score

FEATURE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"


def test_render_verbose_report_includes_feature_and_profile_details() -> None:
    payload = analyze_score(FEATURE_FIXTURE_PATH).to_json_payload()

    report = render_verbose_report(payload)

    assert "Verbose Extraction Report" in report
    assert "Path: " in report
    assert "Feature count: 61" in report
    assert "- metadata.measure_count: 2 measures" in report
    assert "- notation.accidental_count" in report
    assert "source span: measure 2" in report
    assert "- Profile: scoreanalyzer_reference (version 1.0)" in report
    assert "overall score: 2.0" in report
    assert "summary: Estimated speed ratio 42.6% from tempo 100 and significant shortest value 12." in report
    assert "Top-Level Diagnostics" in report
