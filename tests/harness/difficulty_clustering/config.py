from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .core import (
    ClusteringConfig,
    ExperimentConfig,
    OutputOptions,
    PCAConfig,
    PreprocessingConfig,
    REPO_ROOT,
)

_TOP_LEVEL_KEYS = frozenset(
    {
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
)


def load_experiment_config(path: str | Path) -> ExperimentConfig:
    config_path = Path(path).expanduser()
    payload = yaml.safe_load(config_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"Clustering config must decode to a mapping: {config_path}")
    unknown_keys = sorted(set(payload) - _TOP_LEVEL_KEYS)
    if unknown_keys:
        unknown_text = ", ".join(unknown_keys)
        raise ValueError(f"Unknown top-level key(s) in {config_path}: {unknown_text}")

    if "experiment_name" not in payload or "input_matrix_path" not in payload:
        raise ValueError(f"Clustering config must include experiment_name and input_matrix_path: {config_path}")

    preprocessing_mapping = _require_mapping(payload.get("preprocessing", {}), config_path, "preprocessing")
    pca_mapping = _require_mapping(payload.get("pca", {}), config_path, "pca")
    clustering_mapping = _require_mapping(payload.get("clustering", {}), config_path, "clustering")
    output_mapping = _require_mapping(payload.get("output_options", {}), config_path, "output_options")

    return ExperimentConfig(
        experiment_name=str(payload["experiment_name"]).strip(),
        dataset_name=str(payload.get("dataset_name", "oktav")).strip().lower(),
        input_matrix_path=_resolve_repo_path(payload["input_matrix_path"], config_dir=config_path.parent),
        id_columns=tuple(_string_list(payload.get("id_columns", ["source_row_index", "filename", "dataset_relative_path"]), config_path, "id_columns")),
        label_column=_optional_str(payload.get("label_column")),
        feature_columns=tuple(_string_list(payload.get("feature_columns", []), config_path, "feature_columns")),
        feature_set=_optional_str(payload.get("feature_set")),
        excluded_columns=tuple(_string_list(payload.get("excluded_columns", []), config_path, "excluded_columns")),
        preprocessing=PreprocessingConfig(
            missing_feature_strategy=str(preprocessing_mapping.get("missing_feature_strategy", "median")).strip(),
            scaler=_optional_str(preprocessing_mapping.get("scaler")),
        ),
        pca=PCAConfig(
            n_components=_required_int(pca_mapping.get("n_components", 2), config_path, "pca.n_components"),
        ),
        clustering=ClusteringConfig(
            method=str(clustering_mapping.get("method", "ward")).strip().lower(),
            n_clusters=_required_int(clustering_mapping.get("n_clusters", 3), config_path, "clustering.n_clusters"),
            random_state=_optional_int(clustering_mapping.get("random_state"), config_path, "clustering.random_state") or 42,
            n_init=_optional_int(clustering_mapping.get("n_init"), config_path, "clustering.n_init") or 20,
        ),
        output_options=OutputOptions(run_name=_optional_str(output_mapping.get("run_name"))),
        config_path=config_path.resolve(),
    )


def _resolve_repo_path(value: Any, config_dir: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    if config_dir is not None and str(value).startswith((".", "..")):
        return (config_dir / path).resolve()
    return (REPO_ROOT / path).resolve()


def _require_mapping(value: Any, config_path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {field!r} in {config_path}.")
    return value


def _string_list(value: Any, config_path: Path, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"Expected list for {field!r} in {config_path}.")
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


def _required_int(value: Any, config_path: Path, field: str) -> int:
    parsed = _optional_int(value, config_path, field)
    if parsed is None:
        raise ValueError(f"Missing required integer value for {field!r} in {config_path}.")
    return parsed
