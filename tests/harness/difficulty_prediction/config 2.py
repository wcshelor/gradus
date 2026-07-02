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

_TOP_LEVEL_KEYS = {
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

_TARGET_SCHEME_KEYS = {"kind", "bins", "bin_edges", "labels"}
_PREPROCESSING_KEYS = {"imputer_strategy", "scaler"}
_CV_KEYS = {"kind", "folds", "shuffle", "random_state"}
_OUTPUT_KEYS = {
    "run_name",
    "primary_metric",
    "save_predictions",
    "save_confusion_matrix",
    "save_feature_importance",
}


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path).expanduser()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Config '{config_path}' must contain a YAML mapping.")

    unknown = sorted(set(raw) - _TOP_LEVEL_KEYS)
    if unknown:
        raise ValueError(f"Config '{config_path}' contains unsupported top-level keys: {unknown}")

    _require_keys(raw, config_path, "top-level", [
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
    ])

    target_scheme_raw = _require_mapping(raw["target_scheme"], config_path, "target_scheme")
    preprocessing_raw = _require_mapping(raw["preprocessing"], config_path, "preprocessing")
    cv_raw = _require_mapping(raw["cross_validation"], config_path, "cross_validation")
    output_raw = _require_mapping(raw["output_options"], config_path, "output_options")

    _validate_keys(target_scheme_raw, config_path, "target_scheme", _TARGET_SCHEME_KEYS)
    _validate_keys(preprocessing_raw, config_path, "preprocessing", _PREPROCESSING_KEYS)
    _validate_keys(cv_raw, config_path, "cross_validation", _CV_KEYS)
    _validate_keys(output_raw, config_path, "output_options", _OUTPUT_KEYS)

    input_matrix_path = _resolve_repo_path(raw["input_matrix_path"])
    id_columns = tuple(_string_list(raw["id_columns"], config_path, "id_columns"))
    excluded_columns = tuple(_string_list(raw["excluded_columns"], config_path, "excluded_columns"))
    model_parameters_raw = raw["model_parameters"]
    if not isinstance(model_parameters_raw, dict):
        raise ValueError(f"Config '{config_path}' field 'model_parameters' must be a mapping.")

    target_scheme = TargetSchemeConfig(
        kind=str(target_scheme_raw["kind"]).strip(),
        bins=_optional_int(target_scheme_raw.get("bins"), config_path, "target_scheme.bins"),
        bin_edges=_optional_float_tuple(target_scheme_raw.get("bin_edges"), config_path, "target_scheme.bin_edges"),
        labels=_optional_tuple(target_scheme_raw.get("labels"), config_path, "target_scheme.labels"),
    )
    preprocessing = PreprocessingConfig(
        imputer_strategy=str(preprocessing_raw.get("imputer_strategy", "median")).strip(),
        scaler=str(preprocessing_raw.get("scaler", "standard")).strip(),
    )
    cross_validation = CrossValidationConfig(
        kind=str(cv_raw.get("kind", "stratified_kfold")).strip(),
        folds=_optional_int(cv_raw.get("folds", 5), config_path, "cross_validation.folds") or 5,
        shuffle=bool(cv_raw.get("shuffle", True)),
        random_state=_optional_int(cv_raw.get("random_state", 42), config_path, "cross_validation.random_state") or 42,
    )
    output_options = OutputOptions(
        run_name=_optional_str(output_raw.get("run_name")),
        primary_metric=_optional_str(output_raw.get("primary_metric")),
        save_predictions=bool(output_raw.get("save_predictions", True)),
        save_confusion_matrix=bool(output_raw.get("save_confusion_matrix", True)),
        save_feature_importance=bool(output_raw.get("save_feature_importance", True)),
    )

    return ExperimentConfig(
        experiment_name=str(raw["experiment_name"]).strip(),
        dataset_name=str(raw["dataset_name"]).strip().lower(),
        input_matrix_path=input_matrix_path,
        id_columns=id_columns,
        target_column=str(raw["target_column"]).strip(),
        target_scheme=target_scheme,
        feature_set=str(raw["feature_set"]).strip(),
        excluded_columns=excluded_columns,
        preprocessing=preprocessing,
        model_family=str(raw["model_family"]).strip(),
        model_parameters=dict(model_parameters_raw),
        cross_validation=cross_validation,
        output_options=output_options,
        config_path=config_path,
    )


def resolve_config_input_path(path: str | Path, *, config_dir: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    if config_dir is not None:
        relative = (config_dir / candidate).resolve()
        if relative.exists():
            return relative
    return (REPO_ROOT / candidate).resolve()


def _resolve_repo_path(value: Any) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _require_mapping(value: Any, config_path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Config '{config_path}' field '{field}' must be a mapping.")
    return value


def _validate_keys(mapping: dict[str, Any], config_path: Path, field: str, allowed: set[str]) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ValueError(f"Config '{config_path}' field '{field}' contains unsupported keys: {unknown}")


def _require_keys(mapping: dict[str, Any], config_path: Path, field: str, keys: list[str]) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError(f"Config '{config_path}' field '{field}' is missing required keys: {missing}")


def _string_list(value: Any, config_path: Path, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Config '{config_path}' field '{field}' must be a list of strings.")
    return [str(item).strip() for item in value]


def _optional_str(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value).strip()


def _optional_int(value: Any, config_path: Path, field: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config '{config_path}' field '{field}' must be an integer.") from exc


def _optional_float_tuple(value: Any, config_path: Path, field: str) -> tuple[float, ...] | None:
    if value is None or value == "":
        return None
    if not isinstance(value, list):
        raise ValueError(f"Config '{config_path}' field '{field}' must be a list of numbers.")
    try:
        return tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Config '{config_path}' field '{field}' must be numeric.") from exc


def _optional_tuple(value: Any, config_path: Path, field: str) -> tuple[Any, ...] | None:
    if value is None or value == "":
        return None
    if not isinstance(value, list):
        raise ValueError(f"Config '{config_path}' field '{field}' must be a list.")
    return tuple(value)
