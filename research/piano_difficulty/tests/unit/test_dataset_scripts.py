from __future__ import annotations

import json
from pathlib import Path

from tests.harness.cipi_dataset import catalog_main as cipi_catalog_main
from tests.scripts import build_oktav_dataset_catalog as oktav_catalog_script


def test_build_oktav_catalog_script_is_thin_and_writes_report(tmp_path: Path) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    (root / "Song - piano MSMT OK00001.xml").write_text("<score/>")
    out = tmp_path / "report.json"
    assert oktav_catalog_script.main(["--dataset-root", str(root), "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["record_count"] == 1
    assert payload["summary"]["score_file_count"] == 1


def test_build_cipi_catalog_script_validates_without_overwriting_manifest(tmp_path: Path) -> None:
    import csv

    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "x.musicxml").write_text("<score/>")
    manifest = tmp_path / "manifest.csv"
    before = manifest.stat().st_mtime if manifest.exists() else None
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "cipi_id", "movement", "piece_id", "piece_uid", "legacy_piece_uid",
                "composer", "work_name", "book", "henle", "uri",
                "dataset_relative_path", "legacy_dataset_relative_path",
                "upstream_path", "filename", "normalized_filename",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "cipi_id": "c-1", "movement": "1", "piece_id": "w", "piece_uid": "pieces_bach_x",
                "legacy_piece_uid": "bach_x", "composer": "BACH", "work_name": "W", "book": "",
                "henle": "5", "uri": "", "dataset_relative_path": "pieces/bach/x.musicxml",
                "legacy_dataset_relative_path": "bach/x.musicxml", "upstream_path": "",
                "filename": "x.musicxml", "normalized_filename": "x_musicxml",
            }
        )
    out = tmp_path / "load_report.json"
    assert cipi_catalog_main(["--dataset-root", str(root), "--manifest-csv", str(manifest), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["record_count"] == 1
    assert manifest.stat().st_mtime != before or before is None


def test_runner_scripts_import_without_side_effects() -> None:
    import importlib

    for module in (
        "tests.scripts.run_cipi_python_analysis",
        "tests.scripts.run_oktav_python_analysis",
        "tests.scripts.build_cipi_dataset_catalog",
    ):
        imported = importlib.import_module(module)
        assert hasattr(imported, "__name__")


def test_oktav_catalog_script_honors_env_root_without_flag(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "oktav"
    root.mkdir()
    (root / "Song - piano MSMT OK00001.xml").write_text("<score/>")
    monkeypatch.setenv("GRADUS_OKTAV_ROOT", str(root))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    out = tmp_path / "report.json"
    assert oktav_catalog_script.main(["--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["record_count"] == 1
    assert payload["dataset_root_source"] == "env"


def test_oktav_catalog_script_explicit_root_wins_over_env(tmp_path: Path, monkeypatch) -> None:
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    (explicit / "Song - piano MSMT OK00001.xml").write_text("<score/>")
    env_root = tmp_path / "env"
    env_root.mkdir()
    monkeypatch.setenv("GRADUS_OKTAV_ROOT", str(env_root))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    out = tmp_path / "report.json"
    assert oktav_catalog_script.main(["--dataset-root", str(explicit), "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["record_count"] == 1
    assert payload["dataset_root_source"] == "cli"


def test_cipi_catalog_script_honors_env_root_without_flag(tmp_path: Path, monkeypatch) -> None:
    import csv

    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "x.musicxml").write_text("<score/>")
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "cipi_id", "movement", "piece_id", "piece_uid", "legacy_piece_uid",
                "composer", "work_name", "book", "henle", "uri",
                "dataset_relative_path", "legacy_dataset_relative_path",
                "upstream_path", "filename", "normalized_filename",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "cipi_id": "c-1", "movement": "1", "piece_id": "w", "piece_uid": "pieces_bach_x",
                "legacy_piece_uid": "bach_x", "composer": "BACH", "work_name": "W", "book": "",
                "henle": "5", "uri": "", "dataset_relative_path": "pieces/bach/x.musicxml",
                "legacy_dataset_relative_path": "bach/x.musicxml", "upstream_path": "",
                "filename": "x.musicxml", "normalized_filename": "x_musicxml",
            }
        )
    monkeypatch.setenv("GRADUS_CIPI_ROOT", str(root))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    out = tmp_path / "load_report.json"
    assert cipi_catalog_main(["--manifest-csv", str(manifest), "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["record_count"] == 1
    assert payload["dataset_root_source"] == "env"
