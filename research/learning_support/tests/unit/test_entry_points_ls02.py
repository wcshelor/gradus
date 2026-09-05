"""LS-02 acceptance checks: entry-point reconciliation map.

Documentation-only task: verify the implementation map exists with working
links, identifies reused contracts / missing pieces / affected work packages /
required tests for both entries, that local plans no longer imply a hotspot
gate, that the adapter decision is recorded, and that no contract code was
changed. The hotspot regression itself is verified by the full suite run.
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


def test_map_declares_ls02_without_implementation() -> None:
    text = _text(MAP_DOC)
    assert "LS-02" in text
    assert "planned, not implemented" in text
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


def test_map_identifies_reused_contracts_missing_pieces_and_owners() -> None:
    text = _text(MAP_DOC)
    for contract in ("ScorePosition", "SourceRef", "Passage", "View", "D-012"):
        assert contract in text, f"map must name reused contract: {contract}"
    for missing in ("T02.5", "T05.3", "LS-03"):
        assert missing in text, f"map must name missing piece: {missing}"
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
    assert "baseline observations" in work_packages
    # Status board untouched by LS-02: no package row is marked DONE here
    # (the word appears only in the status-vocabulary legend).
    assert not re.search(r"^\| WP-\d+.*\| DONE \|", work_packages, flags=re.MULTILINE)


def test_adapter_decision_recorded_as_proposed() -> None:
    text = _text(PASSAGE_PRACTICE / "docs" / "decisions.md")
    assert "D-013" in text
    assert "proposed" in text
    assert "lead review pending" in text


def test_contracts_flag_hotspot_gap_without_changing_fields() -> None:
    text = _text(PASSAGE_PRACTICE / "docs" / "contracts.md")
    assert "LS-03" in text
    assert "no field change" in text.lower() or "No fields are changed" in text


def test_no_contract_code_changed_for_ls02() -> None:
    assert MODELS_DIR.is_dir()
    for module in ("time.py", "source.py", "diagnostics.py", "passage.py"):
        text = _text(MODELS_DIR / module)
        assert "hotspot" not in text.lower(), f"{module} must stay entry-agnostic"
    passage = _text(MODELS_DIR / "passage.py")
    assert 'PASSAGE_SCHEMA_VERSION = "passage.v1"' in passage


def test_map_keeps_hotspot_regression() -> None:
    text = _text(MAP_DOC).lower()
    assert "regression" in text
    assert "unchanged" in text or "preserved" in text or "kept" in text
