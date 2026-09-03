from __future__ import annotations

from pathlib import Path

from piano_difficulty.difficulty_analysis.registry import PROFILE_REGISTRY
from tests.harness.yan2023.boundary import (
    EXPERIMENTAL_FEATURE_STATUSES,
    LANE_ID,
    build_boundary_report,
)


def test_scoreanalyzer_reference_is_only_runtime_profile() -> None:
    assert set(PROFILE_REGISTRY) == {"scoreanalyzer_reference"}


def test_yan2023_lane_is_not_registered_as_runtime_profile() -> None:
    assert LANE_ID not in PROFILE_REGISTRY


def test_yan2023_boundary_report_points_to_separate_artifact_root() -> None:
    report = build_boundary_report()
    assert report.allowed_artifact_root == "tests/artifacts/yan2023"
    assert any("scoreanalyzer_parity" in rule for rule in report.boundary_rules)


def test_yan2023_feature_status_inventory_covers_blocked_and_proxyable_work() -> None:
    statuses = set(EXPERIMENTAL_FEATURE_STATUSES.values())
    assert {"implemented", "proxyable", "blocked"} <= statuses


def test_analysis_lanes_doc_declares_lane_structure() -> None:
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "analysis_lanes.md"
    text = doc_path.read_text()
    assert "Lane 1: Yan replication / extension" in text
    assert "Lane 2: Dataset staging and cataloging" in text
    assert "Lane 3: OMR pipeline prototyping" in text
    assert "Lane 4: Difficulty Dynamics" in text
    assert "Lane 5: Matrix evaluation" in text


def test_scoreanalyzer_docs_cover_displacement_trace_workflow() -> None:
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "analysis_lanes.md"
    text = doc_path.read_text()
    assert "scoreanalyzer" in text
    assert "tests/artifacts/scoreanalyzer_parity/" in text
