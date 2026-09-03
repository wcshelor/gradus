from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

from tests.harness.omr_pipeline.pdf_export import (
    discover_score_files,
    run_omr_pdf_export,
)


def test_discover_score_files_filters_to_mxl(tmp_path: Path) -> None:
    dataset_root = tmp_path / "oktav"
    keep = dataset_root / "keep.mxl"
    nested_keep = dataset_root / "nested" / "also_keep.mxl"
    ignore = dataset_root / "ignore.musicxml"
    keep.parent.mkdir(parents=True, exist_ok=True)
    nested_keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text("fake", encoding="utf-8")
    nested_keep.write_text("fake", encoding="utf-8")
    ignore.write_text("fake", encoding="utf-8")

    discovered = discover_score_files(dataset_root)

    assert discovered == sorted([keep, nested_keep], key=lambda path: str(path))


def test_run_omr_pdf_export_writes_pdfs_and_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_root = tmp_path / "oktav"
    first = dataset_root / "Alpha Piece.mxl"
    second = dataset_root / "nested" / "Beta Piece.mxl"
    first.parent.mkdir(parents=True, exist_ok=True)
    second.parent.mkdir(parents=True, exist_ok=True)
    first.write_text("fake", encoding="utf-8")
    second.write_text("fake", encoding="utf-8")

    fake_bin = tmp_path / "bin" / "mscore"
    fake_bin.parent.mkdir(parents=True, exist_ok=True)
    fake_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    commands: list[list[str]] = []

    def fake_run(args, cwd, check, capture_output, text, encoding, errors, timeout):
        del check, capture_output, text, encoding, errors, timeout
        commands.append(list(args))
        assert Path(args[0]) == fake_bin.resolve()
        assert cwd == dataset_root.resolve()
        assert "-R" in args
        assert "-s" in args
        assert "-w" in args
        output_index = args.index("-o") + 1
        output_path = Path(args[output_index])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4\n%fake\n")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="exported\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out_dir = tmp_path / "artifacts"
    summary = run_omr_pdf_export(
        dataset_root=dataset_root,
        out_dir=out_dir,
        musescore_bin=fake_bin,
        timeout_seconds=5.0,
    )

    assert summary["input_count"] == 2
    assert summary["success_count"] == 2
    assert summary["failure_count"] == 0
    assert summary["musescore_bin"] == str(fake_bin.resolve())
    assert summary["errors_csv_path"] is None
    assert summary["schema_version"] == "omr_pdf_export_summary.v1"
    assert summary["lane"] == "omr_pipeline"

    manifest_path = out_dir / "pdf_manifest.csv"
    summary_path = out_dir / "corpus_summary.json"
    pdf_dir = out_dir / "pdfs"
    log_dir = out_dir / "logs"

    assert manifest_path.is_file()
    assert summary_path.is_file()
    assert (pdf_dir / "Alpha Piece.pdf").is_file()
    assert (pdf_dir / "nested" / "Beta Piece.pdf").is_file()
    assert (log_dir / "Alpha Piece.stdout.txt").is_file()
    assert (log_dir / "nested" / "Beta Piece.stdout.txt").is_file()

    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["status"] for row in rows] == ["success", "success"]
    assert rows[0]["pdf_path"].endswith("pdfs/Alpha Piece.pdf")
    assert rows[1]["pdf_path"].endswith("pdfs/nested/Beta Piece.pdf")

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["failure_count"] == 0
    assert summary_payload["input_count"] == 2
    assert summary_payload["failed_source_paths"] == []
    assert summary_payload["schema_version"] == "omr_pdf_export_summary.v1"
    assert summary_payload["lane"] == "omr_pipeline"
    assert len(commands) == 2


def test_run_omr_pdf_export_records_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dataset_root = tmp_path / "oktav"
    source_path = dataset_root / "timeout.mxl"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("fake", encoding="utf-8")

    fake_bin = tmp_path / "bin" / "mscore"
    fake_bin.parent.mkdir(parents=True, exist_ok=True)
    fake_bin.write_text("#!/bin/sh\n", encoding="utf-8")

    def fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["mscore"], timeout=1.0, output="partial", stderr="too slow")

    monkeypatch.setattr(subprocess, "run", fake_run)

    out_dir = tmp_path / "artifacts"
    summary = run_omr_pdf_export(
        dataset_root=dataset_root,
        out_dir=out_dir,
        musescore_bin=fake_bin,
        timeout_seconds=1.0,
    )

    assert summary["input_count"] == 1
    assert summary["success_count"] == 0
    assert summary["failure_count"] == 1
    assert summary["errors_csv_path"] is not None
    assert summary["schema_version"] == "omr_pdf_export_summary.v1"
    assert summary["lane"] == "omr_pipeline"

    manifest_path = out_dir / "pdf_manifest.csv"
    errors_path = out_dir / "errors.csv"
    summary_path = out_dir / "corpus_summary.json"
    pdf_path = out_dir / "pdfs" / "timeout.pdf"

    assert manifest_path.is_file()
    assert errors_path.is_file()
    assert summary_path.is_file()
    assert not pdf_path.exists()

    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["status"] == "timeout"
    assert rows[0]["error_type"] == "TimeoutExpired"
    assert rows[0]["stdout_path"].endswith("timeout.stdout.txt")
    assert rows[0]["stderr_path"].endswith("timeout.stderr.txt")

    summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary_payload["failure_count"] == 1
    assert summary_payload["failed_source_paths"] == [str(source_path.resolve())]
    assert summary_payload["schema_version"] == "omr_pdf_export_summary.v1"
    assert summary_payload["lane"] == "omr_pipeline"
