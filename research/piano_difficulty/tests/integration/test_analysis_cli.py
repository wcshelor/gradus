from __future__ import annotations

import json
from pathlib import Path

from piano_difficulty.difficulty_analysis.batch import analyze_batch
from piano_difficulty.cli.main import main

FEATURE_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
REAL_MXL_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "real_mxl_basic_grand_staff.mxl"
)


def test_cli_analyze_json_and_markdown(tmp_path: Path, monkeypatch, capsys) -> None:
    score_path = tmp_path / "feature.musicxml"
    score_path.write_text(FEATURE_FIXTURE_PATH.read_text())

    monkeypatch.setattr(
        "sys.argv",
        ["piano-difficulty", "analyze", str(score_path), "--format", "json"],
    )
    assert main() == 0
    json_payload = json.loads(capsys.readouterr().out)
    assert json_payload["analysis_profiles"][0]["profile_id"] == "difficulty_overview"

    monkeypatch.setattr(
        "sys.argv",
        ["piano-difficulty", "analyze", str(score_path), "--format", "markdown"],
    )
    assert main() == 0
    markdown = capsys.readouterr().out
    assert "## Dominant factors" in markdown
    assert "## Candidate high-demand sections" in markdown


def test_cli_analyze_batch_writes_outputs(tmp_path: Path, monkeypatch, capsys) -> None:
    input_dir = tmp_path / "scores"
    input_dir.mkdir()
    first = input_dir / "b.musicxml"
    second = input_dir / "a.musicxml"
    first.write_text(FEATURE_FIXTURE_PATH.read_text())
    second.write_text(FEATURE_FIXTURE_PATH.read_text().replace("Feature Fixture", "Alpha"))
    out_dir = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv",
        [
            "piano-difficulty",
            "analyze-batch",
            str(input_dir),
            "--out-dir",
            str(out_dir),
            "--write-csv",
        ],
    )
    assert main() == 0
    summary = json.loads(capsys.readouterr().out)

    assert summary["file_count"] == 2
    assert (out_dir / "a.json").exists()
    assert (out_dir / "b.json").exists()
    assert (out_dir / "corpus_summary.json").exists()
    assert (out_dir / "features.csv").exists()
    assert (out_dir / "analysis_dimensions.csv").exists()


def test_cli_analyze_batch_reports_partial_failures(tmp_path: Path, monkeypatch, capsys) -> None:
    input_dir = tmp_path / "scores"
    input_dir.mkdir()
    valid = input_dir / "valid.mxl"
    malformed = input_dir / "broken.mxl"
    valid.write_bytes(REAL_MXL_FIXTURE_PATH.read_bytes())
    malformed.write_text("not a zip archive")
    out_dir = tmp_path / "out"

    monkeypatch.setattr(
        "sys.argv",
        [
            "piano-difficulty",
            "analyze-batch",
            str(input_dir),
            "--out-dir",
            str(out_dir),
        ],
    )
    assert main() == 1
    summary = json.loads(capsys.readouterr().out)

    assert summary["file_count"] == 2
    assert summary["success_count"] == 1
    assert summary["failure_count"] == 1
    assert summary["errors_csv"] == str(out_dir / "errors.csv")
    assert (out_dir / "valid.json").exists()
    assert not (out_dir / "broken.json").exists()
    assert (out_dir / "corpus_summary.json").exists()
    assert (out_dir / "errors.csv").exists()
    assert not (out_dir / "features.csv").exists()
    assert not (out_dir / "analysis_dimensions.csv").exists()

    corpus_summary = json.loads((out_dir / "corpus_summary.json").read_text())
    assert corpus_summary["file_count"] == 2
    assert corpus_summary["success_count"] == 1
    assert corpus_summary["failure_count"] == 1
    assert corpus_summary["schema_version"] == "batch_summary.v2"
    assert corpus_summary["scores"] == [
        {
            "error_type": "ValueError",
            "message": f"File '{malformed}' is not a valid MXL archive.",
            "source_path": str(malformed),
            "status": "failure",
        },
        {
            "json_path": str(out_dir / "valid.json"),
            "source_path": str(valid),
            "status": "success",
        },
    ]
    assert (out_dir / "errors.csv").read_text().splitlines() == [
        "source_path,error_type,message",
        f"{malformed},ValueError,File '{malformed}' is not a valid MXL archive.",
    ]


def test_analyze_batch_returns_failures_instead_of_raising(tmp_path: Path) -> None:
    input_dir = tmp_path / "scores"
    input_dir.mkdir()
    valid = input_dir / "valid.musicxml"
    malformed = input_dir / "broken.mxl"
    valid.write_text(FEATURE_FIXTURE_PATH.read_text())
    malformed.write_text("not a zip archive")
    out_dir = tmp_path / "out"

    batch = analyze_batch(input_dir, out_dir=out_dir)

    assert [path.name for path in batch.payload_paths] == ["valid.json"]
    assert len(batch.failures) == 1
    assert batch.failures[0].source_path == malformed
    assert batch.failures[0].error_type == "ValueError"
    assert batch.errors_csv_path == out_dir / "errors.csv"


def test_explicit_profile_replaces_default_and_output_files_match(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["piano-difficulty", "analyze", str(FEATURE_FIXTURE_PATH),
                                    "--profile", "scoreanalyzer_reference", "--format", "json"])
    assert main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert [p["profile_id"] for p in payload["analysis_profiles"]] == ["scoreanalyzer_reference"]
    monkeypatch.setattr("sys.argv", ["piano-difficulty", "analyze", str(FEATURE_FIXTURE_PATH),
                                    "--out-dir", str(tmp_path), "--window", "beat",
                                    "--window-size", "1", "--hand", "right"])
    assert main() == 0
    assert "Candidate high-demand sections" in capsys.readouterr().out
    saved = json.loads((tmp_path / "analysis.json").read_text())
    assert saved["analysis_profiles"][0]["hand_mode"] == "right"
    assert (tmp_path / "analysis.html").is_file()
    assert (tmp_path / "analysis.csv").is_file()


def test_batch_slug_collisions_preserve_all_results(tmp_path):
    inputs = tmp_path / "scores"
    inputs.mkdir()
    for name in ("a.xml", "a.musicxml", "a-2.xml", "corpus_summary.xml"):
        (inputs / name).write_text(FEATURE_FIXTURE_PATH.read_text())
    result = analyze_batch(inputs, out_dir=tmp_path / "reports")
    assert len(set(result.payload_paths)) == 4
    assert result.corpus_summary_path not in result.payload_paths
    assert all(json.loads(path.read_text())["analysis_profiles"] for path in result.payload_paths)
