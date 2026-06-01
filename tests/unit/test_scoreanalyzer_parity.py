from __future__ import annotations

from pathlib import Path

from piano_difficulty.comparison.scoreanalyzer_parity import (
    CANONICAL_METRICS,
    build_row,
    compare_values,
    discover_piece_files,
    select_piece_files,
)


def test_discover_piece_files_is_deterministic_and_filtered(tmp_path: Path) -> None:
    root = tmp_path / "pieces"
    (root / "b").mkdir(parents=True)
    (root / "a").mkdir(parents=True)
    (root / "a" / "x.xml").write_text("<score-partwise/>")
    (root / "b" / "y.musicxml").write_text("<score-partwise/>")
    (root / "b" / "z.mxl").write_text("fake")
    (root / "a" / "skip.txt").write_text("x")

    found = discover_piece_files(root)
    rel = [str(path.relative_to(root)) for path in found]
    assert rel == ["a/x.xml", "b/y.musicxml", "b/z.mxl"]


def test_select_piece_files_applies_offset_and_count(tmp_path: Path) -> None:
    files = [tmp_path / f"{idx}.xml" for idx in range(5)]
    chosen = select_piece_files(files, count=2, start_offset=1)
    assert chosen == [files[1], files[2]]


def test_compare_values_handles_numbers_strings_and_missing() -> None:
    equal, delta = compare_values("speed", 10.0, 10.0)
    assert equal is True
    assert delta == 0.0

    equal, delta = compare_values("chordsRH", 30.49, 30.4)
    assert equal is True
    assert delta is not None

    equal, delta = compare_values("mode", "major", "minor")
    assert equal is False
    assert delta is None

    equal, delta = compare_values("tempo", None, 120)
    assert equal is False
    assert delta is None


def test_build_row_creates_wide_fields_and_counts_mismatches() -> None:
    og = {metric: 1 for metric in CANONICAL_METRICS}
    replica = {metric: 1 for metric in CANONICAL_METRICS}
    replica["mode"] = "minor"
    row = build_row("piece.xml", og, replica)
    assert row.piece_relpath == "piece.xml"
    assert row.status == "ok"
    assert row.mismatch_count == 1
    assert row.all_equal is False
    assert row.values["equal_mode"] is False
    assert row.values["equal_speed"] is True
