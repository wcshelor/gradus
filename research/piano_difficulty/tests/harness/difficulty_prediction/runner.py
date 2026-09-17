from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .config import load_experiment_config
from .core import DEFAULT_ARTIFACTS_ROOT, DEFAULT_RUNS_ROOT, ExperimentConfig, ExperimentRunResult
from .data import load_dataset_matrix
from .evaluation import EvaluationOutcome, run_cross_validated_evaluation
from .features import DEFAULT_METADATA_COLUMNS, select_feature_columns
from .targets import transform_target


def run_experiment_from_config(
    config: ExperimentConfig | str | Path,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult:
    experiment_config = config if isinstance(config, ExperimentConfig) else load_experiment_config(config)
    return run_experiment(experiment_config, runs_root=runs_root)


def run_experiment(
    config: ExperimentConfig,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult:
    loaded_matrix = load_dataset_matrix(config.dataset_name, config.input_matrix_path)
    frame = loaded_matrix.frame.copy()

    if config.target_column not in frame.columns:
        raise ValueError(
            f"Target column {config.target_column!r} not present in matrix {loaded_matrix.source_path}."
        )

    missing_id_columns = [column for column in config.id_columns if column not in frame.columns]
    if missing_id_columns:
        missing_text = ", ".join(missing_id_columns)
        raise ValueError(f"Missing id column(s) in matrix: {missing_text}")

    target_mask = frame[config.target_column].notna()
    filtered_frame = frame.loc[target_mask].copy()
    if filtered_frame.empty:
        raise ValueError(f"No non-null target rows found for column {config.target_column!r}.")

    excluded_columns = tuple(
        dict.fromkeys(
            [
                *DEFAULT_METADATA_COLUMNS,
                *config.id_columns,
                config.target_column,
                *config.excluded_columns,
            ]
        )
    )
    selection_report = select_feature_columns(
        available_columns=list(filtered_frame.columns),
        feature_set=config.feature_set,
        excluded_columns=excluded_columns,
    )
    if not selection_report.selected_columns:
        raise ValueError(
            f"Feature set {config.feature_set!r} selected no columns for {loaded_matrix.source_path}."
        )

    feature_frame = filtered_frame.loc[:, list(selection_report.selected_columns)].apply(
        pd.to_numeric,
        errors="coerce",
    )
    # Drop columns that are entirely NaN (e.g., sparse runtime duration ratios) before CV;
    # otherwise SimpleImputer with median would drop them and cause feature-importance mismatch.
    all_nan_columns = [col for col in feature_frame.columns if feature_frame[col].isna().all()]
    if all_nan_columns:
        feature_frame = feature_frame.drop(columns=all_nan_columns)
        if feature_frame.empty:
            raise ValueError(
                f"Feature set {config.feature_set!r} has no usable columns after dropping all-NaN features: {all_nan_columns}"
            )

    # Optional hygiene filters (conservative defaults = no-op unless explicitly enabled).
    feature_frame = _apply_feature_hygiene(feature_frame, config.preprocessing, config.feature_set)
    id_frame = filtered_frame.loc[:, list(config.id_columns)].copy()
    target_bundle = transform_target(filtered_frame[config.target_column], config.target_scheme)

    runs_root_path = _resolve_runs_root(config, Path(runs_root).expanduser())
    runs_root_path.mkdir(parents=True, exist_ok=True)
    run_dir = _allocate_run_dir(runs_root_path, config)
    run_dir.mkdir(parents=True, exist_ok=False)

    resolved_config_path = run_dir / "resolved_config.yaml"
    feature_selection_report_path = run_dir / "feature_selection_report.json"
    missingness_report_path = run_dir / "missingness_report.csv"
    metrics_path = run_dir / "metrics.json"
    fold_metrics_path = run_dir / "fold_metrics.csv"
    predictions_path = run_dir / "predictions.csv"
    confusion_matrix_path = run_dir / "confusion_matrix.csv"
    feature_importance_path = run_dir / "feature_importance.csv"

    _write_yaml(resolved_config_path, _build_resolved_config(config, loaded_matrix, selection_report, target_bundle))
    _write_json(feature_selection_report_path, selection_report.to_dict())
    _write_missingness_report(feature_frame, missingness_report_path)

    evaluation_outcome = run_cross_validated_evaluation(
        feature_frame=feature_frame,
        id_frame=id_frame,
        target_bundle=target_bundle,
        model_family=config.model_family,
        model_parameters=config.model_parameters,
        preprocessing=config.preprocessing,
        cross_validation=config.cross_validation,
        output_options=config.output_options,
    )

    evaluation_outcome.fold_metrics.to_csv(fold_metrics_path, index=False)
    if config.output_options.save_predictions:
        evaluation_outcome.predictions.to_csv(predictions_path, index=False)
    if evaluation_outcome.confusion_matrix is not None:
        evaluation_outcome.confusion_matrix.to_csv(confusion_matrix_path)
    if evaluation_outcome.feature_importance is not None:
        evaluation_outcome.feature_importance.to_csv(feature_importance_path, index=False)

    metrics_document = _build_metrics_document(
        config=config,
        loaded_matrix=loaded_matrix,
        selection_report=selection_report,
        evaluation_outcome=evaluation_outcome,
        filtered_row_count=len(filtered_frame),
    )
    _write_json(metrics_path, metrics_document)

    return ExperimentRunResult(
        run_dir=run_dir,
        resolved_config_path=resolved_config_path,
        feature_selection_report_path=feature_selection_report_path,
        missingness_report_path=missingness_report_path,
        metrics_path=metrics_path,
        fold_metrics_path=fold_metrics_path,
        predictions_path=predictions_path,
        confusion_matrix_path=confusion_matrix_path,
        feature_importance_path=feature_importance_path,
        metrics=metrics_document,
        loaded_matrix=loaded_matrix,
        feature_selection_report=selection_report,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a config-driven difficulty prediction experiment.")
    parser.add_argument("config", type=Path, help="Path to a YAML experiment config.")
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    args = parser.parse_args(argv)

    result = run_experiment_from_config(args.config, runs_root=args.runs_root)
    print(
        _json_summary(
            {
                "run_dir": str(result.run_dir),
                "metrics_path": str(result.metrics_path),
                "fold_metrics_path": str(result.fold_metrics_path),
                "predictions_path": str(result.predictions_path),
                "confusion_matrix_path": str(result.confusion_matrix_path),
                "feature_importance_path": str(result.feature_importance_path),
                "missingness_report_path": str(result.missingness_report_path),
                "feature_selection_report_path": str(result.feature_selection_report_path),
                "metrics": result.metrics.get("overall_metrics", {}),
            }
        )
    )
    return 0


def _allocate_run_dir(runs_root: Path, config: ExperimentConfig) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_label = _slugify(config.output_options.run_name or config.experiment_name)
    candidate = runs_root / f"{timestamp}__{run_label}"
    if candidate.exists():
        suffix = 2
        while True:
            numbered_candidate = runs_root / f"{timestamp}__{run_label}-{suffix}"
            if not numbered_candidate.exists():
                return numbered_candidate
            suffix += 1
    return candidate


def _resolve_runs_root(config: ExperimentConfig, runs_root: Path) -> Path:
    if runs_root == DEFAULT_RUNS_ROOT:
        if (
            config.dataset_name == "oktav"
            and config.target_scheme.kind.strip().lower() == "custom_bins"
            and config.target_scheme.labels
            and len(config.target_scheme.labels) == 9
        ):
            return DEFAULT_ARTIFACTS_ROOT / "oktav_henle_9bin"
        return DEFAULT_ARTIFACTS_ROOT / config.dataset_name
    return runs_root


def _build_resolved_config(
    config: ExperimentConfig,
    loaded_matrix: Any,
    selection_report: Any,
    target_bundle: Any,
) -> dict[str, Any]:
    return {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "input_matrix_path": str(config.input_matrix_path.resolve()),
        "source_path": str(loaded_matrix.source_path),
        "id_columns": list(config.id_columns),
        "target_column": config.target_column,
        "target_scheme": {
            "kind": config.target_scheme.kind,
            "bins": config.target_scheme.bins,
            "bin_edges": list(config.target_scheme.bin_edges or ()),
            "labels": list(config.target_scheme.labels or ()),
        },
        "feature_set": config.feature_set,
        "selected_columns": list(selection_report.selected_columns),
        "excluded_columns": list(config.excluded_columns),
        "preprocessing": {
            "imputer_strategy": config.preprocessing.imputer_strategy,
            "scaler": config.preprocessing.scaler,
            "drop_near_zero_variance": config.preprocessing.drop_near_zero_variance,
            "near_zero_variance_threshold": config.preprocessing.near_zero_variance_threshold,
            "max_missing_fraction": config.preprocessing.max_missing_fraction,
            "drop_sparse_duration_ratio": config.preprocessing.drop_sparse_duration_ratio,
            "sparse_duration_ratio_prefix": config.preprocessing.sparse_duration_ratio_prefix,
            "winsorize": config.preprocessing.winsorize,
            "winsorize_lower_quantile": config.preprocessing.winsorize_lower_quantile,
            "winsorize_upper_quantile": config.preprocessing.winsorize_upper_quantile,
        },
        "model_family": config.model_family,
        "model_parameters": config.model_parameters,
        "cross_validation": {
            "kind": config.cross_validation.kind,
            "folds": config.cross_validation.folds,
            "shuffle": config.cross_validation.shuffle,
            "random_state": config.cross_validation.random_state,
        },
        "output_options": {
            "run_name": config.output_options.run_name,
            "primary_metric": config.output_options.primary_metric,
            "save_predictions": config.output_options.save_predictions,
            "save_confusion_matrix": config.output_options.save_confusion_matrix,
            "save_feature_importance": config.output_options.save_feature_importance,
        },
        "class_labels": list(target_bundle.class_labels),
        "effective_bin_edges": list(target_bundle.bin_edges or ()),
    }


def _build_metrics_document(
    config: ExperimentConfig,
    loaded_matrix: Any,
    selection_report: Any,
    evaluation_outcome: EvaluationOutcome,
    filtered_row_count: int,
) -> dict[str, Any]:
    return {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "source_path": str(loaded_matrix.source_path),
        "status_filter_applied": bool(loaded_matrix.status_filter_applied),
        "raw_row_count": int(len(loaded_matrix.raw_frame)),
        "analyzed_row_count": int(filtered_row_count),
        "feature_set": config.feature_set,
        "feature_selection": {
            "selected_columns": list(selection_report.selected_columns),
            "missing_exact_columns": list(selection_report.missing_exact_columns),
            "missing_prefixes": list(selection_report.missing_prefixes),
        },
        "target_column": config.target_column,
        "target_scheme": {
            "kind": config.target_scheme.kind,
            "bins": config.target_scheme.bins,
            "bin_edges": list(config.target_scheme.bin_edges or ()),
            "labels": list(config.target_scheme.labels or ()),
        },
        "model_family": config.model_family,
        "model_parameters": config.model_parameters,
        "primary_metric": config.output_options.primary_metric,
        "effective_folds": int(evaluation_outcome.effective_folds),
        "overall_metrics": evaluation_outcome.overall_metrics,
    }


def _write_missingness_report(feature_frame: pd.DataFrame, output_path: Path) -> None:
    rows = []
    row_count = max(len(feature_frame), 1)
    for column in feature_frame.columns:
        missing_count = int(feature_frame[column].isna().sum())
        rows.append(
            {
                "feature": str(column),
                "dtype": str(feature_frame[column].dtype),
                "missing_count": missing_count,
                "missing_fraction": float(missing_count / row_count),
            }
        )
    pd.DataFrame(rows).to_csv(output_path, index=False)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False))


def _json_summary(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _apply_feature_hygiene(
    feature_frame: pd.DataFrame,
    preprocessing: Any,
    feature_set: str,
) -> pd.DataFrame:
    result = feature_frame.copy()
    # Drop sparse high-cardinality duration-ratio columns by prefix.
    if preprocessing.drop_sparse_duration_ratio:
        prefix = str(preprocessing.sparse_duration_ratio_prefix or "rhythm_duration_value_ratio_")
        sparse_cols = [col for col in result.columns if str(col).startswith(prefix)]
        if sparse_cols:
            result = result.drop(columns=sparse_cols)
            if result.empty:
                raise ValueError(
                    f"Feature set {feature_set!r} has no usable columns after dropping sparse prefix {prefix!r}: {sparse_cols}"
                )

    # Drop columns with missing fraction above threshold.
    if preprocessing.max_missing_fraction is not None:
        threshold = float(preprocessing.max_missing_fraction)
        row_count = max(len(result), 1)
        high_missing = [
            col for col in result.columns if float(result[col].isna().sum() / row_count) > threshold
        ]
        if high_missing:
            result = result.drop(columns=high_missing)
            if result.empty:
                raise ValueError(
                    f"Feature set {feature_set!r} has no usable columns after dropping high-missing columns (threshold {threshold}): {high_missing}"
                )

    # Drop near-zero variance columns.
    if preprocessing.drop_near_zero_variance:
        threshold = float(preprocessing.near_zero_variance_threshold)
        nzv_cols: list[str] = []
        for col in result.columns:
            series = result[col].dropna()
            if series.empty:
                continue
            var = float(series.var(ddof=0))
            if var <= threshold:
                nzv_cols.append(col)
        if nzv_cols:
            result = result.drop(columns=nzv_cols)
            if result.empty:
                raise ValueError(
                    f"Feature set {feature_set!r} has no usable columns after dropping near-zero variance columns (threshold {threshold}): {nzv_cols}"
                )

    # Optionally cap/winsorize extreme numeric features inside preprocessing.
    if preprocessing.winsorize and not result.empty:
        lower_q = float(preprocessing.winsorize_lower_quantile)
        upper_q = float(preprocessing.winsorize_upper_quantile)
        for col in result.columns:
            series = result[col]
            if series.notna().sum() < 2:
                continue
            lower = float(series.quantile(lower_q))
            upper = float(series.quantile(upper_q))
            if lower == upper:
                continue
            result[col] = series.clip(lower=lower, upper=upper)

    return result


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    return normalized.strip("-")
