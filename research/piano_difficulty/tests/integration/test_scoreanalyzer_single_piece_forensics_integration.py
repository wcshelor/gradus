from __future__ import annotations

import csv
import json
from pathlib import Path
import pytest

from piano_difficulty.comparison.scoreanalyzer_parity import CANONICAL_METRICS, run_replica_metrics
from piano_difficulty.comparison.scoreanalyzer_single_piece_forensics import (
    build_artifact_paths,
    run_single_piece_forensics,
)


def test_single_piece_forensics_writes_all_artifacts_with_mocked_og(tmp_path: Path) -> None:
    pieces_root = Path(__file__).resolve().parents[1] / "fixtures"
    piece_relpath = "feature_fixture.musicxml"
    out_dir = tmp_path / "forensics"

    def fake_og_runner(_php_bin: Path, _shim_path: Path, _piece_dir: str) -> dict[str, object]:
        metrics = {metric: 0 for metric in CANONICAL_METRICS}
        metrics["mode"] = "major"
        return metrics

    exit_code = run_single_piece_forensics(
        piece_relpath=piece_relpath,
        php_bin=Path("/tmp/php"),
        pieces_root=pieces_root,
        out_dir=out_dir,
        max_suspects_per_metric=20,
        og_runner=fake_og_runner,
    )
    assert exit_code == 1

    artifact_paths = build_artifact_paths(out_dir=out_dir, piece_relpath=piece_relpath)
    comparison_json = artifact_paths["comparison_json"]
    events_csv = artifact_paths["metric_events_csv"]
    note_flags_csv = artifact_paths["note_flags_csv"]
    summary_md = artifact_paths["summary_md"]
    assert comparison_json.exists()
    assert events_csv.exists()
    assert note_flags_csv.exists()
    assert summary_md.exists()

    payload = json.loads(comparison_json.read_text())
    assert payload["mismatch_count"] > 0
    assert payload["mismatched_metrics"]

    with events_csv.open() as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {"metric", "measure_index", "measure_number", "suspect_note_id"}.issubset(rows[0].keys())


def test_single_piece_forensics_real_alla_turca_has_event_driven_evidence(tmp_path: Path) -> None:
    piece_relpath = "AllaTurca_Mozart/Alla_Turca.xml"
    pieces_root = Path(__file__).resolve().parents[2] / "external/ScoreAnalyzer/pieces"
    piece_path = pieces_root / piece_relpath
    if not piece_path.is_file():
        pytest.skip("Optional local Alla Turca corpus is not installed.")
    replica_metrics = run_replica_metrics(piece_path)

    og_metrics = dict(replica_metrics)
    og_metrics["maxIntervalRH"] = int(replica_metrics["maxIntervalRH"]) + 5
    og_metrics["displacementsRH"] = float(replica_metrics["displacementsRH"]) + 5.0

    def fake_og_runner(_php_bin: Path, _shim_path: Path, _piece_dir: str) -> dict[str, object]:
        return dict(og_metrics)

    out_dir = tmp_path / "alla_turca_forensics"
    exit_code = run_single_piece_forensics(
        piece_relpath=piece_relpath,
        php_bin=Path("/tmp/php"),
        pieces_root=pieces_root,
        out_dir=out_dir,
        max_suspects_per_metric=20,
        og_runner=fake_og_runner,
    )
    assert exit_code == 1

    artifact_paths = build_artifact_paths(out_dir=out_dir, piece_relpath=piece_relpath)
    comparison_json = json.loads(artifact_paths["comparison_json"].read_text())
    assert comparison_json["mismatched_metrics"]
    assert "maxIntervalRH" in comparison_json["mismatched_metrics"]
    assert "displacementsRH" in comparison_json["mismatched_metrics"]

    with artifact_paths["metric_events_csv"].open() as handle:
        rows = list(csv.DictReader(handle))
    max_rows = [row for row in rows if row["metric"] == "maxIntervalRH"]
    disp_rows = [row for row in rows if row["metric"] == "displacementsRH"]
    assert max_rows
    assert disp_rows
    assert any("->" in row["suspect_note_id"] for row in max_rows if row["suspect_note_id"])
    assert any(row["measure_index"] for row in disp_rows)
