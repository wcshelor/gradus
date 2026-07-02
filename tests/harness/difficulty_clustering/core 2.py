from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_clustering"
DEFAULT_RUNS_ROOT = DEFAULT_ARTIFACTS_ROOT / "runs"


@dataclass(slots=True)
class PreprocessingConfig:
    missing_feature_strategy: str = "median"
    scaler: str = "standard"


@dataclass(slots=True)
class PCAConfig:
    n_components: int = 2


@dataclass(slots=True)
class ClusteringMethodConfig:
    method: str
    n_clusters: int
    random_state: int = 42
    n_init: int = 20


@dataclass(slots=True)
class ClusteringSweepConfig:
    enabled: bool = False
    k_values: tuple[int, ...] = ()
    k_min: int | None = None
    k_max: int | None = None
    k_step: int = 1
    selection_metric: str = "silhouette_score"
    selection_goal: str | None = None
    include_label_metrics: bool = False


@dataclass(slots=True)
class OutputOptions:
    run_name: str | None = None


@dataclass(slots=True)
class ExperimentConfig:
    experiment_name: str
    dataset_name: str
    input_matrix_path: Path
    id_columns: tuple[str, ...]
    label_column: str | None
    feature_columns: tuple[str, ...]
    feature_set: str | None
    excluded_columns: tuple[str, ...]
    preprocessing: PreprocessingConfig
    pca: PCAConfig
    clustering: ClusteringMethodConfig
    output_options: OutputOptions
    sweep: ClusteringSweepConfig = field(default_factory=ClusteringSweepConfig)
    config_path: Path | None = None


@dataclass(slots=True)
class ExperimentRunResult:
    run_dir: Path
    resolved_config_path: Path
    metrics_path: Path
    report_path: Path
    metrics: dict[str, Any]


@dataclass(slots=True)
class ClusterSweepResult:
    sweep_dir: Path
    summary_path: Path
    report_path: Path
    best_run: ExperimentRunResult
    candidate_runs: tuple[ExperimentRunResult, ...]
    summary: dict[str, Any]
