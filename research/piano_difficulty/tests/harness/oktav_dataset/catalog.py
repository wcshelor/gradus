from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from tests.harness.shared.dataset_config import DatasetSpec, resolve_dataset_root
from tests.harness.shared.dataset_discovery import (
    DEFAULT_SCORE_SUFFIXES,
    dataset_relative_path,
    discover_score_files,
    normalize_filename,
    repo_relative_path,
)
from tests.harness.shared.dataset_records import DatasetLoadResult, DatasetRecord
from tests.harness.shared.dataset_validation import (
    build_load_summary,
    duplicate_piece_ids,
    duplicate_piece_uids,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_ROOT = REPO_ROOT / "evaluation_scores" / "ad_hoc" / "oktav_starting_dataset"

VALID_OK_PATTERN = re.compile(r"OK\d{5}", re.IGNORECASE)
LOOSE_OK_PATTERN = re.compile(r"OK\s*0*(\d+)", re.IGNORECASE)


def parse_oktav_id(filename: str) -> tuple[str | None, str | None]:
    match = VALID_OK_PATTERN.search(filename or "")
    if match:
        return match.group(0).upper(), None
    loose = LOOSE_OK_PATTERN.search(filename or "")
    if loose:
        return None, "malformed"
    return None, "missing"


def parse_arrangement(filename: str) -> tuple[str, str]:
    stem = Path(str(filename or "")).stem
    if "MSMT2" in stem.upper():
        head = re.split(r"MSMT2", stem, flags=re.IGNORECASE)[0]
    elif "MSMT" in stem.upper():
        head = re.split(r"MSMT", stem, flags=re.IGNORECASE)[0]
    else:
        return "", ""
    segments = [segment.strip(" -_") for segment in re.split(r"\s+-\s+", head) if segment.strip(" -_")]
    if len(segments) < 2:
        return "", ""
    raw = segments[-1].strip()
    if not raw:
        return "", ""
    normalized = re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")
    return raw, normalized


def piece_uid_for_file(filename: str, dataset_rel: str) -> str:
    base = dataset_rel or filename
    candidate = Path(base).with_suffix("").as_posix()
    text = normalize_filename(candidate)
    return text or normalize_filename(Path(filename).stem)


def load_oktav_label_table(label_source: str | Path | None) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if label_source is None:
        return {}, {"label_row_count": 0, "label_source": None}
    path = Path(label_source).expanduser()
    if not path.is_file():
        return {}, {"label_row_count": 0, "label_source": str(path), "label_source_missing": True}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = {str(name or "").strip().lower(): name for name in (reader.fieldnames or [])}
        filename_key = columns.get("filename")
        path_key = columns.get("dataset_relative_path") or columns.get("datasetrelativepath") or columns.get("path")
        difficulty_key = (
            columns.get("difficulty") or columns.get("difficulty_numeric") or columns.get("difficultynumeric")
        )
        raw_rows = list(reader)

    exact: dict[str, dict[str, Any]] = {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    by_path: dict[str, dict[str, Any]] = {}
    duplicate_label_filenames: list[str] = []
    for row in raw_rows:
        filename = str(row.get(filename_key, "")).strip() if filename_key else ""
        difficulty_raw = str(row.get(difficulty_key, "")).strip() if difficulty_key else ""
        rel = str(row.get(path_key, "")).strip() if path_key else ""
        numeric = _parse_difficulty_numeric(difficulty_raw)
        entry = {
            "difficulty_raw": difficulty_raw,
            "difficulty_numeric": numeric,
            "filename": filename,
            "dataset_relative_path": rel,
        }
        if filename and filename not in exact:
            exact[filename] = entry
        elif filename:
            duplicate_label_filenames.append(filename)
        norm = normalize_filename(filename) if filename else ""
        if norm:
            normalized.setdefault(norm, []).append(entry)
        if rel and rel not in by_path:
            by_path[rel] = entry

    diagnostics = {
        "label_row_count": len(raw_rows),
        "label_source": str(path),
        "duplicate_label_filenames": sorted(set(duplicate_label_filenames)),
    }
    return {"exact": exact, "normalized": normalized, "by_path": by_path}, diagnostics


def _parse_difficulty_numeric(raw: str) -> str | float | int:
    text = str(raw or "").strip()
    if not text or text.lower() == "n/a":
        return ""
    try:
        value = float(text)
    except ValueError:
        return ""
    if value.is_integer():
        return int(value)
    return value


def resolve_oktav_label(
    *,
    filename: str,
    normalized: str,
    dataset_rel: str,
    label_tables: dict[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    exact = label_tables.get("exact", {})
    if filename in exact:
        return exact[filename], "exact_filename"
    normalized_table: dict[str, list[dict[str, Any]]] = label_tables.get("normalized", {})
    candidates = normalized_table.get(normalized, [])
    if len(candidates) == 1:
        return candidates[0], "normalized_filename"
    if len(candidates) > 1:
        return None, "normalized_filename_ambiguous"
    by_path = label_tables.get("by_path", {})
    if dataset_rel and dataset_rel in by_path:
        return by_path[dataset_rel], "dataset_relative_path"
    return None, "unmatched"


def load_oktav_dataset(
    spec: DatasetSpec | None = None,
    *,
    dataset_root: str | Path | None = None,
    label_source: str | Path | None = None,
    recursive: bool = False,
) -> DatasetLoadResult:
    explicit = Path(dataset_root).expanduser() if dataset_root is not None else None
    if explicit is None and spec is not None and spec.root is not None:
        explicit = Path(spec.root).expanduser()
    resolution = resolve_dataset_root("oktav", explicit_root=explicit, repo_fallback=DEFAULT_DATASET_ROOT)
    root = resolution.root if resolution.root is not None else DEFAULT_DATASET_ROOT
    label_path = label_source
    if label_path is None and spec is not None:
        label_path = spec.label_source_path
    warnings: list[str] = []
    if resolution.configured and not resolution.exists:
        warnings.append(f"Oktav dataset root does not exist: {resolution.detail}")

    score_files = discover_score_files(root, suffixes=DEFAULT_SCORE_SUFFIXES, recursive=recursive)
    label_tables, label_diagnostics = load_oktav_label_table(label_path)

    unsupported: list[str] = []
    if root.is_dir():
        scope = root.rglob("*") if recursive else root.iterdir()
        for candidate in sorted(scope, key=lambda item: item.as_posix().lower()):
            if not candidate.is_file() or candidate.name == ".DS_Store":
                continue
            if candidate.suffix.lower() not in {suffix.lower() for suffix in DEFAULT_SCORE_SUFFIXES}:
                unsupported.append(candidate.name)

    records: list[DatasetRecord] = []
    nonconforming: list[dict[str, Any]] = []
    unmatched_scores: list[str] = []
    labels_without_scores: list[str] = []
    ambiguous_labels: list[str] = []
    seen_filenames = {path.name for path in score_files}

    for index, source_path in enumerate(score_files):
        dataset_rel = dataset_relative_path(source_path, root)
        normalized = normalize_filename(source_path.name)
        ok_id, problem = parse_oktav_id(source_path.name)
        piece_id = ok_id or source_path.stem
        if problem:
            nonconforming.append(
                {"filename": source_path.name, "dataset_relative_path": dataset_rel, "issue": problem}
            )
        arrangement_raw, arrangement_key = parse_arrangement(source_path.name)
        label_entry, join_key = resolve_oktav_label(
            filename=source_path.name,
            normalized=normalized,
            dataset_rel=dataset_rel,
            label_tables=label_tables,
        )
        labels: dict[str, Any] = {}
        if label_entry is not None:
            labels["difficulty_raw"] = label_entry.get("difficulty_raw", "")
            if label_entry.get("difficulty_numeric") not in (None, ""):
                labels["difficulty_numeric"] = label_entry["difficulty_numeric"]
            labels["label_source"] = label_diagnostics.get("label_source")
            labels["label_join_key"] = join_key
        else:
            if join_key == "normalized_filename_ambiguous":
                ambiguous_labels.append(source_path.name)
                warnings.append(f"Ambiguous normalized label match for {source_path.name}; leaving unlabeled.")
            else:
                unmatched_scores.append(source_path.name)
        records.append(
            DatasetRecord(
                dataset_name="oktav",
                piece_id=piece_id,
                piece_uid=piece_uid_for_file(source_path.name, dataset_rel),
                source_path=source_path,
                dataset_relative_path=dataset_rel,
                filename=source_path.name,
                normalized_filename=normalized,
                title=source_path.stem,
                composer="",
                labels=labels,
                provenance={
                    "repo_relative_path": repo_relative_path(source_path, REPO_ROOT),
                    "source_path": str(source_path.resolve()),
                },
                adapter_metadata={
                    "oktav_id": ok_id or "",
                    "arrangement_raw": arrangement_raw,
                    "arrangement_key": arrangement_key,
                    "source_row_index": index,
                },
            )
        )

    exact_labels = label_tables.get("exact", {}) if label_tables else {}
    for filename in sorted(exact_labels):
        if filename not in seen_filenames:
            labels_without_scores.append(filename)

    dup_ids = duplicate_piece_ids(records)
    dup_uids = duplicate_piece_uids(records)
    if dup_uids:
        warnings.append(f"Duplicate Oktav piece_uid values: {sorted(dup_uids)}")
    if label_diagnostics.get("label_source_missing"):
        warnings.append(f"Oktav label source not found: {label_diagnostics.get('label_source')}")

    summary = build_load_summary(
        dataset_name="oktav",
        record_count=len(records),
        missing_files=[],
        extra_files=[],
        duplicate_piece_ids=dup_ids,
        duplicate_piece_uids=dup_uids,
        nonconforming_ids=nonconforming,
        unsupported_files=sorted(set(unsupported)),
        warnings=warnings,
        extra={
            "dataset_root": str(root),
            "dataset_root_source": resolution.source,
            "dataset_root_detail": resolution.detail,
            "score_file_count": len(score_files),
            "unmatched_scores": sorted(unmatched_scores),
            "unmatched_score_count": len(unmatched_scores),
            "labels_without_scores": sorted(labels_without_scores),
            "labels_without_score_count": len(labels_without_scores),
            "ambiguous_normalized_labels": sorted(ambiguous_labels),
            **label_diagnostics,
        },
    )
    return DatasetLoadResult(
        dataset_name="oktav",
        records=records,
        missing_files=[],
        extra_files=[],
        duplicate_piece_ids=dup_ids,
        duplicate_piece_uids=dup_uids,
        nonconforming_ids=nonconforming,
        unsupported_files=sorted(set(unsupported)),
        warnings=warnings,
        summary=summary,
    )


load_oktav_records = load_oktav_dataset
