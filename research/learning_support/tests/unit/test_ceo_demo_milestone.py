"""LS-11 acceptance checks for the CEO walkthrough milestone plan.

Documentation-only task: verify the milestone doc exists, its local links
resolve, DEMO-01–DEMO-10 are all specified, the three-area plan references
it and marks LS-11 complete, and scope guards hold (thin harness, no live
feedback, no real data, no product claims). No demo code is built here.
"""

from __future__ import annotations

import re
from pathlib import Path

LEARNING_SUPPORT = Path(__file__).resolve().parents[2]
MILESTONE_DOC = LEARNING_SUPPORT / "ceo_demo_milestone_2026-09-06.md"
REPO_ROOT = LEARNING_SUPPORT.parent.parent
PRIMARY_PLAN = (
    REPO_ROOT / "docs" / "Task_list_2026-09-05_flexible_piano_learning_support.md"
)

REQUIRED_TASKS = tuple(f"DEMO-{i:02d}" for i in range(1, 11))

REQUIRED_GUARDS = (
    "thin presentation harness",
    "no live midi/audio",
    "no real learner data",
    "synthetic",
    "unproven",
    "pending lead review",
)

FORBIDDEN_WORDS = (
    "production-ready",
    "deployed",
    "statistically significant",
    "guarantees",
    "validates",
    "validated",
)


def _text(path: Path) -> str:
    assert path.is_file(), f"expected file: {path}"
    return path.read_text()


def test_milestone_doc_is_planning_only() -> None:
    text = _text(MILESTONE_DOC)
    assert "planning only" in text
    assert "LS-11" in text


def test_milestone_links_resolve() -> None:
    text = _text(MILESTONE_DOC)
    targets = re.findall(r"\]\(([^)#][^)]*)\)", text)
    assert targets, "milestone doc must link its authorities"
    for raw in targets:
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (MILESTONE_DOC.parent / raw).resolve()
        assert resolved.is_file(), f"broken link: {raw}"


def test_all_demo_tasks_specified() -> None:
    text = _text(MILESTONE_DOC)
    for task_id in REQUIRED_TASKS:
        assert f"### {task_id}" in text, f"{task_id} section missing"
        assert text.count(task_id) >= 2, f"{task_id} needs scope beyond its heading"
    assert "Done when:" in text
    assert text.count("Done when:") >= len(REQUIRED_TASKS)


def test_plan_references_milestone_and_closes_ls11() -> None:
    plan = _text(PRIMARY_PLAN)
    assert MILESTONE_DOC.name in plan
    assert "LS-11 complete" in plan
    assert "CEO walkthrough prototype" in plan


def test_scope_guards_hold_without_product_claims() -> None:
    lowered = _text(MILESTONE_DOC).lower()
    for guard in REQUIRED_GUARDS:
        assert guard in lowered, f"required guard {guard!r} missing"
    for word in FORBIDDEN_WORDS:
        assert re.search(rf"\b{re.escape(word)}\b", lowered) is None, (
            f"product claim {word!r} in milestone plan"
        )


def test_demo_stays_modular_not_difficulty_centered() -> None:
    text = _text(MILESTONE_DOC)
    assert "difficulty == ()" in text
    assert "one source of evidence" in text
    assert "USER_SELECTED" in text and "ANALYZER_SUGGESTED" in text
