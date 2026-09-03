from __future__ import annotations

import json
from pathlib import Path

from piano_difficulty.comparison.scoreanalyzer_parity_summary import main


def test_summary_cli_writes_json_and_returns_failure_on_mismatches(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "comparison.csv"
    out_json = tmp_path / "summary.json"
    csv_path.write_text(
        """piece_relpath,status,error,all_equal,mismatch_count,og_speed,replica_speed,delta_speed,equal_speed
piece1.xml,ok,,False,1,120,100,-20,False
piece2.xml,error,runner failed,False,1,100,100,0,True
"""
    )
    exit_code = main(
        [
            "--in-csv",
            str(csv_path),
            "--out-json",
            str(out_json),
            "--top-k",
            "2",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "[FAIL]" in captured.out
    assert "Top mismatching metrics" in captured.out
    assert out_json.exists()
    payload = json.loads(out_json.read_text())
    assert payload["summary"]["has_failures"] is True
    assert len(payload["errors"]) == 1


def test_summary_cli_returns_success_for_clean_csv(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "comparison.csv"
    out_json = tmp_path / "summary.json"
    csv_path.write_text(
        """piece_relpath,status,error,all_equal,mismatch_count,og_speed,replica_speed,delta_speed,equal_speed
piece1.xml,ok,,True,0,120,120,0,True
"""
    )
    exit_code = main(
        [
            "--in-csv",
            str(csv_path),
            "--out-json",
            str(out_json),
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[PASS]" in captured.out
    payload = json.loads(out_json.read_text())
    assert payload["summary"]["has_failures"] is False

