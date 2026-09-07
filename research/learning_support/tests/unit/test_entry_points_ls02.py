"""LS-02 acceptance checks: entry-point reconciliation map.

Verify the implementation map exists with working links, identifies reused
contracts / remaining pieces / affected work packages / required tests for both
entries, and records the accepted passage-first design plus later LS runtime
subset. The hotspot regression is verified by the full suite run.
"""

from __future__ import annotations

import re
from pathlib import Path

LEARNING_SUPPORT = Path(__file__).resolve().parents[2]
PASSAGE_PRACTICE = LEARNING_SUPPORT / "passage_practice"
MAP_DOC = PASSAGE_PRACTICE / "docs" / "entry_points.md"
MODELS_DIR = PASSAGE_PRACTICE / "src" / "passage_practice" / "models"


def _text(path: Path) -> str:
    assert path.is_file(), f"expected file: {path}"
    return path.read_text()


def test_map_declares_ls02_and_later_runtime_subset() -> None:
    text = _text(MAP_DOC)
    assert "LS-02" in text
    assert "LS-03–LS-07 subset now\nimplemented" in text
    assert "original LS-02 change was\nprose-only" in text
    assert "D-013" in text


def test_map_links_resolve() -> None:
    text = _text(MAP_DOC)
    targets = re.findall(r"\]\(([^)#][^)]*)\)", text)
    assert targets, "map must link its authorities"
    for raw in targets:
        if raw.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = (MAP_DOC.parent / raw).resolve()
        assert resolved.is_file(), f"broken link: {raw}"


def test_map_identifies_reused_contracts_remaining_pieces_and_owners() -> None:
    text = _text(MAP_DOC)
    for contract in ("ScorePosition", "SourceRef", "Passage", "View", "D-012"):
        assert contract in text, f"map must name reused contract: {contract}"
    for remaining in ("T05.2", "T05.3", "LS-03a"):
        assert remaining in text, f"map must name remaining or implemented piece: {remaining}"
    for owner in ("WP-02", "WP-05", "WP-06", "WP-08", "WP-14", "WP-15"):
        assert owner in text, f"map must name affected package: {owner}"


def test_map_covers_required_tests_for_both_entries() -> None:
    text = _text(MAP_DOC)
    lowered = text.lower()
    assert "manual-region" in lowered or "manual region" in lowered
    assert "baseline" in lowered
    assert "controlled" in lowered
    assert "T14.2" in text and "T14.3" in text


def test_local_plans_no_longer_imply_hotspot_gate() -> None:
    readme = _text(PASSAGE_PRACTICE / "README.md")
    assert "user-selected" in readme
    assert "not a gate" in readme
    architecture = _text(PASSAGE_PRACTICE / "docs" / "architecture.md")
    assert "controlled entry" in architecture
    prototype = _text(PASSAGE_PRACTICE / "docs" / "prototype_v1.md")
    assert "requires no" in prototype and "hotspot ID" in prototype
    work_packages = _text(PASSAGE_PRACTICE / "WORK_PACKAGES.md")
    assert "Ordinary passage observations remain valid" in work_packages
    assert "LS-03a" in work_packages


def test_adapter_decision_records_accepted_design_and_ls_runtime_note() -> None:
    text = _text(PASSAGE_PRACTICE / "docs" / "decisions.md")
    decision = text.split("### D-013", 1)[1].split("### ", 1)[0]
    assert "minimal LS runtime boundary implemented" in decision
    assert "PassageInvestigation" in decision
    assert "selection_origin" in decision
    assert "no dependency loop" in decision
    map_text = _text(MAP_DOC)
    assert "LS-03a/LS-05 now implement the minimal runtime boundary" in map_text


def test_contracts_define_passage_identity_and_distinct_attribution() -> None:
    text = _text(PASSAGE_PRACTICE / "docs" / "contracts.md")
    assert "Passage investigation request — D-013" in text
    assert "required `passage`" in text
    assert "required `selection_origin`" in text
    assert "an empty collection is valid" in text
    assert "An ordinary passage observation does not require an `AttributedSignal`" in text
    diagnosis = text.split("## Diagnosis", 1)[1].split("## Objective", 1)[0]
    assert "required source passage ID" in diagnosis
    assert "without\nany hotspot or attribution record" in diagnosis


def test_existing_region_models_remain_entry_agnostic() -> None:
    assert MODELS_DIR.is_dir()
    for module in ("time.py", "source.py", "diagnostics.py", "passage.py"):
        text = _text(MODELS_DIR / module)
        assert "hotspot" not in text.lower(), f"{module} must stay entry-agnostic"
    passage = _text(MODELS_DIR / "passage.py")
    assert "class Passage:" in passage


def test_adapter_dependencies_name_selection_and_shared_contract() -> None:
    text = _text(PASSAGE_PRACTICE / "IMPLEMENTATION_CHECKLIST.md")
    manual = text.split("**T05.3", 1)[1].split("**T05.4", 1)[0]
    assert "T05.1, T02.5" in manual
    assert "LS-03a" in manual
    assert "no profile call" in manual
    assert "mismatched evidence rejected" in manual


def test_map_keeps_hotspot_regression() -> None:
    text = _text(MAP_DOC).lower()
    assert "regression" in text
    assert "unchanged" in text or "preserved" in text or "kept" in text
