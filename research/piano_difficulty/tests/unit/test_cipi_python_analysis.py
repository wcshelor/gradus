from __future__ import annotations

import csv
import json
from pathlib import Path

from tests.harness.cipi_dataset.python_analysis import run_cipi_python_analysis
from tests.harness.oktav_dataset.python_analysis import run_oktav_python_analysis

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


def test_cipi_runtime_export_writes_matrix_and_load_report(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece_mvt1.musicxml").write_text(FIXTURE_XML)
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
                "cipi_id": "c-1", "movement": "1", "piece_id": "work_mvt1",
                "piece_uid": "pieces_bach_piece_mvt1", "legacy_piece_uid": "bach_piece_mvt1",
                "composer": "JOHANN SEBASTIAN BACH", "work_name": "Work", "book": "",
                "henle": "5", "uri": "",
                "dataset_relative_path": "pieces/bach/piece_mvt1.musicxml",
                "legacy_dataset_relative_path": "bach/piece_mvt1.musicxml",
                "upstream_path": "upstream/x.musicxml", "filename": "piece_mvt1.musicxml",
                "normalized_filename": "piece_mvt1_musicxml",
            }
        )
    out_dir = tmp_path / "out"
    summary = run_cipi_python_analysis(dataset_root=root, manifest_csv=manifest, out_dir=out_dir)
    assert summary["failure_count"] == 0
    matrix = Path(summary["matrix_csv_path"])
    assert matrix.name == "cipi_labeled_feature_matrix.csv"
    with matrix.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["henle"] == "5"
    assert rows[0]["piece_uid"] == "pieces_bach_piece_mvt1"
    assert rows[0]["legacy_piece_uid"] == "bach_piece_mvt1"
    load_report = Path(summary["load_report_path"])
    assert load_report.name == "load_report.json"
    assert json.loads(load_report.read_text())["summary"]["record_count"] == 1


def test_oktav_runtime_export_writes_load_report(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    (dataset_root / "Example OK00001.musicxml").write_text(FIXTURE_XML)
    out_dir = tmp_path / "out"
    summary = run_oktav_python_analysis(
        dataset_root=dataset_root, out_dir=out_dir, label_source_csv=None
    )
    assert summary["failure_count"] == 0
    assert Path(summary["load_report_path"]).is_file()
    assert summary["load_summary"]["record_count"] == 1


def test_oktav_legacy_label_source_still_works(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    (dataset_root / "Example OK00001.musicxml").write_text(FIXTURE_XML)
    legacy = tmp_path / "legacy_matrix.csv"
    legacy.write_text(
        "filename,dataset_relative_path,difficulty_numeric\n"
        "Example OK00001.musicxml,Example OK00001.musicxml,31\n"
    )
    out_dir = tmp_path / "out"
    summary = run_oktav_python_analysis(
        dataset_root=dataset_root,
        out_dir=out_dir,
        label_source_csv=None,
        legacy_label_source_csv=legacy,
    )
    with Path(summary["matrix_csv_path"]).open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["difficulty_numeric"] == "31"


MANIFEST_COLUMNS = [
    "cipi_id", "movement", "piece_id", "piece_uid", "legacy_piece_uid",
    "composer", "work_name", "book", "henle", "uri",
    "dataset_relative_path", "legacy_dataset_relative_path",
    "upstream_path", "filename", "normalized_filename",
]


def _write_two_row_manifest(path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for name in ("mvt1.musicxml", "mvt2.musicxml"):
            writer.writerow(
                {
                    "cipi_id": "c-1", "movement": "1", "piece_id": f"work_{name}",
                    "piece_uid": f"pieces_bach_{name}", "legacy_piece_uid": f"bach_{name}",
                    "composer": "JOHANN SEBASTIAN BACH", "work_name": "Work", "book": "",
                    "henle": "5", "uri": "",
                    "dataset_relative_path": f"pieces/bach/{name}",
                    "legacy_dataset_relative_path": f"bach/{name}",
                    "upstream_path": "", "filename": name,
                    "normalized_filename": name.replace(".", "_"),
                }
            )


def test_cipi_limit_does_not_inflate_missing_count(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "mvt1.musicxml").write_text(FIXTURE_XML)
    (root / "pieces" / "bach" / "mvt2.musicxml").write_text(FIXTURE_XML)
    manifest = tmp_path / "manifest.csv"
    _write_two_row_manifest(manifest)
    summary = run_cipi_python_analysis(
        dataset_root=root, manifest_csv=manifest, out_dir=tmp_path / "out", limit=1
    )
    assert summary["input_count"] == 1
    assert summary["skipped_missing_count"] == 0


def test_cipi_missing_count_with_and_without_limit(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "mvt1.musicxml").write_text(FIXTURE_XML)
    manifest = tmp_path / "manifest.csv"
    _write_two_row_manifest(manifest)
    full = run_cipi_python_analysis(
        dataset_root=root, manifest_csv=manifest, out_dir=tmp_path / "out_full"
    )
    assert full["skipped_missing_count"] == 1
    limited = run_cipi_python_analysis(
        dataset_root=root, manifest_csv=manifest, out_dir=tmp_path / "out_limited", limit=1
    )
    assert limited["skipped_missing_count"] == 1
    assert limited["input_count"] == 1
