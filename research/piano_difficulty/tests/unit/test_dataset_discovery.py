from __future__ import annotations

from pathlib import Path

from tests.harness.shared import (
    dataset_relative_path,
    discover_score_files,
    normalize_filename,
    partition_directory_entries,
)


def test_normalize_filename_handles_accents_and_punctuation() -> None:
    assert normalize_filename("Comptine D_un Autre Été MSMT OK00001.xml") == normalize_filename(
        "comptine d-un autre ete MSMT OK00001.xml"
    )
    assert normalize_filename("(Everything I Do) I Do It For You - PVG-RH MSMT OK00309.musicxml").startswith(
        "everything_i_do"
    )
    assert normalize_filename("a  --  b,,c") == "a_b_c"
    assert normalize_filename("  x  ") == "x"


def test_exact_filename_preserved_separately() -> None:
    original = "Comptine D_un Autre Été (Yann Tiersen) - piano MSMT OK00001 - 01.xml"
    assert normalize_filename(original) != original


def test_discover_score_files_supports_suffixes_and_sorting(tmp_path: Path) -> None:
    (tmp_path / "b.musicxml").write_text("b")
    (tmp_path / "a.xml").write_text("a")
    (tmp_path / "c.mxl").write_text("c")
    (tmp_path / "notes.txt").write_text("nope")
    (tmp_path / ".DS_Store").write_text("nope")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "d.xml").write_text("d")

    flat = discover_score_files(tmp_path)
    assert [path.name for path in flat] == ["a.xml", "b.musicxml", "c.mxl"]

    recursive = discover_score_files(tmp_path, recursive=True)
    assert [path.name for path in recursive] == ["a.xml", "b.musicxml", "c.mxl", "d.xml"]


def test_partition_reports_unsupported(tmp_path: Path) -> None:
    (tmp_path / "a.xml").write_text("a")
    (tmp_path / "b.pdf").write_text("b")
    supported, unsupported = partition_directory_entries(tmp_path)
    assert [path.name for path in supported] == ["a.xml"]
    assert unsupported == ["b.pdf"]


def test_dataset_relative_path_does_not_escape_silently(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    inside = root / "a.xml"
    inside.write_text("a")
    assert dataset_relative_path(inside, root) == "a.xml"
    outside = tmp_path / "elsewhere.xml"
    outside.write_text("x")
    assert "elsewhere" in dataset_relative_path(outside, root)
