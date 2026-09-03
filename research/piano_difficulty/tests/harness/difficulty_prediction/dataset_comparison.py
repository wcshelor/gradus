from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from tests.harness.difficulty_prediction.core import (
    CrossValidationConfig,
    DEFAULT_COMPARISONS_ROOT,
    ExperimentConfig,
    OutputOptions,
    PreprocessingConfig,
    REPO_ROOT,
    TargetSchemeConfig,
)
from tests.harness.difficulty_prediction.runner import run_experiment
from tests.harness.yan2023.dataset_export import DatasetExportSpec, run_yan_dataset_export

DEFAULT_CIPI_ROOT = Path("~/desktop/oktav-thesis/datasets/cipi").expanduser()
DEFAULT_OKTAV_ROOT = Path("~/desktop/oktav-thesis/datasets/oktav-starting-dataset").expanduser()
DEFAULT_YAN_EXPORT_ROOT = REPO_ROOT / "tests" / "artifacts" / "yan2023" / "dataset_exports"
DEFAULT_CIPI_YAN_MATRIX = DEFAULT_YAN_EXPORT_ROOT / "cipi" / "yan_features.csv"
DEFAULT_OKTAV_YAN_MATRIX = DEFAULT_YAN_EXPORT_ROOT / "oktav-starting" / "yan_features.csv"
DEFAULT_OKTAV_LABELED_MATRIX = (
    REPO_ROOT
    / "tests"
    / "artifacts"
    / "oktav_dataset"
    / "python_analysis"
    / "full_run"
    / "oktav_labeled_feature_matrix.csv"
)
DEFAULT_CIPI_MANIFEST = REPO_ROOT / "evaluation_scores" / "manifests" / "cipi" / "cipi_movement_manifest.csv"


@dataclass(frozen=True, slots=True)
class PreparedDataset:
    dataset_name: str
    matrix_path: Path
    target_column: str
    label_name: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    comparison_dir: Path
    report_path: Path
    metrics_csv_path: Path
    dataset_summary_csv_path: Path
    prepared_matrices: tuple[PreparedDataset, ...]
    run_dirs: tuple[Path, ...]


def run_full_yan_dataset_comparison(
    *,
    cipi_root: str | Path = DEFAULT_CIPI_ROOT,
    oktav_root: str | Path = DEFAULT_OKTAV_ROOT,
    yan_export_root: str | Path = DEFAULT_YAN_EXPORT_ROOT,
    cipi_manifest: str | Path = DEFAULT_CIPI_MANIFEST,
    oktav_labeled_matrix: str | Path = DEFAULT_OKTAV_LABELED_MATRIX,
    out_root: str | Path = DEFAULT_COMPARISONS_ROOT,
    rerun_yan_exports: bool = False,
    workers: int | None = None,
    timeout_seconds: float = 15.0,
) -> ComparisonResult:
    comparison_dir = _allocate_comparison_dir(Path(out_root).expanduser())
    matrices_dir = comparison_dir / "matrices"
    runs_root = comparison_dir / "runs"
    matrices_dir.mkdir(parents=True, exist_ok=False)
    runs_root.mkdir(parents=True, exist_ok=False)

    yan_export_root_path = Path(yan_export_root).expanduser()
    cipi_manifest_path = Path(cipi_manifest).expanduser()
    oktav_labeled_matrix_path = Path(oktav_labeled_matrix).expanduser()

    if rerun_yan_exports:
        run_yan_dataset_export(
            DatasetExportSpec(
                dataset_name="cipi",
                dataset_root=Path(cipi_root).expanduser(),
                out_dir=yan_export_root_path / "cipi",
                label_csv=cipi_manifest_path,
                label_join_column="dataset_relative_path",
                label_value_column="henle",
            ),
            workers=workers,
            timeout_seconds=timeout_seconds,
        )
        run_yan_dataset_export(
            DatasetExportSpec(
                dataset_name="oktav-starting",
                dataset_root=Path(oktav_root).expanduser(),
                out_dir=yan_export_root_path / "oktav-starting",
            ),
            workers=workers,
            timeout_seconds=timeout_seconds,
        )

    cipi_prepared = _prepare_cipi_matrix(
        yan_matrix_path=yan_export_root_path / "cipi" / "yan_features.csv",
        manifest_path=cipi_manifest_path,
        out_path=matrices_dir / "cipi_yan_labeled_features.csv",
    )
    oktav_prepared = _prepare_oktav_matrix(
        yan_matrix_path=yan_export_root_path / "oktav-starting" / "yan_features.csv",
        labeled_matrix_path=oktav_labeled_matrix_path,
        out_path=matrices_dir / "oktav_yan_labeled_features.csv",
    )
    prepared = (cipi_prepared, oktav_prepared)

    dataset_summary = _build_dataset_summary(prepared)
    dataset_summary_path = comparison_dir / "dataset_summary.csv"
    dataset_summary.to_csv(dataset_summary_path, index=False)

    run_results = []
    for dataset in prepared:
        for config in _experiment_configs_for_dataset(dataset):
            run_results.append(run_experiment(config, runs_root=runs_root))

    metrics_frame = _build_metrics_frame(run_results)
    metrics_path = comparison_dir / "model_metrics.csv"
    metrics_frame.to_csv(metrics_path, index=False)

    report_path = comparison_dir / "analysis_report.md"
    report_path.write_text(
        _build_report(
            comparison_dir=comparison_dir,
            prepared=prepared,
            dataset_summary=dataset_summary,
            metrics_frame=metrics_frame,
            rerun_yan_exports=rerun_yan_exports,
        )
    )

    summary_path = comparison_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "comparison_dir": str(comparison_dir),
                "report_path": str(report_path),
                "metrics_csv_path": str(metrics_path),
                "dataset_summary_csv_path": str(dataset_summary_path),
                "prepared_matrices": [str(dataset.matrix_path) for dataset in prepared],
                "run_dirs": [str(result.run_dir) for result in run_results],
            },
            indent=2,
            sort_keys=True,
        )
    )

    return ComparisonResult(
        comparison_dir=comparison_dir,
        report_path=report_path,
        metrics_csv_path=metrics_path,
        dataset_summary_csv_path=dataset_summary_path,
        prepared_matrices=prepared,
        run_dirs=tuple(result.run_dir for result in run_results),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare labeled Yan 2023 feature matrices for CIPI and Oktav, run "
            "prediction experiments, and write a cross-dataset analysis report."
        )
    )
    parser.add_argument("--cipi-root", type=Path, default=DEFAULT_CIPI_ROOT)
    parser.add_argument("--oktav-root", type=Path, default=DEFAULT_OKTAV_ROOT)
    parser.add_argument("--yan-export-root", type=Path, default=DEFAULT_YAN_EXPORT_ROOT)
    parser.add_argument("--cipi-manifest", type=Path, default=DEFAULT_CIPI_MANIFEST)
    parser.add_argument("--oktav-labeled-matrix", type=Path, default=DEFAULT_OKTAV_LABELED_MATRIX)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_COMPARISONS_ROOT)
    parser.add_argument("--rerun-yan-exports", action="store_true")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_full_yan_dataset_comparison(
        cipi_root=args.cipi_root,
        oktav_root=args.oktav_root,
        yan_export_root=args.yan_export_root,
        cipi_manifest=args.cipi_manifest,
        oktav_labeled_matrix=args.oktav_labeled_matrix,
        out_root=args.out_root,
        rerun_yan_exports=args.rerun_yan_exports,
        workers=args.workers,
        timeout_seconds=args.timeout_seconds,
    )
    print(
        json.dumps(
            {
                "comparison_dir": str(result.comparison_dir),
                "report_path": str(result.report_path),
                "metrics_csv_path": str(result.metrics_csv_path),
                "dataset_summary_csv_path": str(result.dataset_summary_csv_path),
                "run_count": len(result.run_dirs),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _prepare_cipi_matrix(
    *,
    yan_matrix_path: Path,
    manifest_path: Path,
    out_path: Path,
) -> PreparedDataset:
    yan = _read_csv(yan_matrix_path)
    manifest = _read_csv(manifest_path)
    if "normalized_filename" not in manifest.columns:
        raise ValueError(f"CIPI manifest needs normalized_filename: {manifest_path}")

    working = yan.copy()
    working["normalized_filename"] = working["filename"].map(_normalized_join_key)
    label_columns = [
        "cipi_id",
        "movement",
        "henle",
        "work_name",
        "book",
        "uri",
        "normalized_filename",
    ]
    merged = working.merge(
        manifest.loc[:, label_columns],
        on="normalized_filename",
        how="left",
        validate="one_to_one",
    )
    missing_labels = int(merged["henle"].isna().sum())
    if missing_labels:
        raise ValueError(f"CIPI label join left {missing_labels} rows unlabeled.")
    merged["henle"] = pd.to_numeric(merged["henle"], errors="raise")
    _write_csv(out_path, merged)
    return PreparedDataset(
        dataset_name="cipi",
        matrix_path=out_path,
        target_column="henle",
        label_name="Henle",
    )


def _prepare_oktav_matrix(
    *,
    yan_matrix_path: Path,
    labeled_matrix_path: Path,
    out_path: Path,
) -> PreparedDataset:
    labeled = _read_csv(labeled_matrix_path)
    if "difficulty_numeric" not in labeled.columns:
        raise ValueError(f"Oktav labeled matrix needs difficulty_numeric: {labeled_matrix_path}")

    if yan_matrix_path.is_file():
        yan = _read_csv(yan_matrix_path)
        label_source = labeled.loc[:, ["filename", "difficulty_numeric"]].copy()
        label_source["normalized_filename"] = label_source["filename"].map(_normalized_join_key)
        working = yan.copy()
        working["normalized_filename"] = working["filename"].map(_normalized_join_key)
        merged = working.merge(
            label_source.loc[:, ["normalized_filename", "difficulty_numeric"]],
            on="normalized_filename",
            how="left",
            validate="one_to_one",
        )
        if merged["difficulty_numeric"].notna().sum() == 0:
            raise ValueError("Oktav label join found no labeled rows.")
    else:
        merged = labeled.copy()
        merged["normalized_filename"] = merged["filename"].map(_normalized_join_key)

    merged["difficulty_numeric"] = pd.to_numeric(merged["difficulty_numeric"], errors="coerce")
    _write_csv(out_path, merged)
    return PreparedDataset(
        dataset_name="oktav",
        matrix_path=out_path,
        target_column="difficulty_numeric",
        label_name="Oktav difficulty_numeric",
    )


def _experiment_configs_for_dataset(dataset: PreparedDataset) -> list[ExperimentConfig]:
    base_id_columns = tuple(
        column
        for column in (
            "source_row_index",
            "piece_id",
            "piece_uid",
            "filename",
            "dataset_relative_path",
        )
        if column in pd.read_csv(dataset.matrix_path, nrows=0).columns
    )
    common = {
        "dataset_name": dataset.dataset_name,
        "input_matrix_path": dataset.matrix_path,
        "id_columns": base_id_columns,
        "target_column": dataset.target_column,
        "feature_set": "yan2023_observed",
        "preprocessing": PreprocessingConfig(imputer_strategy="median", scaler="standard"),
        "cross_validation": CrossValidationConfig(kind="kfold", folds=5, shuffle=True, random_state=42),
    }
    prefix = f"{dataset.dataset_name}-yan2023"
    return [
        ExperimentConfig(
            experiment_name=f"{prefix}-dummy-regression",
            target_scheme=TargetSchemeConfig(kind="continuous"),
            model_family="dummy_regression",
            model_parameters={"strategy": "mean"},
            output_options=OutputOptions(
                run_name=f"{prefix}-dummy-regression",
                primary_metric="r2",
                save_predictions=True,
                save_confusion_matrix=False,
                save_feature_importance=False,
            ),
            **common,
        ),
        ExperimentConfig(
            experiment_name=f"{prefix}-ridge-regression",
            target_scheme=TargetSchemeConfig(kind="continuous"),
            model_family="ridge_regression",
            model_parameters={"alpha": 1.0},
            output_options=OutputOptions(
                run_name=f"{prefix}-ridge-regression",
                primary_metric="r2",
                save_predictions=True,
                save_confusion_matrix=False,
                save_feature_importance=True,
            ),
            **common,
        ),
        ExperimentConfig(
            experiment_name=f"{prefix}-random-forest-regression",
            target_scheme=TargetSchemeConfig(kind="continuous"),
            model_family="random_forest_regression",
            model_parameters={"n_estimators": 300, "random_state": 42, "min_samples_leaf": 3},
            output_options=OutputOptions(
                run_name=f"{prefix}-random-forest-regression",
                primary_metric="r2",
                save_predictions=True,
                save_confusion_matrix=False,
                save_feature_importance=True,
            ),
            **common,
        ),
        ExperimentConfig(
            experiment_name=f"{prefix}-dummy-3bin",
            target_scheme=TargetSchemeConfig(kind="quantile_bins", bins=3),
            model_family="dummy_classifier",
            model_parameters={"strategy": "most_frequent"},
            cross_validation=CrossValidationConfig(kind="stratified", folds=5, shuffle=True, random_state=42),
            output_options=OutputOptions(
                run_name=f"{prefix}-dummy-3bin",
                primary_metric="balanced_accuracy",
                save_predictions=True,
                save_confusion_matrix=True,
                save_feature_importance=False,
            ),
            **{key: value for key, value in common.items() if key != "cross_validation"},
        ),
        ExperimentConfig(
            experiment_name=f"{prefix}-logreg-3bin",
            target_scheme=TargetSchemeConfig(kind="quantile_bins", bins=3),
            model_family="logistic_regression",
            model_parameters={"max_iter": 2000},
            cross_validation=CrossValidationConfig(kind="stratified", folds=5, shuffle=True, random_state=42),
            output_options=OutputOptions(
                run_name=f"{prefix}-logreg-3bin",
                primary_metric="balanced_accuracy",
                save_predictions=True,
                save_confusion_matrix=True,
                save_feature_importance=True,
            ),
            **{key: value for key, value in common.items() if key != "cross_validation"},
        ),
        ExperimentConfig(
            experiment_name=f"{prefix}-random-forest-3bin",
            target_scheme=TargetSchemeConfig(kind="quantile_bins", bins=3),
            model_family="random_forest_classifier",
            model_parameters={"n_estimators": 300, "random_state": 42, "min_samples_leaf": 3},
            cross_validation=CrossValidationConfig(kind="stratified", folds=5, shuffle=True, random_state=42),
            output_options=OutputOptions(
                run_name=f"{prefix}-random-forest-3bin",
                primary_metric="balanced_accuracy",
                save_predictions=True,
                save_confusion_matrix=True,
                save_feature_importance=True,
            ),
            **{key: value for key, value in common.items() if key != "cross_validation"},
        ),
    ]


def _build_dataset_summary(prepared: tuple[PreparedDataset, ...]) -> pd.DataFrame:
    rows = []
    for dataset in prepared:
        frame = _read_csv(dataset.matrix_path)
        status_counts = frame["status"].astype(str).str.lower().value_counts().to_dict() if "status" in frame else {}
        target = pd.to_numeric(frame[dataset.target_column], errors="coerce")
        feature_columns = [
            column
            for column in frame.columns
            if column not in _metadata_columns(dataset.target_column)
            and pd.api.types.is_numeric_dtype(pd.to_numeric(frame[column], errors="coerce"))
        ]
        rows.append(
            {
                "dataset_name": dataset.dataset_name,
                "matrix_path": str(dataset.matrix_path),
                "row_count": int(len(frame)),
                "success_rows": int(status_counts.get("success", len(frame))),
                "timeout_rows": int(status_counts.get("timeout", 0)),
                "labeled_rows": int(target.notna().sum()),
                "target_column": dataset.target_column,
                "target_min": float(target.min()),
                "target_median": float(target.median()),
                "target_max": float(target.max()),
                "target_unique_values": int(target.nunique()),
                "numeric_feature_columns": int(len(feature_columns)),
                "feature_missing_fraction_mean": float(
                    frame.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce").isna().mean().mean()
                )
                if feature_columns
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _build_metrics_frame(run_results: list[Any]) -> pd.DataFrame:
    rows = []
    for result in run_results:
        metrics = dict(result.metrics.get("overall_metrics", {}))
        rows.append(
            {
                "experiment_name": result.metrics.get("experiment_name"),
                "dataset_name": result.metrics.get("dataset_name"),
                "target_column": result.metrics.get("target_column"),
                "target_scheme": result.metrics.get("target_scheme", {}).get("kind"),
                "model_family": result.metrics.get("model_family"),
                "feature_set": result.metrics.get("feature_set"),
                "raw_row_count": result.metrics.get("raw_row_count"),
                "analyzed_row_count": result.metrics.get("analyzed_row_count"),
                "effective_folds": result.metrics.get("effective_folds"),
                "run_dir": str(result.run_dir),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def _build_report(
    *,
    comparison_dir: Path,
    prepared: tuple[PreparedDataset, ...],
    dataset_summary: pd.DataFrame,
    metrics_frame: pd.DataFrame,
    rerun_yan_exports: bool,
) -> str:
    lines = [
        "# Yan 2023 Cross-Dataset Difficulty Prediction Analysis",
        "",
        f"- comparison directory: `{comparison_dir}`",
        f"- reran Yan exports: `{rerun_yan_exports}`",
        f"- datasets: `{', '.join(dataset.dataset_name for dataset in prepared)}`",
        "",
        "## Prepared datasets",
        "",
        _frame_to_markdown(dataset_summary),
        "",
        "## Model comparison",
        "",
        _metrics_markdown(metrics_frame),
        "",
        "## Best runs by task",
        "",
        _best_runs_markdown(metrics_frame),
        "",
        "## Interpretation notes",
        "",
        "- Regression metrics compare each dataset on its native label scale; use `r2`, `pearson`, and `spearman` for cross-dataset comparison.",
        "- Three-bin classification uses quantile bins within each dataset, which makes `balanced_accuracy`, `macro_f1`, and off-by-one accuracy more comparable across CIPI and Oktav.",
        "- Rows with `status != success` are retained in prepared matrices for auditability but filtered by the prediction loader before modeling.",
        "- CIPI labels come from `evaluation_scores/manifests/cipi/cipi_movement_manifest.csv`; Oktav labels come from the existing labeled Oktav matrix.",
        "",
    ]
    return "\n".join(lines)


def _metrics_markdown(metrics_frame: pd.DataFrame) -> str:
    preferred = [
        "dataset_name",
        "target_scheme",
        "model_family",
        "analyzed_row_count",
        "r2",
        "mae",
        "rmse",
        "pearson",
        "spearman",
        "balanced_accuracy",
        "macro_f1",
        "off_by_one_accuracy",
    ]
    columns = [column for column in preferred if column in metrics_frame.columns]
    display = metrics_frame.loc[:, columns].copy()
    return _frame_to_markdown(display)


def _best_runs_markdown(metrics_frame: pd.DataFrame) -> str:
    rows = []
    for (dataset_name, target_scheme), group in metrics_frame.groupby(["dataset_name", "target_scheme"], dropna=False):
        metric = "r2" if target_scheme == "continuous" else "balanced_accuracy"
        if metric not in group.columns:
            continue
        best = group.sort_values(metric, ascending=False).iloc[0]
        rows.append(
            {
                "dataset_name": dataset_name,
                "target_scheme": target_scheme,
                "selection_metric": metric,
                "model_family": best.get("model_family"),
                "score": best.get(metric),
                "run_dir": best.get("run_dir"),
            }
        )
    return _frame_to_markdown(pd.DataFrame(rows)) if rows else "_No best-run summary available._"


def _frame_to_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    for column in display.columns:
        display[column] = display[column].map(_markdown_cell)
    headers = [str(column) for column in display.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in display.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def _markdown_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _metadata_columns(target_column: str) -> set[str]:
    return {
        "source_row_index",
        "dataset_name",
        "piece_id",
        "piece_uid",
        "title",
        "composer",
        "filename",
        "dataset_relative_path",
        "repo_relative_path",
        "source_path",
        "piece_json_path",
        "status",
        "error_type",
        "message",
        "normalized_filename",
        "cipi_id",
        "movement",
        "work_name",
        "book",
        "uri",
        target_column,
    }


def _allocate_comparison_dir(out_root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = out_root / f"{timestamp}__yan2023-cipi-vs-oktav"
    if not candidate.exists():
        return candidate
    suffix = 2
    while True:
        alternate = out_root / f"{timestamp}__yan2023-cipi-vs-oktav-{suffix}"
        if not alternate.exists():
            return alternate
        suffix += 1


def _read_csv(path: Path) -> pd.DataFrame:
    resolved = Path(path).expanduser()
    if not resolved.is_file():
        raise FileNotFoundError(f"CSV not found: {resolved}")
    return pd.read_csv(resolved)


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _normalized_join_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


if __name__ == "__main__":
    raise SystemExit(main())
