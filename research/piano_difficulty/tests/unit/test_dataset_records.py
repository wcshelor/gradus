from __future__ import annotations

import json
from pathlib import Path

from tests.harness.shared import (
    DatasetLoadResult,
    DatasetRecord,
    to_runtime_export_input,
)


def _record(tmp_path: Path) -> DatasetRecord:
    source = tmp_path / "Example OK00001.musicxml"
    source.write_text("<score/>")
    return DatasetRecord(
        dataset_name="oktav",
        piece_id="OK00001",
        piece_uid="example_ok00001_musicxml",
        source_path=source,
        dataset_relative_path="Example OK00001.musicxml",
        filename="Example OK00001.musicxml",
        normalized_filename="example_ok00001_musicxml",
        title="Example",
        composer="",
        labels={"difficulty_numeric": 23, "difficulty_raw": "23"},
        provenance={"repo_relative_path": "x"},
        adapter_metadata={"oktav_id": "OK00001"},
    )


def test_dataset_record_to_dict_round_trip(tmp_path: Path) -> None:
    record = _record(tmp_path)
    payload = record.to_dict()
    assert payload["piece_id"] == "OK00001"
    assert payload["source_path"].endswith("Example OK00001.musicxml")
    assert payload["labels"]["difficulty_numeric"] == 23


def test_dataset_load_result_serializes_to_json(tmp_path: Path) -> None:
    record = _record(tmp_path)
    result = DatasetLoadResult(
        dataset_name="oktav",
        records=[record],
        missing_files=["gone.musicxml"],
        duplicate_piece_ids=["OK00001"],
        warnings=["demo"],
        summary={"record_count": 1},
    )
    payload = result.to_dict()
    text = json.dumps(payload)
    assert "gone.musicxml" in text
    assert json.loads(text)["records"][0]["piece_uid"] == "example_ok00001_musicxml"


def test_to_runtime_export_input_preserves_identity_and_labels(tmp_path: Path) -> None:
    record = _record(tmp_path)
    export_input = to_runtime_export_input(record, source_row_index=4)
    assert export_input.source_path == record.source_path
    assert export_input.metadata["piece_uid"] == "example_ok00001_musicxml"
    assert export_input.metadata["dataset_relative_path"] == "Example OK00001.musicxml"
    assert export_input.metadata["normalized_filename"] == "example_ok00001_musicxml"
    assert export_input.metadata["difficulty_numeric"] == 23
    assert export_input.metadata["source_row_index"] == 4


def test_to_runtime_export_input_maps_henle(tmp_path: Path) -> None:
    record = _record(tmp_path)
    cipi = DatasetRecord(
        dataset_name="cipi",
        piece_id="c-1",
        piece_uid="pieces_beethoven_x",
        source_path=record.source_path,
        dataset_relative_path="pieces/beethoven/x.musicxml",
        filename="x.musicxml",
        normalized_filename="x_musicxml",
        labels={"henle": 6},
        provenance={},
        adapter_metadata={"legacy_piece_uid": "beethoven_x"},
    )
    export_input = to_runtime_export_input(cipi)
    assert export_input.metadata["henle"] == 6
    assert export_input.metadata["legacy_piece_uid"] == "beethoven_x"
