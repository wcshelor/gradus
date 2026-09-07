"""LS-09: return visits, revisions, and uncertain context.

One synthetic multi-visit history exercised through the deterministic LS-08
harness (`InteractionSession`) over the LS-05 selection fixtures. Stages:

- V1 (2026-09-01): first region report saved with explicit permission; help
  uses it.
- Gap: nine days pass; represented only by timestamps, never interpreted.
- V2 (2026-09-10): changed difficulty arrives as a dated correction; the old
  revision stays readable but is never selected or authoritative.
- V3: a stale general habit report is dated context, not a trait.
- V4: a conflicting region report yields caveats, never altered score facts.
- V5: the same request runs with history ignored (`ContextScope.NONE`).
- V6: exclusion stales and deletion cascades dependent summaries.
- V7: a learner-reported hard section that is no analyzer hotspot still gets
  manual passage help with no hotspot fabrication.

No model, no network, no progress/inactivity/trait/ability inference. Score
evidence, observations, aid results, and learner reports stay separate.
"""

from __future__ import annotations

import json
from datetime import datetime
from fractions import Fraction
from pathlib import Path

import pytest

from interaction.session import InteractionSession
from learner_context.models import (
    AssistanceRequest,
    ContextScope,
    ContextSummary,
    EntryScope,
    JournalEntry,
    RequestIntent,
)
from passage_practice.models.investigation import SelectionOrigin
from passage_practice.models.time import ScoreInterval, ScorePosition

FIXTURES = (
    Path(__file__).resolve().parents[3]
    / "passage_practice"
    / "tests"
    / "fixtures"
)

PIECE = "two-staff"
START = Fraction(0, 1)
END = Fraction(4, 1)

HARD1 = (
    "In measures 1-2 I can play the hands separately, but lose my place "
    "when joining them. Slow repetition didn't help."
)
HARD1R2 = "The join feels better, the position change still slips."
HABIT = "I tend to restart from the beginning."
CONFLICT = "Measure 2 feels settled; only the opening jump slips."
VOICES_REPORT = "These measures are hard for me; the upper voice keeps slipping."


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


def _note(entry_id: str, **overrides) -> JournalEntry:
    base = dict(
        entry_id=entry_id,
        text=HARD1,
        author="learner",
        recorded_at="2026-09-01T09:00:00",
    )
    base.update(overrides)
    return JournalEntry(**base)


def _request(request_id: str, **overrides) -> AssistanceRequest:
    base = dict(request_id=request_id, intent=RequestIntent.PRACTICE_AID)
    base.update(overrides)
    return AssistanceRequest(**base)


def _help(session, request_id, scope, **overrides):
    return session.request_help(
        _request(request_id, context_scope=scope, piece_id=PIECE, **overrides),
        score=_load(), score_id=PIECE, start=START, end=END,
    )


def _session_through_visit4() -> InteractionSession:
    """Replay V1–V4 saves: first report, dated correction, habit, conflict."""
    session = InteractionSession()
    session.save_note(
        _note(
            "entry.hard1", scope=EntryScope.REGION, piece_id=PIECE,
            region=_region(0, 4),
        ),
        saved=True,
    )
    session.correct_note(
        "entry.hard1", new_id="entry.hard1r2", text=HARD1R2,
        recorded_at="2026-09-10T09:00:00",
    )
    session.save_note(_note("entry.habit", text=HABIT,
                            recorded_at="2026-08-01T09:00:00"), saved=True)
    session.save_note(
        _note(
            "entry.conflict", text=CONFLICT, scope=EntryScope.REGION,
            piece_id=PIECE, region=_region(4, 8),
            recorded_at="2026-09-10T10:00:00",
        ),
        saved=True,
    )
    return session


def _baseline():
    return InteractionSession().request_help(
        _request("req.base"), score=_load(), score_id=PIECE, start=START, end=END,
    )


def _system_text(response) -> str:
    parts = [response.result.rationale, *response.result.limitations]
    parts += [d.message for d in response.result.diagnostics]
    parts += [d.message for d in response.selected.diagnostics]
    if response.observations is not None:
        parts += [d.message for d in response.observations.diagnostics]
    return "\n".join(parts)


# V1 — first report ------------------------------------------------------------


def test_visit1_first_report_saved_with_permission_and_used():
    session = InteractionSession()
    confirmation = session.save_note(
        _note(
            "entry.hard1", scope=EntryScope.REGION, piece_id=PIECE,
            region=_region(0, 4),
        ),
        saved=True,
    )
    assert confirmation.permission.saved is True
    assert session.store.get_entry("entry.hard1").text == HARD1  # verbatim

    response = _help(session, "req.v1", ContextScope.REFERENCED)
    assert [e.entry_id for e in response.selected.entries] == ["entry.hard1"]
    assert response.result.report_refs == ("entry.hard1",)
    assert "entry.hard1" in response.result.rationale
    # Grounded in passage evidence, with layers separate.
    assert [o.value for o in response.observations.observations] == [-12, 14, 2, 1]
    assert response.result.suggestion is not None and "+14" in response.result.suggestion
    assert response.result.passage_refs == (response.investigation.investigation_id,)
    concern = [d for d in response.investigation.diagnostics
               if d.code == "reported_concern"]
    assert [r for d in concern for r in d.context["report_refs"]] == ["entry.hard1"]


# V2 — return after gap, changed difficulty ------------------------------------


def test_visit2_changed_report_supersedes_without_rewriting_history():
    session = InteractionSession()
    session.save_note(
        _note(
            "entry.hard1", scope=EntryScope.REGION, piece_id=PIECE,
            region=_region(0, 4),
        ),
        saved=True,
    )
    revised = session.correct_note(
        "entry.hard1", new_id="entry.hard1r2", text=HARD1R2,
        recorded_at="2026-09-10T09:00:00",
    )
    assert revised.revision == 2 and revised.supersedes == "entry.hard1"
    assert revised.recorded_at == "2026-09-10T09:00:00"
    # The gap exists in the data (nine days) and nowhere else.
    gap = datetime.fromisoformat(revised.recorded_at) - datetime.fromisoformat(
        session.store.get_entry("entry.hard1").recorded_at
    )
    assert gap.days == 9
    # Old report stays dated and readable, not authoritative.
    assert session.store.get_entry("entry.hard1").text == HARD1

    response = _help(session, "req.v2", ContextScope.PERMITTED)
    assert [e.entry_id for e in response.selected.entries] == ["entry.hard1r2"]
    assert response.result.report_refs == ("entry.hard1r2",)
    assert "entry.hard1r2" in response.result.rationale
    # Same score facts as V1; only the framing reference changed.
    assert [o.value for o in response.observations.observations] == [-12, 14, 2, 1]
    assert response.result.suggestion == _baseline().result.suggestion


# V3 — stale habit report ------------------------------------------------------


def test_visit3_stale_habit_report_is_dated_context_not_a_trait():
    session = _session_through_visit4()
    response = _help(session, "req.v3", ContextScope.PERMITTED)
    habit = session.store.get_entry("entry.habit")
    assert habit.scope == EntryScope.GENERAL
    assert habit.recorded_at == "2026-08-01T09:00:00"  # predates the visits
    assert habit.text == HABIT  # verbatim, unexpanded
    assert "entry.habit" in response.result.report_refs
    # It frames; it does not reshape score evidence or become a trait claim.
    assert [o.value for o in response.observations.observations] == [-12, 14, 2, 1]
    assert response.result.suggestion == _baseline().result.suggestion
    assert "trait" not in _system_text(response)


# V4 — conflicting reports -----------------------------------------------------


def test_visit4_conflicting_reports_caveat_without_changing_facts():
    session = _session_through_visit4()
    response = _help(session, "req.v4", ContextScope.PERMITTED)
    assert [e.entry_id for e in response.selected.entries] == [
        "entry.hard1r2", "entry.habit", "entry.conflict",
    ]
    assert response.result.report_refs == (
        "entry.hard1r2", "entry.habit", "entry.conflict",
    )
    caveats = [lim for lim in response.result.limitations if "different region" in lim]
    assert len(caveats) == 1 and "entry.conflict" in caveats[0]
    # The conflict is recorded, not resolved by altering score values.
    assert [o.value for o in response.observations.observations] == [-12, 14, 2, 1]
    assert response.result.suggestion == _baseline().result.suggestion
    assert response.result.suggestion is not None


# V5 — history ignored ---------------------------------------------------------


def test_visit5_ignored_history_matches_score_only_evidence():
    session = _session_through_visit4()
    request = dict(context_scope=ContextScope.NONE, piece_id=PIECE)
    first = session.request_help(
        _request("req.v5", **request),
        score=_load(), score_id=PIECE, start=START, end=END,
    )
    second = session.request_help(
        _request("req.v5", **request),
        score=_load(), score_id=PIECE, start=START, end=END,
    )
    assert first.selected.entries == () and second.selected.entries == ()
    assert first.result.report_refs == ()
    baseline = _baseline()
    assert [o.value for o in first.observations.observations] == [
        o.value for o in baseline.observations.observations
    ]
    assert first.result.suggestion == baseline.result.suggestion
    assert json.dumps(first.result.to_dict(), sort_keys=True) == json.dumps(
        second.result.to_dict(), sort_keys=True
    )


# V6 — deletion and exclusion propagate ----------------------------------------


def test_visit6_exclusion_stales_and_deletion_cascades_summaries():
    session = _session_through_visit4()
    session.store.add_summary(
        ContextSummary(
            summary_id="sum.1",
            source_entry_ids=("entry.hard1r2", "entry.habit"),
            method_id="recurrence_heuristic",
            method_version="v1",
            created_at="2026-09-10T11:00:00",
            interpretation="Join difficulty recurs; unconfirmed.",
        )
    )
    assert session.store.is_summary_current("sum.1") is True
    attached = _help(session, "req.v6a", ContextScope.PERMITTED)
    assert [s.summary_id for s in attached.selected.summaries] == ["sum.1"]

    session.set_excluded("entry.habit")
    assert session.store.is_summary_current("sum.1") is False
    stale = _help(session, "req.v6b", ContextScope.PERMITTED)
    assert "entry.habit" not in [e.entry_id for e in stale.selected.entries]
    assert stale.selected.summaries == ()
    assert stale.result.report_refs == ("entry.hard1r2", "entry.conflict")

    session.set_excluded("entry.habit", excluded=False)
    assert session.store.is_summary_current("sum.1") is True

    session.delete_note("entry.hard1r2")
    with pytest.raises(KeyError):
        session.store.get_summary("sum.1")  # cascaded: no hidden memory
    after = _help(session, "req.v6c", ContextScope.PERMITTED)
    assert "entry.hard1r2" not in [e.entry_id for e in after.selected.entries]
    assert "entry.hard1r2" not in after.result.report_refs
    assert session.inspect_context().summaries == ()


# V7 — reported hard, not a hotspot --------------------------------------------


def test_visit7_reported_hard_non_hotspot_gets_manual_help():
    session = InteractionSession()
    session.save_note(
        _note(
            "entry.voices", text=VOICES_REPORT, scope=EntryScope.REGION,
            piece_id="voices", region=_region(0, 3),
            recorded_at="2026-09-12T09:00:00",
        ),
        saved=True,
    )
    score = _load("selection_two_voices.musicxml")  # sparse, never ranked
    response = session.request_help(
        _request("req.v7", context_scope=ContextScope.REFERENCED, piece_id="voices"),
        score=score, score_id="voices", start=Fraction(0, 1), end=Fraction(3, 1),
    )
    assert [e.entry_id for e in response.selected.entries] == ["entry.voices"]
    assert response.result.report_refs == ("entry.voices",)
    # Manual entry with no difficulty computation and no hotspot IDs.
    assert response.investigation.selection_origin == SelectionOrigin.USER_SELECTED
    assert response.investigation.difficulty == ()
    codes = [d.code for d in response.investigation.diagnostics]
    codes += [d.code for d in response.observations.diagnostics]
    codes += [d.code for d in response.result.diagnostics]
    assert not any("hotspot" in code for code in codes)
    assert "hotspot" not in response.result.rationale
    assert " ".join(response.result.limitations).count("hotspot") == 0
    # Sparse low-demand material: honest below-threshold limitation, still traceable.
    assert [o.value for o in response.observations.observations] == [-4, 5, 2]
    assert response.result.suggestion is None
    assert any("7 semitones" in lim for lim in response.result.limitations)
    assert len(response.result.observation_refs) == 3


# Language prohibitions across the whole history -------------------------------


def test_outputs_claim_no_progress_inactivity_traits_or_diagnosis():
    session = _session_through_visit4()
    responses = [
        _help(session, "req.t1", ContextScope.REFERENCED),
        _help(session, "req.t2", ContextScope.PERMITTED),
        session.request_help(
            _request("req.t3", piece_id=PIECE),  # NONE
            score=_load(), score_id=PIECE, start=START, end=END,
        ),
    ]
    score = _load("selection_two_voices.musicxml")
    fresh = InteractionSession()
    fresh.save_note(_note("entry.v", text=VOICES_REPORT), saved=True)
    responses.append(
        fresh.request_help(
            _request("req.t4", context_scope=ContextScope.PERMITTED),
            score=score, score_id="voices",
            start=Fraction(0, 1), end=Fraction(3, 1),
        )
    )
    forbidden = (
        "progress", "improv", "inactive", "inactivity", "trait", "streak",
        "adherence", "elapsed", "poor", "unmotivated",
        "day", "week", "month", "gap", "since",
    )
    for response in responses:
        text = _system_text(response).lower()
        for word in forbidden:
            assert word not in text, f"{word!r} in {response.result.result_id}"
    # Reports survive verbatim as data, not as system claims.
    assert session.store.get_entry("entry.hard1").text == HARD1
    assert session.store.get_entry("entry.hard1r2").text == HARD1R2
    assert session.store.get_entry("entry.habit").text == HABIT
