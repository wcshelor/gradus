from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import load_experiment_config
from .core import (
    DEFAULT_RUNS_ROOT,
    ExperimentConfig,
    ExperimentRunResult,
    FeatureSelectionReport,
    OutputOptions,
)
from .data import load_dataset_matrix
from .evaluation import EvaluationOutcome, run_cross_validated_evaluation
from .features import DEFAULT_METADATA_COLUMNS, select_feature_columns
from .targets import transform_target


def run_experiment_from_config(
    config: str | Path | ExperimentConfig,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult:
    if isinstance(config, ExperimentConfig):
        experiment = config
    else:
        experiment = load_experiment_config(config)
    return run_experiment(experiment, runs_root=runs_root)


def run_experiment(
    config: ExperimentConfig,
    *,
    runs_root: str | Path = DEFAULT_RUNS_ROOT,
) -> ExperimentRunResult:
    loaded = load_dataset_matrix(config.dataset_name, config.input_matrix_path)
    frame = loaded.frame.copy()
    if config.target_column not in frame.columns:
        raise ValueError(
            f"Matrix '{loaded.source_path}' does not contain target column '{config.target_column}'."
        )

    missing_id_columns = [column for column in config.id_columns if column not in frame.columns]
    if missing_id_columns:
        raise ValueError(
            f"Matrix '{loaded.source_path}' is missing configured id columns: {missing_id_columns}"
        )

    frame = frame[frame[config.target_column].notna()].copy()
    if frame.empty:
        raise ValueError(
            f"Matrix '{loaded.source_path}' has no usable rows after filtering missing target values."
        )

    blocked_columns = tuple(
        dict.fromkeys(
            [
                *DEFAULT_METADATA_COLUMNS,
                *config.id_columns,
                config.target_column,
                *config.excluded_columns,
            ]
        )
    )
    selection = select_feature_columns(
        list(frame.columns),
        feature_set=config.feature_set,
        blocked_columns=blocked_columns,
    )
    if not selection.selected_columns:
        raise ValueError(
            "Feature selection produced no usable columns for "
            f"feature_set='{config.feature_set}'. Missing exact columns: {list(selection.missing_exact_columns)}; "
            f"missing prefixes: {list(selection.missing_prefixes)}."
        )

    target = transform_target(frame[config.target_column], config.target_scheme)
    X = frame.loc[:, list(selection.selected_columns)].copy()

    runs_root_path = Path(runs_root).expanduser()
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

    resolved_config = _build_resolved_config(
        config=config,
        loaded=loaded,
        run_dir=run_dir,
        selected_columns=selection.selected_columns,
        effective_rows=len(frame),
        target=target,
    )
    _write_yaml(resolved_config_path, resolved_config)
    _write_json(feature_selection_report_path, selection.to_dict())
    _write_missingness_report(
        path=missingness_report_path,
        raw_frame=loaded.raw_frame,
        analyzed_frame=frame,
        target_column=config.target_column,
        selected_columns=selection.selected_columns,
    )

    outcome = run_cross_validated_evaluation(
        X=X,
        metadata_frame=frame.loc[:, list(config.id_columns) + ["source_row_index"]],
        target=target,
        model_family=config.model_family,
        model_parameters=config.model_parameters,
        preprocessing=config.preprocessing,
        cross_validation=config.cross_validation,
        random_state=config.cross_validation.random_state,
        id_columns=config.id_columns,
        output_options=config.output_options,
    )

    if config.output_options.save_predictions:
        outcome.predictions.to_csv(predictions_path, index=False)
        predictions_written: Path | None = predictions_path
    else:
        predictions_written = None

    outcome.fold_metrics.to_csv(fold_metrics_path, index=False)
    if outcome.confusion_matrix is not None:
        outcome.confusion_matrix.to_csv(confusion_matrix_path)
        confusion_written: Path | None = confusion_matrix_path
    else:
        confusion_written = None
        if confusion_matrix_path.exists():
            confusion_matrix_path.unlink()

    if outcome.feature_importance is not None and config.output_options.save_feature_importance:
        outcome.feature_importance.to_csv(feature_importance_path, index=False)
        feature_importance_written: Path | None = feature_importance_path
    else:
        feature_importance_written = None
        if feature_importance_path.exists():
            feature_importance_path.unlink()

    metrics = _build_metrics_document(
        config=config,
        loaded=loaded,
        resolved_config=resolved_config,
        selection=selection,
        target=target,
        outcome=outcome,
        predictions_path=predictions_written,
        confusion_matrix_path=confusion_written,
        feature_importance_path=feature_importance_written,
    )
    _write_json(metrics_path, metrics)

    return ExperimentRunResult(
        run_dir=run_dir,
        resolved_config_path=resolved_config_path,
        metrics_path=metrics_path,
        fold_metrics_path=fold_metrics_path,
        predictions_path=predictions_written,
        confusion_matrix_path=confusion_written,
        feature_importance_path=feature_importance_written,
        missingness_report_path=missingness_report_path,
        feature_selection_report_path=feature_selection_report_path,
        metrics=metrics,
        fold_metrics=outcome.fold_metrics,
        predictions=outcome.predictions,
        feature_selection_report=selection,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="run_difficulty_prediction",
        description="Run a config-driven difficulty-prediction experiment.",
    )
    parser.add_argument("config", type=Path, help="Path to a YAML experiment config.")
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=DEFAULT_RUNS_ROOT,
        help="Directory that will hold timestamped run subdirectories.",
    )
    args = parser.parse_args(argv)

    result = run_experiment_from_config(args.config, runs_root=args.runs_root)
    print(
        _json_summary(
            {
                "run_dir": str(result.run_dir),
                "metrics_path": str(result.metrics_path),
                "fold_metrics_path": str(result.fold_metrics_path),
                "predictions_path": str(result.predictions_path) if result.predictions_path else None,
                "confusion_matrix_path": str(result.confusion_matrix_path) if result.confusion_matrix_path else None,
                "feature_importance_path": str(result.feature_importance_path) if result.feature_importance_path else None,
                "missingness_report_path": str(result.missingness_report_path),
                "feature_selection_report_path": str(result.feature_selection_report_path),
                "row_count": int(result.metrics.get("row_count", 0)),
                "feature_count": int(result.metrics.get("feature_count", 0)),
                "target_kind": result.metrics.get("target_kind"),
            }
        )
    )
    return 0


def _allocate_run_dir(runs_root: Path, config: ExperimentConfig) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(config.output_options.run_name or config.experiment_name)
    candidate = runs_root / f"{timestamp}__{slug}"
    suffix = 2
    while candidate.exists():
        candidate = runs_root / f"{timestamp}__{slug}__{suffix}"
        suffix += 1
    return candidate


def _build_resolved_config(
    *,
    config: ExperimentConfig,
    loaded: Any,
    run_dir: Path,
    selected_columns: tuple[str, ...],
    effective_rows: int,
    target: Any,
) -> dict[str, Any]:
    return {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "input_matrix_path": str(config.input_matrix_path.resolve()),
        "resolved_input_matrix_path": str(loaded.source_path.resolve()),
        "id_columns": list(config.id_columns),
        "target_column": config.target_column,
        "target_scheme": {
            "kind": config.target_scheme.kind,
            "bins": config.target_scheme.bins,
            "bin_edges": list(config.target_scheme.bin_edges) if config.target_scheme.bin_edges is not None else None,
            "labels": list(config.target_scheme.labels) if config.target_scheme.labels is not None else None,
        },
        "feature_set": config.feature_set,
        "excluded_columns": list(config.excluded_columns),
        "preprocessing": {
            "imputer_strategy": config.preprocessing.imputer_strategy,
            "scaler": config.preprocessing.scaler,
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
        "resolved_run_dir": str(run_dir.resolve()),
        "effective_row_count": int(effective_rows),
        "selected_feature_count": len(selected_columns),
        "selected_feature_columns": list(selected_columns),
        "target_kind": target.kind,
        "class_labels": list(target.class_labels) if target.class_labels is not None else None,
        "bin_edges": list(target.bin_edges) if target.bin_edges is not None else None,
    }


def _build_metrics_document(
    *,
    config: ExperimentConfig,
    loaded: Any,
    resolved_config: dict[str, Any],
    selection: FeatureSelectionReport,
    target: Any,
    outcome: EvaluationOutcome,
    predictions_path: Path | None,
    confusion_matrix_path: Path | None,
    feature_importance_path: Path | None,
) -> dict[str, Any]:
    document = {
        "experiment_name": config.experiment_name,
        "dataset_name": config.dataset_name,
        "feature_set": config.feature_set,
        "target_scheme": {
            "kind": config.target_scheme.kind,
            "bins": config.target_scheme.bins,
            "bin_edges": list(config.target_scheme.bin_edges) if config.target_scheme.bin_edges is not None else None,
        },
        "model_family": config.model_family,
        "problem_type": target.kind,
        "row_count": int(outcome.overall_metrics.get("row_count", 0)),
        "feature_count": int(outcome.overall_metrics.get("feature_count", 0)),
        "effective_cv_folds": int(outcome.effective_folds),
        "selected_feature_count": len(selection.selected_columns),
        "missing_exact_columns": list(selection.missing_exact_columns),
        "missing_prefixes": list(selection.missing_prefixes),
        "overall_metrics": outcome.overall_metrics,
        "paths": {
            "resolved_config": str((Path(resolved_config["resolved_run_dir"]) / "resolved_config.yaml").resolve()),
            "fold_metrics_csv": str((Path(resolved_config["resolved_run_dir"]) / "fold_metrics.csv").resolve()),
            "predictions_csv": str(predictions_path) if predictions_path is not None else None,
            "confusion_matrix_csv": str(confusion_matrix_path) if confusion_matrix_path is not None else None,
            "feature_importance_csv": str(feature_importance_path) if feature_importance_path is not None else None,
            "missingness_report_csv": str((Path(resolved_config["resolved_run_dir"]) / "missingness_report.csv").resolve()),
            "feature_selection_report_json": str((Path(resolved_config["resolved_run_dir"]) / "feature_selection_report.json").resolve()),
        },
        "loaded_matrix": {
            "source_path": str(loaded.source_path.resolve()),
            "status_filter_applied": loaded.status_filter_applied,
            "raw_row_count": int(len(loaded.raw_frame)),
            "analyzed_row_count": int(outcome.overall_metrics.get("row_count", 0)),
        },
        "resolved_config": resolved_config,
    }
    if config.output_options.primary_metric:
        document["primary_metric"] = config.output_options.primary_metric
    else:
        document["primary_metric"] = "balanced_accuracy" if target.kind == "classification" else "rmse"
    return document


def _write_missingness_report(
    *,
    path: Path,
    raw_frame: pd.DataFrame,
    analyzed_frame: pd.DataFrame,
    target_column: str,
    selected_columns: tuple[str, ...],
) -> None:
    rows: list[dict[str, Any]] = []
    total_raw = len(raw_frame)
    total_analyzed = len(analyzed_frame)
    target_missing = int(raw_frame[target_column].isna().sum()) if target_column in raw_frame.columns else 0
    rows.append(
        {
            "column": target_column,
            "role": "target",
            "missing_count": target_missing,
            "missing_ratio": float(target_missing / total_raw) if total_raw else 0.0,
            "non_missing_count": int(total_raw - target_missing),
            "row_count_reference": total_raw,
            "dtype": str(raw_frame[target_column].dtype) if target_column in raw_frame.columns else "",
        }
    )
    for column in selected_columns:
        missing_count = int(analyzed_frame[column].isna().sum())
        rows.append(
            {
                "column": column,
                "role": "feature",
                "missing_count": missing_count,
                "missing_ratio": float(missing_count / total_analyzed) if total_analyzed else 0.0,
                "non_missing_count": int(total_analyzed - missing_count),
                "row_count_reference": total_analyzed,
                "dtype": str(analyzed_frame[column].dtype),
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    import json

    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    import yaml

    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _json_summary(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True)


def _slugify(value: str) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "run"
