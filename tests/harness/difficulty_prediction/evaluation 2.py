from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import KFold, StratifiedKFold

from .core import CrossValidationConfig, OutputOptions, TargetBundle
from .models import extract_feature_importance, build_estimator
from .core import PreprocessingConfig


@dataclass(slots=True)
class EvaluationOutcome:
    predictions: pd.DataFrame
    fold_metrics: pd.DataFrame
    overall_metrics: dict[str, Any]
    confusion_matrix: pd.DataFrame | None
    feature_importance: pd.DataFrame | None
    effective_folds: int


def run_cross_validated_evaluation(
    *,
    X: pd.DataFrame,
    metadata_frame: pd.DataFrame,
    target: TargetBundle,
    model_family: str,
    model_parameters: dict[str, Any],
    preprocessing: PreprocessingConfig,
    cross_validation: CrossValidationConfig,
    random_state: int,
    id_columns: Iterable[str],
    output_options: OutputOptions,
) -> EvaluationOutcome:
    feature_names = list(X.columns)
    splitter, effective_folds = _build_splitter(target, cross_validation, X.shape[0])
    train_labels = target.model_values
    stratified = target.kind == "classification" and cross_validation.kind.strip().lower() == "stratified_kfold"

    prediction_rows: list[dict[str, Any]] = []
    fold_rows: list[dict[str, Any]] = []
    importance_samples: list[np.ndarray] = []
    fold_importance_source: str | None = None
    all_true_values: list[Any] = []
    all_pred_values: list[Any] = []

    split_y = train_labels if stratified else None
    for fold_index, (train_idx, test_idx) in enumerate(splitter.split(X, split_y), start=1):
        estimator = build_estimator(
            model_family=model_family,
            problem_type=target.kind,
            preprocessing=preprocessing,
            model_parameters=model_parameters,
            random_state=random_state,
        )
        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]
        y_train = train_labels[train_idx]
        y_test = train_labels[test_idx]
        estimator.fit(X_train, y_train)
        y_pred = estimator.predict(X_test)
        all_true_values.extend(y_test.tolist())
        all_pred_values.extend(y_pred.tolist())

        fold_metrics = _compute_metrics(
            y_true=y_test,
            y_pred=y_pred,
            target=target,
        )
        fold_metrics.pop("confusion_matrix_labels", None)
        fold_rows.append(
            {
                "fold_index": fold_index,
                "train_row_count": len(train_idx),
                "test_row_count": len(test_idx),
                **fold_metrics,
            }
        )

        if output_options.save_predictions:
            prediction_rows.extend(
                _build_prediction_rows(
                    X=X,
                    metadata_frame=metadata_frame,
                    test_idx=test_idx,
                    y_true_raw=target.raw_values,
                    y_true_model=target.model_values,
                    y_pred=y_pred,
                    target=target,
                    id_columns=id_columns,
                    fold_index=fold_index,
                )
            )

        importance = extract_feature_importance(estimator, feature_names)
        if importance is not None:
            fold_importance_source = importance.source
            importance_samples.append(np.asarray(importance.values, dtype=float))

    predictions = pd.DataFrame(prediction_rows)
    if not predictions.empty:
        predictions = predictions.sort_values(["row_index", "fold_index"]).reset_index(drop=True)

    fold_metrics = pd.DataFrame(fold_rows)
    overall_metrics = _compute_metrics(
        y_true=np.asarray(all_true_values, dtype=object if target.kind == "classification" else float),
        y_pred=np.asarray(all_pred_values, dtype=object if target.kind == "classification" else float),
        target=target,
    )
    overall_metrics.update(
        {
            "row_count": int(X.shape[0]),
            "feature_count": int(X.shape[1]),
            "effective_cv_folds": int(effective_folds),
            "target_kind": target.kind,
        }
    )

    confusion = (
        _build_confusion_matrix(target, list(all_true_values), list(all_pred_values))
        if target.kind == "classification" and output_options.save_confusion_matrix
        else None
    )
    importance_df = _summarize_importance(feature_names, importance_samples, fold_importance_source) if importance_samples and output_options.save_feature_importance else None
    return EvaluationOutcome(
        predictions=predictions,
        fold_metrics=fold_metrics,
        overall_metrics=overall_metrics,
        confusion_matrix=confusion,
        feature_importance=importance_df,
        effective_folds=effective_folds,
    )


def _build_splitter(
    target: TargetBundle,
    cross_validation: CrossValidationConfig,
    row_count: int,
) -> tuple[Any, int]:
    requested_folds = max(int(cross_validation.folds), 2)
    kind = cross_validation.kind.strip().lower()
    if target.kind == "classification":
        if kind == "stratified_kfold":
            class_counts = pd.Series(target.model_values).value_counts()
            if class_counts.empty:
                raise ValueError("Classification target has no classes after transformation.")
            effective = min(requested_folds, int(class_counts.min()), row_count)
            if effective < 2:
                raise ValueError(
                    "Classification cross-validation needs at least two rows per class. "
                    f"Observed minimum class count: {int(class_counts.min())}."
                )
            splitter = StratifiedKFold(
                n_splits=effective,
                shuffle=bool(cross_validation.shuffle),
                random_state=int(cross_validation.random_state),
            )
            return splitter, effective
        if kind == "kfold":
            effective = min(requested_folds, row_count)
            if effective < 2:
                raise ValueError("Classification cross-validation requires at least two rows.")
            splitter = KFold(
                n_splits=effective,
                shuffle=bool(cross_validation.shuffle),
                random_state=int(cross_validation.random_state) if cross_validation.shuffle else None,
            )
            return splitter, effective
        raise ValueError(
            f"Unsupported cross-validation kind '{cross_validation.kind}' for classification targets."
        )

    if kind != "kfold":
        raise ValueError(f"Unsupported cross-validation kind '{cross_validation.kind}' for regression targets.")
    effective = min(requested_folds, row_count)
    if effective < 2:
        raise ValueError("Regression cross-validation requires at least two rows.")
    splitter = KFold(
        n_splits=effective,
        shuffle=bool(cross_validation.shuffle),
        random_state=int(cross_validation.random_state) if cross_validation.shuffle else None,
    )
    return splitter, effective


def _compute_metrics(*, y_true: np.ndarray, y_pred: np.ndarray, target: TargetBundle) -> dict[str, Any]:
    if target.kind == "classification":
        y_true_values = list(y_true)
        y_pred_values = list(y_pred)
        labels = list(target.class_labels or ())
        ordinal_true = np.asarray([target.ordinal_map[value] for value in y_true_values], dtype=float)
        ordinal_pred = np.asarray([target.ordinal_map[value] for value in y_pred_values], dtype=float)
        return {
            "accuracy": float(accuracy_score(y_true_values, y_pred_values)),
            "balanced_accuracy": float(balanced_accuracy_score(y_true_values, y_pred_values)),
            "macro_f1": float(f1_score(y_true_values, y_pred_values, average="macro", zero_division=0)),
            "off_by_one_accuracy": float(np.mean(np.abs(ordinal_true - ordinal_pred) <= 1.0)),
            "mean_absolute_class_error": float(np.mean(np.abs(ordinal_true - ordinal_pred))),
            "confusion_matrix_labels": labels,
        }

    y_true_float = np.asarray(y_true, dtype=float)
    y_pred_float = np.asarray(y_pred, dtype=float)
    return {
        "mae": float(mean_absolute_error(y_true_float, y_pred_float)),
        "rmse": float(np.sqrt(mean_squared_error(y_true_float, y_pred_float))),
        "r2": float(r2_score(y_true_float, y_pred_float)),
        "pearson": _safe_corr(y_true_float, y_pred_float, method="pearson"),
        "spearman": _safe_corr(y_true_float, y_pred_float, method="spearman"),
    }


def _build_prediction_rows(
    *,
    X: pd.DataFrame,
    metadata_frame: pd.DataFrame,
    test_idx: np.ndarray,
    y_true_raw: np.ndarray,
    y_true_model: np.ndarray,
    y_pred: np.ndarray,
    target: TargetBundle,
    id_columns: Iterable[str],
    fold_index: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    id_column_list = [str(column) for column in id_columns]
    for position, row_index in enumerate(test_idx):
        source_row_index = int(metadata_frame.iloc[row_index]["source_row_index"]) if "source_row_index" in metadata_frame.columns else int(row_index)
        row = {
            "row_index": source_row_index,
            "fold_row_index": int(row_index),
            "fold_index": int(fold_index),
            "target_raw": float(y_true_raw[row_index]),
            "target_model_value": y_true_model[row_index],
            "predicted_model_value": y_pred[position],
            "abs_error": float(_absolute_error(y_true_model[row_index], y_pred[position], target)),
        }
        for column in id_column_list:
            if column in metadata_frame.columns:
                row[column] = metadata_frame.iloc[row_index][column]
        if target.kind == "classification":
            row["target_label"] = y_true_model[row_index]
            row["predicted_label"] = y_pred[position]
            row["target_ordinal"] = int(target.ordinal_map[y_true_model[row_index]])
            row["predicted_ordinal"] = int(target.ordinal_map[y_pred[position]])
            row["signed_error"] = int(target.ordinal_map[y_pred[position]] - target.ordinal_map[y_true_model[row_index]])
        else:
            row["target_label"] = ""
            row["predicted_label"] = ""
            row["target_ordinal"] = ""
            row["predicted_ordinal"] = ""
            row["signed_error"] = float(y_pred[position] - y_true_model[row_index])
        rows.append(row)
    return rows


def _absolute_error(true_value: Any, predicted_value: Any, target: TargetBundle) -> float:
    if target.kind == "classification":
        return float(abs(target.ordinal_map[true_value] - target.ordinal_map[predicted_value]))
    return float(abs(float(predicted_value) - float(true_value)))


def _build_confusion_matrix(target: TargetBundle, y_true: np.ndarray, y_pred: np.ndarray) -> pd.DataFrame | None:
    if target.class_labels is None:
        return None
    matrix = confusion_matrix(list(y_true), list(y_pred), labels=list(target.class_labels))
    labels = [str(label) for label in target.class_labels]
    return pd.DataFrame(matrix, index=labels, columns=labels)


def _summarize_importance(
    feature_names: list[str],
    samples: list[np.ndarray],
    source: str | None,
) -> pd.DataFrame:
    matrix = np.vstack(samples)
    frame = pd.DataFrame(
        {
            "feature": feature_names,
            "importance_mean": matrix.mean(axis=0),
            "importance_std": matrix.std(axis=0, ddof=0),
            "importance_abs_mean": np.abs(matrix).mean(axis=0),
            "importance_source": source or "",
        }
    )
    return frame.sort_values("importance_abs_mean", ascending=False).reset_index(drop=True)


def _safe_corr(left: np.ndarray, right: np.ndarray, *, method: str) -> float:
    if left.size < 2 or right.size < 2:
        return float("nan")
    try:
        if method == "pearson":
            value, _ = pearsonr(left, right)
        else:
            value, _ = spearmanr(left, right)
    except Exception:
        return float("nan")
    return float(value)
