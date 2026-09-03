from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import pytest

from tests.harness.scoreanalyzer.scoreanalyzer_export import (
    DEFAULT_TIMEOUT_SECONDS,
    ExportInput,
    run_scoreanalyzer_export,
)


def test_run_scoreanalyzer_export_parses_noisy_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scoreanalyzer_root = tmp_path / "external" / "ScoreAnalyzer"
    pieces_root = scoreanalyzer_root / "pieces"
    pieces_root.mkdir(parents=True)

    source_path = tmp_path / "Example Piece.musicxml"
    source_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list />
</score-partwise>
""",
        encoding="utf-8",
    )

    def fake_run(args, cwd, check, capture_output, text, encoding, errors, timeout):
        assert cwd == scoreanalyzer_root
        assert args[0] == "php"
        assert args[1] == "scoreanalyzer_json.php"
        assert args[-2] == "--piece"
        assert timeout == DEFAULT_TIMEOUT_SECONDS
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout='<!doctype html>\n{"stats":{"fifths":-2,"mode":"major","nbmeasures":4,"quantise":8,"baseDuration":4,"tempo":120,"beats":4,"beatType":4,"quickestValue":8,"maxIntervalRH":7,"maxIntervalLH":5,"octavesRatioRH":12.5,"octavesRatioLH":8.0,"noteCounterRH":20,"noteCounterLH":18,"nbPositionsRH":3,"nbPositionsLH":4},"criteria":{"speed":42.5,"displacementsRH":10.0,"chordsRH":21.0,"harmonyRH":3.0,"displacementsLH":8.0,"chordsLH":11.0,"harmonyLH":2.0,"rhythm":5.0,"length":2,"speedDifficulty":3,"displacementsDifficulty":2,"chordsDifficulty":2,"harmonyDifficulty":1,"rhythmDifficulty":2,"lengthDifficulty":1,"tonalityDifficulty":2,"overallDifficulty":1.9}}\n',
            stderr="warning: nothing serious\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    out_dir = tmp_path / "out"
    result = run_scoreanalyzer_export(
        [ExportInput(source_path=source_path, metadata={"piece_id": "example"})],
        out_dir=out_dir,
        scoreanalyzer_root=scoreanalyzer_root,
    )

    assert result.matrix_csv_path.is_file()
    with result.matrix_csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "success"
    assert row["piece_id"] == "example"
    assert row["tonality"] == "2"
    assert row["overallDifficulty"] == "1.9"
    assert result.errors_csv_path is None


def test_run_scoreanalyzer_export_records_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scoreanalyzer_root = tmp_path / "external" / "ScoreAnalyzer"
    pieces_root = scoreanalyzer_root / "pieces"
    pieces_root.mkdir(parents=True)

    source_path = tmp_path / "timeout_piece.xml"
    source_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list />
</score-partwise>
""",
        encoding="utf-8",
    )

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["php"], timeout=15.0, output="partial", stderr="too slow")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out_dir = tmp_path / "out"
    result = run_scoreanalyzer_export(
        [ExportInput(source_path=source_path, metadata={"piece_id": "timeout"})],
        out_dir=out_dir,
        scoreanalyzer_root=scoreanalyzer_root,
    )

    assert result.errors_csv_path is not None
    assert result.errors_csv_path.is_file()
    with result.matrix_csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["status"] == "timeout"
    assert rows[0]["error_type"] == "TimeoutExpired"
    assert rows[0]["json_path"] == ""

