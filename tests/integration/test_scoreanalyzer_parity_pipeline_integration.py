from __future__ import annotations

import json
from pathlib import Path

from piano_difficulty.comparison import scoreanalyzer_parity_pipeline as pipeline


def test_run_pipeline_generates_json_summary_from_csv(tmp_path: Path, monkeypatch, capsys) -> None:
    out_csv = tmp_path / "comparison.csv"
    out_json = tmp_path / "summary.json"

    def fake_run_comparison(**_kwargs):
        out_csv.write_text(
            """piece_relpath,status,error,all_equal,mismatch_count,og_speed,replica_speed,delta_speed,equal_speed
piece1.xml,ok,,False,1,120,100,-20,False
"""
        )
        return 1

    monkeypatch.setattr(pipeline, "run_comparison", fake_run_comparison)

    exit_code = pipeline.run_pipeline(
        pieces_root=tmp_path / "pieces",
        count=1,
        start_offset=0,
        php_bin=Path("/tmp/php"),
        out_csv=out_csv,
        out_json=out_json,
        strict=False,
        include_raw_json_dir=None,
        top_k=5,
        show_matches=False,
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "[FAIL]" in captured.out
    assert out_csv.exists()
    assert out_json.exists()
    payload = json.loads(out_json.read_text())
    assert payload["summary"]["has_failures"] is True
    assert payload["top_mismatching_metrics"][0]["metric"] == "speed"


def test_run_pipeline_returns_two_for_bad_summary_input(tmp_path: Path, monkeypatch) -> None:
    out_csv = tmp_path / "comparison.csv"
    out_json = tmp_path / "summary.json"

    def fake_run_comparison(**_kwargs):
        out_csv.write_text("piece_relpath,status\nx,ok\n")
        return 0

    monkeypatch.setattr(pipeline, "run_comparison", fake_run_comparison)

    exit_code = pipeline.run_pipeline(
        pieces_root=tmp_path / "pieces",
        count=1,
        start_offset=0,
        php_bin=Path("/tmp/php"),
        out_csv=out_csv,
        out_json=out_json,
        strict=False,
        include_raw_json_dir=None,
        top_k=5,
        show_matches=False,
    )

    assert exit_code == 2

