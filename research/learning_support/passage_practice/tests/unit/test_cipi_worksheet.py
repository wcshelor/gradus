"""Tests for S-X5 CIPI semantic review worksheet."""

from __future__ import annotations

from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "cipi_semantic_review_worksheet.md"


def test_worksheet_exists_and_has_required_fields():
    assert DOC.exists(), f"missing worksheet {DOC}"
    text = DOC.read_text()
    required = [
        "CIPI piece ID",
        "Passage",
        "Difficulty overview",
        "Human-observed semantics",
        "Likely semantic detectors",
        "Expected hypotheses",
        "Actual bundle",
        "Learner question",
        "Exercise action",
        "Reviewer",
    ]
    for field in required:
        assert field in text, f"field {field!r} missing from worksheet"


def test_worksheet_has_example_and_no_cipi_commit_warning():
    text = DOC.read_text()
    assert "Example row" in text
    assert "No CIPI files are committed" in text or "Do not commit CIPI" in text
    assert "synthetic" in text.lower()


def test_no_cipi_files_committed():
    # Ensure no CIPI music files are tracked in the worksheet fixtures
    # (Check that docs directory does not contain .mxl/.musicxml that looks like CIPI)
    cipi_like = list((Path(__file__).resolve().parents[2] / "docs").glob("*.mxl")) + list(
        (Path(__file__).resolve().parents[2] / "docs").glob("*.musicxml")
    )
    assert cipi_like == [], f"unexpected CIPI files in docs: {cipi_like}"
