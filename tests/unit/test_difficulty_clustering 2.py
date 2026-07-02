from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pandas as pd

from tests.harness.difficulty_clustering.config import load_experiment_config
from tests.harness.difficulty_clustering.runner import (
    _attach_posthoc_label_column,
    run_cluster_sweep,
    run_experiment,
)
from tests.harness.difficulty_clustering.sweep_summary import summarize_sweep

CONFIG_DIR = Path(__file__).resolve().parents[1] / "harness" / "difficulty_clustering" / "configs"
OG_MATRIX_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "artifacts"
    / "oktav_dataset"
    / "og_export"
    / "full_run"
    / "og_full_dataset.csv"
)
CIPI_MATRIX_PATH = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "artifacts"
    / "retired"
    / "cipi_og_export"
    / "full_cipi_run"
    / "og_full_dataset.csv"
)


def test_clustering_configs_parse() -> None:
    configs = sorted(CONFIG_DIR.glob("*.yaml"))
    assert configs, "Expected committed difficulty-clustering configs."
    for config_path in configs:
        config = load_experiment_config(config_path)
        assert config.experiment_name
        assert config.dataset_name in {"oktav", "cipi"}
        assert config.pca.n_components >= 2
        assert config.clustering.n_clusters >= 2


def test_oktav_clustering_experiment_runs_end_to_end_on_trimmed_matrix(tmp_path: Path) -> None:
    source = pd.read_csv(OG_MATRIX_PATH)
    trimmed = source[source["status"] == "success"].head(24).copy()
    trimmed["constant_probe"] = 1.0
    input_matrix = tmp_path / "oktav_trimmed.csv"
    trimmed.to_csv(input_matrix, index=False)

    base = load_experiment_config(CONFIG_DIR / "oktav_sebastian_7features_k3.yaml")
    config = base.__class__(
        experiment_name=base.experiment_name,
        dataset_name=base.dataset_name,
        input_matrix_path=input_matrix,
        id_columns=base.id_columns,
        label_column=base.label_column,
        feature_columns=base.feature_columns + ("constant_probe",),
        feature_set=None,
        excluded_columns=base.excluded_columns,
        preprocessing=base.preprocessing,
        pca=base.pca,
        clustering=base.clustering,
        sweep=base.sweep,
        output_options=base.output_options,
        config_path=base.config_path,
    )

    result = run_experiment(config, runs_root=tmp_path / "runs")

    assert result.run_dir.exists()
    assert result.resolved_config_path.is_file()
    assert result.metrics_path.is_file()
    assert result.report_path.is_file()

    expected_files = [
        "pca_explained_variance.csv",
        "pca_loadings.csv",
        "piece_coordinates.csv",
        "cluster_assignments.csv",
        "cluster_label_crosstab.csv",
        "cluster_profiles.csv",
        "pca_scatter_by_cluster.png",
        "pca_scatter_by_label.png",
        "ward_dendrogram.png",
        "difficulty_by_cluster_boxplot.png",
    ]
    for filename in expected_files:
        assert (result.run_dir / filename).is_file(), filename

    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["experiment_name"] == "oktav_sebastian_7features_k3"
    assert metrics["row_count"] == 24
    assert metrics["cluster_count"] == 3
    assert metrics["feature_count"] == 7
    assert "constant_probe" in metrics["preprocessing"]["constant_feature_columns"]


def test_cipi_clustering_experiment_runs_end_to_end_on_trimmed_matrix(tmp_path: Path) -> None:
    source = pd.read_csv(CIPI_MATRIX_PATH)
    trimmed = source[source["status"] == "success"].head(24).copy()
    trimmed["constant_probe"] = 1.0
    input_matrix = tmp_path / "cipi_trimmed.csv"
    trimmed.to_csv(input_matrix, index=False)

    base = load_experiment_config(CONFIG_DIR / "cipi_sebastien_9features_k3.yaml")
    config = base.__class__(
        experiment_name=base.experiment_name,
        dataset_name=base.dataset_name,
        input_matrix_path=input_matrix,
        id_columns=base.id_columns,
        label_column=base.label_column,
        feature_columns=base.feature_columns,
        feature_set=base.feature_set,
        excluded_columns=base.excluded_columns,
        preprocessing=base.preprocessing,
        pca=base.pca,
        clustering=base.clustering,
        sweep=base.sweep,
        output_options=base.output_options,
        config_path=base.config_path,
    )

    result = run_experiment(config, runs_root=tmp_path / "runs")

    assert result.run_dir.exists()
    assert result.resolved_config_path.is_file()
    assert result.metrics_path.is_file()
    assert result.report_path.is_file()

    metrics = json.loads(result.metrics_path.read_text(encoding="utf-8"))
    assert metrics["experiment_name"] == "cipi_sebastien_9features_k3"
    assert metrics["row_count"] == 24
    assert metrics["cluster_count"] == 3
    assert metrics["feature_count"] == 9
    assert metrics["label_join"]["join_key"] == "dataset_relative_path + filename fallback"
    assert metrics["label_evaluation"] is not None
    assert metrics["label_evaluation"]["label_column"] == "henle"
    assert metrics["label_evaluation"]["label_row_count"] == 24


def test_cipi_label_join_preserves_all_catalog_henle_values() -> None:
    base = load_experiment_config(CONFIG_DIR / "cipi_sebastien_9features_k3.yaml")
    config = base.__class__(
        experiment_name=base.experiment_name,
        dataset_name=base.dataset_name,
        input_matrix_path=base.input_matrix_path,
        id_columns=base.id_columns,
        label_column=base.label_column,
        feature_columns=base.feature_columns,
        feature_set=base.feature_set,
        excluded_columns=base.excluded_columns,
        preprocessing=base.preprocessing,
        pca=base.pca,
        clustering=base.clustering,
        sweep=base.sweep,
        output_options=base.output_options,
        config_path=base.config_path,
    )

    frame = pd.DataFrame(
        {
            "dataset_relative_path": [
                "bach/bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
            ],
            "filename": [
                "bach_prelude-and-fugue-d-major-bwv-850-mvt1.musicxml",
            ],
        }
    )

    joined, diagnostics = _attach_posthoc_label_column(frame, Path("dummy.csv"), config)

    assert joined.loc[0, "henle"] == 5
    assert joined.loc[0, "henle_catalog_values"] == "5|6"
    assert joined.loc[0, "henle_catalog_value_count"] == 2
    assert diagnostics is not None
    assert diagnostics["join_key"].startswith("dataset_relative_path")


def test_clustering_sweep_config_parses() -> None:
    config = load_experiment_config(CONFIG_DIR / "oktav_sebastian_7features_ksweep.yaml")
    assert config.sweep.enabled is True
    assert config.sweep.k_values == (2, 3, 4, 5, 6)
    assert config.sweep.selection_metric == "silhouette_score"
    assert config.sweep.selection_goal == "maximize"


def test_clustering_sweep_runs_and_writes_summary(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "catalog_index": [f"piece-{index}" for index in range(18)],
            "filename": [f"piece-{index}.musicxml" for index in range(18)],
            "repo_relative_path": [f"piece-{index}.musicxml" for index in range(18)],
            "oktav_code": [f"code-{index}" for index in range(18)],
            "difficulty_numeric": [1, 1, 1, 2, 2, 2] * 3,
            "feature_a": [0.0, 0.1, 0.2, 1.0, 1.1, 1.2] * 3,
            "feature_b": [0.0, 0.2, 0.1, 1.0, 1.2, 1.1] * 3,
            "feature_c": [1.0, 0.9, 1.1, 2.0, 1.9, 2.1] * 3,
            "feature_d": [2.0, 2.1, 1.9, 3.0, 3.1, 2.9] * 3,
            "feature_e": [3.0, 3.1, 2.9, 4.0, 4.1, 3.9] * 3,
            "feature_f": [4.0, 4.1, 3.9, 5.0, 5.1, 4.9] * 3,
            "feature_g": [5.0, 5.1, 4.9, 6.0, 6.1, 5.9] * 3,
        }
    )
    input_matrix = tmp_path / "sweep_matrix.csv"
    frame.to_csv(input_matrix, index=False)

    base = load_experiment_config(CONFIG_DIR / "oktav_sebastian_7features_k3.yaml")
    config = replace(
        base,
        experiment_name="sweep_probe",
        input_matrix_path=input_matrix,
        feature_columns=(
            "feature_a",
            "feature_b",
            "feature_c",
            "feature_d",
            "feature_e",
            "feature_f",
            "feature_g",
        ),
        clustering=replace(
            base.clustering,
            n_clusters=3,
        ),
        sweep=replace(
            base.sweep,
            enabled=True,
            k_values=(2, 3, 4),
            selection_metric="silhouette_score",
        ),
    )

    result = run_cluster_sweep(config, runs_root=tmp_path / "runs")

    assert result.sweep_dir.exists()
    assert result.summary_path.is_file()
    assert result.report_path.is_file()
    assert len(result.candidate_runs) == 3
    assert result.summary["best_k"] in {2, 3, 4}
    assert (result.sweep_dir / "sweep_summary.csv").is_file()
    assert (result.sweep_dir / "sweep_metric_curve.png").is_file()


def test_sweep_summary_helper_reads_summary_and_returns_top_candidates(tmp_path: Path) -> None:
    summary_path = tmp_path / "sweep_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "sweep_dir": str(tmp_path),
                "selection_metric": "silhouette_score",
                "selection_goal": "maximize",
                "best_k": 4,
                "best_run_dir": str(tmp_path / "k4"),
                "candidate_rows": [
                    {"k": 2, "selection_score": 0.31, "selection_rank": 3, "run_dir": "k2"},
                    {"k": 3, "selection_score": 0.42, "selection_rank": 2, "run_dir": "k3"},
                    {"k": 4, "selection_score": 0.55, "selection_rank": 1, "run_dir": "k4"},
                ],
            }
        ),
        encoding="utf-8",
    )

    summary = summarize_sweep(summary_path, top_n=2)

    assert summary["best_k"] == 4
    assert summary["candidate_count"] == 3
    assert [row["k"] for row in summary["top_candidates"]] == [4, 3]
