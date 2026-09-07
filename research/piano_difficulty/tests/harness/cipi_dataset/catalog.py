from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tests.harness.shared.dataset_config import DatasetSpec, resolve_dataset_root
from tests.harness.shared.dataset_discovery import dataset_relative_path, normalize_filename, repo_relative_path
from tests.harness.shared.dataset_records import DatasetLoadResult, DatasetRecord
from tests.harness.shared.dataset_validation import (
    build_load_summary,
    compare_manifest_paths_to_discovered,
    duplicate_piece_uids,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "known_levels" / "cipi"
DEFAULT_INDEX_JSON = REPO_ROOT / "evaluation_scores" / "known_levels" / "henle" / "cipi_index.json"
DEFAULT_MOVEMENT_MANIFEST_CSV = REPO_ROOT / "evaluation_scores" / "manifests" / "cipi" / "cipi_movement_manifest.csv"
DEFAULT_CATALOG_CSV = DEFAULT_MOVEMENT_MANIFEST_CSV
LEGACY_CATALOG_CSV = REPO_ROOT / "evaluation_scores" / "manifests" / "cipi_dataset_catalog.csv"


@dataclass(frozen=True, slots=True)
class CipiCatalogResult:
    rows: list[dict[str, Any]]
    missing_files: tuple[str, ...]
    extra_files: tuple[str, ...]


def load_catalog_dataframe(path: str | Path | None = None) -> pd.DataFrame:
    csv_path = Path(path or DEFAULT_CATALOG_CSV).expanduser()
    if not csv_path.is_file():
        raise FileNotFoundError(f"CIPI catalog CSV not found: {csv_path}")
    return pd.read_csv(csv_path)


load_movement_manifest = load_catalog_dataframe


def load_index_json(path: str | Path | None = None) -> dict[str, Any]:
    index_path = Path(path or DEFAULT_INDEX_JSON).expanduser()
    payload = json.loads(index_path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"CIPI index JSON must decode to an object: {index_path}")
    return {str(key): value for key, value in payload.items()}


def build_catalog(
    dataset_root: str | Path,
    index_json: dict[str, Any],
    repo_root: str | Path | None = None,
) -> CipiCatalogResult:
    """Legacy work-level catalog builder.

    Retained for compatibility with older generated-catalog workflows. New code
    should use :func:`load_cipi_dataset`, which loads the canonical
    movement-level manifest.
    """
    dataset_root_path = Path(dataset_root).expanduser().resolve()
    repo_root_path = Path(repo_root or REPO_ROOT).expanduser().resolve()
    dataset_index = _build_dataset_index(dataset_root_path)

    rows: list[dict[str, Any]] = []
    matched_paths: set[str] = set()
    for score_id, record in sorted(index_json.items()):
        if not isinstance(record, dict):
            continue
        resolved_path = _resolve_score_path(dataset_index, record)
        title = _clean_text(record.get("title"))
        composer = _clean_text(record.get("composer"))
        henle = record.get("henle")
        relative_path = ""
        repo_relative = ""
        filename = ""
        if resolved_path is not None:
            matched_paths.add(resolved_path.as_posix())
            relative_path = _relative_path(resolved_path, dataset_root_path)
            repo_relative = _relative_path(resolved_path, repo_root_path)
            filename = resolved_path.name
        rows.append(
            {
                "score_id": str(score_id),
                "title": title,
                "composer": composer,
                "henle": henle,
                "dataset_relative_path": relative_path,
                "repo_relative_path": repo_relative,
                "filename": filename,
            }
        )

    extra_files = sorted(set(dataset_index) - matched_paths)
    missing_files = sorted(row["score_id"] for row in rows if not row["dataset_relative_path"])
    return CipiCatalogResult(
        rows=rows,
        missing_files=tuple(missing_files),
        extra_files=tuple(extra_files),
    )


def load_cipi_dataset(
    spec: DatasetSpec | None = None,
    *,
    dataset_root: str | Path | None = None,
    manifest_csv: str | Path | None = None,
    index_json_path: str | Path | None = None,
    splits_path: str | Path | None = None,
) -> DatasetLoadResult:
    explicit = Path(dataset_root).expanduser() if dataset_root is not None else None
    if explicit is None and spec is not None and spec.root is not None:
        explicit = Path(spec.root).expanduser()
    resolution = resolve_dataset_root("cipi", explicit_root=explicit, repo_fallback=DEFAULT_DATASET_ROOT)
    root = resolution.root if resolution.root is not None else DEFAULT_DATASET_ROOT
    manifest = manifest_csv or (spec.manifest_path if spec is not None else None) or DEFAULT_MOVEMENT_MANIFEST_CSV
    manifest_path = Path(manifest).expanduser()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"CIPI movement manifest not found: {manifest_path}")

    pieces_dir_hint = root.name.lower() == "pieces"
    warnings: list[str] = []
    if resolution.configured and not resolution.exists:
        warnings.append(f"CIPI dataset root does not exist: {resolution.detail}")
    effective_root = root
    if pieces_dir_hint:
        warnings.append(
            f"CIPI root points directly at a pieces/ directory ({root}); "
            "expected the dataset root containing metadata/ and pieces/. "
            "Resolve manifest paths against the parent directory instead, or reconfigure."
        )
        effective_root = root.parent

    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    records: list[DatasetRecord] = []
    manifest_paths: list[str] = []
    nonconforming: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        rel = str(row.get("dataset_relative_path", "") or "").strip().replace("\\", "/")
        manifest_paths.append(rel)
        source_path = (effective_root / rel).expanduser() if rel else effective_root
        exists = source_path.is_file() if rel else False
        piece_uid = str(row.get("piece_uid", "") or "").strip()
        cipi_id = str(row.get("cipi_id", "") or "").strip()
        if not piece_uid:
            nonconforming.append({"row": index, "issue": "missing_piece_uid", "cipi_id": cipi_id})
            piece_uid = f"cipi-row-{index:05d}"
        henle_raw = str(row.get("henle", "") or "").strip()
        labels: dict[str, Any] = {}
        if henle_raw != "":
            try:
                numeric = float(henle_raw)
                labels["henle"] = int(numeric) if numeric.is_integer() else numeric
            except ValueError:
                labels["henle"] = henle_raw
        records.append(
            DatasetRecord(
                dataset_name="cipi",
                piece_id=cipi_id or piece_uid,
                piece_uid=piece_uid,
                source_path=source_path,
                dataset_relative_path=rel,
                filename=str(row.get("filename", "") or "").strip() or source_path.name,
                normalized_filename=str(row.get("normalized_filename", "") or "").strip()
                or normalize_filename(source_path.name),
                title=str(row.get("work_name", "") or "").strip(),
                composer=str(row.get("composer", "") or "").strip(),
                labels=labels,
                provenance={
                    "repo_relative_path": repo_relative_path(source_path, REPO_ROOT)
                    if exists
                    else "",
                    "source_path": str(source_path.resolve()) if exists else str(source_path),
                    "manifest_path": str(manifest_path),
                    "movement": str(row.get("movement", "") or "").strip(),
                },
                adapter_metadata={
                    "cipi_id": cipi_id,
                    "movement": str(row.get("movement", "") or "").strip(),
                    "piece_id_manifest": str(row.get("piece_id", "") or "").strip(),
                    "legacy_piece_uid": str(row.get("legacy_piece_uid", "") or "").strip(),
                    "legacy_dataset_relative_path": str(
                        row.get("legacy_dataset_relative_path", "") or ""
                    ).strip(),
                    "upstream_path": str(row.get("upstream_path", "") or "").strip(),
                    "book": str(row.get("book", "") or "").strip(),
                    "uri": str(row.get("uri", "") or "").strip(),
                    "normalized_filename": str(row.get("normalized_filename", "") or "").strip(),
                    "source_row_index": index,
                    "file_exists": exists,
                },
            )
        )

    discovered = _discover_pieces_files(effective_root)
    comparison = compare_manifest_paths_to_discovered(manifest_paths, discovered)
    missing_files = [path for path in comparison["missing_files"] if path]
    extra_files = comparison["extra_files"]
    actually_missing = [rel for rel in manifest_paths if not (effective_root / rel).is_file()]
    missing_files = sorted(set(missing_files) | set(actually_missing))

    dup_uids = duplicate_piece_uids(records)
    if dup_uids:
        warnings.append(f"Duplicate CIPI piece_uid values: {sorted(dup_uids)}")
    dup_normalized = _duplicate_manifest_values(rows, "normalized_filename")
    if dup_normalized:
        warnings.append(f"Duplicate CIPI normalized_filename values in manifest: {dup_normalized}")

    movement_henle = Counter(str(record.labels["henle"]) for record in records if record.labels.get("henle") not in (None, ""))
    work_henle: dict[str, int] = {}
    work_count: int | None = None
    resolved_index = index_json_path or (spec.metadata.get("index_json") if spec is not None and spec.metadata else None)
    if resolved_index is not None:
        try:
            index_payload = load_index_json(resolved_index)
            work_count = len(index_payload)
            work_values: list[str] = []
            for value in index_payload.values():
                if isinstance(value, dict) and str(value.get("henle", "")).strip() != "":
                    work_values.append(str(value.get("henle")).strip())
            work_henle = dict(Counter(work_values))
        except (FileNotFoundError, ValueError) as exc:
            warnings.append(f"CIPI work-level index metadata unavailable: {exc}")

    split_diagnostics: dict[str, Any] = {}
    resolved_splits = splits_path or (spec.metadata.get("splits_json") if spec is not None and spec.metadata else None)
    if resolved_splits is not None:
        split_diagnostics = validate_split_ids(resolved_splits, index_json_path=resolved_index)

    summary = build_load_summary(
        dataset_name="cipi",
        record_count=len(records),
        missing_files=missing_files,
        extra_files=extra_files,
        duplicate_piece_ids=_duplicate_manifest_values(rows, "cipi_id"),
        duplicate_piece_uids=dup_uids,
        nonconforming_ids=nonconforming,
        unsupported_files=[],
        warnings=warnings,
        extra={
            "manifest_path": str(manifest_path),
            "manifest_row_count": len(rows),
            "dataset_root": str(root),
            "dataset_root_source": resolution.source,
            "dataset_root_detail": resolution.detail,
            "work_count": work_count,
            "movement_henle_distribution": {str(key): int(value) for key, value in sorted(movement_henle.items())},
            "work_henle_distribution": {str(key): int(value) for key, value in sorted(work_henle.items())},
            "pieces_dir_hint": pieces_dir_hint,
            "split_diagnostics": split_diagnostics,
        },
    )
    return DatasetLoadResult(
        dataset_name="cipi",
        records=records,
        missing_files=missing_files,
        extra_files=extra_files,
        duplicate_piece_ids=_duplicate_manifest_values(rows, "cipi_id"),
        duplicate_piece_uids=dup_uids,
        nonconforming_ids=nonconforming,
        unsupported_files=[],
        warnings=warnings,
        summary=summary,
    )


def validate_split_ids(splits_path: str | Path, index_json_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(splits_path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"CIPI splits file not found: {path}")
    payload = json.loads(path.read_text())
    split_ids = _collect_split_ids(payload)
    diagnostics: dict[str, Any] = {
        "splits_path": str(path),
        "split_id_count": len(split_ids),
        "split_ids": sorted(split_ids),
    }
    if index_json_path is None:
        diagnostics["index_ids"] = None
        diagnostics["missing_from_index"] = []
        diagnostics["note"] = "No index.json supplied; split IDs not validated."
        return diagnostics
    index_payload = load_index_json(index_json_path)
    index_ids = {str(key) for key in index_payload}
    diagnostics["index_ids"] = sorted(index_ids)
    diagnostics["index_id_count"] = len(index_ids)
    diagnostics["missing_from_index"] = sorted(split_ids - index_ids)
    return diagnostics


def _collect_split_ids(payload: Any) -> set[str]:
    if isinstance(payload, dict):
        ids: set[str] = set()
        for key, value in payload.items():
            if key in {"train", "validation", "test", "dev", "val"} and isinstance(value, list):
                ids.update(str(item) for item in value)
            elif isinstance(value, (dict, list)):
                ids.update(_collect_split_ids(value))
            elif isinstance(value, str) and key not in {"note", "description"}:
                pass
        if not ids and all(isinstance(value, list) for value in payload.values()):
            for value in payload.values():
                ids.update(str(item) for item in value)
        if not ids:
            flat = _flatten_split_ids(payload)
            ids.update(flat)
        return ids
    if isinstance(payload, list):
        return {str(item) for item in payload if isinstance(item, (str, int))}
    return set()


def _flatten_split_ids(payload: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            found.update(_flatten_split_ids(value))
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, (str, int)):
                found.add(str(item))
            else:
                found.update(_flatten_split_ids(item))
    return found


def write_catalog_csv(rows: list[dict[str, Any]], path: str | Path) -> None:
    csv_path = Path(path).expanduser()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "score_id",
                "title",
                "composer",
                "henle",
                "dataset_relative_path",
                "repo_relative_path",
                "filename",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def catalog_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the CIPI movement manifest against a local CIPI root.")
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--manifest-csv", type=Path, default=DEFAULT_MOVEMENT_MANIFEST_CSV)
    parser.add_argument(
        "--catalog-csv",
        type=Path,
        default=None,
        help="Legacy alias for --manifest-csv.",
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.catalog_csv is not None:
        args.manifest_csv = args.catalog_csv

    result = load_cipi_dataset(dataset_root=args.dataset_root, manifest_csv=args.manifest_csv)
    payload = {
        "manifest_csv": str(args.manifest_csv.expanduser()),
        "dataset_root": result.summary.get("dataset_root"),
        "dataset_root_source": result.summary.get("dataset_root_source"),
        "record_count": len(result.records),
        "missing_files": list(result.missing_files),
        "extra_files": list(result.extra_files),
        "duplicate_piece_uids": list(result.duplicate_piece_uids),
        "warnings": list(result.warnings),
        "summary": result.summary,
    }
    if args.out is not None:
        out_path = Path(args.out).expanduser()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _duplicate_manifest_values(rows: list[dict[str, Any]], column: str) -> list[str]:
    values = [str(row.get(column, "") or "").strip() for row in rows if str(row.get(column, "") or "").strip()]
    counts = Counter(values)
    if column == "cipi_id":
        return sorted([value for value, count in counts.items() if count > 1])
    return sorted([value for value, count in counts.items() if count > 1])


def _discover_pieces_files(root: Path) -> list[str]:
    pieces_dir = root / "pieces" if (root / "pieces").is_dir() else root
    found: list[str] = []
    if not pieces_dir.is_dir():
        return found
    for path in sorted(pieces_dir.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file() or path.suffix.lower() != ".musicxml":
            continue
        try:
            found.append(path.resolve().relative_to(root.resolve()).as_posix())
        except ValueError:
            found.append(path.resolve().as_posix())
    return found


def _build_dataset_index(dataset_root: Path) -> dict[str, Path]:
    score_paths = {}
    for path in dataset_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".xml", ".musicxml", ".mxl"}:
            continue
        score_paths[path.as_posix()] = path
    return score_paths


def _resolve_score_path(dataset_index: dict[str, Path], record: dict[str, Any]) -> Path | None:
    candidates = [record.get("path"), record.get("dataset_relative_path"), record.get("filename")]
    normalized_index = {
        _normalize_text(path.as_posix()): path for path in dataset_index.values()
    }
    for candidate in candidates:
        if not candidate:
            continue
        normalized_candidate = _normalize_text(str(candidate))
        if normalized_candidate in normalized_index:
            return normalized_index[normalized_candidate]

    best_path: Path | None = None
    best_score = 0
    target_text = " ".join(
        filter(
            None,
            [
                _normalize_text(str(record.get("title", ""))),
                _normalize_text(str(record.get("composer", ""))),
                _normalize_text(str(record.get("filename", ""))),
            ],
        )
    )
    for path in dataset_index.values():
        score = _token_overlap_score(target_text, _normalize_text(path.as_posix()))
        if score > best_score:
            best_score = score
            best_path = path
    return best_path


def resolve_score_path(
    record: dict[str, Any],
    *,
    dataset_root: str | Path,
    repo_root: str | Path | None = None,
) -> Path | None:
    dataset_root_path = Path(dataset_root).expanduser().resolve()
    repo_root_path = Path(repo_root or REPO_ROOT).expanduser().resolve()
    dataset_index = _build_dataset_index(dataset_root_path)
    resolved_path = _resolve_score_path(dataset_index, record)
    if resolved_path is None:
        return None
    if resolved_path.is_relative_to(dataset_root_path):
        return resolved_path.resolve()
    if resolved_path.is_relative_to(repo_root_path):
        return resolved_path.resolve()
    return resolved_path.resolve()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return normalized.strip()


def _token_overlap_score(left: str, right: str) -> int:
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    return len(left_tokens & right_tokens)
