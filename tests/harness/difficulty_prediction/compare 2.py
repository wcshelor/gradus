from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

from .core import DEFAULT_COMPARISONS_ROOT


def compare_run_directories(
    run_dirs: Iterable[str | Path],
    *,
    out_csv_path: str | Path = DEFAULT_COMPARISONS_ROOT / "run_comparison.csv",
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        rows.append(_read_run_summary(Path(run_dir).expanduser()))

    frame = pd.DataFrame(rows)
    out_path = Path(out_csv_path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_path, index=False)
    return frame


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="compare_difficulty_prediction_runs",
        description="Compare multiple difficulty-prediction run directories.",
    )
    parser.add_argument("run_dirs", nargs="+", help="One or more run directories to compare.")
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=DEFAULT_COMPARISONS_ROOT / "run_comparison.csv",
        help="Comparison CSV output path.",
    )
    args = parser.parse_args(argv)

    frame = compare_run_directories(args.run_dirs, out_csv_path=args.out_csv)
    print(
        json.dumps(
            {
                "out_csv": str(args.out_csv),
                "row_count": int(len(frame)),
                "columns": list(frame.columns),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _read_run_summary(run_dir: Path) -> dict[str, Any]:
    summary = {
        "run_dir": str(run_dir.resolve()),
        "status": "ok",
        "error": "",
    }
    config_path = run_dir / "resolved_config.yaml"
    metrics_path = run_dir / "metrics.json"
    missing: list[str] = []
    if not config_path.is_file():
        missing.append(str(config_path))
    if not metrics_path.is_file():
        missing.append(str(metrics_path))
    if missing:
        summary["status"] = "missing"
        summary["error"] = "Missing required files: " + ", ".join(missing)
        return summary

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    overall_metrics = metrics.get("overall_metrics", {})

    summary.update(
        {
            "experiment_name": metrics.get("experiment_name", config.get("experiment_name", "")),
            "dataset_name": metrics.get("dataset_name", config.get("dataset_name", "")),
            "feature_set": metrics.get("feature_set", config.get("feature_set", "")),
            "target_scheme": _target_scheme_label(metrics, config),
            "model_family": metrics.get("model_family", config.get("model_family", "")),
            "problem_type": metrics.get("problem_type", config.get("target_kind", "")),
            "row_count": metrics.get("row_count", overall_metrics.get("row_count", "")),
            "feature_count": metrics.get("feature_count", overall_metrics.get("feature_count", "")),
            "effective_cv_folds": metrics.get("effective_cv_folds", overall_metrics.get("effective_cv_folds", "")),
            "primary_metric": metrics.get("primary_metric", ""),
        }
    )
    for key in [
        "accuracy",
        "balanced_accuracy",
        "macro_f1",
        "off_by_one_accuracy",
        "mean_absolute_class_error",
        "mae",
        "rmse",
        "r2",
        "pearson",
        "spearman",
    ]:
        summary[key] = overall_metrics.get(key, "")

    return summary


def _target_scheme_label(metrics: dict[str, Any], config: dict[str, Any]) -> str:
    scheme = metrics.get("target_scheme") or config.get("target_scheme") or {}
    if not isinstance(scheme, dict):
        return str(scheme)
    kind = str(scheme.get("kind", ""))
    if kind == "quantile_bins":
        bins = scheme.get("bins")
        if bins is not None:
            return f"quantile_bins_{bins}"
    if kind == "custom_bins":
        edges = scheme.get("bin_edges")
        if isinstance(edges, list):
            return f"custom_bins_{max(len(edges) - 1, 0)}"
    return kind
