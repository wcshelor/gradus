from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOCAL_CONFIG_PATH = REPO_ROOT / ".local" / "datasets.toml"

DATASET_ENV_VARS: dict[str, str] = {
    "oktav": "GRADUS_OKTAV_ROOT",
    "cipi": "GRADUS_CIPI_ROOT",
}
CONFIG_ENV_VAR = "GRADUS_DATASETS_CONFIG"

SUPPORTED_SCORE_SUFFIXES: tuple[str, ...] = (".xml", ".musicxml", ".mxl")


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    dataset_name: str
    root: Path | None = None
    manifest_path: Path | None = None
    label_source_path: Path | None = None
    score_globs: tuple[str, ...] = ("*.xml", "*.musicxml", "*.mxl")
    expected_suffixes: tuple[str, ...] = SUPPORTED_SCORE_SUFFIXES
    path_mode: str = "dataset_root"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset_name", str(self.dataset_name).strip().lower())

    @property
    def normalized_name(self) -> str:
        return str(self.dataset_name).strip().lower()


@dataclass(frozen=True, slots=True)
class DatasetRootResolution:
    root: Path | None
    source: str
    detail: str
    configured: bool
    exists: bool


def dataset_env_var(dataset_name: str) -> str | None:
    return DATASET_ENV_VARS.get(str(dataset_name).strip().lower())


def parse_dataset_config_file(config_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(config_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Dataset config file not found: {path}")
    try:
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Malformed dataset config TOML at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Dataset config must decode to a table: {path}")
    sections: dict[str, dict[str, Any]] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            sections[str(key).strip().lower()] = dict(value)
    return sections


def _config_root_for_dataset(
    sections: dict[str, dict[str, Any]],
    dataset_name: str,
) -> Path | None:
    section = sections.get(str(dataset_name).strip().lower(), {})
    raw_root = section.get("root")
    if raw_root in (None, ""):
        return None
    return Path(str(raw_root)).expanduser()


def resolve_dataset_root(
    dataset_name: str,
    explicit_root: str | Path | None = None,
    config_path: str | Path | None = None,
    repo_fallback: str | Path | None = None,
) -> DatasetRootResolution:
    normalized = str(dataset_name).strip().lower()
    if explicit_root not in (None, ""):
        root = Path(str(explicit_root)).expanduser()
        exists = root.exists()
        detail = f"explicit CLI root: {root}"
        if not exists:
            detail += " (configured path does not exist)"
        return DatasetRootResolution(root=root, source="cli", detail=detail, configured=True, exists=exists)

    env_var = dataset_env_var(normalized)
    if env_var:
        env_value = os.environ.get(env_var, "").strip()
        if env_value:
            root = Path(env_value).expanduser()
            exists = root.exists()
            detail = f"environment variable {env_var}: {root}"
            if not exists:
                detail += " (configured path does not exist)"
            return DatasetRootResolution(root=root, source="env", detail=detail, configured=True, exists=exists)

    selected_config = config_path
    config_source = "explicit_config"
    if selected_config is None:
        env_config = os.environ.get(CONFIG_ENV_VAR, "").strip()
        if env_config:
            selected_config = env_config
            config_source = "env_config"
        elif DEFAULT_LOCAL_CONFIG_PATH.is_file():
            selected_config = DEFAULT_LOCAL_CONFIG_PATH

    if selected_config is not None:
        config_file = Path(str(selected_config)).expanduser()
        if config_file.is_file():
            try:
                sections = parse_dataset_config_file(config_file)
            except ValueError as exc:
                return DatasetRootResolution(
                    root=None,
                    source="local_config_error",
                    detail=str(exc),
                    configured=True,
                    exists=False,
                )
            root = _config_root_for_dataset(sections, normalized)
            if root is not None:
                exists = root.exists()
                detail = f"local config {config_file}: {root}"
                if not exists:
                    detail += " (configured path does not exist)"
                return DatasetRootResolution(
                    root=root, source="local_config", detail=detail, configured=True, exists=exists
                )
            if config_source == "explicit_config" or str(selected_config) != str(DEFAULT_LOCAL_CONFIG_PATH):
                pass
        elif config_source in {"explicit_config", "env_config"}:
            return DatasetRootResolution(
                root=None,
                source="local_config_error",
                detail=f"Dataset config file not found: {config_file}",
                configured=True,
                exists=False,
            )

    if repo_fallback not in (None, ""):
        root = Path(str(repo_fallback)).expanduser()
        return DatasetRootResolution(
            root=root,
            source="repo_default",
            detail=f"repo-relative fallback: {root}",
            configured=True,
            exists=root.exists(),
        )

    return DatasetRootResolution(
        root=None,
        source="not_configured",
        detail=(
            f"Dataset {normalized!r} is not configured. Set an explicit root, "
            f"{env_var or 'a dataset environment variable'}, or local config "
            f"{DEFAULT_LOCAL_CONFIG_PATH}."
        ),
        configured=False,
        exists=False,
    )
