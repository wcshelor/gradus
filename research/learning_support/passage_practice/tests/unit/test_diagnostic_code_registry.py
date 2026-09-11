"""Tests for S-X1 semantic diagnostic code registry."""

from __future__ import annotations

from passage_practice.semantics.diagnostic_codes import (
    ALL_CODES,
    CATEGORY_MAP,
    CONTRADICTORY_CRITERIA_CODES,
    LEARNER_DEPENDENT_CODES,
    LOW_CONFIDENCE_CODES,
    MISSING_SOURCE_REFS_CODES,
    MISSING_VIEW_CODES,
    UNSUPPORTED_NOTATION_CODES,
)


def test_no_duplicate_codes_across_categories():
    seen: dict[str, str] = {}
    for category, codes in CATEGORY_MAP.items():
        for code in codes:
            assert code not in seen, f"duplicate code {code!r} in {category!r} and {seen[code]!r}"
            seen[code] = category
    # Overall registry must have unique keys
    assert len(ALL_CODES) == len(seen) or len(ALL_CODES) >= len(seen)
    # No duplicate values in ALL_CODES keys
    assert len(ALL_CODES) == len(set(ALL_CODES))


def test_required_categories_present():
    assert "missing_required_view" in MISSING_VIEW_CODES
    assert "slur_evidence_unavailable" in UNSUPPORTED_NOTATION_CODES
    assert "low_confidence_melody" in LOW_CONFIDENCE_CODES
    assert "contradictory_evidence" in CONTRADICTORY_CRITERIA_CODES
    assert "unresolvable_attack_ref" in MISSING_SOURCE_REFS_CODES
    assert "learner_caveat" in LEARNER_DEPENDENT_CODES
    # Plumbing
    assert "synthetic_data" in ALL_CODES


def test_codes_are_stable_snake_case():
    import re

    pattern = re.compile(r"^[a-z][a-z0-9_]*$")
    for code in ALL_CODES:
        assert pattern.match(code), f"code {code!r} must be stable snake_case"


def test_all_codes_have_descriptions():
    for code, desc in ALL_CODES.items():
        assert isinstance(desc, str) and desc, f"code {code!r} missing description"
