from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.harness.shared.dataset_records import to_runtime_export_input
from tests.harness.shared.runtime_matrix_export import run_runtime_matrix_export

from .catalog import DEFAULT_MOVEMENT_MANIFEST_CSV, load_cipi_dataset

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "cipi_dataset" / "python_analysis" / "full_run"
DEFAULT_MATRIX_CSV_NAME = "cipi_labeled_feature_matrix.csv"


def build_export_inputs(
    *,
    dataset_root: str | Path | None = None,
    manifest_csv: str | Path = DEFAULT_MOVEMENT_MANIFEST_CSV,
    limit: int | None = None,
):
    result = load_cipi_dataset(dataset_root=dataset_root, manifest_csv=manifest_csv)
    records = [record for record in result.records if Path(record.source_path).is_file()]
    if limit is not None:
        records = records[: max(0, int(limit))]
    return [to_runtime_export_input(record, source_row_index=index) for index, record in enumerate(records)]


def run_cipi_python_analysis(
    *,
    dataset_root: str | Path | None = None,
    manifest_csv: str | Path = DEFAULT_MOVEMENT_MANIFEST_CSV,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    limit: int | None = None,
    write_load_report: bool = True,
) -> dict[str, Any]:
    load_result = load_cipi_dataset(dataset_root=dataset_root, manifest_csv=manifest_csv)
    exportable_before_limit = [record for record in load_result.records if Path(record.source_path).is_file()]
    skipped_missing_count = len(load_result.records) - len(exportable_before_limit)
    exportable = exportable_before_limit
    limited = limit is not None
    if limit is not None:
        exportable = exportable_before_limit[: max(0, int(limit))]
    inputs = [to_runtime_export_input(record, source_row_index=index) for index, record in enumerate(exportable)]
    result = run_runtime_matrix_export(
        inputs,
        out_dir=out_dir,
        matrix_csv_name=DEFAULT_MATRIX_CSV_NAME,
        summary_json_name="corpus_summary.json",
        errors_csv_name="errors.csv",
    )
    load_report_path: str | None = None
    if write_load_report:
        out_path = Path(out_dir).expanduser()
        out_path.mkdir(parents=True, exist_ok=True)
        report_path = out_path / "load_report.json"
        report_path.write_text(json.dumps(load_result.to_dict(), indent=2, sort_keys=True) + "\n")
        load_report_path = str(report_path)
    summary: dict[str, Any] = {
        "matrix_csv_path": str(result.matrix_csv_path),
        "summary_json_path": str(result.summary_json_path),
        "errors_csv_path": str(result.errors_csv_path) if result.errors_csv_path else None,
        "piece_json_dir": str(result.piece_json_dir),
        "input_count": len(result.inputs),
        "success_count": len(result.inputs) - len(result.failures),
        "failure_count": len(result.failures),
        "manifest_csv": str(Path(manifest_csv).expanduser()),
        "dataset_root": load_result.summary.get("dataset_root"),
        "dataset_root_source": load_result.summary.get("dataset_root_source"),
        "skipped_missing_count": skipped_missing_count,
        "load_report_path": load_report_path,
        "load_summary": load_result.summary,
    }
    if limited:
        summary["limited"] = True
        summary["limit"] = int(limit) if limit is not None else None
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_cipi_python_analysis",
        description="Run repo-native feature extraction over the CIPI corpus and export a labeled matrix CSV.",
    )
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--manifest-csv", type=Path, default=DEFAULT_MOVEMENT_MANIFEST_CSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fail-on-missing", action="store_true")
    parser.add_argument("--write-load-report", action="store_true", default=True)
    parser.add_argument("--no-write-load-report", dest="write_load_report", action="store_false")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_cipi_python_analysis(
        dataset_root=args.dataset_root,
        manifest_csv=args.manifest_csv,
        out_dir=args.out_dir,
        limit=args.limit,
        write_load_report=args.write_load_report,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["failure_count"]:
        return 1
    if args.fail_on_missing and summary["skipped_missing_count"]:
        return 1
    return 0
