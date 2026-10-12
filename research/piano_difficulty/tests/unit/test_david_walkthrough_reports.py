from __future__ import annotations

import csv
import json
from pathlib import Path

from tests.harness.david_walkthrough.cipi_selection import (
    DEFAULT_CURATION_MANIFEST_CSV,
    plan_batch,
)
from tests.harness.david_walkthrough.manifest import load_manifest
from tests.harness.david_walkthrough.reports import (
    REVIEWER_CHECKLIST,
    top_section_summary,
    write_demo_notes,
    write_failures_csv,
    write_index_json,
    write_index_markdown,
    write_piece_context,
)
from tests.harness.david_walkthrough.runner import analyze_single_piece

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SCORE = REPO_ROOT / "tests" / "fixtures" / "minimal_piano.musicxml"


def _planned_single(tmp_path: Path):
    root = tmp_path / "cipi"
    (root / "pieces" / "bach").mkdir(parents=True)
    (root / "pieces" / "bach" / "piece.musicxml").write_text(FIXTURE_SCORE.read_text())
    canonical = tmp_path / "canon.csv"
    with canonical.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["cipi_id", "dataset_relative_path"])
        writer.writeheader()
        writer.writerow({"cipi_id": "c-1", "dataset_relative_path": "pieces/bach/piece.musicxml"})
    from tests.harness.david_walkthrough.manifest import DavidWalkthroughEntry

    entry = DavidWalkthroughEntry(
        demo_id="demo_piece", composer="C", title="T", henle="4",
        dataset_relative_path="pieces/bach/piece.musicxml",
        recognition_tier="familiar", demo_role="role",
        analyzer_led_note="analyzer framing", user_selected_note="user framing",
        disagreement_note="disagreement framing", caveat_note="caveat framing",
        metadata={}, source_row_index=0,
    )
    (planned,) = plan_batch([entry], dataset_root=root, canonical_manifest_csv=canonical)
    return planned


def test_piece_context_success_has_required_keys(tmp_path: Path) -> None:
    planned = _planned_single(tmp_path)
    payload = analyze_single_piece(planned.source_path, tmp_path / "piece")
    out = write_piece_context(
        tmp_path / "piece", planned, status="success",
        artifact_paths={"analysis.json": "x"}, versions={"piano-difficulty": "0.1.0"},
        timestamp="2026-09-07T00:00:00Z", payload=payload,
    )
    context = json.loads(out.read_text())
    assert context["demo_id"] == "demo_piece"
    assert context["status"] == "success"
    assert context["manifest"]["demo_role"] == "role"
    assert context["cipi"]["match_status"] == "matched"
    assert context["resolution"]["source_path"].endswith("piece.musicxml")
    assert context["artifacts"]["analysis.json"] == "x"
    assert context["runtime_versions"]["piano-difficulty"] == "0.1.0"
    assert context["timestamp"] == "2026-09-07T00:00:00Z"
    assert context["analysis"]["profile_ids"] == ["difficulty_aspects", "difficulty_overview"]


def test_piece_context_failure_includes_status_and_reason(tmp_path: Path) -> None:
    planned = _planned_single(tmp_path)
    out = write_piece_context(
        tmp_path / "piece", planned, status="missing_source_file",
        reason="Score file not found.", versions={}, timestamp="t",
    )
    context = json.loads(out.read_text())
    assert context["status"] == "missing_source_file"
    assert context["reason"] == "Score file not found."
    assert "analysis" not in context


def test_demo_notes_success_sections(tmp_path: Path) -> None:
    planned = _planned_single(tmp_path)
    payload = analyze_single_piece(planned.source_path, tmp_path / "piece")
    out = write_demo_notes(
        tmp_path / "piece", planned, payload=payload, status="success"
    )
    notes = out.read_text()
    assert "demo_piece" in notes or "T" in notes
    assert "role" in notes
    assert "analyzer framing" in notes
    assert "user framing" in notes
    assert "disagreement framing" in notes
    assert "caveat framing" in notes
    assert "Top analyzer section" in notes


def test_demo_notes_failure_explains_unavailability(tmp_path: Path) -> None:
    planned = _planned_single(tmp_path)
    out = write_demo_notes(
        tmp_path / "piece", planned, payload=None,
        status="missing_source_file", reason="Score file not found.",
    )
    notes = out.read_text()
    assert "unavailable" in notes
    assert "missing_source_file" in notes


def test_top_section_summary_handles_missing_analysis() -> None:
    assert top_section_summary(None) is None
    assert top_section_summary({}) is None
    assert top_section_summary({"analysis_profiles": []}) is None


def test_index_json_summary_shape(tmp_path: Path) -> None:
    entries = load_manifest(DEFAULT_CURATION_MANIFEST_CSV)
    results = [
        {"demo_id": entry.demo_id, "status": "success", "reason": "",
         "piece_dir": str(tmp_path / entry.demo_id), "source_path": "s"}
        for entry in entries
    ]
    payload = write_index_json(tmp_path, entries, results, manifest_csv="m.csv")
    assert payload["manifest_csv"] == "m.csv"
    assert payload["output_root"] == str(tmp_path)
    assert payload["piece_count"] == 8
    assert payload["success_count"] == 8
    assert payload["failure_count"] == 0
    assert [piece["demo_id"] for piece in payload["pieces"]] == [
        entry.demo_id for entry in entries
    ]
    assert all("artifacts" in piece for piece in payload["pieces"])


def test_index_markdown_lists_all_pieces_with_links(tmp_path: Path) -> None:
    entries = load_manifest(DEFAULT_CURATION_MANIFEST_CSV)
    results = [
        {"demo_id": entry.demo_id, "status": "success", "reason": "",
         "piece_dir": str(tmp_path / entry.demo_id), "source_path": "s"}
        for entry in entries
    ]
    out = write_index_markdown(tmp_path, entries, results)
    text = out.read_text()
    for entry in entries:
        assert entry.demo_id in text
    assert "analysis.html" in text
    assert "analysis.md" in text
    assert "demo_notes.md" in text


def test_index_markdown_reviewer_checklist_covers_claim_boundaries(tmp_path: Path) -> None:
    entries = load_manifest(DEFAULT_CURATION_MANIFEST_CSV)[:1]
    results = [
        {"demo_id": entries[0].demo_id, "status": "success", "reason": "",
         "piece_dir": "d", "source_path": "s"}
    ]
    text = write_index_markdown(tmp_path, entries, results).read_text()
    lowered = text.lower()
    for fragment in ("score facts", "system ranking", "learner self-report",
                     "system hypothesis", "limitations"):
        assert fragment in lowered, fragment
    assert len(REVIEWER_CHECKLIST) == 5


def test_failures_csv_written_for_bad_rows(tmp_path: Path) -> None:
    planned = [_planned_single(tmp_path)]
    results = [{"demo_id": "demo_piece", "status": "missing_source_file",
                "reason": "gone", "piece_dir": "d", "source_path": ""}]
    out = write_failures_csv(tmp_path, planned, results)
    assert out is not None and out.name == "failures.csv"
    with out.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["demo_id"] == "demo_piece"
    assert rows[0]["phase"] == "missing_source_file"
    assert rows[0]["reason"] == "gone"
    assert rows[0]["source_path"].endswith("piece.musicxml")


def test_failures_csv_absent_when_all_succeed(tmp_path: Path) -> None:
    planned = [_planned_single(tmp_path)]
    (tmp_path / "failures.csv").write_text("stale")
    results = [{"demo_id": "demo_piece", "status": "success",
                "reason": "", "piece_dir": "d", "source_path": "s"}]
    assert write_failures_csv(tmp_path, planned, results) is None
    assert not (tmp_path / "failures.csv").exists()
