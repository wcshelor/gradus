from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from tests.harness.scoreanalyzer.scoreanalyzer_export import discover_score_files
from tests.harness.shared.runtime_matrix_export import (
    RuntimeExportInput,
    run_runtime_matrix_export,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "ad_hoc" / "oktav_starting_dataset"
DEFAULT_OUT_DIR = REPO_ROOT / "tests" / "artifacts" / "oktav_dataset" / "python_analysis" / "full_run"
DEFAULT_LABEL_SOURCE_CSV = DEFAULT_OUT_DIR / "oktav_labeled_feature_matrix.csv"


def build_export_inputs(
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    *,
    label_source_csv: str | Path | None = DEFAULT_LABEL_SOURCE_CSV,
) -> list[RuntimeExportInput]:
    dataset_root_path = Path(dataset_root).expanduser()
    label_lookup = _load_label_lookup(Path(label_source_csv).expanduser() if label_source_csv else None)
    source_paths = discover_score_files(dataset_root_path)
    inputs: list[RuntimeExportInput] = []
    for source_path in source_paths:
        dataset_relative_path = _relative_path(source_path, dataset_root_path)
        normalized_filename = _normalized_join_key(source_path.name)
        metadata = {
            "dataset_name": "oktav",
            "piece_id": _piece_id_from_path(source_path),
            "piece_uid": _piece_uid_from_path(source_path, dataset_root=dataset_root_path),
            "title": source_path.stem,
            "composer": "",
            "filename": source_path.name,
            "dataset_relative_path": dataset_relative_path,
            "repo_relative_path": _relative_path(source_path, REPO_ROOT),
            "normalized_filename": normalized_filename,
            "difficulty_numeric": label_lookup.get(dataset_relative_path, label_lookup.get(normalized_filename, "")),
        }
        inputs.append(RuntimeExportInput(source_path=source_path, metadata=metadata))
    return inputs


def run_oktav_python_analysis(
    *,
    dataset_root: str | Path = DEFAULT_DATASET_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    label_source_csv: str | Path | None = DEFAULT_LABEL_SOURCE_CSV,
) -> dict[str, Any]:
    inputs = build_export_inputs(dataset_root, label_source_csv=label_source_csv)
    result = run_runtime_matrix_export(
        inputs,
        out_dir=out_dir,
        matrix_csv_name="oktav_labeled_feature_matrix.csv",
        summary_json_name="corpus_summary.json",
        errors_csv_name="errors.csv",
    )
    return {
        "matrix_csv_path": str(result.matrix_csv_path),
        "summary_json_path": str(result.summary_json_path),
        "errors_csv_path": str(result.errors_csv_path) if result.errors_csv_path else None,
        "piece_json_dir": str(result.piece_json_dir),
        "input_count": len(result.inputs),
        "success_count": len(result.inputs) - len(result.failures),
        "failure_count": len(result.failures),
        "label_source_csv": str(Path(label_source_csv).expanduser()) if label_source_csv else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_oktav_python_analysis",
        description="Run repo-native feature extraction over the Oktav corpus and export a labeled matrix CSV.",
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--label-source-csv", type=Path, default=DEFAULT_LABEL_SOURCE_CSV)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_oktav_python_analysis(
        dataset_root=args.dataset_root,
        out_dir=args.out_dir,
        label_source_csv=args.label_source_csv,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failure_count"] else 0


def _load_label_lookup(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}

    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    lookup: dict[str, Any] = {}
    for row in rows:
        label = str(row.get("difficulty_numeric", "")).strip()
        if not label:
            continue

        dataset_relative_path = str(row.get("dataset_relative_path", "")).strip()
        if dataset_relative_path and dataset_relative_path not in lookup:
            lookup[dataset_relative_path] = label

        filename = str(row.get("filename", "")).strip()
        if filename:
            normalized_filename = _normalized_join_key(filename)
            if normalized_filename and normalized_filename not in lookup:
                lookup[normalized_filename] = label
    return lookup


def _piece_id_from_path(path: Path) -> str:
    stem = path.stem
    match = re.search(r"(OK\d{5})", stem, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return stem


def _piece_uid_from_path(path: Path, *, dataset_root: Path) -> str:
    relative = _relative_path(path, dataset_root)
    candidate = Path(relative).with_suffix("").as_posix()
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or path.stem


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _normalized_join_key(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")
