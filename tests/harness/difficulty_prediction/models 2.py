from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge, RidgeClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .core import PreprocessingConfig

LINEAR_MODEL_FAMILIES = {
    "logistic_regression",
    "ridge_classifier",
    "ridge_regression",
    "elastic_net",
}

CLASSIFICATION_MODEL_FAMILIES = {
    "dummy_classifier",
    "logistic_regression",
    "ridge_classifier",
    "random_forest_classifier",
    "gradient_boosting_classifier",
}

REGRESSION_MODEL_FAMILIES = {
    "dummy_regressor",
    "ridge_regression",
    "elastic_net",
    "random_forest_regressor",
    "gradient_boosting_regressor",
}


@dataclass(slots=True)
class ImportanceRecord:
    feature: str
    values: list[float]
    source: str


def build_estimator(
    *,
    model_family: str,
    problem_type: str,
    preprocessing: PreprocessingConfig,
    model_parameters: dict[str, Any],
    random_state: int,
) -> Pipeline:
    family = model_family.strip().lower()
    problem = problem_type.strip().lower()
    if problem == "classification" and family not in CLASSIFICATION_MODEL_FAMILIES:
        raise ValueError(
            f"Unsupported classification model family '{model_family}'. Supported families: {sorted(CLASSIFICATION_MODEL_FAMILIES)}"
        )
    if problem == "regression" and family not in REGRESSION_MODEL_FAMILIES:
        raise ValueError(
            f"Unsupported regression model family '{model_family}'. Supported families: {sorted(REGRESSION_MODEL_FAMILIES)}"
        )

    steps: list[tuple[str, Any]] = []
    strategy = preprocessing.imputer_strategy.strip().lower()
    if strategy and strategy != "none":
        imputer_kwargs: dict[str, Any] = {"strategy": strategy}
        if strategy == "constant" and "fill_value" in model_parameters:
            imputer_kwargs["fill_value"] = model_parameters["fill_value"]
        steps.append(("impute", SimpleImputer(**imputer_kwargs)))

    if preprocessing.scaler.strip().lower() == "standard" and family in LINEAR_MODEL_FAMILIES:
        steps.append(("scale", StandardScaler()))

    steps.append(
        (
            "model",
            _make_model(
                family=family,
                problem_type=problem,
                model_parameters=dict(model_parameters),
                random_state=random_state,
            ),
        )
    )
    return Pipeline(steps)


def extract_feature_importance(estimator: Pipeline, feature_names: list[str]) -> ImportanceRecord | None:
    model = estimator.named_steps.get("model")
    if model is None:
        return None

    if hasattr(model, "feature_importances_"):
        values = np.asarray(getattr(model, "feature_importances_"), dtype=float)
        return ImportanceRecord(feature="feature_importances_", values=values.tolist(), source="feature_importances")

    if hasattr(model, "coef_"):
        coef = np.asarray(getattr(model, "coef_"), dtype=float)
        if coef.ndim == 1:
            values = coef
        else:
            values = np.mean(np.abs(coef), axis=0)
        return ImportanceRecord(feature="coef_", values=values.tolist(), source="coef")

    return None


def _make_model(
    *,
    family: str,
    problem_type: str,
    model_parameters: dict[str, Any],
    random_state: int,
) -> Any:
    params = dict(model_parameters)

    if family == "dummy_classifier":
        params.setdefault("strategy", "most_frequent")
        return DummyClassifier(**params)
    if family == "dummy_regressor":
        params.setdefault("strategy", "mean")
        return DummyRegressor(**params)

    if family == "logistic_regression":
        params.setdefault("max_iter", 2000)
        params.setdefault("solver", "lbfgs")
        params.setdefault("random_state", random_state)
        return LogisticRegression(**params)

    if family == "ridge_classifier":
        return RidgeClassifier(**params)

    if family == "ridge_regression":
        return Ridge(**params)

    if family == "elastic_net":
        params.setdefault("max_iter", 4000)
        params.setdefault("random_state", random_state)
        return ElasticNet(**params)

    if family == "random_forest_classifier":
        params.setdefault("n_estimators", 200)
        params.setdefault("random_state", random_state)
        params.setdefault("n_jobs", -1)
        return RandomForestClassifier(**params)

    if family == "random_forest_regressor":
        params.setdefault("n_estimators", 200)
        params.setdefault("random_state", random_state)
        params.setdefault("n_jobs", -1)
        return RandomForestRegressor(**params)

    if family == "gradient_boosting_classifier":
        params.setdefault("random_state", random_state)
        return GradientBoostingClassifier(**params)

    if family == "gradient_boosting_regressor":
        params.setdefault("random_state", random_state)
        return GradientBoostingRegressor(**params)

    raise ValueError(f"Unsupported model family '{family}' for problem type '{problem_type}'.")
