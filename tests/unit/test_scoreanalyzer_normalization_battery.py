from __future__ import annotations

import json
from pathlib import Path

import pytest

from piano_difficulty.comparison.scoreanalyzer_normalization_battery import (
    DEFAULT_VARIANT_IDS,
    build_default_variants,
    run_normalization_battery,
)
from piano_difficulty.comparison.scoreanalyzer_parity import run_replica_metrics


ALLA_TURCA_REL = "AllaTurca_Mozart/Alla_Turca.xml"
ALLA_TURCA_PIECES_ROOT = Path("external/ScoreAnalyzer/pieces")
ALLA_TURCA_PATH = ALLA_TURCA_PIECES_ROOT / ALLA_TURCA_REL


def test_default_variant_registry_is_deterministic() -> None:
    variants = build_default_variants()
    assert tuple(variant.variant_id for variant in variants) == DEFAULT_VARIANT_IDS
    assert len({variant.variant_id for variant in variants}) == len(DEFAULT_VARIANT_IDS)


def test_selected_variants_apply_expected_overrides_on_alla_turca(tmp_path: Path) -> None:
    if not ALLA_TURCA_PATH.exists():
        pytest.skip("Alla Turca fixture is not present in this workspace.")

    baseline_metrics = run_replica_metrics(ALLA_TURCA_PATH)

    def fake_og_runner(_php_bin: Path, _shim_path: Path, _piece_dir: str) -> dict[str, object]:
        return dict(baseline_metrics)

    selected_variants = (
        "baseline_current",
        "norm_base_duration_raw_units",
        "norm_hand_counts_by_voice",
        "norm_chord_detection_sequential",
        "quirk_max_interval_measure_index",
    )
    out_dir = tmp_path / "battery"
    exit_code = run_normalization_battery(
        piece_relpath=ALLA_TURCA_REL,
        php_bin=Path("/tmp/php"),
        pieces_root=ALLA_TURCA_PIECES_ROOT,
        out_dir=out_dir,
        variants=selected_variants,
        og_runner=fake_og_runner,
    )

    assert exit_code == 0
    summary_path = out_dir / "battery_summary.json"
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text())
    by_id = {
        row["variant_id"]: row
        for row in payload["variant_results"]
    }

    baseline = by_id["baseline_current"]
    assert baseline["mismatch_count"] == 0
    assert baseline["mismatched_metrics"] == []

    base_duration_variant = by_id["norm_base_duration_raw_units"]
    assert base_duration_variant["metrics"]["baseDuration"] == pytest.approx(1.0)
    assert base_duration_variant["metrics"]["baseDuration"] != baseline_metrics["baseDuration"]

    voice_variant = by_id["norm_hand_counts_by_voice"]
    assert voice_variant["metrics"]["noteCounterRH"] == 823
    assert voice_variant["metrics"]["noteCounterLH"] == 635
    assert voice_variant["metrics"]["noteCounterRH"] != baseline_metrics["noteCounterRH"]
    assert voice_variant["metrics"]["noteCounterLH"] != baseline_metrics["noteCounterLH"]

    chord_variant = by_id["norm_chord_detection_sequential"]
    assert chord_variant["metrics"]["chordsRH"] == pytest.approx(23.75776397515528)
    assert chord_variant["metrics"]["chordsRH"] != baseline_metrics["chordsRH"]

    quirk_variant = by_id["quirk_max_interval_measure_index"]
    quirk_max_interval = quirk_variant["metrics"]["maxIntervalRH"]
    assert isinstance(quirk_max_interval, int)
    assert quirk_max_interval != baseline_metrics["maxIntervalRH"]
    assert 0 <= quirk_max_interval <= quirk_variant["metrics"]["nbmeasures"]

