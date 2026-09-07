"""Tests for LS-07 grounded transition-practice aid."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from learner_context.models import (
    AssistanceRequest,
    AssistanceResult,
    EntryScope,
    JournalEntry,
    RequestIntent,
)
from passage_practice.aids import (
    AID_METHOD_ID,
    AID_OBJECTIVE,
    suggest_transition_practice,
)
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.observations import observe_pitch_transitions
from passage_practice.passages.investigate import manual_investigation

from test_selection import _load


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


def _observations(fixture="selection_two_staff.musicxml", start=Fraction(0, 1), end=Fraction(4, 1)):
    score = _load(fixture)
    inv = manual_investigation(
        score, score_id="t", start=start, end=end, investigation_id="inv.aid.1"
    )
    return score, inv, observe_pitch_transitions(inv, score)


def _request(**overrides) -> AssistanceRequest:
    base = dict(request_id="req.aid.1", intent=RequestIntent.PRACTICE_AID)
    base.update(overrides)
    return AssistanceRequest(**base)


def _note(entry_id="entry.1", **overrides) -> JournalEntry:
    base = dict(
        entry_id=entry_id,
        text="The big jump keeps slipping.",
        author="learner",
        recorded_at="2026-09-05T10:00:00",
    )
    base.update(overrides)
    return JournalEntry(**base)


def _region(start: int, end: int) -> ScoreInterval:
    return ScoreInterval(
        start=ScorePosition(quarters=Fraction(start, 1), measure_index=2),
        end=ScorePosition(quarters=Fraction(end, 1), measure_index=2),
    )


def test_no_history_baseline_aid_is_traceable():
    _, inv, observed = _observations()
    result = suggest_transition_practice(_request(), observed)
    assert result.suggestion is not None and "+14" in result.suggestion
    assert result.objective == AID_OBJECTIVE
    assert result.passage_refs == (inv.passage.passage_id,)
    assert len(result.observation_refs) == 2  # -12 and +14 only
    assert result.report_refs == ()
    assert result.rationale and len(result.limitations) >= 2
    assert "prototype_unvalidated" in result.rationale
    assert result.method_id == AID_METHOD_ID
    data = result.to_dict()
    assert _dump(data) == _dump(AssistanceResult.from_dict(data).to_dict())


def test_applicable_report_frames_without_altering_facts():
    _, inv, observed = _observations()
    baseline = suggest_transition_practice(_request(), observed)
    framed = suggest_transition_practice(
        _request(), observed, reports=(_note(),)
    )
    assert framed.report_refs == ("entry.1",)
    assert framed.suggestion == baseline.suggestion  # score facts unchanged
    assert framed.observation_refs == baseline.observation_refs
    assert "entry.1" in framed.rationale


def test_conflicting_region_report_yields_caveat_not_diagnosis():
    _, _, observed = _observations()
    stray = _note(
        scope=EntryScope.REGION, piece_id="t",
        region=_region(8, 12),  # outside the observed [0,4) passage
    )
    result = suggest_transition_practice(_request(), observed, reports=(stray,))
    assert result.report_refs == ("entry.1",)
    assert any("different region" in lim for lim in result.limitations)
    assert result.suggestion is not None  # still grounded in passage evidence
    assert "diagnosis of why" in result.limitations[0] or any(
        "not a diagnosis" in lim for lim in result.limitations
    )


def test_empty_observations_abstain_honestly():
    score = _load("selection_two_staff.musicxml")
    empty_inv = manual_investigation(
        score, score_id="t", start=Fraction(7, 2),
        end=Fraction(4, 1), investigation_id="inv.aid.empty",
    )
    result = suggest_transition_practice(
        _request(), observe_pitch_transitions(empty_inv, score)
    )
    assert result.suggestion is None
    assert result.objective is None
    assert "No pitch-transition observations" in result.rationale
    assert result.limitations[0].startswith("Aid requires")


def test_below_threshold_returns_limitation():
    _, _, observed = _observations(
        fixture="selection_ties.musicxml", start=Fraction(4, 1), end=Fraction(8, 1)
    )
    assert [o.value for o in observed.observations] == [2]
    result = suggest_transition_practice(_request(), observed)
    assert result.suggestion is None
    assert any("7 semitones" in lim for lim in result.limitations)
    assert result.observation_refs != ()


def test_rejects_bad_input_shapes():
    _, _, observed = _observations()
    with pytest.raises(TypeError):
        suggest_transition_practice("req", observed)  # type: ignore
    with pytest.raises(TypeError):
        suggest_transition_practice(_request(), "observations")  # type: ignore
    with pytest.raises(TypeError):
        suggest_transition_practice(_request(), observed, reports=["entry.1"])  # type: ignore
