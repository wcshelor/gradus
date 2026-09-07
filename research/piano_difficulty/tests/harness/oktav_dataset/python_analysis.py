from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.harness.shared.dataset_records import to_runtime_export_input
from tests.harness.shared.runtime_matrix_export import (
    RuntimeExportInput,
    run_runtime_matrix_export,
)

from .catalog import load_oktav_dataset

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "oktav_dataset" / "python_analysis" / "full_run"
DEFAULT_LABEL_SOURCE_CSV = DEFAULT_OUT_DIR / "oktav_labeled_feature_matrix.csv"


def build_export_inputs(
    dataset_root: str | Path | None = None,
    *,
    label_source_csv: str | Path | None = DEFAULT_LABEL_SOURCE_CSV,
    legacy_label_source_csv: str | Path | None = None,
    limit: int | None = None,
) -> list[RuntimeExportInput]:
    label_source = label_source_csv if label_source_csv is not None else legacy_label_source_csv
    result = load_oktav_dataset(dataset_root=dataset_root, label_source=label_source)
    records = result.records
    if limit is not None:
        records = records[: max(0, int(limit))]
    return [to_runtime_export_input(record, source_row_index=index) for index, record in enumerate(records)]


def run_oktav_python_analysis(
    *,
    dataset_root: str | Path | None = None,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    label_source_csv: str | Path | None = DEFAULT_LABEL_SOURCE_CSV,
    legacy_label_source_csv: str | Path | None = None,
    limit: int | None = None,
    write_load_report: bool = True,
) -> dict[str, Any]:
    label_source = label_source_csv if label_source_csv is not None else legacy_label_source_csv
    load_result = load_oktav_dataset(dataset_root=dataset_root, label_source=label_source)
    records = load_result.records
    limited = limit is not None
    if limit is not None:
        records = records[: max(0, int(limit))]
    inputs = [to_runtime_export_input(record, source_row_index=index) for index, record in enumerate(records)]
    result = run_runtime_matrix_export(
        inputs,
        out_dir=out_dir,
        matrix_csv_name="oktav_labeled_feature_matrix.csv",
        summary_json_name="corpus_summary.json",
        errors_csv_name="errors.csv",
    )
    load_report_path: str | None = None
    if write_load_report:
        out_path = Path(out_dir).expanduser()
        out_path.mkdir(parents=True, exist_ok=True)
        report_path = out_path / "load_report.json"
        report_path.write_text(
            json.dumps(load_result.to_dict(), indent=2, sort_keys=True) + "\n"
        )
        load_report_path = str(report_path)
    summary: dict[str, Any] = {
        "matrix_csv_path": str(result.matrix_csv_path),
        "summary_json_path": str(result.summary_json_path),
        "errors_csv_path": str(result.errors_csv_path) if result.errors_csv_path else None,
        "piece_json_dir": str(result.piece_json_dir),
        "input_count": len(result.inputs),
        "success_count": len(result.inputs) - len(result.failures),
        "failure_count": len(result.failures),
        "label_source_csv": str(Path(label_source).expanduser()) if label_source else None,
        "load_report_path": load_report_path,
        "load_summary": load_result.summary,
    }
    if limited:
        summary["limited"] = True
        summary["limit"] = int(limit) if limit is not None else None
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_oktav_python_analysis",
        description="Run repo-native feature extraction over the Oktav corpus and export a labeled matrix CSV.",
    )
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--label-source-csv", type=Path, default=DEFAULT_LABEL_SOURCE_CSV)
    parser.add_argument(
        "--legacy-label-source-csv",
        type=Path,
        default=None,
        help="Legacy fallback: read labels from a previously generated matrix. "
        "Prefer --label-source-csv; generated matrices are outputs, not canonical labels.",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fail-on-missing", action="store_true")
    parser.add_argument("--write-load-report", action="store_true", default=True)
    parser.add_argument("--no-write-load-report", dest="write_load_report", action="store_false")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_oktav_python_analysis(
        dataset_root=args.dataset_root,
        out_dir=args.out_dir,
        label_source_csv=args.label_source_csv,
        legacy_label_source_csv=args.legacy_label_source_csv,
        limit=args.limit,
        write_load_report=args.write_load_report,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["failure_count"]:
        return 1
    if args.fail_on_missing and summary["load_summary"].get("unmatched_score_count"):
        return 1
    return 0
