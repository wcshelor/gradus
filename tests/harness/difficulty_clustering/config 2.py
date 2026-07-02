from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .core import (
    ClusteringMethodConfig,
    ClusteringSweepConfig,
    ExperimentConfig,
    OutputOptions,
    PCAConfig,
    PreprocessingConfig,
    REPO_ROOT,
)

_TOP_LEVEL_KEYS = {
    "experiment_name",
    "dataset_name",
    "input_matrix_path",
    "id_columns",
    "label_column",
    "feature_columns",
    "feature_set",
    "excluded_columns",
    "preprocessing",
    "pca",
    "clustering",
    "output_options",
}
_PREPROCESSING_KEYS = {"missing_feature_strategy", "scaler"}
_PCA_KEYS = {"n_components"}
_CLUSTERING_KEYS = {"method", "n_clusters", "random_state", "n_init", "sweep"}
_SWEEP_KEYS = {
    "enabled",
    "k_values",
    "k_min",
    "k_max",
    "k_step",
    "selection_metric",
    "selection_goal",
    "include_label_metrics",
}
_OUTPUT_KEYS = {"run_name"}


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path).expanduser()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Config '{config_path}' must contain a YAML mapping.")

    unknown = sorted(set(raw) - _TOP_LEVEL_KEYS)
    if unknown:
        raise ValueError(f"Config '{config_path}' contains unsupported top-level keys: {unknown}")

    _require_keys(
        raw,
        config_path,
        "top-level",
        [
            "experiment_name",
            "dataset_name",
            "input_matrix_path",
            "id_columns",
            "excluded_columns",
            "preprocessing",
            "pca",
            "clustering",
            "output_options",
        ],
    )

    preprocessing_raw = _require_mapping(raw["preprocessing"], config_path, "preprocessing")
    pca_raw = _require_mapping(raw["pca"], config_path, "pca")
    clustering_raw = _require_mapping(raw["clustering"], config_path, "clustering")
    output_raw = _require_mapping(raw["output_options"], config_path, "output_options")

    _validate_keys(preprocessing_raw, config_path, "preprocessing", _PREPROCESSING_KEYS)
    _validate_keys(pca_raw, config_path, "pca", _PCA_KEYS)
    _validate_keys(clustering_raw, config_path, "clustering", _CLUSTERING_KEYS)
    _validate_keys(output_raw, config_path, "output_options", _OUTPUT_KEYS)

    feature_columns = tuple(_string_list(raw.get("feature_columns"), config_path, "feature_columns"))
    feature_set = _optional_str(raw.get("feature_set"))
    if not feature_columns and not feature_set:
        raise ValueError(
            f"Config '{config_path}' must provide either 'feature_columns' or 'feature_set'."
        )
    if feature_columns and feature_set:
        raise ValueError(
            f"Config '{config_path}' must not provide both 'feature_columns' and 'feature_set'."
        )

    return ExperimentConfig(
        experiment_name=str(raw["experiment_name"]).strip(),
        dataset_name=str(raw["dataset_name"]).strip().lower(),
        input_matrix_path=_resolve_repo_path(raw["input_matrix_path"]),
        id_columns=tuple(_string_list(raw["id_columns"], config_path, "id_columns")),
        label_column=_optional_str(raw.get("label_column")),
        feature_columns=feature_columns,
        feature_set=feature_set,
        excluded_columns=tuple(_string_list(raw["excluded_columns"], config_path, "excluded_columns")),
        preprocessing=PreprocessingConfig(
            missing_feature_strategy=str(preprocessing_raw.get("missing_feature_strategy", "median")).strip(),
            scaler=str(preprocessing_raw.get("scaler", "standard")).strip(),
        ),
        pca=PCAConfig(
            n_components=_required_int(pca_raw.get("n_components"), config_path, "pca.n_components"),
        ),
        clustering=ClusteringMethodConfig(
            method=str(clustering_raw["method"]).strip(),
            n_clusters=_required_int(clustering_raw.get("n_clusters"), config_path, "clustering.n_clusters"),
            random_state=_optional_int(clustering_raw.get("random_state"), config_path, "clustering.random_state")
            or 42,
            n_init=_optional_int(clustering_raw.get("n_init"), config_path, "clustering.n_init") or 20,
        ),
        sweep=_load_sweep_config(clustering_raw.get("sweep"), config_path),
        output_options=OutputOptions(run_name=_optional_str(output_raw.get("run_name"))),
        config_path=config_path,
    )


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


def _required_int(value: Any, config_path: Path, field: str) -> int:
    result = _optional_int(value, config_path, field)
    if result is None:
        raise ValueError(f"Config '{config_path}' field '{field}' is required.")
    return result


def _load_sweep_config(value: Any, config_path: Path) -> ClusteringSweepConfig:
    if value is None:
        return ClusteringSweepConfig()

    mapping = _require_mapping(value, config_path, "clustering.sweep")
    _validate_keys(mapping, config_path, "clustering.sweep", _SWEEP_KEYS)

    enabled = bool(mapping.get("enabled", True))
    k_values = tuple(_positive_int_list(mapping.get("k_values"), config_path, "clustering.sweep.k_values"))
    k_min = _optional_int(mapping.get("k_min"), config_path, "clustering.sweep.k_min")
    k_max = _optional_int(mapping.get("k_max"), config_path, "clustering.sweep.k_max")
    k_step = _optional_int(mapping.get("k_step"), config_path, "clustering.sweep.k_step") or 1
    if k_step <= 0:
        raise ValueError(f"Config '{config_path}' field 'clustering.sweep.k_step' must be positive.")

    if k_values and (k_min is not None or k_max is not None):
        raise ValueError(
            f"Config '{config_path}' field 'clustering.sweep' must not combine 'k_values' with 'k_min'/'k_max'."
        )
    if (k_min is None) ^ (k_max is None):
        raise ValueError(
            f"Config '{config_path}' field 'clustering.sweep' must provide both 'k_min' and 'k_max' or neither."
        )
    if k_min is not None and k_max is not None and k_min > k_max:
        raise ValueError(
            f"Config '{config_path}' field 'clustering.sweep' requires k_min <= k_max."
        )

    selection_metric = str(mapping.get("selection_metric", "silhouette_score")).strip()
    selection_goal = _optional_str(mapping.get("selection_goal"))
    include_label_metrics = bool(mapping.get("include_label_metrics", False))

    return ClusteringSweepConfig(
        enabled=enabled,
        k_values=k_values,
        k_min=k_min,
        k_max=k_max,
        k_step=k_step,
        selection_metric=selection_metric,
        selection_goal=selection_goal,
        include_label_metrics=include_label_metrics,
    )


def _positive_int_list(value: Any, config_path: Path, field: str) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Config '{config_path}' field '{field}' must be a list of integers.")
    result: list[int] = []
    for item in value:
        integer = _required_int(item, config_path, field)
        if integer < 2:
            raise ValueError(f"Config '{config_path}' field '{field}' values must be at least 2.")
        result.append(integer)
    return result
