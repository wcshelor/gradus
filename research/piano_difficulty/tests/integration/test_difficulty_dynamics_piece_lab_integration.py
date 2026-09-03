from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from tests.harness.difficulty_dynamics.config import load_difficulty_dynamics_config
from tests.harness.difficulty_dynamics.piece_lab import run_piece_lab

CONFIG_PATH = Path(__file__).resolve().parents[1] / "harness" / "difficulty_dynamics" / "configs" / "demo.yaml"
FIXTURE_SCORE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"


def test_piece_lab_runs_manifest_and_writes_consolidated_outputs(tmp_path: Path) -> None:
    manifest_path = tmp_path / "piece_lab.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["score_id", "title", "composer", "score_path", "learned_by_user", "known_hard_measures"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "score_id": "fixture-piece",
                "title": "Fixture Piece",
                "composer": "Fixture Composer",
                "score_path": str(FIXTURE_SCORE_PATH),
                "learned_by_user": "yes",
                "known_hard_measures": "1",
            }
        )

    config = load_difficulty_dynamics_config(CONFIG_PATH)
    config = replace(
        config,
        export=replace(
            config.export,
            output_root=tmp_path / "difficulty_dynamics_piece_lab",
            run_name="piece-lab",
            write_plot=False,
        ),
    )

    result = run_piece_lab(config, manifest_path)

    assert result.batch_dir.exists()
    assert result.summary_csv_path.is_file()
    assert result.report_path.is_file()
    assert len(result.item_results) == 1
    assert result.item_results[0].status == "success"
    assert result.item_results[0].run_result is not None
    assert result.item_results[0].run_result.hotspots_path.is_file()
    assert result.item_results[0].run_result.report_path.is_file()
    assert "Difficulty Dynamics Piece Lab" in result.report_path.read_text(encoding="utf-8")
