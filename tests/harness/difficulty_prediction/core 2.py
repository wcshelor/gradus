from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tests.harness.shared.matrix_data import LoadedMatrix
from tests.harness.shared.matrix_features import FeatureSelectionReport

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ARTIFACTS_ROOT = REPO_ROOT / "tests" / "artifacts" / "difficulty_prediction"
DEFAULT_RUNS_ROOT = DEFAULT_ARTIFACTS_ROOT / "runs"
DEFAULT_COMPARISONS_ROOT = DEFAULT_ARTIFACTS_ROOT / "comparisons"


@dataclass(slots=True)
class TargetSchemeConfig:
    kind: str
    bins: int | None = None
    bin_edges: tuple[float, ...] | None = None
    labels: tuple[Any, ...] | None = None


@dataclass(slots=True)
class PreprocessingConfig:
    imputer_strategy: str = "median"
    scaler: str = "standard"


@dataclass(slots=True)
class CrossValidationConfig:
    kind: str = "stratified_kfold"
    folds: int = 5
    shuffle: bool = True
    random_state: int = 42


@dataclass(slots=True)
class OutputOptions:
    run_name: str | None = None
    primary_metric: str | None = None
    save_predictions: bool = True
    save_confusion_matrix: bool = True
    save_feature_importance: bool = True


@dataclass(slots=True)
class ExperimentConfig:
    experiment_name: str
    dataset_name: str
    input_matrix_path: Path
    id_columns: tuple[str, ...]
    target_column: str
    target_scheme: TargetSchemeConfig
    feature_set: str
    excluded_columns: tuple[str, ...]
    preprocessing: PreprocessingConfig
    model_family: str
    model_parameters: dict[str, Any]
    cross_validation: CrossValidationConfig
    output_options: OutputOptions
    config_path: Path | None = None


@dataclass(slots=True)
class TargetBundle:
    kind: str
    raw_values: np.ndarray
    model_values: np.ndarray
    class_labels: tuple[Any, ...] | None = None
    ordinal_map: dict[Any, int] | None = None
    bin_edges: tuple[float, ...] | None = None


@dataclass(slots=True)
class ExperimentRunResult:
    run_dir: Path
    resolved_config_path: Path
    metrics_path: Path
    fold_metrics_path: Path
    predictions_path: Path | None
    confusion_matrix_path: Path | None
    feature_importance_path: Path | None
    missingness_report_path: Path
    feature_selection_report_path: Path
    metrics: dict[str, Any]
    fold_metrics: pd.DataFrame
    predictions: pd.DataFrame
    feature_selection_report: FeatureSelectionReport
