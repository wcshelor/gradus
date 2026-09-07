"""Tests for LS-06 bounded pitch-transition observations."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from passage_practice.models.investigation import PassageInvestigation, SelectionOrigin
from passage_practice.models.observations import (
    OBSERVATION_RESULT_SCHEMA_VERSION,
    OBSERVATION_SCHEMA_VERSION,
    Observation,
    ObservationBasis,
    ObservationResult,
)
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref
from passage_practice.observations import (
    TRANSITION_METHOD_ID,
    observe_pitch_transitions,
)
from passage_practice.passages.investigate import manual_investigation
from passage_practice.passages.selection import select_passage

from test_selection import _load


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


def _manual(start=Fraction(0, 1), end=Fraction(4, 1), fixture="selection_two_staff.musicxml"):
    score = _load(fixture)
    inv = manual_investigation(
        score, score_id="t", start=start, end=end, investigation_id="inv.obs.1"
    )
    return score, inv


def test_user_selected_transitions_are_signed_facts():
    score, inv = _manual()
    result = observe_pitch_transitions(inv, score)
    assert [o.value for o in result.observations] == [-12, 14, 2, 1]
    assert all(o.units == "semitones" for o in result.observations)
    assert all(o.basis == ObservationBasis.FACT for o in result.observations)
    assert all(o.method_id == TRANSITION_METHOD_ID for o in result.observations)
    assert all(o.passage_id == inv.passage.passage_id for o in result.observations)
    # Simultaneous pair has no temporal extent: region omitted, diagnosed.
    first = result.observations[0]
    assert first.region is None
    assert any(d.code == "simultaneous_pair" for d in first.diagnostics)
    assert first.hand is None  # right -> left is not one hand
    second = result.observations[1]
    assert second.region is not None
    assert (second.region.start.quarters, second.region.end.quarters) == (
        Fraction(0, 1), Fraction(1, 1),
    )


def test_analyzer_route_observes_identically():
    score, manual = _manual()
    analyzer = PassageInvestigation(
        investigation_id="inv.obs.2",
        passage=manual.passage,
        selection_origin=SelectionOrigin.ANALYZER_SUGGESTED,
        method_id="hotspot_adapter",
        method_version="v1",
    )
    manual_result = observe_pitch_transitions(manual, score)
    analyzer_result = observe_pitch_transitions(analyzer, score)
    assert [o.value for o in analyzer_result.observations] == [
        o.value for o in manual_result.observations
    ]
    assert [o.observation_id for o in analyzer_result.observations] == [
        o.observation_id for o in manual_result.observations
    ]


def test_evidence_refs_resolve_to_source_events():
    score, inv = _manual()
    result = observe_pitch_transitions(inv, score)
    assert result.observations
    for obs in result.observations:
        assert len(obs.source_refs) == 2
        assert all(resolve_ref(score, r) is not None for r in obs.source_refs)


def test_hand_scoping_is_marked_inference():
    score, inv = _manual()
    result = observe_pitch_transitions(inv, score, hand="right")
    assert [o.value for o in result.observations] == [2, 2, 1]
    assert all(o.basis == ObservationBasis.INFERENCE for o in result.observations)
    assert all(o.hand == "right" for o in result.observations)
    assert any(d.code == "hand_scoped_inference" for d in result.diagnostics)


def test_tie_collapse_yields_no_self_transition():
    score = _load("selection_ties.musicxml")
    inv = manual_investigation(
        score, score_id="t", start=Fraction(4, 1), end=Fraction(8, 1),
        investigation_id="inv.obs.3",
    )
    result = observe_pitch_transitions(inv, score)
    assert [o.value for o in result.observations] == [2]  # G -> A, no G -> G


def test_empty_and_single_attack_abstain_without_diagnosing_learner():
    score, _ = _manual()
    empty_inv = manual_investigation(
        score, score_id="t", start=Fraction(7, 2), end=Fraction(4, 1),
        investigation_id="inv.obs.empty",
    )
    empty = observe_pitch_transitions(empty_inv, score)
    assert empty.observations == ()
    assert any(d.code == "insufficient_attacks" for d in empty.diagnostics)

    left = observe_pitch_transitions(_manual()[1], score, hand="left")
    assert left.observations == ()
    assert any(d.code == "insufficient_attacks" for d in left.diagnostics)

    for result in (empty, left):
        text = _dump(result.to_dict())
        assert "learner" not in text
        assert "difficult" not in text


def test_unresolvable_refs_warn_and_skip():
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition

    score, inv = _manual()
    pos = ScorePosition(quarters=Fraction(0, 1), measure_index=1)
    bad = Passage(
        passage_id="bad.refs", score_id="t", start=pos,
        end=ScorePosition(quarters=Fraction(4, 1), measure_index=2),
        purpose=PassagePurpose.DETECTION, method_id="m", method_version="v1",
        event_refs=inv.passage.event_refs + (
            SourceRef(id="ghost", kind=SourceKind.LOGICAL_NOTE),
        ),
    )
    ghost_inv = PassageInvestigation(
        investigation_id="inv.obs.ghost", passage=bad,
        selection_origin=SelectionOrigin.USER_SELECTED,
        method_id="m", method_version="v1",
    )
    result = observe_pitch_transitions(ghost_inv, score)
    assert [o.value for o in result.observations] == [-12, 14, 2, 1]
    assert any(d.code == "unresolvable_attack_ref" for d in result.diagnostics)


def test_rejects_unsupported_hand_and_bad_inputs():
    score, inv = _manual()
    with pytest.raises(ValueError):
        observe_pitch_transitions(inv, score, hand="middle")
    with pytest.raises(TypeError):
        observe_pitch_transitions("not-an-investigation", score)  # type: ignore


def test_serialization_round_trip_deterministic_and_versioned():
    score, inv = _manual()
    result = observe_pitch_transitions(inv, score)
    data = result.to_dict()
    assert data["schema_version"] == OBSERVATION_RESULT_SCHEMA_VERSION
    assert data["observations"][0]["schema_version"] == OBSERVATION_SCHEMA_VERSION
    assert _dump(data) == _dump(ObservationResult.from_dict(data).to_dict())
    assert ObservationResult.from_dict(data) == result
    broken = dict(data)
    broken["schema_version"] = "observation_result.v99"
    with pytest.raises(ValueError):
        ObservationResult.from_dict(broken)
    assert Observation.from_dict(data["observations"][0]).basis == ObservationBasis.FACT
