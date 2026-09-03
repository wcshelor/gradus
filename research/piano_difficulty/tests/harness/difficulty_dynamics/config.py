from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - exercised only in stripped runtimes
    yaml = None

from piano_difficulty.temporal.windows import HandMode

from .models import (
    CompositeConfig,
    DifficultyDynamicsConfig,
    ExportConfig,
    NormalizationConfig,
    PeakDetectionConfig,
    SmoothingConfig,
    WindowStrategyConfig,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_TOP_LEVEL_KEYS = frozenset(
    {
        "experiment_name",
        "score_path",
        "score_id",
        "feature_ids",
        "hand_mode",
        "window",
        "normalization",
        "smoothing",
        "composite",
        "peaks",
        "export",
    }
)
_WINDOW_KEYS = frozenset({"kind", "size", "step", "final_window_behavior", "beat_size", "beat_step"})
_NORMALIZATION_KEYS = frozenset({"method"})
_SMOOTHING_KEYS = frozenset({"method", "window_size", "centered"})
_COMPOSITE_KEYS = frozenset(
    {"enabled", "feature_ids", "weights", "minimum_valid_features", "exclude_missing", "output_feature_id"}
)
_PEAK_KEYS = frozenset({"method", "top_n", "percentile", "minimum_separation"})
_EXPORT_KEYS = frozenset(
    {
        "output_root",
        "run_name",
        "json_filename",
        "csv_filename",
        "peaks_filename",
        "hotspots_filename",
        "report_filename",
        "plot_filename",
        "write_plot",
    }
)


def load_difficulty_dynamics_config(path: str | Path) -> DifficultyDynamicsConfig:
    config_path = Path(path).expanduser()
    payload = _load_config_payload(config_path)
    if not isinstance(payload, dict):
        raise ValueError(f"Difficulty Dynamics config must decode to a mapping: {config_path}")

    _require_keys(payload, config_path, ["experiment_name", "score_path", "feature_ids"], "top_level")
    _validate_keys(payload, config_path, _TOP_LEVEL_KEYS, "top_level")

    window_mapping = _require_mapping(payload.get("window", {}), config_path, "window")
    _validate_keys(window_mapping, config_path, _WINDOW_KEYS, "window")
    normalization_mapping = _require_mapping(payload.get("normalization", {}), config_path, "normalization")
    _validate_keys(normalization_mapping, config_path, _NORMALIZATION_KEYS, "normalization")
    smoothing_mapping = _require_mapping(payload.get("smoothing", {}), config_path, "smoothing")
    _validate_keys(smoothing_mapping, config_path, _SMOOTHING_KEYS, "smoothing")
    composite_mapping = _require_mapping(payload.get("composite", {}), config_path, "composite")
    _validate_keys(composite_mapping, config_path, _COMPOSITE_KEYS, "composite")
    peaks_mapping = _require_mapping(payload.get("peaks", {}), config_path, "peaks")
    _validate_keys(peaks_mapping, config_path, _PEAK_KEYS, "peaks")
    export_mapping = _require_mapping(payload.get("export", {}), config_path, "export")
    _validate_keys(export_mapping, config_path, _EXPORT_KEYS, "export")

    feature_ids = tuple(_string_list(payload["feature_ids"], config_path, "feature_ids"))
    hand_mode = _optional_hand_mode(payload.get("hand_mode", "both"), config_path, "hand_mode")
    window_kind = str(window_mapping.get("kind", "measure")).strip().lower()
    if window_kind not in {"measure", "beat"}:
        raise ValueError(
            f"Expected window.kind to be one of measure or beat in {config_path}."
        )

    window = WindowStrategyConfig(
        kind=window_kind,
        size=_optional_int(window_mapping.get("size", 4), config_path, "window.size") or 4,
        step=_optional_int(window_mapping.get("step", 1), config_path, "window.step") or 1,
        final_window_behavior=str(window_mapping.get("final_window_behavior", "include")).strip(),
        beat_size=_optional_float(window_mapping.get("beat_size"), config_path, "window.beat_size"),
        beat_step=_optional_float(window_mapping.get("beat_step"), config_path, "window.beat_step"),
    )
    normalization = NormalizationConfig(method=str(normalization_mapping.get("method", "none")).strip())
    smoothing = SmoothingConfig(
        method=str(smoothing_mapping.get("method", "none")).strip(),
        window_size=_optional_int(smoothing_mapping.get("window_size", 3), config_path, "smoothing.window_size") or 3,
        centered=bool(smoothing_mapping.get("centered", True)),
    )
    composite = CompositeConfig(
        enabled=bool(composite_mapping.get("enabled", True)),
        feature_ids=tuple(_string_list(composite_mapping.get("feature_ids", []), config_path, "composite.feature_ids")),
        weights=_float_mapping(composite_mapping.get("weights", {}), config_path, "composite.weights"),
        minimum_valid_features=_optional_int(
            composite_mapping.get("minimum_valid_features", 1), config_path, "composite.minimum_valid_features"
        )
        or 1,
        exclude_missing=bool(composite_mapping.get("exclude_missing", True)),
        output_feature_id=str(composite_mapping.get("output_feature_id", "composite.difficulty")).strip(),
    )
    peaks = PeakDetectionConfig(
        method=str(peaks_mapping.get("method", "top_n")).strip(),
        top_n=_optional_int(peaks_mapping.get("top_n", 3), config_path, "peaks.top_n") or 3,
        percentile=_optional_float(peaks_mapping.get("percentile", 0.9), config_path, "peaks.percentile") or 0.9,
        minimum_separation=_optional_int(
            peaks_mapping.get("minimum_separation", 1), config_path, "peaks.minimum_separation"
        )
        or 1,
    )
    export = ExportConfig(
        output_root=_resolve_path(export_mapping.get("output_root", "tests/artifacts/difficulty_dynamics"), config_path.parent),
        run_name=_optional_str(export_mapping.get("run_name")),
        json_filename=str(export_mapping.get("json_filename", "difficulty_profile.json")).strip(),
        csv_filename=str(export_mapping.get("csv_filename", "difficulty_profile.csv")).strip(),
        peaks_filename=str(export_mapping.get("peaks_filename", "difficulty_peaks.json")).strip(),
        hotspots_filename=str(export_mapping.get("hotspots_filename", "difficulty_hotspots.csv")).strip(),
        report_filename=str(export_mapping.get("report_filename", "difficulty_summary.md")).strip(),
        plot_filename=str(export_mapping.get("plot_filename", "difficulty_profile.png")).strip(),
        write_plot=bool(export_mapping.get("write_plot", True)),
    )

    return DifficultyDynamicsConfig(
        experiment_name=str(payload["experiment_name"]).strip(),
        score_path=_resolve_path(payload["score_path"], config_path.parent),
        feature_ids=feature_ids,
        hand_mode=hand_mode,
        score_id=_optional_str(payload.get("score_id")),
        window=window,
        normalization=normalization,
        smoothing=smoothing,
        composite=composite,
        peaks=peaks,
        export=export,
        config_path=config_path.resolve(),
    )


def _load_config_payload(config_path: Path) -> Any:
    text = config_path.read_text()
    if yaml is not None:
        return yaml.safe_load(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModuleNotFoundError(
            "PyYAML is not available in this workspace. Use a JSON-formatted config file or install PyYAML."
        ) from exc


def _optional_hand_mode(value: Any, config_path: Path, field: str) -> HandMode:
    hand_mode = str(value).strip().lower()
    if hand_mode not in {"both", "left", "right"}:
        raise ValueError(f"Expected hand_mode to be one of both, left, or right in {config_path} ({field}).")
    return hand_mode  # type: ignore[return-value]


def _resolve_path(value: Any, base_dir: Path) -> Path:
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    if str(value).startswith((".", "..")):
        return (base_dir / candidate).resolve()
    return (REPO_ROOT / candidate).resolve()


def _require_mapping(value: Any, config_path: Path, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {field!r} in {config_path}.")
    return value


def _validate_keys(mapping: dict[str, Any], config_path: Path, allowed: set[str], field: str) -> None:
    unknown = sorted(set(mapping) - set(allowed))
    if unknown:
        raise ValueError(f"Unknown key(s) for {field!r} in {config_path}: {', '.join(unknown)}")


def _require_keys(mapping: dict[str, Any], config_path: Path, keys: list[str], field: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ValueError(f"Missing required key(s) for {field!r} in {config_path}: {', '.join(missing)}")


def _string_list(value: Any, config_path: Path, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"Expected list for {field!r} in {config_path}.")
    return [str(item).strip() for item in value]


def _float_mapping(value: Any, config_path: Path, field: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise ValueError(f"Expected mapping for {field!r} in {config_path}.")
    try:
        return {str(key): float(amount) for key, amount in value.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected float-compatible mapping for {field!r} in {config_path}.") from exc


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


def _optional_float(value: Any, config_path: Path, field: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected float-compatible value for {field!r} in {config_path}.") from exc
