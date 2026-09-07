"""LS-10 lightweight evaluation checks.

Verifies that `research/learning_support/evaluation_ls10.md` links every
evidence ID (E01–E12) to its test, makes no overclaims, and live
re-verifies the starred joint-evaluation facts against current behavior.
Deterministic, synthetic fixtures only; no model, no network.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from interaction.session import InteractionSession
from learner_context.models import (
    AssistanceRequest,
    ContextScope,
    EntryScope,
    JournalEntry,
    RequestIntent,
)
from passage_practice.models.investigation import SelectionOrigin
from passage_practice.models.time import ScoreInterval, ScorePosition

HERE = Path(__file__).resolve()
REPORT = HERE.parents[2] / "evaluation_ls10.md"
FIXTURES = HERE.parents[2] / "passage_practice" / "tests" / "fixtures"

EVIDENCE_LINKS: dict[str, tuple[str, ...]] = {
    "E01": ("test_user_selected_transitions_are_signed_facts",),
    "E02": ("test_evidence_refs_resolve_to_source_events",),
    "E03": ("test_empty_and_single_attack_abstain_without_diagnosing_learner",),
    "E04": (
        "test_rejects_malformed_and_unlocatable_bounds",
        "test_unresolved_selections_are_explicit_without_fabrication",
    ),
    "E05": (
        "test_hand_scoping_is_marked_inference",
        "test_analyzer_route_observes_identically",
    ),
    "E06": ("test_no_history_baseline_aid_is_traceable",),
    "E07": (
        "test_applicable_report_frames_without_altering_facts",
        "test_visit4_conflicting_reports_caveat_without_changing_facts",
    ),
    "E08": (
        "test_below_threshold_returns_limitation",
        "test_visit7_reported_hard_non_hotspot_gets_manual_help",
    ),
    "E09": (
        "test_context_store.py",
        "test_interaction_surface.py",
    ),
    "E10": ("test_return_visits.py",),
    "E11": (
        "test_visit5_ignored_history_matches_score_only_evidence",
        "test_visit7_reported_hard_non_hotspot_gets_manual_help",
    ),
    "E12": (
        "test_outputs_claim_no_progress_inactivity_traits_or_diagnosis",
        "test_report_makes_no_overclaims",
    ),
}

REQUIRED_PHRASES = (
    "synthetic",
    "unproven",
    "not yet reviewed",
    "pending lead review",
    "no measured learning benefit",
    "no real learner data",
)

FORBIDDEN_WORDS = (
    "production",
    "deployed",
    "efficacy",
    "proves",
    "validates",
    "validated",
)

FORBIDDEN_PHRASES = (
    "statistically significant",
)

ALLOWED_LITERALS = (
    "prototype_unvalidated",  # contract constant, not a claim
)

DENIED_THEN_ABSENT = (
    ("no measured learning benefit", "measured learning benefit"),
    ("no real learner data", "real learner data"),
)

FORBIDDEN_SYSTEM_WORDS = (
    "progress", "improv", "inactive", "inactivity", "trait", "streak",
    "adherence", "elapsed", "poor", "unmotivated",
    "day", "week", "month", "gap", "since",
)


def _load(name: str = "selection_two_staff.musicxml"):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _region(start: int, end: int) -> ScoreInterval:
    def pos(quarters: int, measure_index: int) -> ScorePosition:
        return ScorePosition(
            quarters=Fraction(quarters, 1),
            measure_index=measure_index,
            offset_in_measure=Fraction(0, 1),
        )

    return ScoreInterval(start=pos(start, 1), end=pos(end, 2))


def _note(entry_id: str, **overrides) -> JournalEntry:
    base = dict(
        entry_id=entry_id,
        text="The opening jump still slips.",
        author="learner",
        recorded_at="2026-09-01T09:00:00",
    )
    base.update(overrides)
    return JournalEntry(**base)


def _request(request_id: str, **overrides) -> AssistanceRequest:
    base = dict(request_id=request_id, intent=RequestIntent.PRACTICE_AID)
    base.update(overrides)
    return AssistanceRequest(**base)


def _system_text(response) -> str:
    parts = [response.result.rationale, *response.result.limitations]
    parts += [d.message for d in response.result.diagnostics]
    parts += [d.message for d in response.selected.diagnostics]
    if response.observations is not None:
        parts += [d.message for d in response.observations.diagnostics]
    return "\n".join(parts)


def _read_report() -> str:
    assert REPORT.is_file(), f"evaluation report missing at {REPORT}"
    return REPORT.read_text()


def test_evidence_table_links_exist_in_report():
    report = _read_report()
    assert "E01" in report and "E12" in report
    for check_id, nodes in EVIDENCE_LINKS.items():
        assert check_id in report, f"{check_id} missing from report"
        for node in nodes:
            assert node in report, f"{node} ({check_id}) missing from report"
    for fixture in (
        "selection_two_staff.musicxml",
        "selection_ties.musicxml",
        "selection_two_voices.musicxml",
    ):
        assert fixture in report
        assert (FIXTURES / fixture).is_file()


def test_report_makes_no_overclaims():
    import re

    lowered = _read_report().lower()
    for phrase in REQUIRED_PHRASES:
        assert phrase in lowered, f"required guard {phrase!r} missing"
    scrubbed = lowered
    for literal in ALLOWED_LITERALS:
        scrubbed = scrubbed.replace(literal, "")
    for denial, claim in DENIED_THEN_ABSENT:
        assert denial in scrubbed
        scrubbed = scrubbed.replace(denial, "")
    for _, claim in DENIED_THEN_ABSENT:
        assert claim in lowered  # sanity: the denial form is what appears
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in scrubbed, f"overclaim {phrase!r} in report"
    for word in FORBIDDEN_WORDS:
        assert re.search(rf"\b{re.escape(word)}\b", scrubbed) is None, (
            f"overclaim {word!r} in report"
        )


def test_joint_score_only_matches_score_plus_report():
    session = InteractionSession()
    session.save_note(
        _note("entry.j", scope=EntryScope.REGION, piece_id="two-staff",
              region=_region(0, 4)),
        saved=True,
    )
    score = _load()
    kwargs = dict(score=score, score_id="two-staff",
                  start=Fraction(0, 1), end=Fraction(4, 1))
    score_only = InteractionSession().request_help(_request("req.o"), **kwargs)
    with_report = session.request_help(
        _request("req.r", context_scope=ContextScope.REFERENCED, piece_id="two-staff"),
        **kwargs,
    )
    assert [o.value for o in score_only.observations.observations] == [-12, 14, 2, 1]
    assert [o.value for o in with_report.observations.observations] == [-12, 14, 2, 1]
    assert with_report.result.suggestion == score_only.result.suggestion
    assert with_report.result.report_refs == ("entry.j",)
    assert score_only.result.report_refs == ()


def test_joint_ignored_history_matches_score_only():
    session = InteractionSession()
    session.save_note(_note("entry.j", piece_id="two-staff"), saved=True)
    score = _load()
    declined = session.request_help(
        _request("req.n", piece_id="two-staff"),
        score=score, score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert declined.selected.entries == ()
    assert declined.result.report_refs == ()
    assert [o.value for o in declined.observations.observations] == [-12, 14, 2, 1]
    assert declined.result.suggestion is not None


def test_joint_non_hotspot_manual_path_without_fabrication():
    session = InteractionSession()
    session.save_note(
        _note("entry.v", scope=EntryScope.REGION, piece_id="voices",
              region=_region(0, 3)),
        saved=True,
    )
    response = session.request_help(
        _request("req.v", context_scope=ContextScope.REFERENCED, piece_id="voices"),
        score=_load("selection_two_voices.musicxml"), score_id="voices",
        start=Fraction(0, 1), end=Fraction(3, 1),
    )
    assert response.investigation.selection_origin == SelectionOrigin.USER_SELECTED
    assert response.investigation.difficulty == ()
    codes = [d.code for d in response.investigation.diagnostics]
    codes += [d.code for d in response.observations.diagnostics]
    codes += [d.code for d in response.result.diagnostics]
    assert not any("hotspot" in code for code in codes)
    assert [o.value for o in response.observations.observations] == [-4, 5, 2]
    assert response.result.suggestion is None
    assert response.result.report_refs == ("entry.v",)


def test_area_controls_correct_delete_exclude_and_abstain():
    session = InteractionSession()
    session.save_note(_note("entry.a"), saved=True)
    session.save_note(_note("entry.b"), saved=True)
    session.correct_note("entry.a", new_id="entry.a2", text="Revised wording.",
                         recorded_at="2026-09-10T09:00:00")
    session.delete_note("entry.b")
    selected = session.request_help(
        _request("req.c", context_scope=ContextScope.PERMITTED),
        score=_load(), score_id="two-staff",
        start=Fraction(0, 1), end=Fraction(4, 1),
    )
    assert [e.entry_id for e in selected.selected.entries] == ["entry.a2"]

    empty = session.request_help(
        _request("req.e"), score=_load(), score_id="two-staff",
        start=Fraction(7, 2), end=Fraction(4, 1),
    )
    assert empty.result.suggestion is None
    assert empty.observations.observations == ()

    unresolved = session.request_help(
        _request("req.u"), score=_load(), score_id="two-staff"
    )
    assert unresolved.result.suggestion is None
    assert any(d.code == "unresolved_region" for d in unresolved.result.diagnostics)


def test_system_text_has_no_forbidden_claims():
    session = InteractionSession()
    session.save_note(
        _note("entry.j", scope=EntryScope.REGION, piece_id="two-staff",
              region=_region(0, 4)),
        saved=True,
    )
    responses = [
        session.request_help(
            _request("req.s1", context_scope=ContextScope.PERMITTED, piece_id="two-staff"),
            score=_load(), score_id="two-staff",
            start=Fraction(0, 1), end=Fraction(4, 1),
        ),
        session.request_help(
            _request("req.s2", piece_id="two-staff"),
            score=_load(), score_id="two-staff",
            start=Fraction(0, 1), end=Fraction(4, 1),
        ),
    ]
    for response in responses:
        text = _system_text(response).lower()
        for word in FORBIDDEN_SYSTEM_WORDS:
            assert word not in text, f"{word!r} in {response.result.result_id}"
