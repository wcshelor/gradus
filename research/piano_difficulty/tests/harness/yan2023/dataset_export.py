from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from tests.harness.yan2023.extractor import extract_first_pass_from_path
from tests.harness.yan2023.slot_inventory import WORKING_FEATURE_SLOTS

SUPPORTED_SCORE_SUFFIXES = {".xml", ".musicxml", ".mxl"}
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tests" / "artifacts" / "yan2023" / "dataset_exports"


@dataclass(frozen=True, slots=True)
class DatasetExportSpec:
    dataset_name: str
    dataset_root: Path
    out_dir: Path
    label_csv: Path | None = None
    label_join_column: str = "piece_id"
    label_value_column: str | None = None


@dataclass(frozen=True, slots=True)
class YanDatasetExportResult:
    dataset_name: str
    dataset_root: Path
    matrix_csv_path: Path
    summary_json_path: Path
    errors_csv_path: Path | None
    skipped_csv_path: Path | None
    piece_json_dir: Path
    log_dir: Path
    inputs: list[Path] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)


def discover_score_files(source_root: str | Path) -> list[Path]:
    root = Path(source_root).expanduser()
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset root not found: {root}")
    return sorted(
        [
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SCORE_SUFFIXES
        ],
        key=lambda path: str(path),
    )


def run_yan_dataset_export(
    spec: DatasetExportSpec,
    *,
    include_diagnostics: bool = True,
    workers: int | None = None,
    timeout_seconds: float = 15.0,
) -> YanDatasetExportResult:
    score_paths = discover_score_files(spec.dataset_root)
    spec.out_dir.mkdir(parents=True, exist_ok=True)
    piece_json_dir = spec.out_dir / "piece_json"
    log_dir = spec.out_dir / "logs"
    piece_json_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    label_lookup, label_column_name = _load_label_lookup(
        spec.label_csv,
        join_column=spec.label_join_column,
        value_column=spec.label_value_column,
    )

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    worker_count = workers if workers is not None else _default_worker_count()
    jobs = list(enumerate(score_paths))
    if worker_count <= 1 or len(jobs) < 2:
        results = (
            _extract_score_job(
                index=index,
                source_path=source_path,
                dataset_root=spec.dataset_root,
                dataset_name=spec.dataset_name,
                label_lookup=label_lookup,
                label_join_column=spec.label_join_column,
                label_column_name=label_column_name,
                include_diagnostics=include_diagnostics,
            )
            for index, source_path in jobs
        )
    else:
        results = _map_score_jobs(
            jobs,
            dataset_root=spec.dataset_root,
            dataset_name=spec.dataset_name,
            label_lookup=label_lookup,
            label_join_column=spec.label_join_column,
            label_column_name=label_column_name,
            include_diagnostics=include_diagnostics,
            timeout_seconds=timeout_seconds,
            max_workers=worker_count,
        )

    for row, failure, payload in results:
        if payload is not None:
            piece_json_path = piece_json_dir / f"{int(row['source_row_index']):05d}__{row['piece_uid']}.json"
            payload["piece_json_path"] = str(piece_json_path)
            piece_json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
            row["piece_json_path"] = str(piece_json_path)
        rows.append(row)
        if failure is not None:
            failures.append(failure)
            skipped.append(failure)

    matrix_csv_path = spec.out_dir / "yan_features.csv"
    summary_json_path = spec.out_dir / "corpus_summary.json"
    errors_csv_path = spec.out_dir / "errors.csv" if failures else None
    skipped_csv_path = spec.out_dir / "skipped.csv" if skipped else None
    _write_matrix_csv(matrix_csv_path, rows)
    _write_summary_json(
        summary_json_path,
        dataset_name=spec.dataset_name,
        dataset_root=spec.dataset_root,
        rows=rows,
        failures=failures,
        skipped=skipped,
        label_csv=spec.label_csv,
        label_join_column=spec.label_join_column,
        label_value_column=label_column_name,
        timeout_seconds=timeout_seconds,
    )
    if failures:
        _write_errors_csv(errors_csv_path, failures)
    if skipped:
        _write_skipped_csv(skipped_csv_path, skipped)

    return YanDatasetExportResult(
        dataset_name=spec.dataset_name,
        dataset_root=spec.dataset_root,
        matrix_csv_path=matrix_csv_path,
        summary_json_path=summary_json_path,
        errors_csv_path=errors_csv_path,
        skipped_csv_path=skipped_csv_path,
        piece_json_dir=piece_json_dir,
        log_dir=log_dir,
        inputs=score_paths,
        failures=failures,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_yan2023_dataset_export",
        description="Run the current Yan 2023 extractor over one or more dataset roots.",
    )
    parser.add_argument(
        "--dataset",
        action="append",
        choices=("cipi", "oktav-starting"),
        help="Dataset to export. Omit to export both default datasets.",
    )
    parser.add_argument(
        "--cipi-root",
        type=Path,
        default=Path("~/desktop/oktav-thesis/datasets/cipi").expanduser(),
        help="Path to the local CIPI corpus root.",
    )
    parser.add_argument(
        "--oktav-root",
        type=Path,
        default=Path("~/desktop/oktav-thesis/datasets/oktav-starting-dataset").expanduser(),
        help="Path to the local Oktav-starting corpus root.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory under which per-dataset Yan exports will be written.",
    )
    parser.add_argument(
        "--cipi-labels-csv",
        type=Path,
        default=None,
        help="Optional CIPI label manifest to join into the feature matrix.",
    )
    parser.add_argument(
        "--oktav-labels-csv",
        type=Path,
        default=None,
        help="Optional Oktav label manifest to join into the feature matrix.",
    )
    parser.add_argument(
        "--cipi-label-column",
        type=str,
        default="henle",
        help="Label column to join for CIPI if a manifest is provided.",
    )
    parser.add_argument(
        "--oktav-label-column",
        type=str,
        default="difficulty_numeric",
        help="Label column to join for Oktav-starting if a manifest is provided.",
    )
    parser.add_argument(
        "--label-join-column",
        type=str,
        default="piece_id",
        help="Column used to join labels from an external manifest.",
    )
    parser.add_argument(
        "--no-diagnostics",
        action="store_true",
        help="Skip writing the per-piece diagnostics payload into the JSON sidecars.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes to use per dataset. Defaults to all available CPUs.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=15.0,
        help="Per-piece timeout for Yan extraction subprocesses.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dataset_names = tuple(args.dataset or ("cipi", "oktav-starting"))
    specs = []
    for dataset_name in dataset_names:
        if dataset_name == "cipi":
            specs.append(
                DatasetExportSpec(
                    dataset_name="cipi",
                    dataset_root=args.cipi_root,
                    out_dir=args.out_root / "cipi",
                    label_csv=args.cipi_labels_csv,
                    label_join_column=args.label_join_column,
                    label_value_column=args.cipi_label_column if args.cipi_labels_csv else None,
                )
            )
        elif dataset_name == "oktav-starting":
            specs.append(
                DatasetExportSpec(
                    dataset_name="oktav-starting",
                    dataset_root=args.oktav_root,
                    out_dir=args.out_root / "oktav-starting",
                    label_csv=args.oktav_labels_csv,
                    label_join_column=args.label_join_column,
                    label_value_column=args.oktav_label_column if args.oktav_labels_csv else None,
                )
            )

    summaries = [
        _result_to_summary(
            run_yan_dataset_export(
                spec,
                include_diagnostics=not args.no_diagnostics,
                workers=args.workers,
                timeout_seconds=args.timeout_seconds,
            )
        )
        for spec in specs
    ]
    print(
        json.dumps(
            {
                "datasets": summaries,
                "default_output_root": str(args.out_root.expanduser()),
                "note": "Yan extraction uses per-piece subprocess timeouts and logs skipped files.",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if any(summary["failure_count"] for summary in summaries) else 0


def _map_score_jobs(
    jobs: list[tuple[int, Path]],
    *,
    dataset_root: Path,
    dataset_name: str,
    label_lookup: dict[str, Any] | None,
    label_join_column: str,
    label_column_name: str | None,
    include_diagnostics: bool,
    timeout_seconds: float,
    max_workers: int,
):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        yield from executor.map(
            _extract_score_job_subprocess,
            (
                {
                    "index": index,
                    "source_path": str(source_path),
                    "dataset_root": str(dataset_root),
                    "dataset_name": dataset_name,
                    "label_lookup": label_lookup,
                    "label_join_column": label_join_column,
                    "label_column_name": label_column_name,
                    "include_diagnostics": include_diagnostics,
                    "timeout_seconds": timeout_seconds,
                }
                for index, source_path in jobs
            ),
        )


def _extract_score_job_subprocess(job: dict[str, Any]):
    source_path = Path(job["source_path"])
    dataset_root = Path(job["dataset_root"])
    dataset_name = str(job["dataset_name"])
    include_diagnostics = bool(job["include_diagnostics"])
    timeout_seconds = float(job["timeout_seconds"])
    label_lookup = job["label_lookup"]
    label_join_column = str(job["label_join_column"])
    label_column_name = job["label_column_name"]

    command = [
        sys.executable,
        str(REPO_ROOT / "tests" / "scripts" / "run_yan2023_extract_features.py"),
        str(source_path),
        "--format",
        "json",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return _failure_from_timeout(
            source_path=source_path,
            index=int(job["index"]),
            dataset_root=dataset_root,
            dataset_name=dataset_name,
            timeout_seconds=timeout_seconds,
            stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else None,
        )
    if completed.returncode != 0:
        return _failure_from_subprocess(
            source_path=source_path,
            index=int(job["index"]),
            dataset_root=dataset_root,
            dataset_name=dataset_name,
            stderr=completed.stderr or completed.stdout,
        )

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return _failure_from_subprocess(
            source_path=source_path,
            index=int(job["index"]),
            dataset_root=dataset_root,
            dataset_name=dataset_name,
            stderr=f"JSONDecodeError: {exc}\n{completed.stdout}",
        )

    values = payload.get("values", [])
    row, failure = _build_row_from_values(
        source_path=source_path,
        index=int(job["index"]),
        dataset_root=dataset_root,
        dataset_name=dataset_name,
        values=values,
        label_lookup=label_lookup,
        label_join_column=label_join_column,
        label_column_name=label_column_name,
    )
    if failure is not None:
        return row, failure, None

    if not include_diagnostics:
        for value in values:
            if isinstance(value, dict):
                value["diagnostics"] = []
    payload["values"] = values
    return row, None, payload


def _extract_score_job(job: dict[str, Any]):
    return _run_single_score(
        Path(job["source_path"]),
        index=int(job["index"]),
        dataset_root=Path(job["dataset_root"]),
        dataset_name=str(job["dataset_name"]),
        label_lookup=job["label_lookup"],
        label_join_column=str(job["label_join_column"]),
        label_column_name=job["label_column_name"],
        include_diagnostics=bool(job["include_diagnostics"]),
    )


def _run_single_score(
    source_path: Path,
    *,
    index: int,
    dataset_root: Path,
    dataset_name: str,
    label_lookup: dict[str, Any] | None,
    label_join_column: str,
    label_column_name: str | None,
    include_diagnostics: bool,
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    source_path = Path(source_path).expanduser()
    dataset_root = Path(dataset_root).expanduser()
    piece_uid = _piece_uid_from_path(source_path, dataset_root=dataset_root)
    piece_id = _piece_id_from_path(source_path, dataset_root=dataset_root)
    dataset_relative_path = _relative_path(source_path, dataset_root)
    repo_relative_path = _relative_path(source_path, REPO_ROOT)

    base_row: dict[str, Any] = {
        "source_row_index": index,
        "dataset_name": dataset_name,
        "piece_id": piece_id,
        "piece_uid": piece_uid,
        "title": source_path.stem,
        "composer": _composer_from_path(source_path),
        "filename": source_path.name,
        "dataset_relative_path": dataset_relative_path,
        "repo_relative_path": repo_relative_path,
        "source_path": str(source_path),
        "status": "failure",
        "error_type": "",
        "message": "",
        "piece_json_path": "",
    }

    try:
        _score, values = extract_first_pass_from_path(source_path)
        for slot in WORKING_FEATURE_SLOTS:
            base_row[slot.slot_id] = None
        for value in values:
            base_row[value.slot_id] = value.value
        if label_lookup is not None and label_column_name is not None:
            lookup_key = _label_join_value(base_row, label_join_column)
            base_row[label_column_name] = label_lookup.get(lookup_key)
        base_row["status"] = "success"
        payload = {
            "source_path": str(source_path),
            "dataset_name": dataset_name,
            "piece_id": piece_id,
            "piece_uid": piece_uid,
            "status": "success",
            "values": [
                value.to_payload() if include_diagnostics else _strip_diagnostics(value.to_payload())
                for value in values
            ],
        }
        return base_row, None, payload
    except Exception as exc:  # pragma: no cover - exercised by batch runs
        message = f"{exc.__class__.__name__}: {exc}"
        base_row["error_type"] = exc.__class__.__name__
        base_row["message"] = message
        for slot in WORKING_FEATURE_SLOTS:
            base_row.setdefault(slot.slot_id, None)
        failure = {
            "source_row_index": index,
            "piece_id": piece_id,
            "piece_uid": piece_uid,
            "source_path": str(source_path),
            "error_type": exc.__class__.__name__,
            "message": message,
        }
        return base_row, failure, None


def _build_row_from_values(
    *,
    source_path: Path,
    index: int,
    dataset_root: Path,
    dataset_name: str,
    values: list[dict[str, Any]],
    label_lookup: dict[str, Any] | None,
    label_join_column: str,
    label_column_name: str | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    source_path = Path(source_path).expanduser()
    dataset_root = Path(dataset_root).expanduser()
    piece_uid = _piece_uid_from_path(source_path, dataset_root=dataset_root)
    piece_id = _piece_id_from_path(source_path, dataset_root=dataset_root)
    dataset_relative_path = _relative_path(source_path, dataset_root)
    repo_relative_path = _relative_path(source_path, REPO_ROOT)

    base_row: dict[str, Any] = {
        "source_row_index": index,
        "dataset_name": dataset_name,
        "piece_id": piece_id,
        "piece_uid": piece_uid,
        "title": source_path.stem,
        "composer": _composer_from_path(source_path),
        "filename": source_path.name,
        "dataset_relative_path": dataset_relative_path,
        "repo_relative_path": repo_relative_path,
        "source_path": str(source_path),
        "status": "success",
        "error_type": "",
        "message": "",
        "piece_json_path": "",
    }

    for slot in WORKING_FEATURE_SLOTS:
        base_row[slot.slot_id] = None
    for value in values:
        slot_id = value.get("slot_id")
        if slot_id in base_row:
            base_row[slot_id] = value.get("value")
    if label_lookup is not None and label_column_name is not None:
        lookup_key = _label_join_value(base_row, label_join_column)
        base_row[label_column_name] = label_lookup.get(lookup_key)
    return base_row, None


def _failure_from_subprocess(
    *,
    source_path: Path,
    index: int,
    dataset_root: Path,
    dataset_name: str,
    stderr: str | None,
) -> tuple[dict[str, Any], dict[str, Any], None]:
    source_path = Path(source_path).expanduser()
    dataset_root = Path(dataset_root).expanduser()
    piece_uid = _piece_uid_from_path(source_path, dataset_root=dataset_root)
    piece_id = _piece_id_from_path(source_path, dataset_root=dataset_root)
    row = {
        "source_row_index": index,
        "dataset_name": dataset_name,
        "piece_id": piece_id,
        "piece_uid": piece_uid,
        "title": source_path.stem,
        "composer": _composer_from_path(source_path),
        "filename": source_path.name,
        "dataset_relative_path": _relative_path(source_path, dataset_root),
        "repo_relative_path": _relative_path(source_path, REPO_ROOT),
        "source_path": str(source_path),
        "status": "failure",
        "error_type": "SubprocessError",
        "message": stderr or "Yan extraction subprocess failed.",
        "piece_json_path": "",
    }
    for slot in WORKING_FEATURE_SLOTS:
        row[slot.slot_id] = None
    failure = {
        "source_row_index": index,
        "piece_id": piece_id,
        "piece_uid": piece_uid,
        "source_path": str(source_path),
        "error_type": "SubprocessError",
        "message": stderr or "Yan extraction subprocess failed.",
    }
    return row, failure, None


def _default_worker_count() -> int:
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count)


def _failure_from_timeout(
    *,
    source_path: Path,
    index: int,
    dataset_root: Path,
    dataset_name: str,
    timeout_seconds: float,
    stderr: str | None,
) -> tuple[dict[str, Any], dict[str, Any], None]:
    source_path = Path(source_path).expanduser()
    dataset_root = Path(dataset_root).expanduser()
    piece_uid = _piece_uid_from_path(source_path, dataset_root=dataset_root)
    piece_id = _piece_id_from_path(source_path, dataset_root=dataset_root)
    row = {
        "source_row_index": index,
        "dataset_name": dataset_name,
        "piece_id": piece_id,
        "piece_uid": piece_uid,
        "title": source_path.stem,
        "composer": _composer_from_path(source_path),
        "filename": source_path.name,
        "dataset_relative_path": _relative_path(source_path, dataset_root),
        "repo_relative_path": _relative_path(source_path, REPO_ROOT),
        "source_path": str(source_path),
        "status": "timeout",
        "error_type": "TimeoutError",
        "message": f"Yan extraction exceeded {timeout_seconds:.1f} seconds.",
        "piece_json_path": "",
    }
    for slot in WORKING_FEATURE_SLOTS:
        row[slot.slot_id] = None
    if stderr:
        row["message"] = f"{row['message']} {stderr.strip()}"
    failure = {
        "source_row_index": index,
        "piece_id": piece_id,
        "piece_uid": piece_uid,
        "source_path": str(source_path),
        "error_type": "TimeoutError",
        "message": row["message"],
    }
    return row, failure, None


def _write_matrix_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = _matrix_fieldnames(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_errors_csv(path: Path | None, failures: list[dict[str, Any]]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        "source_row_index",
        "piece_id",
        "piece_uid",
        "source_path",
        "error_type",
        "message",
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(failures)


def _write_skipped_csv(path: Path | None, skipped: list[dict[str, Any]]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = (
        "source_row_index",
        "piece_id",
        "piece_uid",
        "source_path",
        "error_type",
        "message",
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(skipped)


def _write_summary_json(
    path: Path,
    *,
    dataset_name: str,
    dataset_root: Path,
    rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    label_csv: Path | None,
    label_join_column: str,
    label_value_column: str | None,
    timeout_seconds: float,
) -> None:
    payload = {
        "dataset_name": dataset_name,
        "dataset_root": str(dataset_root.expanduser()),
        "row_count": len(rows),
        "success_count": sum(1 for row in rows if row.get("status") == "success"),
        "failure_count": len(failures),
        "skipped_count": len(skipped),
        "feature_column_count": len(WORKING_FEATURE_SLOTS),
        "feature_columns": [slot.slot_id for slot in WORKING_FEATURE_SLOTS],
        "label_csv": str(label_csv.expanduser()) if label_csv else None,
        "label_join_column": label_join_column,
        "label_value_column": label_value_column,
        "timeout_seconds": timeout_seconds,
        "note": "Yan extraction uses per-piece subprocess timeouts and logs skipped files.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _matrix_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    preferred = [
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
    ]
    feature_columns = [slot.slot_id for slot in WORKING_FEATURE_SLOTS]
    extra_columns = sorted(
        {
            key
            for row in rows
            for key in row.keys()
            if key not in preferred and key not in feature_columns
        }
    )
    return preferred + feature_columns + extra_columns


def _load_label_lookup(
    label_csv: Path | None,
    *,
    join_column: str,
    value_column: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if label_csv is None:
        return None, None

    frame = pd.read_csv(label_csv)
    if join_column not in frame.columns:
        raise ValueError(
            f"Label manifest {label_csv} does not contain join column {join_column!r}."
        )

    resolved_value_column = value_column
    if resolved_value_column is None:
        candidate_columns = [column for column in frame.columns if column != join_column]
        if len(candidate_columns) != 1:
            available = ", ".join(str(column) for column in frame.columns)
            raise ValueError(
                f"Label manifest {label_csv} needs exactly one non-join column when no label value column is supplied. "
                f"Available columns: {available}."
            )
        resolved_value_column = candidate_columns[0]
    if resolved_value_column not in frame.columns:
        raise ValueError(
            f"Label manifest {label_csv} does not contain label column {resolved_value_column!r}."
        )

    lookup = {
        str(key): value
        for key, value in zip(frame[join_column].astype(str), frame[resolved_value_column])
    }
    return lookup, resolved_value_column


def _result_to_summary(result: YanDatasetExportResult) -> dict[str, Any]:
    return {
        "dataset_name": result.dataset_name,
        "dataset_root": str(result.dataset_root),
        "matrix_csv_path": str(result.matrix_csv_path),
        "summary_json_path": str(result.summary_json_path),
        "errors_csv_path": str(result.errors_csv_path) if result.errors_csv_path else None,
        "skipped_csv_path": str(result.skipped_csv_path) if result.skipped_csv_path else None,
        "input_count": len(result.inputs),
        "success_count": len(result.inputs) - len(result.failures),
        "failure_count": len(result.failures),
        "skipped_count": len(result.failures),
        "piece_json_dir": str(result.piece_json_dir),
        "log_dir": str(result.log_dir),
    }


def _piece_uid_from_path(path: Path, *, dataset_root: Path) -> str:
    relative = _relative_path(path, dataset_root)
    return _sanitize_id(Path(relative).with_suffix("").as_posix())


def _piece_id_from_path(path: Path, *, dataset_root: Path) -> str:
    relative = _relative_path(path, dataset_root)
    match = re.search(r"(OK\d{5})", relative, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return _sanitize_id(Path(relative).with_suffix("").name)


def _composer_from_path(path: Path) -> str:
    if path.parent == path:
        return ""
    return path.parent.name


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _sanitize_id(value: str) -> str:
    text = value.strip()
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "piece"


def _label_join_value(row: dict[str, Any], join_column: str) -> str:
    if join_column not in row:
        raise KeyError(
            f"Cannot join labels on {join_column!r} because the export row does not contain that column."
        )
    return str(row[join_column]).strip()


def _strip_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    stripped = dict(payload)
    stripped["diagnostics"] = []
    return stripped
