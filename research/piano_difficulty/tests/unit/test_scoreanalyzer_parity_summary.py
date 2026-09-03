from __future__ import annotations

from pathlib import Path

from piano_difficulty.comparison.scoreanalyzer_parity_summary import build_report


def _write_csv(path: Path, content: str) -> None:
    path.write_text(content)


def test_build_report_detects_mismatches_and_errors(tmp_path: Path) -> None:
    csv_path = tmp_path / "comparison.csv"
    _write_csv(
        csv_path,
        """piece_relpath,status,error,all_equal,mismatch_count,og_speed,replica_speed,delta_speed,equal_speed,og_mode,replica_mode,delta_mode,equal_mode
piece1.xml,ok,,True,0,120,120,0.0,True,major,major,,True
piece2.xml,ok,,False,1,100,105,5.0,False,major,major,,True
piece3.xml,error,boom,False,2,90,,,"",minor,major,,False
""",
    )
    report = build_report(csv_path, top_k=5, show_matches=False)
    summary = report["summary"]
    assert summary["row_count"] == 3
    assert summary["success_count"] == 2
    assert summary["error_count"] == 1
    assert summary["mismatch_piece_count"] == 2
    assert summary["has_failures"] is True
    assert report["top_mismatching_metrics"][0]["metric"] in {"mode", "speed"}
    pieces = {item["piece_relpath"]: item for item in report["pieces"]}
    assert "piece1.xml" not in pieces
    assert pieces["piece2.xml"]["mismatch_count"] == 1
    assert pieces["piece3.xml"]["status"] == "error"


def test_build_report_show_matches_includes_clean_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "comparison.csv"
    _write_csv(
        csv_path,
        """piece_relpath,status,error,all_equal,mismatch_count,og_speed,replica_speed,delta_speed,equal_speed
piece1.xml,ok,,True,0,120,120,0.0,True
""",
    )
    report = build_report(csv_path, top_k=3, show_matches=True)
    assert report["summary"]["has_failures"] is False
    assert len(report["pieces"]) == 1
    assert report["pieces"][0]["piece_relpath"] == "piece1.xml"


def test_build_report_rejects_missing_required_columns(tmp_path: Path) -> None:
    csv_path = tmp_path / "comparison.csv"
    _write_csv(csv_path, "piece_relpath,status\nx,ok\n")
    try:
        build_report(csv_path)
    except ValueError as exc:
        assert "Missing required base columns" in str(exc)
    else:
        raise AssertionError("Expected ValueError for malformed CSV")

