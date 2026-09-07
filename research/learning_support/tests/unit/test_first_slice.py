"""LS-01 acceptance checks for the first learning-support slice.

Verify links resolve, required scenario coverage is present, exclusions are
explicit, the success rubric is reviewable, and the document distinguishes the
original specification from later LS implementation/evaluation work.
"""

from __future__ import annotations

import re
from pathlib import Path

LEARNING_SUPPORT = Path(__file__).resolve().parents[2]
SLICE_DOC = LEARNING_SUPPORT / "first_slice.md"
AREA_README = LEARNING_SUPPORT / "README.md"
REPO_ROOT = LEARNING_SUPPORT.parent.parent
PRIMARY_PLAN = (
    REPO_ROOT / "docs" / "Task_list_2026-09-05_flexible_piano_learning_support.md"
)
PROJECT_DIRECTION = REPO_ROOT / "docs" / "project_direction.md"
PASSAGE_PROTOTYPE = LEARNING_SUPPORT / "passage_practice" / "docs" / "prototype_v1.md"
PASSAGE_CONTRACTS = LEARNING_SUPPORT / "passage_practice" / "docs" / "contracts.md"
PASSAGE_ARCHITECTURE = (
    LEARNING_SUPPORT / "passage_practice" / "docs" / "architecture.md"
)

REQUIRED_SCENARIOS = ("S1", "S2", "S3", "S4", "S5", "S6", "S7")


def _text(path: Path) -> str:
    assert path.is_file(), f"expected file: {path}"
    return path.read_text()


def test_slice_doc_declares_original_spec_and_later_implementation() -> None:
    text = _text(SLICE_DOC)
    assert "original LS-01 specification" in text
    assert "later implemented and evaluated" in text
    assert "evaluation_ls10.md" in text
    assert "LS-01" in text


def test_slice_doc_links_resolve() -> None:
    text = _text(SLICE_DOC)
    targets = re.findall(r"\]\(([^)#][^)]*)\)", text)
    assert targets, "slice doc must link its authorities"
    for raw in targets:
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (SLICE_DOC.parent / raw).resolve()
        assert resolved.is_file(), f"broken link: {raw}"


def test_slice_doc_references_authorities() -> None:
    text = _text(SLICE_DOC)
    assert PRIMARY_PLAN.is_file()
    assert PROJECT_DIRECTION.is_file()
    assert PASSAGE_PROTOTYPE.is_file()
    assert PASSAGE_CONTRACTS.is_file()
    assert PASSAGE_ARCHITECTURE.is_file()
    for name in (
        "Task_list_2026-09-05_flexible_piano_learning_support.md",
        "project_direction.md",
        "prototype_v1.md",
        "contracts.md",
        "architecture.md",
    ):
        assert name in text, f"slice must reference {name}"


def test_slice_covers_all_required_scenarios() -> None:
    text = _text(SLICE_DOC)
    for scenario in REQUIRED_SCENARIOS:
        assert f"### {scenario} " in text, f"missing scenario {scenario}"
    # Each scenario must state expected behavior and a must-not.
    blocks = re.split(r"^### S\d+ ", text, flags=re.MULTILINE)[1:]
    assert len(blocks) == len(REQUIRED_SCENARIOS)
    for block in blocks:
        assert "Expected:" in block
        assert "Must not:" in block


def test_slice_requires_disagreement_journal_and_return_cases() -> None:
    text = _text(SLICE_DOC)
    lowered = text.lower()
    assert "disagree" in lowered  # S3: perceived difficulty vs ranking
    assert "journal-only" in lowered  # S4
    assert "withdraw" in lowered  # S5 variant
    assert "ignore my history" in lowered  # S5 variant
    assert "user-selected passage" in lowered  # S1 without hotspot
    assert "no history" in lowered  # S1/S2
    assert "unresolved" in lowered  # S7


def test_slice_states_abstention_and_exclusions() -> None:
    text = _text(SLICE_DOC)
    lowered = text.lower()
    assert "abstain" in lowered or "abstention" in lowered
    for excluded in (
        "live",
        "midi",
        "trait",
        "prescribed",
        "fingering",
        "deployment",
        "real learner data",
    ):
        assert excluded in lowered, f"exclusions must name: {excluded}"


def test_slice_keeps_effectiveness_unproven() -> None:
    text = _text(SLICE_DOC)
    assert "remains unproven" in text or "not measured learning benefit" in text


def test_slice_has_reviewable_rubric_and_next_step() -> None:
    text = _text(SLICE_DOC)
    assert "## 8. Success rubric" in text
    for scenario in REQUIRED_SCENARIOS:
        assert re.search(rf"^- {scenario}:", text, flags=re.MULTILINE), (
            f"rubric must judge {scenario}"
        )
    assert "LS-02" in text


def test_area_readme_links_slice() -> None:
    text = _text(AREA_README)
    assert "first_slice.md" in text
