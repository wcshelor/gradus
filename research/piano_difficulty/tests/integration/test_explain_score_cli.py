from __future__ import annotations

from pathlib import Path

from piano_difficulty.cli.explain_score import main

FEATURE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
REAL_MXL_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "real_mxl_basic_grand_staff.mxl"
)


def test_explain_score_cli_renders_verbose_report_for_musicxml(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["explain_score", str(FEATURE_FIXTURE_PATH)],
    )

    assert main() == 0
    output = capsys.readouterr().out

    assert "Verbose Extraction Report" in output
    assert f"Path: {FEATURE_FIXTURE_PATH}" in output
    assert "Feature Records" in output
    assert "Analysis Profiles" in output


def test_explain_score_cli_supports_extract_only_for_mxl(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["explain_score", str(REAL_MXL_FIXTURE_PATH), "--extract-only"],
    )

    assert main() == 0
    output = capsys.readouterr().out

    assert f"Path: {REAL_MXL_FIXTURE_PATH}" in output
    assert "Profiles: 0" in output
    assert "Feature Records" in output
