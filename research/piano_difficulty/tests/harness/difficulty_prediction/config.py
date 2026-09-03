from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .core import (
    CrossValidationConfig,
    ExperimentConfig,
    OutputOptions,
    PreprocessingConfig,
    REPO_ROOT,
    TargetSchemeConfig,
)

_TOP_LEVEL_KEYS = frozenset(
    {
        "experiment_name",
        "dataset_name",
        "input_matrix_path",
        "id_columns",
        "target_column",
        "target_scheme",
        "feature_set",
        "excluded_columns",
        "preprocessing",
        "model_family",
        "model_parameters",
        "cross_validation",
        "output_options",
    }
)
_TARGET_SCHEME_KEYS = frozenset({"kind", "bins", "bin_edges", "labels"})
_PREPROCESSING_KEYS = frozenset({"imputer_strategy", "scaler"})
_CV_KEYS = frozenset({"kind", "folds", "shuffle", "random_state"})
_OUTPUT_KEYS = frozenset(
    {"run_name", "primary_metric", "save_predictions", "save_confusion_matrix", "save_feature_importance"}
)


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path).expanduser()
    payload = yaml.safe_load(config_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Prediction config must decode to a mapping: {config_path}")

    _require_keys(payload, config_path, "top_level", ["experiment_name", "input_matrix_path", "target_column", "target_scheme", "feature_set"])
    _validate_keys(payload, config_path, "top_level", _TOP_LEVEL_KEYS)

    target_mapping = _require_mapping(payload.get("target_scheme"), config_path, "target_scheme")
    _validate_keys(target_mapping, config_path, "target_scheme", _TARGET_SCHEME_KEYS)

    preprocessing_mapping = _require_mapping(payload.get("preprocessing", {}), config_path, "preprocessing")
    _validate_keys(preprocessing_mapping, config_path, "preprocessing", _PREPROCESSING_KEYS)

    cv_mapping = _require_mapping(payload.get("cross_validation", {}), config_path, "cross_validation")
    _validate_keys(cv_mapping, config_path, "cross_validation", _CV_KEYS)

    output_mapping = _require_mapping(payload.get("output_options", {}), config_path, "output_options")
    _validate_keys(output_mapping, config_path, "output_options", _OUTPUT_KEYS)

    target_scheme = TargetSchemeConfig(
        kind=str(target_mapping["kind"]).strip(),
        bins=_optional_int(target_mapping.get("bins"), config_path, "target_scheme.bins"),
        bin_edges=_optional_float_tuple(target_mapping.get("bin_edges"), config_path, "target_scheme.bin_edges"),
        labels=_optional_tuple(target_mapping.get("labels"), config_path, "target_scheme.labels"),
    )

    preprocessing = PreprocessingConfig(
        imputer_strategy=str(preprocessing_mapping.get("imputer_strategy", "median")).strip(),
        scaler=_optional_str(preprocessing_mapping.get("scaler")),
    )

    cross_validation = CrossValidationConfig(
        kind=str(cv_mapping.get("kind", "kfold")).strip(),
        folds=_optional_int(cv_mapping.get("folds"), config_path, "cross_validation.folds") or 5,
        shuffle=bool(cv_mapping.get("shuffle", True)),
        random_state=_optional_int(cv_mapping.get("random_state"), config_path, "cross_validation.random_state"),
    )

    output_options = OutputOptions(
        run_name=_optional_str(output_mapping.get("run_name")),
        primary_metric=_optional_str(output_mapping.get("primary_metric")),
        save_predictions=bool(output_mapping.get("save_predictions", True)),
        save_confusion_matrix=bool(output_mapping.get("save_confusion_matrix", True)),
        save_feature_importance=bool(output_mapping.get("save_feature_importance", True)),
    )

    resolved_input_path = resolve_config_input_path(
        payload["input_matrix_path"],
        config_dir=config_path.parent,
    )

    return ExperimentConfig(
        experiment_name=str(payload["experiment_name"]).strip(),
        dataset_name=str(payload.get("dataset_name", "oktav")).strip().lower(),
        input_matrix_path=resolved_input_path,
        id_columns=tuple(_string_list(payload.get("id_columns", ["source_row_index", "filename", "dataset_relative_path"]), config_path, "id_columns")),
        target_column=str(payload["target_column"]).strip(),
        target_scheme=target_scheme,
        feature_set=str(payload["feature_set"]).strip(),
        excluded_columns=tuple(_string_list(payload.get("excluded_columns", []), config_path, "excluded_columns")),
        preprocessing=preprocessing,
        model_family=str(payload.get("model_family", "ridge_regression")).strip().lower(),
        model_parameters=dict(payload.get("model_parameters", {})),
        cross_validation=cross_validation,
        output_options=output_options,
        config_path=config_path.resolve(),
    )


def resolve_config_input_path(path: str | Path, config_dir: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if config_dir is not None and str(path).startswith((".", "..")):
        return (config_dir / candidate).resolve()
    return (REPO_ROOT / candidate).resolve()


def _resolve_repo_path(value: Any) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (REPO_ROOT / candidate).resolve()


def _require_mapping(value: Any, config_path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {field!r} in {config_path}.")
    return value


def _validate_keys(mapping: dict[str, Any], config_path: Path, field: str, allowed: set[str]) -> None:
    unknown = sorted(set(mapping) - set(allowed))
    if unknown:
        unknown_text = ", ".join(unknown)
        raise ValueError(f"Unknown key(s) for {field!r} in {config_path}: {unknown_text}")


def _require_keys(mapping: dict[str, Any], config_path: Path, field: str, keys: list[str]) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required key(s) for {field!r} in {config_path}: {missing_text}")


def _string_list(value: Any, config_path: Path, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"Expected a list for {field!r} in {config_path}.")
    return [str(item).strip() for item in value]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def _optional_int(value: Any, config_path: Path, field: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected integer-compatible value for {field!r} in {config_path}.") from exc


def _optional_float_tuple(value: Any, config_path: Path, field: str) -> tuple[float, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"Expected list for {field!r} in {config_path}.")
    try:
        return tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected float-compatible values for {field!r} in {config_path}.") from exc


def _optional_tuple(value: Any, config_path: Path, field: str) -> tuple[Any, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError(f"Expected list for {field!r} in {config_path}.")
    return tuple(value)

