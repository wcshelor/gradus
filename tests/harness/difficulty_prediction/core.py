from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from tests.harness.shared.matrix_data import LoadedMatrix
from tests.harness.shared.matrix_features import FeatureSelectionReport

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction"
DEFAULT_RUNS_ROOT = DEFAULT_ARTIFACTS_ROOT / "runs"
DEFAULT_COMPARISONS_ROOT = DEFAULT_ARTIFACTS_ROOT / "comparisons"


@dataclass(frozen=True, slots=True)
class TargetSchemeConfig:
    kind: str
    bins: int | None = None
    bin_edges: tuple[float, ...] | None = None
    labels: tuple[Any, ...] | None = None


@dataclass(frozen=True, slots=True)
class PreprocessingConfig:
    imputer_strategy: str = "median"
    scaler: str | None = "standard"


@dataclass(frozen=True, slots=True)
class CrossValidationConfig:
    kind: str = "kfold"
    folds: int = 5
    shuffle: bool = True
    random_state: int | None = 42


@dataclass(frozen=True, slots=True)
class OutputOptions:
    run_name: str | None = None
    primary_metric: str | None = None
    save_predictions: bool = True
    save_confusion_matrix: bool = True
    save_feature_importance: bool = True


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    experiment_name: str
    dataset_name: str
    input_matrix_path: Path
    id_columns: tuple[str, ...]
    target_column: str
    target_scheme: TargetSchemeConfig
    feature_set: str
    excluded_columns: tuple[str, ...] = ()
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    model_family: str = "ridge_regression"
    model_parameters: dict[str, Any] = field(default_factory=dict)
    cross_validation: CrossValidationConfig = field(default_factory=CrossValidationConfig)
    output_options: OutputOptions = field(default_factory=OutputOptions)
    config_path: Path | None = None


@dataclass(frozen=True, slots=True)
class TargetBundle:
    kind: str
    raw_values: pd.Series
    model_values: pd.Series
    class_labels: tuple[Any, ...] = ()
    ordinal_map: dict[Any, int] = field(default_factory=dict)
    bin_edges: tuple[float, ...] | None = None


@dataclass(frozen=True, slots=True)
class ExperimentRunResult:
    run_dir: Path
    resolved_config_path: Path
    feature_selection_report_path: Path
    missingness_report_path: Path
    metrics_path: Path
    fold_metrics_path: Path
    predictions_path: Path
    confusion_matrix_path: Path
    feature_importance_path: Path
    metrics: dict[str, Any]
    loaded_matrix: LoadedMatrix
    feature_selection_report: FeatureSelectionReport


__all__ = [
    "CrossValidationConfig",
    "DEFAULT_ARTIFACTS_ROOT",
    "DEFAULT_COMPARISONS_ROOT",
    "DEFAULT_RUNS_ROOT",
    "ExperimentConfig",
    "ExperimentRunResult",
    "OutputOptions",
    "PreprocessingConfig",
    "REPO_ROOT",
    "TargetBundle",
    "TargetSchemeConfig",
]

