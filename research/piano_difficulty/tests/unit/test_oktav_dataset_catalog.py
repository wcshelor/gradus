from __future__ import annotations

from pathlib import Path

from tests.harness.oktav_dataset.catalog import (
    load_oktav_dataset,
    parse_arrangement,
    parse_oktav_id,
    piece_uid_for_file,
)
from tests.harness.shared import DatasetSpec


def _write(root: Path, name: str) -> Path:
    path = root / name
    path.write_text("<score/>")
    return path


def test_oktav_catalog_loads_flat_fixture(tmp_path: Path) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "Song A - piano MSMT OK00001.xml")
    _write(root, "Song B - PVG-Ac MSMT OK00002.musicxml")
    _write(root, "Song C - piano MSMT OK00003.mxl")

    result = load_oktav_dataset(dataset_root=root)
    assert len(result.records) == 3
    assert result.dataset_name == "oktav"
    assert {record.piece_id for record in result.records} == {"OK00001", "OK00002", "OK00003"}
    assert result.summary["score_file_count"] == 3


def test_oktav_valid_duplicate_and_malformed_ids(tmp_path: Path) -> None:
    assert parse_oktav_id("Song MSMT OK00309.xml")[0] == "OK00309"
    assert parse_oktav_id("Honey - PVG-Ac MSMT OK0357.musicxml")[1] == "malformed"
    assert parse_oktav_id("Dustland PVG-Ac MSMT.mxl")[1] == "missing"

    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "(Everything I Do) I Do It For You - PVG-RH MSMT OK00309.musicxml")
    _write(root, "(Everything I Do) I Do It For You - piano beginner MSMT2 OK00309.xml")
    _write(root, "Honey (Taylor Swift) - PVG-Ac MSMT OK0357.musicxml")

    result = load_oktav_dataset(dataset_root=root)
    assert result.duplicate_piece_ids == ["OK00309"]
    assert result.duplicate_piece_uids == []
    kinds = {entry["issue"] for entry in result.nonconforming_ids}
    assert "malformed" in kinds
    assert len(result.records) == 3


def test_oktav_piece_uid_derives_from_path_not_ok_id() -> None:
    first = piece_uid_for_file("Song - piano MSMT OK00309.xml", "Song - piano MSMT OK00309.xml")
    second = piece_uid_for_file("Song - PVG-RH MSMT OK00309.xml", "Song - PVG-RH MSMT OK00309.xml")
    assert first != second
    assert "ok00309" in first


def test_oktav_arrangement_metadata_best_effort() -> None:
    raw, key = parse_arrangement("Song - PVG-RH MSMT OK00309.xml")
    assert raw == "PVG-RH"
    assert key == "pvg_rh"
    raw, key = parse_arrangement("Song - piano beginner MSMT2 OK00309.xml")
    assert key == "piano_beginner"
    raw, key = parse_arrangement("ambiguous_name.xml")
    assert raw == "" and key == ""


def test_oktav_csv_labels_exact_and_na(tmp_path: Path) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "Alpha - piano MSMT OK00001.xml")
    _write(root, "Beta - piano MSMT OK00002.xml")
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "Filename,ArrID,Difficulty\n"
        "Alpha - piano MSMT OK00001.xml,,23\n"
        "Beta - piano MSMT OK00002.xml,,n/a\n"
        "Ghost - piano MSMT OK00999.xml,,11\n"
    )
    result = load_oktav_dataset(dataset_root=root, label_source=labels)
    by_name = {record.filename: record for record in result.records}
    assert by_name["Alpha - piano MSMT OK00001.xml"].labels["difficulty_numeric"] == 23
    assert by_name["Alpha - piano MSMT OK00001.xml"].labels["label_join_key"] == "exact_filename"
    beta = by_name["Beta - piano MSMT OK00002.xml"].labels
    assert beta["difficulty_raw"] == "n/a"
    assert "difficulty_numeric" not in beta
    assert result.summary["labels_without_scores"] == ["Ghost - piano MSMT OK00999.xml"]
    assert result.summary["unmatched_score_count"] == 0


def test_oktav_normalized_label_join_and_ambiguous(tmp_path: Path) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "Comptine D_un Autre Été - piano MSMT OK00001.xml")
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "Filename,Difficulty\n"
        "comptine d-un autre ete - piano msmt ok00001.xml,45\n"
    )
    result = load_oktav_dataset(dataset_root=root, label_source=labels)
    assert result.records[0].labels["difficulty_numeric"] == 45
    assert result.records[0].labels["label_join_key"] == "normalized_filename"

    root2 = tmp_path / "oktav2"
    root2.mkdir()
    _write(root2, "Same Song - piano MSMT OK00001.xml")
    dup_labels = tmp_path / "dup.csv"
    dup_labels.write_text(
        "Filename,Difficulty\n"
        "same song - piano msmt ok00001.xml,11\n"
        "SAME SONG - PIANO MSMT OK00001.XML,22\n"
    )
    result2 = load_oktav_dataset(dataset_root=root2, label_source=dup_labels)
    assert result2.records[0].labels == {}
    assert result2.summary["ambiguous_normalized_labels"]


def test_oktav_never_joins_by_ok_id_alone(tmp_path: Path) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "Song A - piano MSMT OK00309.xml")
    _write(root, "Song B - PVG-RH MSMT OK00309.xml")
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "Filename,Difficulty\n"
        "Song A - piano MSMT OK00309.xml,11\n"
        "Song B - PVG-RH MSMT OK00309.xml,55\n"
    )
    result = load_oktav_dataset(dataset_root=root, label_source=labels)
    values = sorted(record.labels.get("difficulty_numeric", "") for record in result.records)
    assert values == [11, 55]
    assert len({record.piece_uid for record in result.records}) == 2


def test_oktav_accepts_dataset_spec(tmp_path: Path) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "Song - piano MSMT OK00001.xml")
    spec = DatasetSpec(dataset_name="oktav", root=root)
    result = load_oktav_dataset(spec)
    assert len(result.records) == 1


def test_oktav_bare_call_honors_env_root(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "Song - piano MSMT OK00001.xml")
    monkeypatch.setenv("GRADUS_OKTAV_ROOT", str(root))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    result = load_oktav_dataset()
    assert len(result.records) == 1
    assert result.summary["dataset_root"] == str(root)
    assert result.summary["dataset_root_source"] == "env"
    assert "GRADUS_OKTAV_ROOT" in result.summary["dataset_root_detail"]


def test_oktav_bare_call_honors_config_file(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    _write(root, "Song - piano MSMT OK00001.xml")
    config_path = tmp_path / "datasets.toml"
    config_path.write_text(f'[oktav]\nroot = "{root}"\n')
    monkeypatch.delenv("GRADUS_OKTAV_ROOT", raising=False)
    monkeypatch.setenv("GRADUS_DATASETS_CONFIG", str(config_path))
    result = load_oktav_dataset()
    assert len(result.records) == 1
    assert result.summary["dataset_root_source"] == "local_config"


def test_oktav_explicit_root_wins_over_env(tmp_path: Path, monkeypatch) -> None:
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    _write(explicit, "Song - piano MSMT OK00001.xml")
    env_root = tmp_path / "env"
    env_root.mkdir()
    _write(env_root, "Other - piano MSMT OK00002.xml")
    monkeypatch.setenv("GRADUS_OKTAV_ROOT", str(env_root))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    result = load_oktav_dataset(dataset_root=explicit)
    assert [record.filename for record in result.records] == ["Song - piano MSMT OK00001.xml"]
    assert result.summary["dataset_root_source"] == "cli"
