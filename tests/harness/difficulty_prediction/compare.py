from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

from .core import DEFAULT_COMPARISONS_ROOT


def compare_run_directories(
    run_dirs: Iterable[str | Path],
    out_csv: str | Path = DEFAULT_COMPARISONS_ROOT / "run_comparison.csv",
) -> pd.DataFrame:
    rows = [_read_run_summary(run_dir) for run_dir in run_dirs]
    frame = pd.DataFrame(rows)
    out_path = Path(out_csv).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_path, index=False)
    return frame


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare difficulty prediction run directories.")
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_COMPARISONS_ROOT / "run_comparison.csv")
    args = parser.parse_args(argv)

    frame = compare_run_directories(args.run_dirs, out_csv=args.out_csv)
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


def _read_run_summary(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir).expanduser().resolve()
    if not run_path.is_dir():
        raise FileNotFoundError(f"Run directory not found: {run_path}")

    resolved_config_path = run_path / "resolved_config.yaml"
    metrics_path = run_path / "metrics.json"
    if not resolved_config_path.is_file() or not metrics_path.is_file():
        raise FileNotFoundError(
            f"Run directory must contain resolved_config.yaml and metrics.json: {run_path}"
        )

    resolved_config = yaml.safe_load(resolved_config_path.read_text()) or {}
    metrics = json.loads(metrics_path.read_text())
    row = {
        "run_dir": str(run_path),
        "experiment_name": resolved_config.get("experiment_name"),
        "dataset_name": resolved_config.get("dataset_name"),
        "feature_set": resolved_config.get("feature_set"),
        "model_family": resolved_config.get("model_family"),
        "target_scheme": _target_scheme_label(resolved_config.get("target_scheme")),
        "primary_metric": metrics.get("primary_metric"),
    }
    row.update(metrics.get("overall_metrics", {}))
    return row


def _target_scheme_label(target_scheme: Any) -> str:
    if not isinstance(target_scheme, dict):
        return "unknown"
    kind = str(target_scheme.get("kind", "unknown"))
    if kind == "quantile_bins":
        return f"{kind}:{target_scheme.get('bins')}"
    if kind == "custom_bins":
        labels = target_scheme.get("labels")
        if isinstance(labels, list):
            return f"{kind}:{len(labels)}"
    return kind

