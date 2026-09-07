"""Tests for the LS-08 minimal interaction surface.

Deterministic harness checks over synthetic fixtures: help with and without
history, journal-only saves, inspect/correct/delete/exclude, declining
history, and explicit abstention for unsupported input. No model, no
network, no trait inference.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from interaction.session import (
    HARNESS_METHOD_ID,
    InteractionSession,
)
from learner_context.models import (
    AssistanceRequest,
    ContextScope,
    EntryScope,
    JournalEntry,
    RequestIntent,
)
from passage_practice.models.time import ScoreInterval, ScorePosition

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "passage_practice"
    / "tests"
    / "fixtures"
)


def _load(name: str = "selection_two_staff.musicxml"):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _pos(quarters: int, measure_index: int = 1) -> ScorePosition:
    return ScorePosition(
        quarters=Fraction(quarters, 1),
        measure_index=measure_index,
        offset_in_measure=Fraction(0, 1),
    )


def _region(start: int, end: int) -> ScoreInterval:
    return ScoreInterval(start=_pos(start, 1), end=_pos(end, 2))


def _note(entry_id: str = "entry.1", **overrides) -> JournalEntry:
    base = dict(
        entry_id=entry_id,
        text="The big jump keeps slipping.",
        author="learner",
        recorded_at="2026-09-05T10:00:00",
    )
    base.update(overrides)
    return JournalEntry(**base)


def _request(request_id: str = "req.1", **overrides) -> AssistanceRequest:
    base = dict(request_id=request_id, intent=RequestIntent.PRACTICE_AID)
    base.update(overrides)
    return AssistanceRequest(**base)


def test_help_with_no_history_returns_grounded_aid():
    session = InteractionSession()
    score = _load()
    response = session.request_help(
        _request(), score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert response.investigation is not None
    assert response.observations is not None
    assert [o.value for o in response.observations.observations] == [-12, 14, 2, 1]
    assert response.selected.entries == ()
    assert response.result.report_refs == ()
    assert response.result.suggestion is not None and "+14" in response.result.suggestion
    assert response.result.passage_refs == (response.investigation.investigation_id,)
    assert len(response.result.observation_refs) == 2  # -12 and +14 only
    assert response.result.rationale and len(response.result.limitations) >= 2


def test_help_with_saved_report_keeps_report_separate():
    session = InteractionSession()
    session.save_note(_note(piece_id="two-staff"), saved=True)
    score = _load()
    baseline = InteractionSession().request_help(
        _request(), score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    framed = session.request_help(
        _request(context_scope=ContextScope.REFERENCED, piece_id="two-staff"),
        score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert [e.entry_id for e in framed.selected.entries] == ["entry.1"]
    assert framed.result.report_refs == ("entry.1",)
    # Score facts untouched by the report.
    assert [o.value for o in framed.observations.observations] == [
        o.value for o in baseline.observations.observations
    ]
    assert framed.result.suggestion == baseline.result.suggestion
    assert "entry.1" in framed.result.rationale


def test_none_scope_ignores_saved_context():
    session = InteractionSession()
    session.save_note(_note(piece_id="two-staff"), saved=True)
    score = _load()
    declined = session.request_help(
        _request(),  # default ContextScope.NONE
        score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert declined.selected.entries == ()
    assert declined.result.report_refs == ()
    assert declined.result.suggestion is not None and "+14" in declined.result.suggestion


def test_request_region_bounds_are_honored_without_explicit_start_end():
    session = InteractionSession()
    score = _load()
    explicit = session.request_help(
        _request("req.a"), score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    from_request = session.request_help(
        _request("req.b", region=_region(0, 4)),
        score=score, score_id="two-staff",
    )
    assert (
        from_request.investigation.passage.passage_id
        == explicit.investigation.passage.passage_id
    )
    assert from_request.result.suggestion == explicit.result.suggestion


def test_journal_only_save_produces_no_aid():
    session = InteractionSession()
    confirmation = session.save_note(_note())
    assert confirmation.aid_generated is False
    assert "no analysis or aid generated" in confirmation.message
    assert confirmation.permission.saved is False
    assert session.store.get_entry("entry.1").text == "The big jump keeps slipping."
    assert session.inspect_context().summaries == ()


def test_inspect_shows_saved_and_session_entries_without_hidden_summaries():
    session = InteractionSession()
    session.save_note(_note("entry.1"))
    session.save_note(_note("entry.2"), saved=True)
    view = session.inspect_context()
    assert [e.entry_id for e in view.entries] == ["entry.1", "entry.2"]
    assert [p.saved for p in view.permissions] == [False, True]
    assert [e.text for e in view.entries] == [
        "The big jump keeps slipping.",
        "The big jump keeps slipping.",
    ]
    assert view.summaries == ()


def test_correcting_a_note_selects_only_the_new_revision():
    session = InteractionSession()
    session.save_note(_note(), saved=True)
    revised = session.correct_note(
        "entry.1", new_id="entry.2",
        text="The join feels better; the position change still slips.",
        recorded_at="2026-09-06T10:00:00",
    )
    assert revised.revision == 2 and revised.supersedes == "entry.1"
    assert session.store.get_entry("entry.1").revision == 1  # dated, retained
    selected = session.request_help(
        _request(context_scope=ContextScope.PERMITTED),
        score=_load(), score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert [e.entry_id for e in selected.selected.entries] == ["entry.2"]
    assert selected.result.report_refs == ("entry.2",)


def test_deleted_or_excluded_notes_are_never_selected():
    session = InteractionSession()
    session.save_note(_note("entry.1"), saved=True)
    session.save_note(_note("entry.2"), saved=True)
    session.delete_note("entry.1")
    session.set_excluded("entry.2")
    selected = session.request_help(
        _request(context_scope=ContextScope.PERMITTED),
        score=_load(), score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert selected.selected.entries == ()
    assert selected.result.report_refs == ()
    session.set_excluded("entry.2", excluded=False)
    restored = session.request_help(
        _request("req.2", context_scope=ContextScope.PERMITTED),
        score=_load(), score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert [e.entry_id for e in restored.selected.entries] == ["entry.2"]


def test_same_request_runs_with_and_without_history():
    session = InteractionSession()
    session.save_note(_note(piece_id="two-staff"), saved=True)
    score = _load()
    with_history = session.request_help(
        _request("req.a", context_scope=ContextScope.REFERENCED, piece_id="two-staff"),
        score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    without_history = session.request_help(
        _request("req.b", piece_id="two-staff"),  # NONE: history declined
        score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert with_history.result.report_refs == ("entry.1",)
    assert without_history.selected.entries == ()
    assert without_history.result.report_refs == ()
    assert (
        without_history.result.observation_refs == with_history.result.observation_refs
    )
    assert without_history.result.suggestion == with_history.result.suggestion


def test_missing_score_abstains_without_learner_claims():
    session = InteractionSession()
    response = session.request_help(
        _request(), score=None, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert response.investigation is None and response.observations is None
    assert response.result.suggestion is None
    assert response.result.method_id == HARNESS_METHOD_ID
    assert any(d.code == "missing_score" for d in response.result.diagnostics)
    combined = response.result.rationale + " ".join(response.result.limitations)
    assert "not a diagnosis" in combined  # denial, not a claim
    for word in ("trait", "poor coordination", "unmotivated", "measured"):
        assert word not in combined


def test_unresolved_region_abstains_without_guessing():
    session = InteractionSession()
    response = session.request_help(_request(), score=_load(), score_id="two-staff")
    assert response.result.suggestion is None
    assert any(d.code == "unresolved_region" for d in response.result.diagnostics)
    assert "will not be guessed" in response.result.limitations[0]


def test_out_of_range_region_reports_the_reason_code():
    session = InteractionSession()
    response = session.request_help(
        _request(), score=_load(), score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(99, 1),
    )
    assert response.result.suggestion is None
    assert any(d.code == "region_out_of_range" for d in response.result.diagnostics)
    assert "out_of_range" in response.result.rationale


def test_empty_passage_returns_aid_shaped_limitation():
    session = InteractionSession()
    response = session.request_help(
        _request(), score=_load(), score_id="two-staff",
        start=Fraction(7, 2), end=Fraction(4, 1),
    )
    assert response.investigation is not None  # resolved, but no attacks
    assert response.observations is not None and response.observations.observations == ()
    assert response.result.suggestion is None
    assert response.result.limitations[0].startswith("Aid requires")
    combined = response.result.rationale + " ".join(response.result.limitations)
    assert "learner" not in combined and "difficult" not in combined


def test_region_scoped_note_outside_passage_is_kept_separate():
    session = InteractionSession()
    session.save_note(
        _note(
            scope=EntryScope.REGION, piece_id="two-staff", region=_region(8, 12),
        ),
        saved=True,
    )
    response = session.request_help(
        _request("req.c", context_scope=ContextScope.PERMITTED, piece_id="two-staff"),
        score=_load(), score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert response.result.report_refs == ("entry.1",)
    assert any("different region" in lim for lim in response.result.limitations)
    assert response.result.suggestion is not None
