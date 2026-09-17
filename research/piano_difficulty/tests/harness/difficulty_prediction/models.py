from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge, RidgeClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .core import PreprocessingConfig

LINEAR_MODEL_FAMILIES = frozenset(
    {"logistic_regression", "ridge_classifier", "ridge_regression", "elasticnet"}
)
CLASSIFICATION_MODEL_FAMILIES = frozenset(
    {
        "dummy_classifier",
        "logistic_regression",
        "ridge_classifier",
        "random_forest_classifier",
        "gradient_boosting_classifier",
    }
)
REGRESSION_MODEL_FAMILIES = frozenset(
    {
        "dummy_regression",
        "ridge_regression",
        "elasticnet",
        "random_forest_regression",
        "gradient_boosting_regression",
    }
)


@dataclass(frozen=True, slots=True)
class ImportanceRecord:
    feature: str
    importance: float
    absolute_importance: float
    source: str


def build_estimator(
    model_family: str,
    model_parameters: dict[str, Any],
    preprocessing: PreprocessingConfig,
) -> Pipeline:
    normalized_family = model_family.strip().lower()
    if normalized_family not in CLASSIFICATION_MODEL_FAMILIES | REGRESSION_MODEL_FAMILIES:
        available = ", ".join(sorted(CLASSIFICATION_MODEL_FAMILIES | REGRESSION_MODEL_FAMILIES))
        raise ValueError(f"Unknown model_family {model_family!r}. Available models: {available}.")

    steps: list[tuple[str, Any]] = []
    if preprocessing.imputer_strategy.strip().lower():
        strategy = preprocessing.imputer_strategy.strip().lower()
        if strategy == "zero":
            try:
                steps.append(("imputer", SimpleImputer(strategy="constant", fill_value=0.0, keep_empty_features=True)))
            except TypeError:
                steps.append(("imputer", SimpleImputer(strategy="constant", fill_value=0.0)))
        else:
            try:
                steps.append(("imputer", SimpleImputer(strategy=strategy, keep_empty_features=True)))
            except TypeError:
                steps.append(("imputer", SimpleImputer(strategy=strategy)))

    if preprocessing.scaler and normalized_family in LINEAR_MODEL_FAMILIES:
        steps.append(("scaler", StandardScaler()))

    steps.append(("model", _make_model(normalized_family, model_parameters)))
    return Pipeline(steps)


def extract_feature_importance(
    estimator: Pipeline,
    feature_names: list[str],
) -> list[ImportanceRecord]:
    model = estimator.named_steps.get("model", estimator)
    # Try to map importance back to the feature names that actually entered the model.
    # If the imputer dropped empty columns, the model will have fewer coefficients than names;
    # in that case align by truncating or padding.
    if hasattr(model, "feature_importances_"):
        values = np.asarray(getattr(model, "feature_importances_"), dtype=float)
        aligned_names = feature_names[-len(values) :] if len(values) < len(feature_names) else feature_names
        if len(values) != len(aligned_names):
            aligned_names = feature_names[: len(values)]
        return [
            ImportanceRecord(
                feature=feature_name,
                importance=float(value),
                absolute_importance=float(abs(value)),
                source="feature_importances_",
            )
            for feature_name, value in zip(aligned_names, values.tolist(), strict=False)
        ]

    if hasattr(model, "coef_"):
        values = np.asarray(getattr(model, "coef_"), dtype=float)
        if values.ndim > 1:
            values = np.mean(np.abs(values), axis=0)
        aligned_names = feature_names[-len(values) :] if len(values) < len(feature_names) else feature_names
        if len(values) != len(aligned_names):
            aligned_names = feature_names[: len(values)]
        return [
            ImportanceRecord(
                feature=feature_name,
                importance=float(value),
                absolute_importance=float(abs(value)),
                source="coef_",
            )
            for feature_name, value in zip(aligned_names, values.tolist(), strict=False)
        ]

    return []


def _make_model(model_family: str, model_parameters: dict[str, Any]) -> Any:
    parameters = dict(model_parameters)
    if model_family == "dummy_classifier":
        parameters.setdefault("strategy", "most_frequent")
        return DummyClassifier(**parameters)
    if model_family == "dummy_regression":
        parameters.setdefault("strategy", "mean")
        return DummyRegressor(**parameters)
    if model_family == "logistic_regression":
        parameters.setdefault("max_iter", 2000)
        return LogisticRegression(**parameters)
    if model_family == "ridge_classifier":
        return RidgeClassifier(**parameters)
    if model_family == "ridge_regression":
        return Ridge(**parameters)
    if model_family == "elasticnet":
        parameters.setdefault("max_iter", 5000)
        return ElasticNet(**parameters)
    if model_family == "random_forest_classifier":
        parameters.setdefault("random_state", 42)
        return RandomForestClassifier(**parameters)
    if model_family == "random_forest_regression":
        parameters.setdefault("random_state", 42)
        return RandomForestRegressor(**parameters)
    if model_family == "gradient_boosting_classifier":
        parameters.setdefault("random_state", 42)
        return GradientBoostingClassifier(**parameters)
    if model_family == "gradient_boosting_regression":
        parameters.setdefault("random_state", 42)
        return GradientBoostingRegressor(**parameters)
    raise ValueError(f"Unsupported model_family {model_family!r}.")
