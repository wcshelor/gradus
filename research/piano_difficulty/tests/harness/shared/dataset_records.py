from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    dataset_name: str
    piece_id: str
    piece_uid: str
    source_path: Path
    dataset_relative_path: str
    filename: str
    normalized_filename: str
    title: str = ""
    composer: str = ""
    labels: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    adapter_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "piece_id": self.piece_id,
            "piece_uid": self.piece_uid,
            "source_path": str(self.source_path),
            "dataset_relative_path": self.dataset_relative_path,
            "filename": self.filename,
            "normalized_filename": self.normalized_filename,
            "title": self.title,
            "composer": self.composer,
            "labels": dict(self.labels),
            "provenance": dict(self.provenance),
            "adapter_metadata": dict(self.adapter_metadata),
        }


@dataclass(slots=True)
class DatasetLoadResult:
    dataset_name: str
    records: list[DatasetRecord] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    extra_files: list[str] = field(default_factory=list)
    duplicate_piece_ids: list[str] = field(default_factory=list)
    duplicate_piece_uids: list[str] = field(default_factory=list)
    nonconforming_ids: list[dict[str, Any]] = field(default_factory=list)
    unsupported_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_name": self.dataset_name,
            "records": [record.to_dict() for record in self.records],
            "missing_files": list(self.missing_files),
            "extra_files": list(self.extra_files),
            "duplicate_piece_ids": list(self.duplicate_piece_ids),
            "duplicate_piece_uids": list(self.duplicate_piece_uids),
            "nonconforming_ids": [dict(entry) for entry in self.nonconforming_ids],
            "unsupported_files": list(self.unsupported_files),
            "warnings": list(self.warnings),
            "summary": dict(self.summary),
        }


def to_runtime_export_input(record: DatasetRecord, source_row_index: int = 0):
    from .runtime_matrix_export import RuntimeExportInput

    metadata: dict[str, Any] = {
        "source_row_index": source_row_index,
        "dataset_name": record.dataset_name,
        "piece_id": record.piece_id,
        "piece_uid": record.piece_uid,
        "title": record.title,
        "composer": record.composer,
        "filename": record.filename,
        "dataset_relative_path": record.dataset_relative_path,
        "normalized_filename": record.normalized_filename,
    }
    provenance = dict(record.provenance or {})
    if provenance.get("repo_relative_path"):
        metadata["repo_relative_path"] = provenance["repo_relative_path"]
    if provenance.get("source_path"):
        metadata["source_path"] = provenance["source_path"]

    labels = dict(record.labels or {})
    for key in ("difficulty_numeric", "overallDifficulty", "henle"):
        if labels.get(key) not in (None, ""):
            metadata[key] = labels[key]
    adapter_metadata = dict(record.adapter_metadata or {})
    for key, value in adapter_metadata.items():
        if key in metadata or key.startswith("_"):
            continue
        metadata[key] = value
    return RuntimeExportInput(source_path=record.source_path, metadata=metadata)
