"""Tests for S1.2/S1.3 minimal semantic contracts (D-015).

In-memory construction only: no MusicXML, no fixtures, no network.
Follows the contract-test policy (schema versions, resolvable references,
exact fractions, diagnostics, deterministic serialization).
"""

from __future__ import annotations

import json
import math
from fractions import Fraction

import pytest

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.semantics.contracts import (
    SEMANTIC_BUNDLE_SCHEMA_VERSION,
    SEMANTIC_HYPOTHESIS_SCHEMA_VERSION,
    SemanticBundle,
    SemanticHypothesis,
)


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


def _region(start=Fraction(0), end=Fraction(4)) -> ScoreInterval:
    return ScoreInterval(
        start=ScorePosition(quarters=start, measure_index=0),
        end=ScorePosition(quarters=end, measure_index=1),
    )


def _ref(note_id="n1") -> SourceRef:
    return SourceRef(id=note_id, kind=SourceKind.LOGICAL_NOTE)


def _hypothesis(**overrides) -> SemanticHypothesis:
    fields: dict = {
        "hypothesis_id": "hyp.melody.1",
        "hypothesis_type": "role.melody",
        "source_passage_id": "passage.1",
        "covered_region": _region(),
        "covered_event_ids": (_ref("n1"), _ref("n2")),
        "confidence": 0.8,
        "confidence_method": "heuristic",
        "method_id": "melody_salience",
        "method_version": "v1",
        "supporting_observation_ids": ("passage.1:pitch-transition:000",),
        "satisfied_criteria": ("top_voice", "longest_duration"),
    }
    fields.update(overrides)
    return SemanticHypothesis(**fields)


def _bundle(**overrides) -> SemanticBundle:
    fields: dict = {
        "bundle_id": "bundle.1",
        "source_passage_id": "passage.1",
    }
    fields.update(overrides)
    return SemanticBundle(**fields)


# S1.2 — SemanticHypothesis -------------------------------------------------


def test_hypothesis_rejects_out_of_range_confidence():
    for bad in (-0.1, 1.1, 2, math.nan, math.inf):
        with pytest.raises(ValueError):
            _hypothesis(confidence=bad)


def test_hypothesis_rejects_non_numeric_confidence():
    for bad in (True, "0.8", None):
        with pytest.raises(TypeError):
            _hypothesis(confidence=bad)


def test_hypothesis_accepts_confidence_boundaries():
    assert _hypothesis(confidence=0.0).confidence == 0.0
    assert _hypothesis(confidence=1).confidence == 1.0


def test_hypothesis_rejects_missing_passage_reference():
    with pytest.raises(ValueError):
        _hypothesis(source_passage_id="")
    with pytest.raises(ValueError):
        payload = _hypothesis().to_dict()
        del payload["source_passage_id"]
        SemanticHypothesis.from_dict(payload)


def test_hypothesis_rejects_bad_version():
    payload = _hypothesis().to_dict()
    payload["schema_version"] = "semantic_hypothesis.v99"
    with pytest.raises(ValueError):
        SemanticHypothesis.from_dict(payload)


def test_hypothesis_rejects_empty_covered_events():
    with pytest.raises(ValueError):
        _hypothesis(covered_event_ids=())


def test_hypothesis_type_vocabulary_is_open():
    # The contract must not hard-code the plan's type families: a detector
    # for a new family must not break this schema (taxonomy arrives later).
    assert _hypothesis(hypothesis_type="custom.new_family").hypothesis_type == (
        "custom.new_family"
    )


def test_hypothesis_serializes_deterministically():
    first, second = _hypothesis(), _hypothesis()
    assert _dump(first.to_dict()) == _dump(second.to_dict())
    assert SemanticHypothesis.from_dict(first.to_dict()) == first
    assert SemanticHypothesis.from_dict(json.loads(_dump(first.to_dict()))) == first


def test_hypothesis_frozen_representative_payload():
    # Inline frozen payload per the contract-test policy (schema-version
    # assertion plus exact shape); S1.6 owns committed fixture files.
    payload = _hypothesis().to_dict()
    assert payload["schema_version"] == SEMANTIC_HYPOTHESIS_SCHEMA_VERSION
    assert payload["hypothesis_id"] == "hyp.melody.1"
    assert payload["confidence"] == 0.8
    assert payload["covered_event_ids"][0]["kind"] == "logical_note"
    assert payload["covered_region"]["start"]["quarters"] == {
        "numerator": 0,
        "denominator": 1,
    }


# S1.3 — SemanticBundle -----------------------------------------------------


def test_bundle_rejects_mixed_passage_ids():
    local = _hypothesis(hypothesis_id="hyp.a", source_passage_id="passage.1")
    foreign = _hypothesis(hypothesis_id="hyp.b", source_passage_id="passage.2")
    with pytest.raises(ValueError):
        _bundle(hypotheses=(local, foreign))


def test_bundle_rejects_duplicate_hypothesis_ids():
    first = _hypothesis(hypothesis_id="hyp.same")
    second = _hypothesis(hypothesis_id="hyp.same")
    with pytest.raises(ValueError):
        _bundle(hypotheses=(first, second))


def test_bundle_preserves_contradictory_hypotheses():
    melody = _hypothesis(
        hypothesis_id="hyp.melody",
        hypothesis_type="role.melody",
        satisfied_criteria=("top_voice",),
        contradictory_criteria=(),
        confidence=0.7,
    )
    rival = _hypothesis(
        hypothesis_id="hyp.inner",
        hypothesis_type="role.inner_voice",
        satisfied_criteria=(),
        contradictory_criteria=("top_voice",),
        confidence=0.4,
    )
    bundle = _bundle(
        hypotheses=(melody, rival),
        ranked_hypothesis_ids=("hyp.melody", "hyp.inner"),
    )
    # Neither winner-takes-all filtering nor re-sorting: both survive,
    # authored order and authored ranking intact through a round trip.
    assert [h.hypothesis_id for h in bundle.hypotheses] == [
        "hyp.melody",
        "hyp.inner",
    ]
    assert bundle.ranked_hypothesis_ids == ("hyp.melody", "hyp.inner")
    revived = SemanticBundle.from_dict(json.loads(_dump(bundle.to_dict())))
    assert revived == bundle
    assert [h.hypothesis_id for h in revived.hypotheses] == [
        "hyp.melody",
        "hyp.inner",
    ]


def test_bundle_rejects_unresolvable_ranked_refs():
    only = _hypothesis(hypothesis_id="hyp.only")
    with pytest.raises(ValueError):
        _bundle(hypotheses=(only,), ranked_hypothesis_ids=("hyp.ghost",))
    with pytest.raises(ValueError):
        _bundle(
            hypotheses=(only,),
            ranked_hypothesis_ids=("hyp.only", "hyp.only"),
        )


def test_empty_bundle_round_trips_for_no_supported_hypothesis():
    # Anticipates S1.6: an empty hypotheses tuple with a diagnostic is a
    # valid bundle, not a missing bundle.
    diagnostic = Diagnostic(
        code="no_supported_hypothesis",
        severity=Severity.INFO,
        message="no detector met its minimum evidence threshold",
    )
    bundle = _bundle(
        hypotheses=(),
        method_versions=("melody_salience@v1",),
        diagnostics=(diagnostic,),
    )
    revived = SemanticBundle.from_dict(bundle.to_dict())
    assert revived == bundle
    assert revived.hypotheses == ()


def test_bundle_rejects_bad_version():
    payload = _bundle().to_dict()
    payload["schema_version"] = "semantic_bundle.v99"
    with pytest.raises(ValueError):
        SemanticBundle.from_dict(payload)


def test_bundle_serializes_deterministically():
    bundle = _bundle(
        hypotheses=(_hypothesis(),),
        ranked_hypothesis_ids=("hyp.melody.1",),
        view_refs=("attack_stream:passage.1",),
        observation_refs=("passage.1:pitch-transition:000",),
        method_versions=("melody_salience@v1",),
    )
    assert _dump(bundle.to_dict()) == _dump(_bundle(
        hypotheses=(_hypothesis(),),
        ranked_hypothesis_ids=("hyp.melody.1",),
        view_refs=("attack_stream:passage.1",),
        observation_refs=("passage.1:pitch-transition:000",),
        method_versions=("melody_salience@v1",),
    ).to_dict())
    assert bundle.to_dict()["schema_version"] == SEMANTIC_BUNDLE_SCHEMA_VERSION
    assert SemanticBundle.from_dict(bundle.to_dict()) == bundle
