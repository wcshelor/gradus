"""Tests for S1.5 confidence helpers (D-016, S-Q003 policy).

In-memory only: band boundaries, invalid scores, method-status
vocabulary (including contract wiring), penalty arithmetic, and
missing-vs-negative evidence separation. No detectors, no thresholds,
no presentation behavior.
"""

from __future__ import annotations

import math

import pytest

from passage_practice.semantics.confidence import (
    ConfidenceBand,
    ConfidenceMethod,
    apply_contradiction_penalty,
    band_for,
    check_confidence,
    parse_method_status,
)
from passage_practice.semantics.contracts import SemanticHypothesis

from test_semantic_contracts import _hypothesis


# Boundary values -----------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "expected"),
    (
        (1.0, ConfidenceBand.HIGH),
        (1, ConfidenceBand.HIGH),
        (0.75, ConfidenceBand.HIGH),
        (0.7499999, ConfidenceBand.MEDIUM),
        (0.5, ConfidenceBand.MEDIUM),
        (0.4999999, ConfidenceBand.LOW),
        (0.25, ConfidenceBand.LOW),
        (0.2499999, ConfidenceBand.UNSUPPORTED),
        (0.0, ConfidenceBand.UNSUPPORTED),
        (0, ConfidenceBand.UNSUPPORTED),
    ),
)
def test_band_boundaries(score, expected):
    assert band_for(score) is expected


def test_band_mapping_is_deterministic():
    table = {score: band_for(score) for score in (0.0, 0.25, 0.5, 0.75, 1.0)}
    assert table == {
        0.0: ConfidenceBand.UNSUPPORTED,
        0.25: ConfidenceBand.LOW,
        0.5: ConfidenceBand.MEDIUM,
        0.75: ConfidenceBand.HIGH,
        1.0: ConfidenceBand.HIGH,
    }
    assert band_for(0.8) is band_for(0.8)


# Invalid / unsupported scores ------------------------------------------------


@pytest.mark.parametrize("bad", (True, False, "0.8", None, (0.5,)))
def test_helper_rejects_non_numeric_scores(bad):
    with pytest.raises(TypeError):
        check_confidence(bad)
    with pytest.raises(TypeError):
        band_for(bad)


@pytest.mark.parametrize("bad", (math.nan, math.inf, -math.inf, -0.1, 1.1))
def test_helper_rejects_unbounded_scores(bad):
    with pytest.raises(ValueError):
        check_confidence(bad)
    with pytest.raises(ValueError):
        band_for(bad)
    with pytest.raises(ValueError):
        apply_contradiction_penalty(bad, 0.1)


# Method status vocabulary ----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    (
        ("heuristic", ConfidenceMethod.HEURISTIC),
        ("calibrated", ConfidenceMethod.CALIBRATED),
        ("learned", ConfidenceMethod.LEARNED),
    ),
)
def test_method_status_parses_supported_vocabulary(raw, expected):
    assert parse_method_status(raw) is expected


@pytest.mark.parametrize("bad", ("", "Heuristic", "HEURISTIC", "ensemble", "rule_based"))
def test_method_status_rejects_unknown_vocabulary(bad):
    with pytest.raises(ValueError):
        parse_method_status(bad)


def test_method_status_rejects_non_strings():
    for bad in (None, 0, ["heuristic"]):
        with pytest.raises(TypeError):
            parse_method_status(bad)


def test_hypothesis_enforces_method_status():
    assert _hypothesis(confidence_method="heuristic").confidence_method == "heuristic"
    with pytest.raises(ValueError):
        _hypothesis(confidence_method="ensemble")
    payload = _hypothesis().to_dict()
    payload["confidence_method"] = "ensemble"
    with pytest.raises(ValueError):
        SemanticHypothesis.from_dict(payload)
    # Serialized form stays a plain string: no payload-shape change from S1.2.
    assert _hypothesis().to_dict()["confidence_method"] == "heuristic"


# Contradiction penalty helper --------------------------------------------------


def test_penalty_reduces_but_never_increases():
    assert apply_contradiction_penalty(0.8, 0.1) == pytest.approx(0.7)
    assert apply_contradiction_penalty(0.8, 0.0) == 0.8
    assert apply_contradiction_penalty(0.1, 0.5) == 0.0
    assert apply_contradiction_penalty(0.0, 0.3) == 0.0


@pytest.mark.parametrize("bad_penalty", (-0.1, math.nan, math.inf))
def test_penalty_rejects_negative_or_nonfinite(bad_penalty):
    with pytest.raises(ValueError):
        apply_contradiction_penalty(0.8, bad_penalty)


@pytest.mark.parametrize("bad_penalty", (True, "0.1", None))
def test_penalty_rejects_non_numeric(bad_penalty):
    with pytest.raises(TypeError):
        apply_contradiction_penalty(0.8, bad_penalty)


# Missing vs negative evidence --------------------------------------------------


def test_missing_evidence_is_not_a_contradiction():
    # A hypothesis resting partly on unavailable evidence keeps its authored
    # confidence through construction and round trip: the contract performs
    # no automatic reduction, and missing/contradictory fields serialize
    # as separate claims (policy §4).
    hypothesis = _hypothesis(
        confidence=0.3,
        missing_evidence=("accompaniment_pattern_unobserved",),
        contradictory_criteria=(),
    )
    assert hypothesis.confidence == 0.3
    payload = hypothesis.to_dict()
    assert payload["missing_evidence"] == ["accompaniment_pattern_unobserved"]
    assert payload["contradictory_criteria"] == []
    assert SemanticHypothesis.from_dict(payload) == hypothesis
    # Zero penalty (nothing contradictory, only missing) leaves the score
    # untouched — the representation-level counterpart of the same rule.
    assert apply_contradiction_penalty(hypothesis.confidence, 0.0) == 0.3
