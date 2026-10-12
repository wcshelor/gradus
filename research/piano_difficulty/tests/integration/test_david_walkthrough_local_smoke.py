"""David walkthrough smoke coverage.

Default tests use committed safe scores or tiny fixtures and never require
a private CIPI corpus. The full eight-piece run only executes when a local
CIPI root is configured and actually holds the curated files.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.harness.david_walkthrough.cipi_selection import (
    DEFAULT_CANONICAL_MANIFEST_CSV,
    DEFAULT_CURATION_MANIFEST_CSV,
)
from tests.harness.david_walkthrough.manifest import load_manifest
from tests.harness.david_walkthrough.runner import run_walkthrough
from tests.harness.shared.dataset_config import resolve_dataset_root

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SCORE = REPO_ROOT / "tests" / "fixtures" / "minimal_piano.musicxml"
SAFE_KNOWN_SCORE = (
    REPO_ROOT
    / "evaluation_scores"
    / "known_levels"
    / "cipi"
    / "beethoven"
    / "beethoven_bagatelle-a-major-op.-119,10-mvt1.musicxml"
)


def _configured_cipi_root() -> Path | None:
    resolution = resolve_dataset_root("cipi")
    if resolution.root is None or not resolution.exists:
        return None
    return resolution.root


def test_safe_known_score_runs_single_piece(tmp_path: Path) -> None:
    """Ordinary smoke test over a committed CIPI-safe score (David-CIPI-22)."""
    assert SAFE_KNOWN_SCORE.is_file()
    summary = run_walkthrough(
        manifest_csv=_single_row_manifest_for_known_score(tmp_path),
        out_dir=tmp_path / "out",
        dataset_root=REPO_ROOT / "evaluation_scores" / "known_levels" / "cipi",
        canonical_manifest_csv=_single_row_canonical(tmp_path),
    )
    assert summary["success_count"] == 1
    piece_dir = tmp_path / "out" / "beethoven_bagatelle_119_10"
    for name in (
        "analysis.json", "analysis.md", "analysis.html", "analysis.csv",
        "piece_context.json", "demo_notes.md",
    ):
        assert (piece_dir / name).is_file(), name
    assert (tmp_path / "out" / "index.json").is_file()
    assert (tmp_path / "out" / "index.md").is_file()


def _single_row_manifest_for_known_score(tmp_path: Path) -> Path:
    import csv

    path = tmp_path / "curated.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "demo_id", "composer", "title", "henle", "dataset_relative_path",
                "recognition_tier", "demo_role", "analyzer_led_note",
                "user_selected_note", "disagreement_note", "caveat_note",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "demo_id": "beethoven_bagatelle_119_10",
            "composer": "Ludwig van Beethoven",
            "title": "Bagatelle A major op. 119 no. 10",
            "henle": "3",
            "dataset_relative_path": "beethoven/beethoven_bagatelle-a-major-op.-119,10-mvt1.musicxml",
            "recognition_tier": "useful_control",
            "demo_role": "existing_preview_anchor",
            "analyzer_led_note": "a", "user_selected_note": "u",
            "disagreement_note": "d", "caveat_note": "c",
        })
    return path


def _single_row_canonical(tmp_path: Path) -> Path:
    import csv

    path = tmp_path / "canon.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cipi_id", "dataset_relative_path"])
        writer.writeheader()
        writer.writerow({
            "cipi_id": "x-31",
            "dataset_relative_path": "beethoven/beethoven_bagatelle-a-major-op.-119,10-mvt1.musicxml",
        })
    return path


def test_full_cipi_walkthrough_when_configured(tmp_path: Path) -> None:
    """End-to-end demo set on the David prep machine (David-CIPI-23)."""
    if not os.environ.get("GRADUS_CIPI_ROOT", "").strip():
        pytest.skip("GRADUS_CIPI_ROOT is not configured")
    root = _configured_cipi_root()
    if root is None:
        pytest.skip("CIPI root resolved but does not exist")
    entries = load_manifest(DEFAULT_CURATION_MANIFEST_CSV)
    effective = root.parent if root.name.lower() == "pieces" else root
    missing = [
        entry.demo_id
        for entry in entries
        if not (effective / entry.dataset_relative_path).is_file()
    ]
    if missing:
        pytest.skip(f"CIPI root lacks curated files: {missing}")
    summary = run_walkthrough(
        manifest_csv=DEFAULT_CURATION_MANIFEST_CSV,
        out_dir=tmp_path / "out",
        dataset_root=root,
        canonical_manifest_csv=DEFAULT_CANONICAL_MANIFEST_CSV,
    )
    assert summary["piece_count"] == 8
    assert summary["success_count"] == 8, json.dumps(summary["results"], indent=2)
    assert (tmp_path / "out" / "index.md").is_file()
