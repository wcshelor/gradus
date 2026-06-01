from __future__ import annotations

from pathlib import Path

from piano_difficulty.pipeline import analyze_score
from tests.regression._snapshot import snapshot_json


def test_scoreanalyzer_reference_feature_fixture_snapshot() -> None:
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
    payload = analyze_score(fixture_path).to_json_payload()
    actual = snapshot_json(payload)
    snapshot_path = Path(__file__).with_name("scoreanalyzer_reference_feature_fixture.json")

    assert actual == snapshot_path.read_text()


def test_scoreanalyzer_reference_real_mxl_snapshot() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "real_mxl_basic_grand_staff.mxl"
    )
    payload = analyze_score(fixture_path).to_json_payload()
    actual = snapshot_json(payload)
    snapshot_path = Path(__file__).with_name("scoreanalyzer_reference_real_mxl_basic_grand_staff.json")

    assert actual == snapshot_path.read_text()
