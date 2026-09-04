"""Tests for T01.4 minimal versioned passage/view containers."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import PASSAGE_SCHEMA_VERSION, VIEW_SCHEMA_VERSION, Passage, PassagePurpose, View, ViewType
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScorePosition


def _pos(q: Fraction, measure_index: int = 0) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=measure_index, measure_number=str(measure_index + 1), offset_in_measure=Fraction(0, 1))


def _make_passage(**overrides):
    base = dict(
        passage_id="test.passage.1",
        score_id="score.test",
        start=_pos(Fraction(0, 1), 0),
        end=_pos(Fraction(4, 1), 1),
        purpose=PassagePurpose.DETECTION,
        method_id="test.method",
        method_version="1.0.0",
        event_refs=(SourceRef(id="n1", kind=SourceKind.WRITTEN_NOTE), SourceRef(id="n2", kind=SourceKind.WRITTEN_NOTE)),
        omissions=("non-target-hand",),
        diagnostics=(Diagnostic(code="test_diag", severity=Severity.INFO, message="test"),),
    )
    base.update(overrides)
    return Passage(**base)


def test_passage_basic_valid():
    p = _make_passage()
    assert p.passage_id == "test.passage.1"
    assert p.purpose == PassagePurpose.DETECTION
    assert p.parent_id is None


def test_passage_parent_lineage():
    parent = _make_passage(passage_id="parent.1")
    child = _make_passage(passage_id="child.1", parent_id=parent.passage_id, purpose=PassagePurpose.EVIDENCE)
    assert child.parent_id == "parent.1"


def test_passage_immutability():
    p = _make_passage()
    with pytest.raises(AttributeError):
        p.passage_id = "other"  # type: ignore


def test_passage_rejects_empty_id():
    with pytest.raises(ValueError):
        _make_passage(passage_id="")


def test_passage_rejects_invalid_purpose():
    with pytest.raises(TypeError):
        _make_passage(purpose="detection")  # type: ignore


def test_passage_rejects_start_not_before_end():
    with pytest.raises(ValueError):
        _make_passage(start=_pos(Fraction(4, 1)), end=_pos(Fraction(0, 1)))


def test_passage_rejects_zero_interval():
    with pytest.raises(ValueError):
        _make_passage(start=_pos(Fraction(2, 1)), end=_pos(Fraction(2, 1)))


def test_passage_serialization_round_trip():
    p = _make_passage()
    data = p.to_dict()
    assert data["schema_version"] == PASSAGE_SCHEMA_VERSION
    j1 = json.dumps(data, sort_keys=True)
    j2 = json.dumps(Passage.from_dict(data).to_dict(), sort_keys=True)
    assert j1 == j2
    assert Passage.from_dict(data) == p


def test_passage_frozen_compact_json():
    # Compact payload with only required fields (no optional)
    p = Passage(
        passage_id="compact.1",
        score_id="score.1",
        start=_pos(Fraction(0, 1)),
        end=_pos(Fraction(2, 1)),
        purpose=PassagePurpose.PRACTICE,
        method_id="m",
        method_version="v1",
    )
    data = p.to_dict()
    # Should not contain parent_id, event_refs, omissions, diagnostics when empty
    assert "parent_id" not in data
    assert "event_refs" not in data
    assert "omissions" not in data
    assert "diagnostics" not in data
    assert Passage.from_dict(data) == p
    # Deterministic keys via json dumps sort_keys
    assert json.dumps(data, sort_keys=True) == json.dumps(Passage.from_dict(data).to_dict(), sort_keys=True)


def test_passage_deterministic_event_refs_order():
    r1 = SourceRef(id="n1", kind=SourceKind.WRITTEN_NOTE)
    r2 = SourceRef(id="n2", kind=SourceKind.WRITTEN_NOTE)
    p = _make_passage(event_refs=(r1, r2))
    data = p.to_dict()
    assert [r["id"] for r in data["event_refs"]] == ["n1", "n2"]
    # order preserved round-trip
    assert Passage.from_dict(data).event_refs == (r1, r2)


def test_passage_unsupported_version():
    p = _make_passage()
    data = p.to_dict()
    data["schema_version"] = "passage.v999"
    with pytest.raises(ValueError, match="unsupported.*Passage"):
        Passage.from_dict(data)


def test_passage_unknown_purpose():
    p = _make_passage()
    data = p.to_dict()
    data["purpose"] = "bogus"
    with pytest.raises(ValueError, match="unknown PassagePurpose"):
        Passage.from_dict(data)


def test_passage_invalid_id_too_long():
    with pytest.raises(ValueError):
        _make_passage(passage_id="x" * 129)


# View tests ------------------------------------------------------------------------


def _make_view(**overrides):
    base = dict(
        view_type=ViewType.LOGICAL_ATTACK_STREAM,
        source_passage_id="test.passage.1",
        method_id="test.method",
        method_version="1.0.0",
        included_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
        ordering="onset",
        grouping=None,
        omissions=("voice:2",),
        confidence=None,
    )
    base.update(overrides)
    return View(**base)


def test_view_basic_valid():
    v = _make_view()
    assert v.view_type == ViewType.LOGICAL_ATTACK_STREAM
    assert v.ordering == "onset"


def test_view_with_confidence():
    v = _make_view(confidence=0.85, grouping="onset")
    assert v.confidence == 0.85
    assert v.grouping == "onset"


def test_view_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        _make_view(confidence=1.5)


def test_view_rejects_unknown_type():
    with pytest.raises(TypeError):
        _make_view(view_type="onset_slices")  # type: ignore


def test_view_serialization_round_trip():
    v = _make_view(
        confidence=0.9,
        grouping="onset",
        diagnostics=(Diagnostic(code="inferred_hand", severity=Severity.INFO, message="hand inferred"),),
    )
    data = v.to_dict()
    assert data["schema_version"] == VIEW_SCHEMA_VERSION
    j1 = json.dumps(data, sort_keys=True)
    j2 = json.dumps(View.from_dict(data).to_dict(), sort_keys=True)
    assert j1 == j2
    assert View.from_dict(data) == v


def test_view_frozen_compact():
    v = View(
        view_type=ViewType.WRITTEN_EVENT_STREAM,
        source_passage_id="p1",
        method_id="m",
        method_version="v1",
        ordering="onset",
    )
    data = v.to_dict()
    assert "included_refs" not in data
    assert "grouping" not in data
    assert "omissions" not in data
    assert "confidence" not in data
    assert View.from_dict(data) == v


def test_view_unsupported_version():
    v = _make_view()
    data = v.to_dict()
    data["schema_version"] = "view.v999"
    with pytest.raises(ValueError, match="unsupported.*View"):
        View.from_dict(data)


def test_view_invalid_enum():
    v = _make_view()
    data = v.to_dict()
    data["view_type"] = "bogus_view"
    with pytest.raises(ValueError, match="unknown ViewType"):
        View.from_dict(data)


def test_view_invalid_missing_field():
    with pytest.raises(ValueError, match="missing View field"):
        View.from_dict({"schema_version": VIEW_SCHEMA_VERSION, "view_type": "onset_slices"})


def test_view_deterministic_serialization():
    v = _make_view(
        included_refs=(SourceRef(id="n2", kind=SourceKind.LOGICAL_NOTE), SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE)),
        omissions=("b", "a"),
    )
    # Ensure deterministic: included_refs order as given, omissions order as given (caller must sort if needed)
    data = v.to_dict()
    assert [r["id"] for r in data["included_refs"]] == ["n2", "n1"]
    assert data["omissions"] == ["b", "a"]
    assert View.from_dict(data) == v
