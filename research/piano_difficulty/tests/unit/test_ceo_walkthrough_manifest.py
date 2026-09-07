from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tests.harness.ceo_walkthrough.cipi_selection import DEFAULT_CURATION_MANIFEST_CSV
from tests.harness.ceo_walkthrough.manifest import (
    REQUIRED_COLUMNS,
    load_manifest,
    validate_demo_id,
)

EXPECTED_ORDER = [
    "beethoven_fur_elise",
    "beethoven_bagatelle_119_10",
    "mozart_k545",
    "chopin_waltz_a_minor_kk_ivb_11",
    "chopin_prelude_e_minor_28_4",
    "chopin_prelude_a_major_28_7",
    "debussy_arabesque_1",
    "satie_gymnopedie_1",
]


def _write_manifest(path: Path, rows: list[dict[str, str]], fieldnames=None) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames or list(REQUIRED_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)
    return path


def _valid_row(**overrides: str) -> dict[str, str]:
    row = {
        "demo_id": "mozart_k545",
        "composer": "Wolfgang Amadeus Mozart",
        "title": "Piano Sonata Facile",
        "henle": "4",
        "dataset_relative_path": "pieces/mozart/x.musicxml",
        "recognition_tier": "familiar",
        "demo_role": "classical_texture",
        "analyzer_led_note": "analyzer note",
        "user_selected_note": "user note",
        "disagreement_note": "disagreement note",
        "caveat_note": "caveat note",
    }
    row.update(overrides)
    return row


def test_curated_manifest_loads_eight_rows_in_order() -> None:
    entries = load_manifest(DEFAULT_CURATION_MANIFEST_CSV)
    assert [entry.demo_id for entry in entries] == EXPECTED_ORDER
    assert all(entry.dataset_relative_path.startswith("pieces/") for entry in entries)
    assert all("/" not in entry.demo_id for entry in entries)


def test_curated_manifest_preserves_scenario_notes() -> None:
    entries = load_manifest(DEFAULT_CURATION_MANIFEST_CSV)
    by_id = {entry.demo_id: entry for entry in entries}
    assert by_id["satie_gymnopedie_1"].demo_role == "sparse_baseline"
    assert by_id["satie_gymnopedie_1"].caveat_note != ""
    assert by_id["mozart_k545"].analyzer_led_note != ""
    assert by_id["mozart_k545"].henle == "4"


def test_missing_required_columns_name_the_columns(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["demo_id", "composer"])
        writer.writeheader()
        writer.writerow({"demo_id": "x", "composer": "y"})
    with pytest.raises(ValueError, match="dataset_relative_path"):
        load_manifest(manifest)


def test_extra_columns_preserved_as_metadata(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [_valid_row()],
        fieldnames=[*REQUIRED_COLUMNS, "source_url"],
    )
    # rewrite with the extra value since _valid_row lacks it
    with manifest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["source_url"] = "https://example.invalid"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*REQUIRED_COLUMNS, "source_url"])
        writer.writeheader()
        writer.writerows(rows)
    (entry,) = load_manifest(manifest)
    assert entry.metadata["source_url"] == "https://example.invalid"


def test_empty_manifest_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [])
    with pytest.raises(ValueError, match="no rows"):
        load_manifest(manifest)


def test_blank_dataset_relative_path_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_valid_row(dataset_relative_path="  ")])
    with pytest.raises(ValueError, match="blank dataset_relative_path"):
        load_manifest(manifest)


def test_cells_are_trimmed(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_valid_row(composer="  Mozart  ", title=" Sonata ")])
    (entry,) = load_manifest(manifest)
    assert entry.composer == "Mozart"
    assert entry.title == "Sonata"


def test_duplicate_demo_id_fails(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_valid_row(), _valid_row()])
    with pytest.raises(ValueError, match="Duplicate demo_id"):
        load_manifest(manifest)


@pytest.mark.parametrize("bad_id", ["", "  ", "Has Space", "UPPER", "a/b", "../x", "a--b", "a__b", "trailing_"])
def test_unsafe_demo_ids_fail(bad_id: str) -> None:
    with pytest.raises(ValueError, match="[Dd]emo_id|Invalid demo_id"):
        validate_demo_id(bad_id)


@pytest.mark.parametrize("good_id", ["mozart_k545", "a", "x_1_2", "beethoven_fur_elise"])
def test_valid_slug_ids_pass(good_id: str) -> None:
    assert validate_demo_id(good_id) == good_id


def test_blank_scenario_notes_fail(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(
        manifest,
        [_valid_row(analyzer_led_note="", user_selected_note="", disagreement_note="")],
    )
    with pytest.raises(ValueError, match="scenario note"):
        load_manifest(manifest)


def test_blank_caveat_note_fails(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    _write_manifest(manifest, [_valid_row(caveat_note="   ")])
    with pytest.raises(ValueError, match="caveat_note"):
        load_manifest(manifest)


def test_missing_manifest_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "does-not-exist.csv")
