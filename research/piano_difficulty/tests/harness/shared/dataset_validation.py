from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any

from .dataset_records import DatasetRecord


def find_duplicate_values(values: Iterable[str]) -> list[str]:
    counts = Counter(str(value) for value in values)
    return sorted([value for value, count in counts.items() if count > 1])


def find_duplicate_record_values(
    records: Iterable[DatasetRecord],
    key: Callable[[DatasetRecord], str] | str,
) -> list[str]:
    if isinstance(key, str):
        attribute = key
        values = [str(getattr(record, attribute, "")) for record in records]
    else:
        values = [str(key(record)) for record in records]
    return find_duplicate_values(values)


def duplicate_piece_ids(records: Iterable[DatasetRecord]) -> list[str]:
    return find_duplicate_record_values(records, "piece_id")


def duplicate_piece_uids(records: Iterable[DatasetRecord]) -> list[str]:
    return find_duplicate_record_values(records, "piece_uid")


def compare_manifest_paths_to_discovered(
    manifest_paths: Iterable[str],
    discovered_paths: Iterable[str],
) -> dict[str, list[str]]:
    manifest_set = {str(value).strip().replace("\\", "/") for value in manifest_paths if str(value).strip()}
    discovered_set = {str(value).strip().replace("\\", "/") for value in discovered_paths if str(value).strip()}
    return {
        "missing_files": sorted(manifest_set - discovered_set),
        "extra_files": sorted(discovered_set - manifest_set),
    }


def build_load_summary(
    *,
    dataset_name: str,
    record_count: int,
    missing_files: Iterable[str] | None = None,
    extra_files: Iterable[str] | None = None,
    duplicate_piece_ids: Iterable[str] | None = None,
    duplicate_piece_uids: Iterable[str] | None = None,
    nonconforming_ids: Iterable[dict[str, Any]] | None = None,
    unsupported_files: Iterable[str] | None = None,
    warnings: Iterable[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "dataset_name": dataset_name,
        "record_count": int(record_count),
        "missing_file_count": len(list(missing_files or [])),
        "extra_file_count": len(list(extra_files or [])),
        "duplicate_piece_id_count": len(list(duplicate_piece_ids or [])),
        "duplicate_piece_uid_count": len(list(duplicate_piece_uids or [])),
        "nonconforming_id_count": len(list(nonconforming_ids or [])),
        "unsupported_file_count": len(list(unsupported_files or [])),
        "warning_count": len(list(warnings or [])),
    }
    if extra:
        summary.update(dict(extra))
    return summary
