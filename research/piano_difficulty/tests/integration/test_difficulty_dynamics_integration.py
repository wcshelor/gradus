from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

from tests.harness.difficulty_dynamics.config import load_difficulty_dynamics_config
from tests.harness.difficulty_dynamics.runner import run_experiment

CONFIG_PATH = Path(__file__).resolve().parents[1] / "harness" / "difficulty_dynamics" / "configs" / "demo.yaml"


def test_difficulty_dynamics_demo_runs_end_to_end_on_fixture(tmp_path: Path) -> None:
    config = load_difficulty_dynamics_config(CONFIG_PATH)
    config = replace(
        config,
        export=replace(config.export, output_root=tmp_path / "difficulty_dynamics_runs", run_name="demo"),
    )

    result = run_experiment(config)

    assert result.run_dir.exists()
    assert result.json_path.is_file()
    assert result.csv_path.is_file()
    assert result.peaks_path.is_file()
    assert result.hotspots_path.is_file()
    assert result.report_path.is_file()
    assert result.profile.overall_series is not None
    assert result.profile.hard_spots
    assert result.profile.series["rhythm.note_density"].provenance == "yan2023"
    assert result.profile.series["leaps.mean_melodic_leap"].provenance == "repo_native"

    payload = json.loads(result.json_path.read_text())
    assert payload["schema_version"] == "difficulty_dynamics.v1"
    assert payload["series"]["rhythm.note_density"]["raw_values"]
    assert payload["overall_series"]["feature_id"] == "composite.difficulty"
    assert payload["hard_spots"]
    assert payload["hard_spots"][0]["feature_contributions"]

    with result.csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {"score_id", "window_index", "raw_value", "normalized_value", "smoothed_value"} <= set(rows[0])

    with result.hotspots_path.open(newline="", encoding="utf-8") as handle:
        hotspot_rows = list(csv.DictReader(handle))
    assert hotspot_rows
    assert {"hotspot_id", "contributor_feature_id", "support_count"} <= set(hotspot_rows[0])

    assert "Difficulty Dynamics Summary" in result.report_path.read_text(encoding="utf-8")

    if result.plot_path is not None:
        assert result.plot_path.is_file()
