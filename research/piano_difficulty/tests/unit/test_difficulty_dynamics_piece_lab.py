from __future__ import annotations

import csv
from pathlib import Path

from tests.harness.difficulty_dynamics.piece_lab import load_piece_lab_manifest


def test_piece_lab_manifest_loader_resolves_relative_paths_and_optional_fields(tmp_path: Path) -> None:
    manifest_path = tmp_path / "piece_lab.csv"
    score_path = tmp_path / "scores" / "piece-a.musicxml"
    score_path.parent.mkdir(parents=True, exist_ok=True)
    score_path.write_text("<score-partwise />", encoding="utf-8")

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "score_id",
                "title",
                "composer",
                "score_path",
                "learned_by_user",
                "known_hard_measures",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "score_id": "piece-a",
                "title": "Piece A",
                "composer": "Composer A",
                "score_path": "scores/piece-a.musicxml",
                "learned_by_user": "yes",
                "known_hard_measures": "12-16",
                "notes": "octave passage",
            }
        )

    entries = load_piece_lab_manifest(manifest_path)

    assert len(entries) == 1
    assert entries[0].piece_id == "piece-a"
    assert entries[0].score_path == score_path.resolve()
    assert entries[0].learned_by_user is True
    assert entries[0].known_hard_measures == "12-16"
