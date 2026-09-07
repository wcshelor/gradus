from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tests.harness.cipi_dataset.catalog import (
    DEFAULT_CATALOG_CSV,
    DEFAULT_MOVEMENT_MANIFEST_CSV,
    LEGACY_CATALOG_CSV,
    load_catalog_dataframe,
    load_cipi_dataset,
    validate_split_ids,
)

EXPECTED_COLUMNS = [
    "cipi_id",
    "movement",
    "piece_id",
    "piece_uid",
    "legacy_piece_uid",
    "composer",
    "work_name",
    "book",
    "henle",
    "uri",
    "dataset_relative_path",
    "legacy_dataset_relative_path",
    "upstream_path",
    "filename",
    "normalized_filename",
]

FIXTURE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Piano</part-name></score-part></part-list>
  <part id="P1"><measure number="1">
    <attributes><divisions>1</divisions><key><fifths>0</fifths></key>
    <time><beats>4</beats><beat-type>4</beat-type></time>
    <clef><sign>G</sign><line>2</line></clef></attributes>
    <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>whole</type></note>
  </measure></part>
</score-partwise>
"""


def test_default_catalog_is_canonical_movement_manifest() -> None:
    assert DEFAULT_CATALOG_CSV == DEFAULT_MOVEMENT_MANIFEST_CSV
    assert str(DEFAULT_CATALOG_CSV).endswith("manifests/cipi/cipi_movement_manifest.csv")
    assert "cipi_dataset_catalog" in str(LEGACY_CATALOG_CSV)


def test_load_catalog_dataframe_reads_committed_manifest() -> None:
    frame = load_catalog_dataframe()
    for column in EXPECTED_COLUMNS:
        assert column in frame.columns
    assert len(frame) == 744


def test_load_catalog_dataframe_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_catalog_dataframe(tmp_path / "absent.csv")


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPECTED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _manifest_row(**overrides: str) -> dict[str, str]:
    row = {
        "cipi_id": "c-1",
        "movement": "1",
        "piece_id": "work_mvt1",
        "piece_uid": "pieces_bach_x_mvt1",
        "legacy_piece_uid": "bach_x_mvt1",
        "composer": "JOHANN SEBASTIAN BACH",
        "work_name": "Work",
        "book": "",
        "henle": "5",
        "uri": "",
        "dataset_relative_path": "pieces/bach/x_mvt1.musicxml",
        "legacy_dataset_relative_path": "bach/x_mvt1.musicxml",
        "upstream_path": "upstream/x.musicxml",
        "filename": "x_mvt1.musicxml",
        "normalized_filename": "x_mvt1_musicxml",
    }
    row.update(overrides)
    return row


def _fixture_root(tmp_path: Path, files: list[str]) -> Path:
    root = tmp_path / "cipi"
    pieces = root / "pieces" / "bach"
    pieces.mkdir(parents=True)
    for name in files:
        (pieces / name).write_text(FIXTURE_XML)
    return root


def test_movement_first_multi_movement_work(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path, ["x_mvt1.musicxml", "x_mvt2.musicxml"])
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            _manifest_row(movement="1", piece_uid="pieces_bach_x_mvt1",
                          dataset_relative_path="pieces/bach/x_mvt1.musicxml",
                          filename="x_mvt1.musicxml", normalized_filename="x_mvt1_musicxml"),
            _manifest_row(movement="2", piece_uid="pieces_bach_x_mvt2",
                          dataset_relative_path="pieces/bach/x_mvt2.musicxml",
                          filename="x_mvt2.musicxml", normalized_filename="x_mvt2_musicxml"),
        ],
    )
    result = load_cipi_dataset(dataset_root=root, manifest_csv=manifest)
    assert len(result.records) == 2
    assert {record.piece_id for record in result.records} == {"c-1"}
    assert len({record.piece_uid for record in result.records}) == 2
    assert all(record.labels["henle"] == 5 for record in result.records)
    assert result.missing_files == []


def test_cipi_paths_resolve_and_missing_reported(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path, ["present.musicxml"])
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            _manifest_row(piece_uid="pieces_bach_present", cipi_id="c-1",
                          dataset_relative_path="pieces/bach/present.musicxml",
                          filename="present.musicxml"),
            _manifest_row(piece_uid="pieces_bach_gone", cipi_id="c-2", movement="1",
                          dataset_relative_path="pieces/bach/gone.musicxml",
                          filename="gone.musicxml", normalized_filename="gone_musicxml"),
        ],
    )
    result = load_cipi_dataset(dataset_root=root, manifest_csv=manifest)
    assert "pieces/bach/gone.musicxml" in result.missing_files


def test_cipi_pieces_root_hint_and_extra_files(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path, ["a.musicxml", "extra.musicxml"])
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [_manifest_row(piece_uid="pieces_bach_a", dataset_relative_path="pieces/bach/a.musicxml",
                       filename="a.musicxml", normalized_filename="a_musicxml")],
    )
    result = load_cipi_dataset(dataset_root=root, manifest_csv=manifest)
    assert "pieces/bach/extra.musicxml" in result.extra_files

    pieces_direct = root / "pieces"
    pointed = load_cipi_dataset(dataset_root=pieces_direct, manifest_csv=manifest)
    assert pointed.summary["pieces_dir_hint"] is True
    assert any("pieces/" in warning for warning in pointed.warnings)


def test_cipi_legacy_fields_preserved(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path, ["x_mvt1.musicxml"])
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_manifest_row()])
    result = load_cipi_dataset(dataset_root=root, manifest_csv=manifest)
    metadata = result.records[0].adapter_metadata
    assert metadata["legacy_piece_uid"] == "bach_x_mvt1"
    assert metadata["legacy_dataset_relative_path"] == "bach/x_mvt1.musicxml"
    assert metadata["upstream_path"] == "upstream/x.musicxml"


def test_cipi_split_validation(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps({"c-1": {"henle": 5}, "c-2": {"henle": 6}}))
    splits_path = tmp_path / "splits.json"
    splits_path.write_text(json.dumps({"train": ["c-1"], "test": ["c-2", "x-999"]}))
    diagnostics = validate_split_ids(splits_path, index_json_path=index_path)
    assert diagnostics["missing_from_index"] == ["x-999"]

    clean = tmp_path / "clean.json"
    clean.write_text(json.dumps({"train": ["c-1"], "test": ["c-2"]}))
    assert validate_split_ids(clean, index_json_path=index_path)["missing_from_index"] == []


def test_cipi_henle_distributions(tmp_path: Path) -> None:
    root = _fixture_root(tmp_path, ["m1.musicxml", "m2.musicxml", "n1.musicxml"])
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [
            _manifest_row(cipi_id="c-1", movement="1", piece_uid="pieces_bach_m1",
                          dataset_relative_path="pieces/bach/m1.musicxml",
                          filename="m1.musicxml", normalized_filename="m1_musicxml", henle="5"),
            _manifest_row(cipi_id="c-1", movement="2", piece_uid="pieces_bach_m2",
                          dataset_relative_path="pieces/bach/m2.musicxml",
                          filename="m2.musicxml", normalized_filename="m2_musicxml", henle="5"),
            _manifest_row(cipi_id="c-2", movement="1", piece_uid="pieces_bach_n1",
                          dataset_relative_path="pieces/bach/n1.musicxml",
                          filename="n1.musicxml", normalized_filename="n1_musicxml", henle="7"),
        ],
    )
    index_path = tmp_path / "index.json"
    index_path.write_text(json.dumps({"c-1": {"henle": 5}, "c-2": {"henle": 7}}))
    result = load_cipi_dataset(dataset_root=root, manifest_csv=manifest, index_json_path=index_path)
    assert result.summary["movement_henle_distribution"] == {"5": 2, "7": 1}
    assert result.summary["work_henle_distribution"] == {"5": 1, "7": 1}


def test_cipi_bare_call_honors_env_root(tmp_path: Path, monkeypatch) -> None:
    root = _fixture_root(tmp_path, ["x_mvt1.musicxml"])
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_manifest_row()])
    monkeypatch.setenv("GRADUS_CIPI_ROOT", str(root))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    result = load_cipi_dataset(manifest_csv=manifest)
    assert len(result.records) == 1
    assert result.summary["dataset_root"] == str(root)
    assert result.summary["dataset_root_source"] == "env"
    assert "GRADUS_CIPI_ROOT" in result.summary["dataset_root_detail"]


def test_cipi_bare_call_honors_config_file(tmp_path: Path, monkeypatch) -> None:
    root = _fixture_root(tmp_path, ["x_mvt1.musicxml"])
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_manifest_row()])
    config_path = tmp_path / "datasets.toml"
    config_path.write_text(f'[cipi]\nroot = "{root}"\n')
    monkeypatch.delenv("GRADUS_CIPI_ROOT", raising=False)
    monkeypatch.setenv("GRADUS_DATASETS_CONFIG", str(config_path))
    result = load_cipi_dataset(manifest_csv=manifest)
    assert len(result.records) == 1
    assert result.summary["dataset_root_source"] == "local_config"


def test_cipi_explicit_root_wins_over_env(tmp_path: Path, monkeypatch) -> None:
    explicit = _fixture_root(tmp_path, ["x_mvt1.musicxml"])
    other = tmp_path / "other"
    (other / "pieces" / "bach").mkdir(parents=True)
    monkeypatch.setenv("GRADUS_CIPI_ROOT", str(other))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_manifest_row()])
    result = load_cipi_dataset(dataset_root=explicit, manifest_csv=manifest)
    assert result.missing_files == []
    assert result.summary["dataset_root_source"] == "cli"
