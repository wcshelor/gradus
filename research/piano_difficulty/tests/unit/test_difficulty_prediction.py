from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from tests.harness.difficulty_prediction.config import load_experiment_config
from tests.harness.difficulty_prediction.core import TargetSchemeConfig
from tests.harness.difficulty_prediction.features import select_feature_columns
from tests.harness.difficulty_prediction.runner import run_experiment
from tests.harness.difficulty_prediction.targets import transform_target

CONFIG_DIR = Path(__file__).resolve().parents[1] / "harness" / "difficulty_prediction" / "configs"


def test_configs_parse() -> None:
    for config_path in sorted(CONFIG_DIR.glob("*.yaml")):
        config = load_experiment_config(config_path)
        assert config.experiment_name
        assert config.dataset_name in {"oktav", "cipi"}
        assert config.target_scheme.kind


def test_target_transform_quantile_bins_and_rounding() -> None:
    series = pd.Series([10.0, 12.0, 14.0, 18.0, 22.0, 28.0])
    quantile_bundle = transform_target(series, TargetSchemeConfig(kind="quantile_bins", bins=3))
    assert len(quantile_bundle.class_labels) == 3
    assert set(quantile_bundle.ordinal_map) == set(quantile_bundle.class_labels)

    rounded_bundle = transform_target(pd.Series([1.2, 1.9, 2.2, 3.8]), TargetSchemeConfig(kind="rounded_class"))
    assert rounded_bundle.class_labels == (1, 2, 4)


def test_oktav_henle_matched_9bin_config_produces_nine_classes() -> None:
    config = load_experiment_config(CONFIG_DIR / "oktav_sebastien_clustering_henle_9bin_logreg.yaml")
    series = pd.Series([11.0, 20.0, 23.0, 26.0, 34.0, 44.0, 47.5, 51.0, 56.0, 76.0])
    bundle = transform_target(series, config.target_scheme)
    assert bundle.class_labels == (1, 2, 3, 4, 5, 6, 7, 8, 9)
    assert str(bundle.model_values.dtype).startswith("int")


def test_sebastien_feature_selection_returns_nine_columns() -> None:
    config = load_experiment_config(CONFIG_DIR / "oktav_sebastien_clustering_ridge_regression.yaml")
    assert config.feature_set == "sebastien_clustering"


def test_runtime_feature_selection_supports_expression_ablation() -> None:
    available_columns = [
        "rhythm_note_density",
        "pitch_geometry_mean_simultaneity_span",
        "leaps_mean_melodic_leap_right",
        "texture_notes_per_onset",
        "coordination_aligned_hand_onset_ratio",
        "notation_accidental_density",
        "expression_staccato_note_ratio",
        "expression_dynamic_marking_count",
    ]

    runtime_all = select_feature_columns(available_columns, "runtime_all")
    runtime_no_expression = select_feature_columns(available_columns, "runtime_no_expression")
    expression_only = select_feature_columns(available_columns, "expression_only")

    assert "expression_staccato_note_ratio" in runtime_all.selected_columns
    assert "expression_staccato_note_ratio" not in runtime_no_expression.selected_columns
    assert expression_only.selected_columns == (
        "expression_staccato_note_ratio",
        "expression_dynamic_marking_count",
    )


def test_oktav_experiment_runs_end_to_end_on_fixture_matrix(tmp_path: Path) -> None:
    fixture_matrix = _build_oktav_fixture_matrix()
    matrix_path = tmp_path / "oktav_fixture.csv"
    fixture_matrix.to_csv(matrix_path, index=False)

    base_config = load_experiment_config(CONFIG_DIR / "oktav_sebastien_clustering_ridge_regression.yaml")
    config = base_config.__class__(
        experiment_name=base_config.experiment_name,
        dataset_name=base_config.dataset_name,
        input_matrix_path=matrix_path,
        id_columns=base_config.id_columns,
        target_column=base_config.target_column,
        target_scheme=base_config.target_scheme,
        feature_set=base_config.feature_set,
        excluded_columns=base_config.excluded_columns,
        preprocessing=base_config.preprocessing,
        model_family=base_config.model_family,
        model_parameters=base_config.model_parameters,
        cross_validation=base_config.cross_validation.__class__(
            kind=base_config.cross_validation.kind,
            folds=4,
            shuffle=base_config.cross_validation.shuffle,
            random_state=base_config.cross_validation.random_state,
        ),
        output_options=base_config.output_options,
        config_path=base_config.config_path,
    )

    result = run_experiment(config, runs_root=tmp_path / "prediction_runs")

    assert result.run_dir.exists()
    assert result.resolved_config_path.is_file()
    assert result.metrics_path.is_file()
    assert result.fold_metrics_path.is_file()
    assert result.predictions_path.is_file()
    assert result.feature_importance_path.is_file()
    assert result.missingness_report_path.is_file()
    assert result.feature_selection_report_path.is_file()

    metrics = json.loads(result.metrics_path.read_text())
    assert {"r2", "rmse", "mae"} <= set(metrics["overall_metrics"])
    with result.predictions_path.open() as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {"fold", "actual_raw_value", "predicted_model_value"} <= set(rows[0])


def test_cipi_experiment_runs_end_to_end_on_fixture_matrix(tmp_path: Path) -> None:
    fixture_matrix = _build_cipi_fixture_matrix()
    matrix_path = tmp_path / "cipi_fixture.csv"
    fixture_matrix.to_csv(matrix_path, index=False)

    base_config = load_experiment_config(CONFIG_DIR / "cipi_sebastien_clustering_ridge_regression.yaml")
    config = base_config.__class__(
        experiment_name=base_config.experiment_name,
        dataset_name=base_config.dataset_name,
        input_matrix_path=matrix_path,
        id_columns=base_config.id_columns,
        target_column=base_config.target_column,
        target_scheme=base_config.target_scheme,
        feature_set=base_config.feature_set,
        excluded_columns=base_config.excluded_columns,
        preprocessing=base_config.preprocessing,
        model_family=base_config.model_family,
        model_parameters=base_config.model_parameters,
        cross_validation=base_config.cross_validation.__class__(
            kind=base_config.cross_validation.kind,
            folds=4,
            shuffle=base_config.cross_validation.shuffle,
            random_state=base_config.cross_validation.random_state,
        ),
        output_options=base_config.output_options,
        config_path=base_config.config_path,
    )

    result = run_experiment(config, runs_root=tmp_path / "prediction_runs")
    metrics = json.loads(result.metrics_path.read_text())
    assert metrics["dataset_name"] == "cipi"
    assert metrics["target_column"] == "overallDifficulty"


def _build_oktav_fixture_matrix() -> pd.DataFrame:
    rows = []
    for index, difficulty in enumerate([12, 15, 18, 21, 25, 29, 33, 37, 42, 48, 54, 60], start=1):
        rows.append(
            {
                "piece_id": f"OK{index:03d}",
                "filename": f"oktav_piece_{index:03d}.musicxml",
                "dataset_relative_path": f"oktav/oktav_piece_{index:03d}.musicxml",
                "status": "success" if index < 12 else "failed",
                "difficulty_numeric": float(difficulty),
                "length": difficulty * 0.60,
                "rhythm": difficulty * 0.35 + (index % 3),
                "speed": difficulty * 0.50 + (index % 2),
                "tonality": (index % 5) + 1,
                "harmony": difficulty * 0.25,
                "chords": difficulty * 0.22,
                "displacements": difficulty * 0.18,
                "harmonyRH": difficulty * 0.20 + 0.5,
                "harmonyLH": difficulty * 0.18 + 0.3,
                "chordsRH": difficulty * 0.15 + 0.4,
                "chordsLH": difficulty * 0.12 + 0.2,
                "displacementsRH": difficulty * 0.10 + 0.1,
                "displacementsLH": difficulty * 0.08 + 0.2,
                "rhythm_density": difficulty * 0.16 + 0.5,
                "rhythm_syncopation": difficulty * 0.04 + (index % 4),
                "leap_mean": difficulty * 0.12 + 0.2,
                "leap_max": difficulty * 0.20 + 1.0,
                "texture_density": difficulty * 0.14 + 0.4,
                "texture_polyphony": difficulty * 0.10 + 0.3,
                "coordination_async_ratio": difficulty * 0.02 + 0.1,
                "notation_accidental_density": difficulty * 0.03 + 0.2,
                "expression_staccato_note_ratio": difficulty * 0.004 + 0.05,
                "expression_dynamic_marking_count": difficulty * 0.08 + 1.0,
            }
        )
    return pd.DataFrame(rows)


def _build_cipi_fixture_matrix() -> pd.DataFrame:
    rows = []
    for index, difficulty in enumerate([1.2, 1.6, 1.9, 2.3, 2.6, 2.9, 3.2, 3.6, 4.0, 4.3, 4.7, 5.0], start=1):
        rows.append(
            {
                "piece_id": f"CP{index:03d}",
                "filename": f"cipi_piece_{index:03d}.musicxml",
                "dataset_relative_path": f"cipi/cipi_piece_{index:03d}.musicxml",
                "status": "success",
                "overallDifficulty": float(difficulty),
                "length": difficulty * 8.0,
                "rhythm": difficulty * 4.0 + (index % 3),
                "speed": difficulty * 5.0 + (index % 2),
                "tonality": (index % 4) + 1,
                "harmony": difficulty * 2.5,
                "chords": difficulty * 2.0,
                "displacements": difficulty * 1.5,
                "harmonyRH": difficulty * 1.4 + 0.1,
                "harmonyLH": difficulty * 1.1 + 0.2,
                "chordsRH": difficulty * 1.0 + 0.1,
                "chordsLH": difficulty * 0.9 + 0.2,
                "displacementsRH": difficulty * 0.8 + 0.1,
                "displacementsLH": difficulty * 0.7 + 0.2,
                "rhythm_density": difficulty * 0.9 + 0.1,
                "rhythm_syncopation": difficulty * 0.5 + 0.1,
                "leap_mean": difficulty * 0.7 + 0.1,
                "leap_max": difficulty * 1.0 + 0.3,
                "texture_density": difficulty * 0.8 + 0.1,
                "texture_polyphony": difficulty * 0.6 + 0.1,
                "coordination_async_ratio": difficulty * 0.2 + 0.01,
                "notation_accidental_density": difficulty * 0.15 + 0.02,
                "expression_staccato_note_ratio": difficulty * 0.05 + 0.01,
                "expression_dynamic_marking_count": difficulty * 0.3 + 0.2,
            }
        )
    return pd.DataFrame(rows)
