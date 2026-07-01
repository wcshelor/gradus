from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from tests.harness.difficulty_clustering.config import load_experiment_config
from tests.harness.difficulty_clustering.runner import (
    _attach_posthoc_label_column,
    run_experiment,
)

CONFIG_DIR = Path(__file__).resolve().parents[1] / "harness" / "difficulty_clustering" / "configs"


def test_clustering_configs_parse() -> None:
    for config_path in sorted(CONFIG_DIR.glob("*.yaml")):
        config = load_experiment_config(config_path)
        assert config.experiment_name
        assert config.dataset_name in {"oktav", "cipi"}
        assert config.pca.n_components >= 1
        assert config.clustering.n_clusters >= 2


def test_oktav_clustering_experiment_runs_end_to_end(tmp_path: Path) -> None:
    matrix_path = tmp_path / "oktav_fixture.csv"
    _build_oktav_fixture_matrix().to_csv(matrix_path, index=False)

    base_config = load_experiment_config(CONFIG_DIR / "oktav_sebastien_9features_k3.yaml")
    config = base_config.__class__(
        experiment_name=base_config.experiment_name,
        dataset_name=base_config.dataset_name,
        input_matrix_path=matrix_path,
        id_columns=base_config.id_columns,
        label_column=base_config.label_column,
        feature_columns=base_config.feature_columns,
        feature_set=base_config.feature_set,
        excluded_columns=base_config.excluded_columns,
        preprocessing=base_config.preprocessing,
        pca=base_config.pca,
        clustering=base_config.clustering,
        output_options=base_config.output_options,
        config_path=base_config.config_path,
    )

    result = run_experiment(config, runs_root=tmp_path / "clustering_runs")
    assert result.run_dir.exists()
    assert result.resolved_config_path.is_file()
    assert result.metrics_path.is_file()
    assert result.report_path.is_file()
    assert result.piece_coordinates_path.is_file()
    assert result.cluster_profiles_path.is_file()

    metrics = json.loads(result.metrics_path.read_text())
    assert {"silhouette", "cluster_counts"} <= set(metrics)


def test_cipi_clustering_experiment_runs_end_to_end_with_catalog_join(tmp_path: Path, monkeypatch) -> None:
    matrix_path = tmp_path / "cipi_fixture.csv"
    _build_cipi_fixture_matrix().to_csv(matrix_path, index=False)
    catalog_path = tmp_path / "cipi_catalog.csv"
    _build_cipi_catalog_fixture().to_csv(catalog_path, index=False)

    import tests.harness.difficulty_clustering.runner as clustering_runner

    monkeypatch.setattr(clustering_runner, "DEFAULT_CATALOG_CSV", catalog_path)

    base_config = load_experiment_config(CONFIG_DIR / "cipi_sebastien_9features_k3.yaml")
    config = base_config.__class__(
        experiment_name=base_config.experiment_name,
        dataset_name=base_config.dataset_name,
        input_matrix_path=matrix_path,
        id_columns=base_config.id_columns,
        label_column=base_config.label_column,
        feature_columns=base_config.feature_columns,
        feature_set=base_config.feature_set,
        excluded_columns=base_config.excluded_columns,
        preprocessing=base_config.preprocessing,
        pca=base_config.pca,
        clustering=base_config.clustering,
        output_options=base_config.output_options,
        config_path=base_config.config_path,
    )

    result = run_experiment(config, runs_root=tmp_path / "clustering_runs")
    metrics = json.loads(result.metrics_path.read_text())
    assert metrics["dataset_name"] == "cipi"
    assert metrics["label_join"]["joined_rows"] >= 1


def test_attach_posthoc_label_column_preserves_all_catalog_labels(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "dataset_relative_path": "bach/bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
                "filename": "bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
                "length": 10.0,
            }
        ]
    )
    catalog_path = tmp_path / "cipi_catalog.csv"
    pd.DataFrame(
        [
            {
                "dataset_relative_path": "bach/bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
                "filename": "bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
                "henle": 5,
            },
            {
                "dataset_relative_path": "bach/bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
                "filename": "bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
                "henle": 6,
            },
        ]
    ).to_csv(catalog_path, index=False)

    joined_frame, diagnostics = _attach_posthoc_label_column(frame, "henle", catalog_path=catalog_path)
    assert joined_frame.loc[0, "henle"] == 5
    assert joined_frame.loc[0, "henle_catalog_values"] == "5|6"
    assert joined_frame.loc[0, "henle_catalog_value_count"] == 2
    assert diagnostics["join_key"].startswith("dataset_relative_path")


def _build_oktav_fixture_matrix() -> pd.DataFrame:
    rows = []
    for index, difficulty in enumerate([12, 16, 19, 23, 28, 31, 36, 41, 47], start=1):
        rows.append(
            {
                "piece_id": f"OK{index:03d}",
                "filename": f"oktav_cluster_{index:03d}.musicxml",
                "dataset_relative_path": f"oktav/oktav_cluster_{index:03d}.musicxml",
                "status": "success",
                "difficulty_numeric": float(difficulty),
                "length": difficulty * 0.5,
                "rhythm": difficulty * 0.3,
                "speed": difficulty * 0.4,
                "tonality": (index % 4) + 1,
                "harmony": difficulty * 0.25,
                "chords": difficulty * 0.2,
                "displacements": difficulty * 0.15,
                "harmonyRH": difficulty * 0.18 + 0.1,
                "harmonyLH": difficulty * 0.16 + 0.2,
                "chordsRH": difficulty * 0.14 + 0.1,
                "chordsLH": difficulty * 0.12 + 0.2,
                "displacementsRH": difficulty * 0.10 + 0.1,
                "displacementsLH": difficulty * 0.08 + 0.2,
            }
        )
    return pd.DataFrame(rows)


def _build_cipi_fixture_matrix() -> pd.DataFrame:
    rows = []
    for index, difficulty in enumerate([1.4, 1.8, 2.1, 2.7, 3.0, 3.4, 3.9, 4.4, 4.9], start=1):
        rows.append(
            {
                "piece_id": f"CP{index:03d}",
                "filename": f"cipi_cluster_{index:03d}.musicxml",
                "dataset_relative_path": f"cipi/cipi_cluster_{index:03d}.musicxml",
                "status": "success",
                "overallDifficulty": float(difficulty),
                "length": difficulty * 8.0,
                "rhythm": difficulty * 4.0,
                "speed": difficulty * 5.0,
                "tonality": (index % 3) + 1,
                "harmony": difficulty * 2.0,
                "chords": difficulty * 1.8,
                "displacements": difficulty * 1.5,
                "harmonyRH": difficulty * 1.2 + 0.1,
                "harmonyLH": difficulty * 1.1 + 0.2,
                "chordsRH": difficulty * 0.9 + 0.1,
                "chordsLH": difficulty * 0.8 + 0.2,
                "displacementsRH": difficulty * 0.7 + 0.1,
                "displacementsLH": difficulty * 0.6 + 0.2,
            }
        )
    return pd.DataFrame(rows)


def _build_cipi_catalog_fixture() -> pd.DataFrame:
    rows = []
    for index, henle in enumerate([2, 2, 3, 4, 4, 5, 6, 7, 8], start=1):
        rows.append(
            {
                "dataset_relative_path": f"cipi/cipi_cluster_{index:03d}.musicxml",
                "filename": f"cipi_cluster_{index:03d}.musicxml",
                "henle": henle,
            }
        )
    return pd.DataFrame(rows)

