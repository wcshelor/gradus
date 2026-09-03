from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_clustering"
DEFAULT_RUNS_ROOT = DEFAULT_ARTIFACTS_ROOT / "runs"


@dataclass(frozen=True, slots=True)
class PreprocessingConfig:
    missing_feature_strategy: str = "median"
    scaler: str | None = "standard"


@dataclass(frozen=True, slots=True)
class PCAConfig:
    n_components: int = 2


@dataclass(frozen=True, slots=True)
class ClusteringConfig:
    method: str = "ward"
    n_clusters: int = 3
    random_state: int = 42
    n_init: int = 20


@dataclass(frozen=True, slots=True)
class OutputOptions:
    run_name: str | None = None


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    experiment_name: str
    dataset_name: str
    input_matrix_path: Path
    id_columns: tuple[str, ...]
    label_column: str | None = None
    feature_columns: tuple[str, ...] = ()
    feature_set: str | None = None
    excluded_columns: tuple[str, ...] = ()
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    pca: PCAConfig = field(default_factory=PCAConfig)
    clustering: ClusteringConfig = field(default_factory=ClusteringConfig)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    config_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ExperimentRunResult:
    run_dir: Path
    resolved_config_path: Path
    metrics_path: Path
    report_path: Path
    piece_coordinates_path: Path
    cluster_assignments_path: Path
    cluster_profiles_path: Path
    metrics: dict[str, Any]


__all__ = [
    "ClusteringConfig",
    "DEFAULT_ARTIFACTS_ROOT",
    "DEFAULT_RUNS_ROOT",
    "ExperimentConfig",
    "ExperimentRunResult",
    "OutputOptions",
    "PCAConfig",
    "PreprocessingConfig",
    "REPO_ROOT",
]

