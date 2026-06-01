from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from piano_difficulty.comparison.scoreanalyzer_normalization_battery import (
    DEFAULT_VARIANT_IDS,
    run_normalization_battery,
)
from piano_difficulty.comparison.scoreanalyzer_parity import CANONICAL_METRICS


def test_normalization_battery_writes_artifacts_and_ranking_with_mocked_og(
    tmp_path: Path,
) -> None:
    pieces_root = Path("tests/fixtures")
    piece_relpath = "parity_feature_probe.musicxml"
    out_dir = tmp_path / "battery"
    selected_variants = (
        "baseline_current",
        "norm_base_duration_raw_units",
        "quirk_max_interval_measure_index",
    )

    def fake_og_runner(_php_bin: Path, _shim_path: Path, _piece_dir: str) -> dict[str, object]:
        payload = {metric: 0 for metric in CANONICAL_METRICS}
        payload["mode"] = "major"
        return payload

    exit_code = run_normalization_battery(
        piece_relpath=piece_relpath,
        php_bin=Path("/tmp/php"),
        pieces_root=pieces_root,
        out_dir=out_dir,
        variants=selected_variants,
        og_runner=fake_og_runner,
    )

    assert exit_code == 1
    summary_path = out_dir / "battery_summary.json"
    matrix_path = out_dir / "variant_metric_matrix.csv"
    ranking_path = out_dir / "variant_ranking.csv"
    assert summary_path.exists()
    assert matrix_path.exists()
    assert ranking_path.exists()

    payload = json.loads(summary_path.read_text())
    assert payload["baseline_mismatch_count"] > 0
    assert tuple(payload["selected_variants"]) == selected_variants
    assert payload["ranking"]

    for row in payload["variant_results"]:
        assert row["net_gain"] == (len(row["fixed_metrics"]) - len(row["regressed_metrics"]))

    with matrix_path.open() as handle:
        matrix_rows = list(csv.DictReader(handle))
    assert len(matrix_rows) == len(selected_variants) * len(CANONICAL_METRICS)
    assert {"variant_id", "metric", "og_value", "replica_value", "delta", "equal"} == set(
        matrix_rows[0].keys()
    )

    with ranking_path.open() as handle:
        ranking_rows = list(csv.DictReader(handle))
    assert ranking_rows
    assert {"variant_id", "mismatch_count", "net_gain", "fixed_metrics", "regressed_metrics"}.issubset(
        ranking_rows[0].keys()
    )


def test_normalization_battery_real_alla_turca_smoke(tmp_path: Path) -> None:
    php = shutil.which("php")
    if not php:
        pytest.skip("php executable is not available in this environment.")

    pieces_root = Path("external/ScoreAnalyzer/pieces")
    piece_relpath = "AllaTurca_Mozart/Alla_Turca.xml"
    if not (pieces_root / piece_relpath).exists():
        pytest.skip("Alla Turca fixture is not available in this workspace.")

    out_dir = tmp_path / "alla_turca_battery"
    selected_variants = ("baseline_current", "combined_og_compat_core")
    exit_code = run_normalization_battery(
        piece_relpath=piece_relpath,
        php_bin=Path(php),
        pieces_root=pieces_root,
        out_dir=out_dir,
        variants=selected_variants,
    )
    assert exit_code == 1

    summary_path = out_dir / "battery_summary.json"
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text())
    assert payload["baseline_mismatch_count"] > 0
    assert payload["ranking"]
    result_ids = [row["variant_id"] for row in payload["variant_results"]]
    for expected in selected_variants:
        assert expected in result_ids


def test_default_variant_registry_matches_expected_contract() -> None:
    assert "baseline_current" in DEFAULT_VARIANT_IDS
    assert "combined_og_compat_core" in DEFAULT_VARIANT_IDS

