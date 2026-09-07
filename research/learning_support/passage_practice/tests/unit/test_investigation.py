"""Tests for LS-03a shared passage-investigation contract (D-013)."""

from __future__ import annotations

import json
import math
from fractions import Fraction

import pytest

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.investigation import (
    CONTRIBUTION_SCHEMA_VERSION,
    DIFFICULTY_EVIDENCE_SCHEMA_VERSION,
    PASSAGE_INVESTIGATION_SCHEMA_VERSION,
    Contribution,
    DifficultyEvidence,
    PassageInvestigation,
    SelectionOrigin,
)
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScoreInterval, ScorePosition


def _pos(q: Fraction, measure_index: int = 0) -> ScorePosition:
    return ScorePosition(
        quarters=q,
        measure_index=measure_index,
        measure_number=str(measure_index + 1),
        offset_in_measure=Fraction(0, 1),
    )


def _interval(start_q: Fraction, end_q: Fraction) -> ScoreInterval:
    return ScoreInterval(start=_pos(start_q), end=_pos(end_q))


def _passage(**overrides) -> Passage:
    base = dict(
        passage_id="test.passage.1",
        score_id="score.test",
        start=_pos(Fraction(0, 1), 0),
        end=_pos(Fraction(4, 1), 1),
        purpose=PassagePurpose.DETECTION,
        method_id="test.selection",
        method_version="1.0.0",
    )
    base.update(overrides)
    return Passage(**base)


def _evidence(**overrides) -> DifficultyEvidence:
    base = dict(
        source_score_id="score.test",
        method_id="difficulty_overview",
        method_version="v1",
        covered=_interval(Fraction(0, 1), Fraction(2, 1)),
        feature_id="attack_density",
        evidence_ref="ev.attack_density.w0",
    )
    base.update(overrides)
    return DifficultyEvidence(**base)


def _manual(**overrides) -> PassageInvestigation:
    base = dict(
        investigation_id="inv.manual.1",
        passage=_passage(),
        selection_origin=SelectionOrigin.USER_SELECTED,
        method_id="manual_region_selection",
        method_version="v1",
    )
    base.update(overrides)
    return PassageInvestigation(**base)


def _analyzer(**overrides) -> PassageInvestigation:
    evidence = _evidence(
        hotspot_id="hs.w0",
        window_score=0.82,
        contributions=(Contribution(dimension_id="attack_density", value=0.6),),
    )
    base = dict(
        investigation_id="inv.analyzer.1",
        passage=_passage(),
        selection_origin=SelectionOrigin.ANALYZER_SUGGESTED,
        method_id="hotspot_adapter",
        method_version="v1",
        requested_hand="right",
        difficulty=(evidence,),
    )
    base.update(overrides)
    return PassageInvestigation(**base)


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


# Both origins ---------------------------------------------------------------


def test_manual_origin_empty_difficulty_is_valid():
    inv = _manual()
    assert inv.selection_origin == SelectionOrigin.USER_SELECTED
    assert inv.difficulty == ()
    assert inv.requested_hand is None


def test_analyzer_origin_with_hotspot_evidence_is_valid():
    inv = _analyzer()
    assert inv.selection_origin == SelectionOrigin.ANALYZER_SUGGESTED
    assert inv.difficulty[0].hotspot_id == "hs.w0"


def test_round_trip_deterministic_both_origins():
    for inv in (_manual(), _analyzer()):
        data = inv.to_dict()
        assert data["schema_version"] == PASSAGE_INVESTIGATION_SCHEMA_VERSION
        assert _dump(data) == _dump(PassageInvestigation.from_dict(data).to_dict())
        assert PassageInvestigation.from_dict(data) == inv


def test_versioned_payload_constants():
    assert _manual().to_dict()["schema_version"] == PASSAGE_INVESTIGATION_SCHEMA_VERSION
    assert _evidence().to_dict()["schema_version"] == DIFFICULTY_EVIDENCE_SCHEMA_VERSION
    assert (
        Contribution(dimension_id="d", value=1.0).to_dict()["schema_version"]
        == CONTRIBUTION_SCHEMA_VERSION
    )


def test_rejects_unknown_origin():
    with pytest.raises(TypeError):
        _manual(selection_origin="manual")  # type: ignore
    data = _manual().to_dict()
    data["selection_origin"] = "manual"
    with pytest.raises(ValueError):
        PassageInvestigation.from_dict(data)


def test_rejects_unsupported_hand():
    with pytest.raises(ValueError):
        _manual(requested_hand="third")


def test_unknown_hand_is_none_with_diagnostic():
    diag = Diagnostic(
        code="requested_hand_unknown", severity=Severity.INFO, message="hand unknown"
    )
    inv = _manual(requested_hand=None, diagnostics=(diag,))
    assert inv.requested_hand is None
    assert inv.diagnostics[0].code == "requested_hand_unknown"


# Enrichment preserves origin/identity ----------------------------------------


def test_with_evidence_preserves_origin_and_identity():
    inv = _manual()
    enriched = inv.with_evidence(_evidence())
    assert enriched.selection_origin == SelectionOrigin.USER_SELECTED
    assert enriched.passage.passage_id == "test.passage.1"
    assert enriched.investigation_id == "inv.manual.1"
    assert len(enriched.difficulty) == 1
    assert inv.difficulty == ()  # original unchanged (frozen)


def test_with_evidence_rejects_unrelated_source():
    inv = _manual()
    with pytest.raises(ValueError):
        inv.with_evidence(_evidence(source_score_id="score.other"))


def test_manual_payload_manufactures_no_hotspot():
    data = _manual().to_dict()
    text = _dump(data)
    assert "hotspot_id" not in text
    assert "window_score" not in text
    assert "contributions" not in text


# Difficulty validation -------------------------------------------------------


def test_rejects_orphan_score_without_hotspot():
    with pytest.raises(ValueError):
        _evidence(window_score=0.5)


def test_rejects_orphan_contributions_without_hotspot():
    with pytest.raises(ValueError):
        _evidence(contributions=(Contribution(dimension_id="d", value=0.5),))


def test_rejects_non_finite_score():
    for bad in (float("nan"), float("inf"), "0.5", True):
        with pytest.raises((ValueError, TypeError)):
            _evidence(hotspot_id="hs.w0", window_score=bad)


def test_rejects_empty_evidence_reference():
    with pytest.raises(ValueError):
        _evidence(evidence_ref="")


def test_rejects_source_mismatch():
    with pytest.raises(ValueError):
        _manual(difficulty=(_evidence(source_score_id="score.other"),))


def test_rejects_coverage_outside_passage():
    with pytest.raises(ValueError):
        _manual(
            difficulty=(
                _evidence(covered=_interval(Fraction(2, 1), Fraction(6, 1))),
            )
        )


def test_rejects_non_evidence_member():
    with pytest.raises(TypeError):
        _manual(difficulty=("ev1",))  # type: ignore


# Exact time ------------------------------------------------------------------


def test_exact_time_round_trip_no_floats_in_score_time():
    inv = _analyzer()
    data = inv.to_dict()
    entry = data["difficulty"][0]["covered"]
    assert entry["start"]["quarters"] == {"numerator": 0, "denominator": 1}
    assert entry["end"]["quarters"] == {"numerator": 2, "denominator": 1}
    assert Fraction(0, 1) == inv.difficulty[0].covered.start.quarters
    # Score-time payloads carry no floats; model-boundary scores may.
    assert not isinstance(entry["start"]["quarters"], float)


# Versions and missing fields --------------------------------------------------


def test_rejects_unsupported_investigation_version():
    data = _manual().to_dict()
    data["schema_version"] = "passage_investigation.v99"
    with pytest.raises(ValueError):
        PassageInvestigation.from_dict(data)


def test_rejects_unsupported_nested_passage_version():
    data = _manual().to_dict()
    data["passage"]["schema_version"] = "passage.v99"
    with pytest.raises(ValueError):
        PassageInvestigation.from_dict(data)


def test_rejects_unsupported_evidence_and_contribution_versions():
    data = _analyzer().to_dict()
    data["difficulty"][0]["schema_version"] = "difficulty_evidence.v99"
    with pytest.raises(ValueError):
        PassageInvestigation.from_dict(data)
    data = _analyzer().to_dict()
    data["difficulty"][0]["contributions"][0]["schema_version"] = "contribution.v99"
    with pytest.raises(ValueError):
        PassageInvestigation.from_dict(data)


def test_rejects_missing_required_fields():
    data = _manual().to_dict()
    for field in ("investigation_id", "passage", "selection_origin", "method_id"):
        broken = dict(data)
        del broken[field]
        with pytest.raises(ValueError):
            PassageInvestigation.from_dict(broken)


# Frozen representative payloads ------------------------------------------------


def test_frozen_manual_payload():
    inv = _manual()
    assert inv.to_dict() == {
        "schema_version": "passage_investigation.v1",
        "investigation_id": "inv.manual.1",
        "passage": inv.passage.to_dict(),
        "selection_origin": "user_selected",
        "method_id": "manual_region_selection",
        "method_version": "v1",
    }
    assert inv.passage.to_dict()["passage_id"] == "test.passage.1"


def test_frozen_analyzer_payload_shape():
    data = _analyzer().to_dict()
    assert data["selection_origin"] == "analyzer_suggested"
    assert data["requested_hand"] == "right"
    (entry,) = data["difficulty"]
    assert entry["hotspot_id"] == "hs.w0"
    assert entry["window_score"] == 0.82
    assert entry["contributions"] == [
        {
            "schema_version": "contribution.v1",
            "dimension_id": "attack_density",
            "value": 0.6,
        }
    ]
    assert math.isfinite(entry["window_score"])
