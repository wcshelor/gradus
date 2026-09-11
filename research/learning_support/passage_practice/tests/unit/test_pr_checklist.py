"""Tests for S-X4 review checklist for semantic PRs."""

from __future__ import annotations

from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "semantic_pr_checklist.md"

REQUIRED_SECTIONS = [
    "Provenance",
    "Uncertainty",
    "Source Refs",
    "Layer Boundaries",
    "Learner Caveats",
    "Positive/Negative Tests",
    "No Hidden LLM Dependency",
]


def test_checklist_exists_and_covers_required_sections():
    assert DOC.exists(), f"missing checklist {DOC}"
    text = DOC.read_text()
    for section in REQUIRED_SECTIONS:
        assert section in text, f"section {section!r} missing from checklist"
    # Must mention synthetic_data, provenance, confidence_method, source_refs, no hidden LLM
    assert "synthetic_data" in text or "synthetic" in text.lower()
    assert "confidence_method" in text
    assert "SourceRef" in text
    assert "LLM" in text


def test_checklist_has_checkbox_items():
    text = DOC.read_text()
    # At least one checkbox per section
    assert text.count("- [ ]") >= len(REQUIRED_SECTIONS)
