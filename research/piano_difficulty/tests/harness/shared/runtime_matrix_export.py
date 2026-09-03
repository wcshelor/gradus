from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.pipeline import extract_score

MATRIX_METADATA_COLUMNS: tuple[str, ...] = (
    "source_row_index",
    "dataset_name",
    "piece_id",
    "piece_uid",
    "title",
    "composer",
    "filename",
    "dataset_relative_path",
    "repo_relative_path",
    "normalized_filename",
    "source_path",
    "piece_json_path",
    "status",
    "error_type",
    "message",
    "difficulty_numeric",
    "overallDifficulty",
    "henle",
)


@dataclass(frozen=True, slots=True)
class RuntimeExportInput:
    source_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimePieceExportResult:
    source_path: Path
    status: str
    error_type: str
    message: str
    payload_path: Path | None
    payload: dict[str, Any] | None


@dataclass(slots=True)
class RuntimeMatrixExportResult:
    inputs: list[RuntimeExportInput]
    matrix_csv_path: Path
    summary_json_path: Path
    errors_csv_path: Path | None
    piece_json_dir: Path
    failures: list[RuntimePieceExportResult]


def run_runtime_matrix_export(
    inputs: Sequence[RuntimeExportInput],
    *,
    out_dir: str | Path,
    matrix_csv_name: str = "feature_matrix.csv",
    summary_json_name: str = "corpus_summary.json",
    errors_csv_name: str = "errors.csv",
) -> RuntimeMatrixExportResult:
    out_dir_path = Path(out_dir).expanduser()
    out_dir_path.mkdir(parents=True, exist_ok=True)

    matrix_csv_path = out_dir_path / matrix_csv_name
    summary_json_path = out_dir_path / summary_json_name
    errors_csv_path = out_dir_path / errors_csv_name
    piece_json_dir = out_dir_path / "piece_json"
    piece_json_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    failures: list[RuntimePieceExportResult] = []
    for index, export_input in enumerate(inputs):
        row, failure = _run_single_input(
            export_input,
            index=index,
            piece_json_dir=piece_json_dir,
        )
        rows.append(row)
        if failure is not None:
            failures.append(failure)

    _write_matrix_csv(matrix_csv_path, rows)
    _write_summary_json(summary_json_path, rows=rows, failures=failures)
    if failures:
        _write_errors_csv(errors_csv_path, failures)
    else:
        errors_csv_path = None

    return RuntimeMatrixExportResult(
        inputs=list(inputs),
        matrix_csv_path=matrix_csv_path,
        summary_json_path=summary_json_path,
        errors_csv_path=errors_csv_path,
        piece_json_dir=piece_json_dir,
        failures=failures,
    )


def _run_single_input(
    export_input: RuntimeExportInput,
    *,
    index: int,
    piece_json_dir: Path,
) -> tuple[dict[str, Any], RuntimePieceExportResult | None]:
    source_path = Path(export_input.source_path).expanduser()
    base_row = _build_base_row(export_input=export_input, index=index, source_path=source_path)
    piece_uid = str(base_row["piece_uid"]).strip() or f"piece-{index:05d}"
    payload_path = piece_json_dir / f"{index:05d}__{_slugify(piece_uid)}.json"

    try:
        result = extract_score(source_path)
        payload = result.to_json_payload()
        payload_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

        row = dict(base_row)
        row.update(_flatten_feature_records(result.features))
        row.update(
            {
                "status": "success",
                "error_type": "",
                "message": "",
                "piece_json_path": str(payload_path),
            }
        )
        return row, None
    except Exception as exc:  # noqa: BLE001
        failure = RuntimePieceExportResult(
            source_path=source_path,
            status="failure",
            error_type=type(exc).__name__,
            message=_clean_message(str(exc)),
            payload_path=None,
            payload=None,
        )
        row = dict(base_row)
        row.update(
            {
                "status": failure.status,
                "error_type": failure.error_type,
                "message": failure.message,
                "piece_json_path": "",
            }
        )
        return row, failure


def _flatten_feature_records(features: list[FeatureRecord]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for feature in features:
        if feature.scope == "measure":
            continue
        if not isinstance(feature.value, (int, float)) or isinstance(feature.value, bool):
            if isinstance(feature.value, bool):
                value: int | float = int(feature.value)
            else:
                continue
        else:
            value = feature.value

        column_name = _feature_column_name(feature)
        if column_name in row:
            raise ValueError(f"Duplicate runtime matrix column emitted for one score: {column_name}")
        row[column_name] = value
    return row


def _feature_column_name(feature: FeatureRecord) -> str:
    base = feature.feature_id.replace(".", "_")
    if feature.scope == "piece" and feature.scope_ref == "all":
        return base
    if feature.scope == "hand":
        return f"{base}_{_sanitize_token(feature.scope_ref)}"
    return f"{base}_{_sanitize_token(feature.scope)}_{_sanitize_token(feature.scope_ref)}"


def _build_base_row(
    *,
    export_input: RuntimeExportInput,
    index: int,
    source_path: Path,
) -> dict[str, Any]:
    metadata = dict(export_input.metadata)
    row = {column: metadata.get(column, "") for column in MATRIX_METADATA_COLUMNS}
    row.update(
        {
            "source_row_index": metadata.get("source_row_index", index),
            "piece_id": metadata.get("piece_id", source_path.stem),
            "piece_uid": metadata.get("piece_uid", source_path.stem),
            "title": metadata.get("title", source_path.stem),
            "composer": metadata.get("composer", ""),
            "filename": metadata.get("filename", source_path.name),
            "source_path": str(source_path.resolve()),
            "status": "failure",
            "error_type": "",
            "message": "",
            "piece_json_path": "",
        }
    )
    for key, value in metadata.items():
        if key not in row:
            row[key] = value
    return row


def _matrix_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    preferred = list(MATRIX_METADATA_COLUMNS)
    extra_columns = sorted(
        {
            key
            for row in rows
            for key in row.keys()
            if key not in MATRIX_METADATA_COLUMNS and not key.startswith("_")
        }
    )
    feature_columns = sorted(column for column in extra_columns if _is_feature_column(column))
    metadata_columns = sorted(column for column in extra_columns if not _is_feature_column(column))
    return preferred + metadata_columns + feature_columns


def _is_feature_column(column: str) -> bool:
    return column not in MATRIX_METADATA_COLUMNS and (
        "_" in column or column.startswith("metadata")
    )


def _write_matrix_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = _matrix_fieldnames(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in fieldnames})


def _write_summary_json(
    path: Path,
    *,
    rows: list[dict[str, Any]],
    failures: list[RuntimePieceExportResult],
) -> None:
    fieldnames = _matrix_fieldnames(rows)
    feature_columns = [column for column in fieldnames if _is_feature_column(column)]
    payload = {
        "row_count": len(rows),
        "success_count": sum(1 for row in rows if row.get("status") == "success"),
        "failure_count": len(failures),
        "feature_column_count": len(feature_columns),
        "feature_columns": feature_columns,
        "note": "Runtime matrix export writes repo-native feature columns derived from extract_score(...).",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _write_errors_csv(path: Path, failures: list[RuntimePieceExportResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("source_path", "error_type", "message"),
        )
        writer.writeheader()
        for failure in failures:
            writer.writerow(
                {
                    "source_path": str(failure.source_path),
                    "error_type": failure.error_type,
                    "message": failure.message,
                }
            )


def _clean_message(message: str) -> str:
    return " ".join(message.strip().split())


def _slugify(value: str) -> str:
    text = value.strip().replace("\\", "__").replace("/", "__")
    text = "".join(character if character.isalnum() or character in {".", "-", "_"} else "-" for character in text)
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-._")


def _sanitize_token(value: str) -> str:
    text = "".join(character if character.isalnum() or character == "_" else "_" for character in value.strip())
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_") or "value"
