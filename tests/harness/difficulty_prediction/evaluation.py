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

from .core import CrossValidationConfig, OutputOptions, PreprocessingConfig, TargetBundle
from .models import build_estimator, extract_feature_importance


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    overall_metrics: dict[str, float]
    fold_metrics: pd.DataFrame
    predictions: pd.DataFrame
    confusion_matrix: pd.DataFrame | None
    feature_importance: pd.DataFrame | None
    effective_folds: int


def run_cross_validated_evaluation(
    feature_frame: pd.DataFrame,
    id_frame: pd.DataFrame,
    target_bundle: TargetBundle,
    model_family: str,
    model_parameters: dict[str, Any],
    preprocessing: PreprocessingConfig,
    cross_validation: CrossValidationConfig,
    output_options: OutputOptions,
) -> EvaluationOutcome:
    splitter = _build_splitter(cross_validation, target_bundle)
    feature_names = list(feature_frame.columns)

    fold_metric_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    feature_importance_by_fold: list[np.ndarray] = []
    importance_source: str | None = None

    all_true: list[Any] = []
    all_pred: list[Any] = []
    for fold_index, (train_index, test_index) in enumerate(
        splitter.split(feature_frame, target_bundle.model_values),
        start=1,
    ):
        estimator = build_estimator(model_family, model_parameters, preprocessing)
        train_features = feature_frame.iloc[train_index]
        test_features = feature_frame.iloc[test_index]
        train_target = target_bundle.model_values.iloc[train_index]
        test_target = target_bundle.model_values.iloc[test_index]

        estimator.fit(train_features, train_target)
        predictions = estimator.predict(test_features)

        all_true.extend(test_target.tolist())
        all_pred.extend(predictions.tolist())

        fold_metrics = _compute_metrics(
            kind=target_bundle.kind,
            y_true=test_target,
            y_pred=predictions,
            class_labels=target_bundle.class_labels,
            ordinal_map=target_bundle.ordinal_map,
        )
        fold_metrics.update(
            {
                "fold": fold_index,
                "train_size": len(train_index),
                "test_size": len(test_index),
            }
        )
        fold_metric_rows.append(fold_metrics)

        if output_options.save_predictions:
            prediction_rows.extend(
                _build_prediction_rows(
                    id_frame=id_frame.iloc[test_index],
                    fold=fold_index,
                    raw_values=target_bundle.raw_values.iloc[test_index],
                    actual_model_values=test_target,
                    predicted_values=predictions,
                    kind=target_bundle.kind,
                    ordinal_map=target_bundle.ordinal_map,
                )
            )

        fold_importance = extract_feature_importance(estimator, feature_names)
        if fold_importance:
            importance_source = fold_importance[0].source
            feature_importance_by_fold.append(
                np.asarray([record.importance for record in fold_importance], dtype=float)
            )

    overall_metrics = _compute_metrics(
        kind=target_bundle.kind,
        y_true=pd.Series(all_true),
        y_pred=np.asarray(all_pred),
        class_labels=target_bundle.class_labels,
        ordinal_map=target_bundle.ordinal_map,
    )

    predictions_frame = pd.DataFrame(prediction_rows)
    if not predictions_frame.empty:
        predictions_frame = predictions_frame.sort_values(["fold", "source_index"]).reset_index(drop=True)

    confusion_matrix_frame = None
    if output_options.save_confusion_matrix and target_bundle.kind != "continuous":
        confusion_matrix_frame = _build_confusion_matrix(
            y_true=pd.Series(all_true),
            y_pred=np.asarray(all_pred),
            class_labels=target_bundle.class_labels,
        )

    feature_importance_frame = None
    if output_options.save_feature_importance and feature_importance_by_fold:
        feature_importance_frame = _summarize_importance(
            feature_names=feature_names,
            importance_arrays=feature_importance_by_fold,
            source=importance_source or "unknown",
        )

    return EvaluationOutcome(
        overall_metrics=overall_metrics,
        fold_metrics=pd.DataFrame(fold_metric_rows),
        predictions=predictions_frame,
        confusion_matrix=confusion_matrix_frame,
        feature_importance=feature_importance_frame,
        effective_folds=len(fold_metric_rows),
    )


def _build_splitter(cross_validation: CrossValidationConfig, target_bundle: TargetBundle) -> KFold | StratifiedKFold:
    requested_folds = max(2, int(cross_validation.folds))
    kind = cross_validation.kind.strip().lower()
    if target_bundle.kind != "continuous" and kind in {"stratified", "stratified_kfold", "stratifiedkfold"}:
        class_counts = pd.Series(target_bundle.model_values).value_counts()
        if class_counts.empty:
            raise ValueError("Cannot build stratified CV splitter without classification labels.")
        effective_folds = min(requested_folds, int(class_counts.min()))
        if effective_folds < 2:
            raise ValueError("Need at least two examples in every class for stratified CV.")
        return StratifiedKFold(
            n_splits=effective_folds,
            shuffle=bool(cross_validation.shuffle),
            random_state=cross_validation.random_state,
        )

    return KFold(
        n_splits=requested_folds,
        shuffle=bool(cross_validation.shuffle),
        random_state=cross_validation.random_state,
    )


def _compute_metrics(
    kind: str,
    y_true: Iterable[Any],
    y_pred: Iterable[Any],
    class_labels: tuple[Any, ...],
    ordinal_map: dict[Any, int],
) -> dict[str, float]:
    true_array = np.asarray(list(y_true))
    pred_array = np.asarray(list(y_pred))

    if kind != "continuous":
        true_ord = np.asarray([ordinal_map[label] for label in true_array], dtype=float)
        pred_ord = np.asarray([ordinal_map[label] for label in pred_array], dtype=float)
        abs_class_error = np.abs(true_ord - pred_ord)
        return {
            "accuracy": float(accuracy_score(true_array, pred_array)),
            "balanced_accuracy": float(balanced_accuracy_score(true_array, pred_array)),
            "macro_f1": float(f1_score(true_array, pred_array, labels=list(class_labels), average="macro")),
            "off_by_one_accuracy": float(np.mean(abs_class_error <= 1.0)),
            "mean_absolute_class_error": float(np.mean(abs_class_error)),
        }

    true_numeric = np.asarray(true_array, dtype=float)
    pred_numeric = np.asarray(pred_array, dtype=float)
    return {
        "mae": float(mean_absolute_error(true_numeric, pred_numeric)),
        "rmse": float(np.sqrt(mean_squared_error(true_numeric, pred_numeric))),
        "r2": float(r2_score(true_numeric, pred_numeric)),
        "pearson": _safe_corr(true_numeric, pred_numeric, "pearson"),
        "spearman": _safe_corr(true_numeric, pred_numeric, "spearman"),
    }


def _build_prediction_rows(
    id_frame: pd.DataFrame,
    fold: int,
    raw_values: pd.Series,
    actual_model_values: pd.Series,
    predicted_values: Iterable[Any],
    kind: str,
    ordinal_map: dict[Any, int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset, predicted_value in enumerate(predicted_values):
        row_payload = {str(column): id_frame.iloc[offset][column] for column in id_frame.columns}
        actual_model_value = actual_model_values.iloc[offset]
        row_payload.update(
            {
                "fold": fold,
                "source_index": int(id_frame.index[offset]),
                "actual_raw_value": float(raw_values.iloc[offset]),
                "actual_model_value": actual_model_value,
                "predicted_model_value": predicted_value,
                "absolute_error": _absolute_error(kind, actual_model_value, predicted_value, ordinal_map),
            }
        )
        rows.append(row_payload)
    return rows


def _absolute_error(
    kind: str,
    actual_value: Any,
    predicted_value: Any,
    ordinal_map: dict[Any, int],
) -> float:
    if kind == "continuous":
        return float(abs(float(actual_value) - float(predicted_value)))
    return float(abs(ordinal_map[actual_value] - ordinal_map[predicted_value]))


def _build_confusion_matrix(
    y_true: pd.Series,
    y_pred: np.ndarray,
    class_labels: tuple[Any, ...],
) -> pd.DataFrame:
    matrix = confusion_matrix(y_true, y_pred, labels=list(class_labels))
    labels = [str(label) for label in class_labels]
    return pd.DataFrame(matrix, index=labels, columns=labels)


def _summarize_importance(
    feature_names: list[str],
    importance_arrays: list[np.ndarray],
    source: str,
) -> pd.DataFrame:
    stacked = np.vstack(importance_arrays)
    frame = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_importance": stacked.mean(axis=0),
            "std_importance": stacked.std(axis=0),
            "mean_abs_importance": np.abs(stacked).mean(axis=0),
            "source": source,
        }
    )
    return frame.sort_values("mean_abs_importance", ascending=False).reset_index(drop=True)


def _safe_corr(left: np.ndarray, right: np.ndarray, method: str) -> float:
    if left.size < 2:
        return float("nan")
    try:
        if method == "pearson":
            return float(pearsonr(left, right).statistic)
        return float(spearmanr(left, right).statistic)
    except Exception:
        return float("nan")
