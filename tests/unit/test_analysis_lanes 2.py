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
    assert "scoreanalyzer_parity" not in report.allowed_artifact_root
    assert any("Do not modify or shadow scoreanalyzer parity modules." == rule for rule in report.boundary_rules)


def test_yan2023_feature_status_inventory_covers_blocked_and_proxyable_work() -> None:
    statuses = set(EXPERIMENTAL_FEATURE_STATUSES.values())
    assert statuses == {"implemented", "proxyable", "blocked"}
    assert EXPERIMENTAL_FEATURE_STATUSES["pressing_velocity_entropy"] == "blocked"
    assert EXPERIMENTAL_FEATURE_STATUSES["note_density"] == "implemented"


def test_analysis_lanes_doc_declares_lane_structure() -> None:
    doc_path = Path(__file__).resolve().parents[2] / "docs" / "analysis_lanes.md"
    content = doc_path.read_text(encoding="utf-8")

    assert "Lane 1: ScoreAnalyzer parity" in content
    assert "Lane 2: Yan paper replication" in content
    assert "Lane 3: Yan-inspired repo experiments" in content
    assert "Lane 4: Oktav thesis dataset operations" in content
    assert "Lane 5: Difficulty-prediction experiments" in content
    assert "Lane 6: Difficulty-clustering experiments" in content


def test_scoreanalyzer_docs_cover_displacement_trace_workflow() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    lane_doc = (repo_root / "docs" / "analysis_lanes.md").read_text(encoding="utf-8")
    harness_readme = (repo_root / "tests" / "harness" / "scoreanalyzer" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "scoreanalyzer_displacement_trace.py" in readme
    assert "stable coordinate match" in readme
    assert "measure number and attack index" in lane_doc
    assert "displacement trace" in harness_readme
    assert "OG displacement rows are matched by stable musical coordinates" in harness_readme
