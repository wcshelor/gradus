"""Tests for T01.3 shared diagnostics and provenance references."""

from __future__ import annotations

import json

import pytest

from passage_practice.models.diagnostics import DIAGNOSTIC_SCHEMA_VERSION, Diagnostic, Severity
from passage_practice.models.source import SourceKind, SourceRef


def test_diagnostic_basic_valid():
    d = Diagnostic(code="unsupported_tuplet", severity=Severity.WARNING, message="tuplet outside v1")
    assert d.code == "unsupported_tuplet"
    assert d.severity == Severity.WARNING


def test_diagnostic_immutability():
    d = Diagnostic(code="test", severity=Severity.INFO, message="msg")
    with pytest.raises(AttributeError):
        d.code = "other"  # type: ignore


def test_diagnostic_rejects_invalid_severity():
    with pytest.raises(TypeError):
        Diagnostic(code="x", severity="warning", message="m")  # type: ignore


def test_diagnostic_rejects_empty_code():
    with pytest.raises(ValueError):
        Diagnostic(code="", severity=Severity.ERROR, message="msg")


def test_diagnostic_with_optional_context_and_refs():
    ref = SourceRef(id="n1", kind=SourceKind.WRITTEN_NOTE)
    d = Diagnostic(
        code="missing_context",
        severity=Severity.INFO,
        message="no key sig",
        context={"measure_index": 3, "staff": 1},
        source_refs=(ref,),
    )
    assert d.context == {"measure_index": 3, "staff": 1}
    assert d.source_refs == (ref,)


def test_diagnostic_serialization_round_trip():
    ref = SourceRef(id="n2", kind=SourceKind.WRITTEN_NOTE)
    d = Diagnostic(
        code="hand_inferred",
        severity=Severity.INFO,
        message="hand inferred from staff",
        context={"staff": 2, "measure_index": 1},
        source_refs=(ref,),
    )
    data = d.to_dict()
    assert data["schema_version"] == DIAGNOSTIC_SCHEMA_VERSION
    # deterministic: context keys sorted
    j1 = json.dumps(data, sort_keys=True)
    j2 = json.dumps(Diagnostic.from_dict(data).to_dict(), sort_keys=True)
    assert j1 == j2
    assert Diagnostic.from_dict(data) == d


def test_diagnostic_missing_optional_context():
    d = Diagnostic(code="no_context", severity=Severity.WARNING, message="warn")
    data = d.to_dict()
    assert "context" not in data
    assert "source_refs" not in data
    assert Diagnostic.from_dict(data) == d


def test_diagnostic_deterministic_order_context_keys_sorted():
    # context with unsorted keys should serialize sorted
    d = Diagnostic(code="c", severity=Severity.INFO, message="m", context={"z": 1, "a": 2})
    data = d.to_dict()
    assert list(data["context"].keys()) == ["a", "z"]
    # round-trip preserves sorted
    assert Diagnostic.from_dict(data).context == {"a": 2, "z": 1}


def test_diagnostic_rejects_invalid_reference():
    # source_refs must be SourceRef, not raw dict string
    with pytest.raises(TypeError):
        Diagnostic(code="c", severity=Severity.INFO, message="m", source_refs=("n1",))  # type: ignore
    # from_dict with invalid source_ref should fail
    with pytest.raises(ValueError):
        Diagnostic.from_dict(
            {
                "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
                "code": "c",
                "severity": "info",
                "message": "m",
                "source_refs": [{"schema_version": "source_ref.v1", "id": "n1", "kind": "bogus_kind"}],
            }
        )


def test_diagnostic_unsupported_version():
    d = Diagnostic(code="c", severity=Severity.INFO, message="m")
    data = d.to_dict()
    data["schema_version"] = "diagnostic.v999"
    with pytest.raises(ValueError, match="unsupported.*Diagnostic"):
        Diagnostic.from_dict(data)


def test_diagnostic_unknown_severity():
    with pytest.raises(ValueError, match="unknown Severity"):
        Diagnostic.from_dict(
            {"schema_version": DIAGNOSTIC_SCHEMA_VERSION, "code": "c", "severity": "critical", "message": "m"}
        )


def test_diagnostic_missing_field():
    with pytest.raises(ValueError, match="missing Diagnostic field"):
        Diagnostic.from_dict({"schema_version": DIAGNOSTIC_SCHEMA_VERSION, "code": "c", "severity": "info"})


def test_diagnostic_list_deterministic_order():
    # Wolf: diagnostics when serialized as list should be in insertion order, but callers can sort
    diags = [
        Diagnostic(code="b_code", severity=Severity.WARNING, message="b"),
        Diagnostic(code="a_code", severity=Severity.INFO, message="a"),
    ]
    # Ensure individual serialization is deterministic; list order is input order
    data = [d.to_dict() for d in diags]
    assert data[0]["code"] == "b_code"
    assert data[1]["code"] == "a_code"
    # Round-trip preserves order
    restored = [Diagnostic.from_dict(d) for d in data]
    assert restored == diags
