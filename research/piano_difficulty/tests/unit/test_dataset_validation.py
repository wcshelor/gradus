from __future__ import annotations

from pathlib import Path

from tests.harness.shared import (
    DatasetRecord,
    build_load_summary,
    compare_manifest_paths_to_discovered,
    duplicate_piece_ids,
    duplicate_piece_uids,
    find_duplicate_values,
)


def _record(piece_id: str, piece_uid: str) -> DatasetRecord:
    return DatasetRecord(
        dataset_name="demo",
        piece_id=piece_id,
        piece_uid=piece_uid,
        source_path=Path(f"/tmp/{piece_uid}.musicxml"),
        dataset_relative_path=f"{piece_uid}.musicxml",
        filename=f"{piece_uid}.musicxml",
        normalized_filename=piece_uid,
    )


def test_duplicate_piece_id_allowed_but_reported() -> None:
    records = [_record("OK00309", "a"), _record("OK00309", "b"), _record("OK00001", "c")]
    assert duplicate_piece_ids(records) == ["OK00309"]
    assert duplicate_piece_uids(records) == []


def test_duplicate_piece_uid_flagged() -> None:
    records = [_record("A", "same"), _record("B", "same")]
    assert duplicate_piece_uids(records) == ["same"]


def test_find_duplicate_values_sorted_unique() -> None:
    assert find_duplicate_values(["b", "a", "b", "a", "c"]) == ["a", "b"]


def test_compare_manifest_paths_reports_missing_and_extra() -> None:
    comparison = compare_manifest_paths_to_discovered(
        ["pieces/a.musicxml", "pieces/b.musicxml"],
        ["pieces/b.musicxml", "pieces/c.musicxml"],
    )
    assert comparison["missing_files"] == ["pieces/a.musicxml"]
    assert comparison["extra_files"] == ["pieces/c.musicxml"]


def test_build_load_summary_counts() -> None:
    summary = build_load_summary(
        dataset_name="cipi",
        record_count=3,
        missing_files=["a"],
        extra_files=[],
        duplicate_piece_ids=["c-1"],
        duplicate_piece_uids=[],
        nonconforming_ids=[{"issue": "x"}],
        unsupported_files=[],
        warnings=["w"],
    )
    assert summary["record_count"] == 3
    assert summary["missing_file_count"] == 1
    assert summary["duplicate_piece_id_count"] == 1
    assert summary["nonconforming_id_count"] == 1
