from __future__ import annotations

import csv
from pathlib import Path

from tests.harness.ceo_walkthrough.cipi_selection import (
    DEFAULT_CANONICAL_MANIFEST_CSV,
    DEFAULT_CURATION_MANIFEST_CSV,
    load_canonical_index,
    match_entry,
    plan_batch,
    resolve_dataset_root_for_ceo,
)
from tests.harness.ceo_walkthrough.manifest import CeoWalkthroughEntry, load_manifest

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

CANONICAL_COLUMNS = [
    "cipi_id", "movement", "piece_id", "piece_uid", "legacy_piece_uid",
    "composer", "work_name", "book", "henle", "uri",
    "dataset_relative_path", "legacy_dataset_relative_path",
    "upstream_path", "filename", "normalized_filename",
]


def _curated_entry(**overrides: str) -> CeoWalkthroughEntry:
    values = {
        "demo_id": "demo_piece",
        "composer": "Composer",
        "title": "Title",
        "henle": "4",
        "dataset_relative_path": "pieces/bach/piece.musicxml",
        "recognition_tier": "familiar",
        "demo_role": "role",
        "analyzer_led_note": "analyzer",
        "user_selected_note": "user",
        "disagreement_note": "disagreement",
        "caveat_note": "caveat",
    }
    values.update(overrides)
    return CeoWalkthroughEntry(**values, metadata={}, source_row_index=0)  # type: ignore[arg-type]


def _write_canonical(path: Path, rel_paths: list[str]) -> Path:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        for index, rel in enumerate(rel_paths):
            writer.writerow({
                "cipi_id": f"c-{index}", "movement": "1", "piece_id": f"p{index}",
                "piece_uid": f"uid{index}", "legacy_piece_uid": "",
                "composer": "C", "work_name": "W", "book": "", "henle": "4",
                "uri": "", "dataset_relative_path": rel,
                "legacy_dataset_relative_path": "", "upstream_path": "",
                "filename": Path(rel).name, "normalized_filename": "",
            })
    return path


def test_curated_paths_match_exactly_one_canonical_row() -> None:
    entries = load_manifest(DEFAULT_CURATION_MANIFEST_CSV)
    index = load_canonical_index(DEFAULT_CANONICAL_MANIFEST_CSV)
    assert len(entries) == 8
    for entry in entries:
        match = match_entry(entry, index)
        assert match.status == "matched", entry.demo_id
        assert match.cipi_row is not None
        assert match.cipi_row["dataset_relative_path"] == entry.dataset_relative_path


def test_unknown_path_gives_structured_missing_match(tmp_path: Path) -> None:
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/other.musicxml"])
    index = load_canonical_index(canonical)
    match = match_entry(_curated_entry(), index)
    assert match.status == "missing_catalog_match"
    assert match.cipi_row is None
    assert "pieces/bach/piece.musicxml" in match.reason


def test_duplicate_canonical_match_fails_loudly(tmp_path: Path) -> None:
    canonical = _write_canonical(
        tmp_path / "canon.csv",
        ["pieces/bach/piece.musicxml", "pieces/bach/piece.musicxml"],
    )
    index = load_canonical_index(canonical)
    match = match_entry(_curated_entry(), index)
    assert match.status == "duplicate_catalog_match"
    assert match.cipi_row is None


def test_explicit_dataset_root_wins(tmp_path: Path, monkeypatch) -> None:
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    env_root = tmp_path / "env"
    env_root.mkdir()
    monkeypatch.setenv("GRADUS_CIPI_ROOT", str(env_root))
    monkeypatch.delenv("GRADUS_DATASETS_CONFIG", raising=False)
    resolution = resolve_dataset_root_for_ceo(explicit)
    assert resolution.source == "cli"
    assert resolution.root == explicit


def test_missing_root_is_structured_and_uncreated(tmp_path: Path) -> None:
    missing = tmp_path / "not-there"
    assert not missing.exists()
    resolution = resolve_dataset_root_for_ceo(missing)
    assert resolution.source == "cli"
    assert resolution.exists is False
    assert not missing.exists(), "resolution must not create dataset roots"


def test_existing_files_resolve_to_absolute_paths(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_XML)
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/piece.musicxml"])
    (planned,) = plan_batch(
        [_curated_entry()], dataset_root=root, canonical_manifest_csv=canonical
    )
    assert planned.status == "ready"
    assert planned.source_path is not None and planned.source_path.is_absolute()
    assert planned.source_path.is_file()


def test_missing_files_do_not_stop_batch_planning(tmp_path: Path) -> None:
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_XML)
    canonical = _write_canonical(
        tmp_path / "canon.csv",
        ["pieces/bach/piece.musicxml", "pieces/bach/absent.musicxml"],
    )
    planned = plan_batch(
        [
            _curated_entry(demo_id="present", dataset_relative_path="pieces/bach/piece.musicxml"),
            _curated_entry(demo_id="absent", dataset_relative_path="pieces/bach/absent.musicxml"),
        ],
        dataset_root=root,
        canonical_manifest_csv=canonical,
    )
    assert [item.entry.demo_id for item in planned] == ["present", "absent"]
    assert planned[0].status == "ready"
    assert planned[1].status == "missing_source_file"
    assert planned[1].reason != ""


def test_pieces_dir_root_gets_diagnostic(tmp_path: Path) -> None:
    pieces = tmp_path / "cipi" / "pieces"
    (pieces / "bach").mkdir(parents=True)
    (pieces / "bach" / "piece.musicxml").write_text(FIXTURE_XML)
    canonical = _write_canonical(tmp_path / "canon.csv", ["pieces/bach/piece.musicxml"])
    (planned,) = plan_batch(
        [_curated_entry()], dataset_root=pieces, canonical_manifest_csv=canonical
    )
    assert planned.pieces_dir_hint is True
    assert planned.status == "ready"
    assert "pieces/" in planned.reason
