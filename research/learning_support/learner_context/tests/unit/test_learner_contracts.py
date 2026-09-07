"""Tests for LS-03b learner request, journal, and context contracts."""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from learner_context.models import (
    ASSISTANCE_REQUEST_SCHEMA_VERSION,
    ASSISTANCE_RESULT_SCHEMA_VERSION,
    CONTEXT_PERMISSION_SCHEMA_VERSION,
    CONTEXT_SUMMARY_SCHEMA_VERSION,
    JOURNAL_ENTRY_SCHEMA_VERSION,
    AssistanceRequest,
    AssistanceResult,
    ContextPermission,
    ContextScope,
    ContextSummary,
    EntryScope,
    JournalEntry,
    RequestIntent,
)
from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.time import ScoreInterval, ScorePosition


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=0, offset_in_measure=Fraction(0, 1))


def _region() -> ScoreInterval:
    return ScoreInterval(start=_pos(Fraction(4, 1)), end=_pos(Fraction(8, 1)))


def _note(**overrides) -> JournalEntry:
    base = dict(
        entry_id="entry.1",
        text="The join still feels uncertain.",
        author="learner",
        recorded_at="2026-09-05T10:00:00",
    )
    base.update(overrides)
    return JournalEntry(**base)


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


def _round_trip(obj):
    data = obj.to_dict()
    assert _dump(data) == _dump(type(obj).from_dict(data).to_dict())
    assert type(obj).from_dict(data) == obj
    return data


# Journal entries --------------------------------------------------------------


def test_free_text_only_note_is_valid():
    entry = _note()
    assert entry.scope == EntryScope.GENERAL
    assert entry.revision == 1
    assert entry.supersedes is None


def test_frozen_minimal_note_payload():
    assert _note().to_dict() == {
        "schema_version": "journal_entry.v1",
        "entry_id": "entry.1",
        "text": "The join still feels uncertain.",
        "author": "learner",
        "recorded_at": "2026-09-05T10:00:00",
        "scope": "general",
        "revision": 1,
    }


def test_full_entry_round_trip_with_sorted_fields():
    entry = _note(
        scope=EntryScope.REGION,
        piece_id="piece.burgmueller",
        region=_region(),
        practice_note="hands separately twice",
        tags=("join", "hands-together"),
        fields={"tempo": "slow", "hand": "both"},
        revision=2,
        supersedes="entry.1",
    )
    data = _round_trip(entry)
    assert list(data["fields"].keys()) == ["hand", "tempo"]
    assert entry.region is not None
    assert entry.region.start.quarters == Fraction(4, 1)


def test_region_scope_requires_region():
    with pytest.raises(ValueError):
        _note(scope=EntryScope.REGION)


def test_non_region_scope_forbids_region():
    with pytest.raises(ValueError):
        _note(scope=EntryScope.PIECE, region=_region())


def test_rejects_bad_time_empty_text_and_bad_revision():
    with pytest.raises(ValueError):
        _note(recorded_at="last Tuesday")
    with pytest.raises(ValueError):
        _note(text="")
    with pytest.raises(ValueError):
        _note(revision=0)
    with pytest.raises(TypeError):
        _note(revision=True)  # type: ignore


def test_rejects_bad_tags_fields_and_scope():
    with pytest.raises(ValueError):
        _note(tags=("",))
    with pytest.raises(TypeError):
        _note(fields={"tempo": 120})  # type: ignore
    with pytest.raises(TypeError):
        _note(scope="region")  # type: ignore


def test_reports_carry_no_score_fact_fields():
    data = _note().to_dict()
    for key in ("passage_refs", "report_refs", "observations", "hotspot_id"):
        assert key not in data


def test_rejects_unsupported_journal_version():
    data = _note().to_dict()
    data["schema_version"] = "journal_entry.v99"
    with pytest.raises(ValueError):
        JournalEntry.from_dict(data)


# Permissions ------------------------------------------------------------------


def test_session_only_default_permission():
    perm = ContextPermission(entry_id="entry.1")
    assert perm.saved is False
    assert perm.use_current is True
    assert perm.use_future is False
    assert perm.excluded is False
    _round_trip(perm)


def test_exclusion_wins_over_use_flags():
    with pytest.raises(ValueError):
        ContextPermission(entry_id="entry.1", excluded=True, use_current=True)
    with pytest.raises(ValueError):
        ContextPermission(
            entry_id="entry.1",
            excluded=True,
            use_current=False,
            use_future=True,
            saved=True,
        )
    perm = ContextPermission(
        entry_id="entry.1", saved=True, use_current=False, excluded=True
    )
    assert perm.excluded is True


def test_future_use_requires_saved():
    with pytest.raises(ValueError):
        ContextPermission(entry_id="entry.1", saved=False, use_future=True)
    perm = ContextPermission(entry_id="entry.1", saved=True, use_future=True)
    assert perm.use_future is True


def test_rejects_non_bool_flags_and_bad_version():
    with pytest.raises(TypeError):
        ContextPermission(entry_id="entry.1", saved="yes")  # type: ignore
    data = ContextPermission(entry_id="entry.1").to_dict()
    assert data["schema_version"] == CONTEXT_PERMISSION_SCHEMA_VERSION
    data["schema_version"] = "context_permission.v99"
    with pytest.raises(ValueError):
        ContextPermission.from_dict(data)


# Summaries --------------------------------------------------------------------


def test_summary_requires_sources_and_round_trips():
    with pytest.raises(ValueError):
        ContextSummary(
            summary_id="sum.1",
            source_entry_ids=(),
            method_id="m",
            method_version="v1",
            created_at="2026-09-05T11:00:00",
            interpretation="x",
        )
    summary = ContextSummary(
        summary_id="sum.1",
        source_entry_ids=("entry.1", "entry.2"),
        method_id="recurrence_heuristic",
        method_version="v1",
        created_at="2026-09-05T11:00:00",
        interpretation="Join difficulty recurs across two visits; unconfirmed.",
    )
    assert summary.confirmed is False
    data = _round_trip(summary)
    assert data["schema_version"] == CONTEXT_SUMMARY_SCHEMA_VERSION
    data["schema_version"] = "context_summary.v99"
    with pytest.raises(ValueError):
        ContextSummary.from_dict(data)


# Requests ---------------------------------------------------------------------


def test_unresolved_request_is_valid():
    req = AssistanceRequest(
        request_id="req.1",
        intent=RequestIntent.UNDERSTAND,
        question="What is happening in measures 17-20?",
        diagnostics=(
            Diagnostic(
                code="region_unresolved",
                severity=Severity.WARNING,
                message="measure reference needs edition context",
            ),
        ),
    )
    assert req.region is None
    assert req.investigation_ref is None
    assert req.context_scope == ContextScope.NONE
    data = _round_trip(req)
    assert data["schema_version"] == ASSISTANCE_REQUEST_SCHEMA_VERSION


def test_resolved_request_round_trip_with_exact_region():
    req = AssistanceRequest(
        request_id="req.2",
        intent=RequestIntent.PRACTICE_AID,
        context_scope=ContextScope.PERMITTED,
        piece_id="piece.burgmueller",
        score_version="edition.a",
        region=_region(),
        investigation_ref="inv.manual.1",
    )
    data = _round_trip(req)
    assert data["region"]["start"]["quarters"] == {"numerator": 4, "denominator": 1}


def test_rejects_bad_intent_scope_and_version():
    with pytest.raises(TypeError):
        AssistanceRequest(request_id="r", intent="understand")  # type: ignore
    data = AssistanceRequest(
        request_id="r", intent=RequestIntent.JOURNAL_ONLY
    ).to_dict()
    data["context_scope"] = "everything"
    with pytest.raises(ValueError):
        AssistanceRequest.from_dict(data)
    data["context_scope"] = "none"
    data["schema_version"] = "assistance_request.v99"
    with pytest.raises(ValueError):
        AssistanceRequest.from_dict(data)


# Results ----------------------------------------------------------------------


def test_result_keeps_evidence_and_reports_separate():
    result = AssistanceResult(
        result_id="res.1",
        request_ref="req.2",
        need="practice_aid for the join",
        rationale="Blocked-chord reduction exposes the recurring hand shapes.",
        limitations=("Covers broken-chord subset only.",),
        method_id="aid_selector",
        method_version="v1",
        passage_refs=("test.passage.1",),
        report_refs=("entry.1",),
        observation_refs=("obs.1",),
        suggestion="Try the blocked-chord reduction.",
        objective="objective.recognize_chord_shapes",
    )
    data = _round_trip(result)
    assert data["schema_version"] == ASSISTANCE_RESULT_SCHEMA_VERSION
    assert data["passage_refs"] == ["test.passage.1"]
    assert data["report_refs"] == ["entry.1"]
    assert set(data["passage_refs"]).isdisjoint(data["report_refs"])
    assert result.learner_response is None


def test_result_requires_rationale_and_limitations():
    with pytest.raises(ValueError):
        AssistanceResult(
            result_id="res.x",
            request_ref="req.1",
            need="n",
            rationale="",
            limitations=("scope-limited",),
            method_id="m",
            method_version="v1",
        )
    with pytest.raises(ValueError):
        AssistanceResult(
            result_id="res.x",
            request_ref="req.1",
            need="n",
            rationale="r",
            limitations=(),
            method_id="m",
            method_version="v1",
        )


def test_result_records_learner_response_optionally():
    result = AssistanceResult(
        result_id="res.2",
        request_ref="req.1",
        need="journal_only confirmation",
        rationale="No aid requested; save confirmed.",
        limitations=("No musical analysis performed.",),
        method_id="journal",
        method_version="v1",
        report_refs=("entry.1",),
        learner_response="That matches what I meant.",
    )
    assert AssistanceResult.from_dict(result.to_dict()) == result


def test_result_limitations_are_prose_without_id_length_cap():
    # Regression (LS-09): limitations are sentences, not IDs; a caveat naming
    # a longer entry ID must not trip the 128-char ID validator.
    long_limitation = (
        "report 'entry.conflict' concerns a different region than the "
        "observed passage; the aid below is grounded in passage evidence only"
    )
    assert len(long_limitation) > 128
    result = AssistanceResult(
        result_id="res.3",
        request_ref="req.1",
        need="practice_aid",
        rationale="Grounded in passage evidence.",
        limitations=(long_limitation, "Practice aid only; not a diagnosis."),
        method_id="m",
        method_version="v1",
    )
    assert AssistanceResult.from_dict(result.to_dict()) == result
