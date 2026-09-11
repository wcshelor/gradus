"""Tests for the S2.8 candidate salience view.

Covers top-note register salience, longest-duration salience, metric
accent, explicit accent/dynamic evidence, unavailable slur and
pattern-exclusion evidence, contradictory cues, and exact fractions
using the S2.3 semantic fixtures. Accent/dynamic and contradiction edges
use tiny in-memory ScoreIR doubles over real `Passage` objects so fixture
provenance rules are untouched. No detectors or confidence logic here —
only passage-to-view candidate-factor projection.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.passage import Passage, PassagePurpose, ViewType
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScorePosition
from passage_practice.passages.selection import select_passage
from passage_practice.views.salience_view import (
    SALIENCE_VIEW_SCHEMA_VERSION,
    SalienceView,
    build_salience_view,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _view(name: str, start: Fraction, end: Fraction) -> SalienceView:
    score = _load(name)
    selected = select_passage(score, score_id=name, start=start, end=end)
    return build_salience_view(selected.passage, score)


def _passage(
    passage_id: str,
    refs: tuple,
    start: Fraction = Fraction(0),
    end: Fraction = Fraction(4),
) -> Passage:
    return Passage(
        passage_id=passage_id,
        score_id="synthetic",
        start=ScorePosition(quarters=start, measure_index=0),
        end=ScorePosition(quarters=end, measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=tuple(refs),
    )


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


# --- synthetic ScoreIR doubles (no new fixtures) ---


@dataclass
class _FakeMeasure:
    measure_index: int
    start: Fraction
    end: Fraction
    time_beats: int | None = 4
    time_beat_type: int | None = 4


@dataclass
class _FakeLogical:
    note_id: str
    pitch_midi: int
    onset: Fraction
    duration: Fraction
    hand: str | None = None
    staff: int | None = 1
    voice: str | None = None
    measure_index: int | None = 0
    source_note_ids: tuple[str, ...] = ()
    xml_order: int | None = None


@dataclass
class _FakeWritten:
    note_id: str
    pitch_midi: int
    onset: Fraction
    duration: Fraction
    articulations: tuple[str, ...] = ()


@dataclass
class _FakeDirection:
    direction_id: str
    kind: str
    value: str
    start: Fraction
    end: Fraction | None = None
    measure_index: int | None = 0
    staff: int | None = 1


@dataclass
class _FakeScore:
    measures: list = field(default_factory=list)
    logical_notes: list = field(default_factory=list)
    written_notes: list = field(default_factory=list)
    directions: list = field(default_factory=list)


def _simple_score(
    *,
    dynamics: tuple[tuple[Fraction, str], ...] = (),
    articulations: tuple[str, ...] = (),
) -> _FakeScore:
    """Two attacks at onset 0: a high short note and a low long note.

    The high note is top-of-onset; the low note is longest and carries the
    given articulations. This is the contradiction fixture: register and
    duration/accent cues point at different events and must both survive.
    """
    return _FakeScore(
        measures=[
            _FakeMeasure(measure_index=0, start=Fraction(0), end=Fraction(4))
        ],
        logical_notes=[
            _FakeLogical(
                note_id="n1",
                pitch_midi=79,
                onset=Fraction(0),
                duration=Fraction(1, 2),
                hand="right",
                source_note_ids=("n1",),
                xml_order=1,
            ),
            _FakeLogical(
                note_id="n2",
                pitch_midi=48,
                onset=Fraction(0),
                duration=Fraction(4),
                hand="left",
                source_note_ids=("n2",),
                xml_order=2,
            ),
        ],
        written_notes=[
            _FakeWritten(
                note_id="n1",
                pitch_midi=79,
                onset=Fraction(0),
                duration=Fraction(1, 2),
            ),
            _FakeWritten(
                note_id="n2",
                pitch_midi=48,
                onset=Fraction(0),
                duration=Fraction(4),
                articulations=articulations,
            ),
        ],
        directions=[
            _FakeDirection(
                direction_id=f"d{i}",
                kind="dynamics",
                value=value,
                start=start,
            )
            for i, (start, value) in enumerate(dynamics)
        ],
    )


def _simple_passage() -> Passage:
    return _passage(
        "salience",
        (
            SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="n2", kind=SourceKind.LOGICAL_NOTE),
        ),
    )


# --- top-note register salience ---


def test_top_voice_quarters_are_onset_top_notes():
    view = _view("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    by_id = {e.source_ref.id: e for e in view.events}
    assert by_id["n1"].is_onset_top_note
    assert by_id["n2"].is_onset_top_note
    assert by_id["n3"].is_onset_top_note
    assert by_id["n4"].is_onset_top_note
    # The sustained LH bass is the longest-duration cue but not register-top.
    assert not by_id["n5"].is_onset_top_note
    assert by_id["n5"].is_longest_in_passage
    assert view.summary()["top_note_refs"] == ["n1", "n2", "n3", "n4"]
    assert view.summary()["longest_duration_refs"] == ["n5"]


def test_cross_boundary_sustain_suppresses_is_onset_top_note():
    # A high note starts before the passage and sustains through it.
    # Lower selected attacks occur while it is still sounding, so they
    # must not be is_onset_top_note.  The sustaining high note itself
    # is not in passage.event_refs and must not be emitted.
    score = _FakeScore(
        measures=[
            _FakeMeasure(measure_index=0, start=Fraction(0), end=Fraction(8))
        ],
        logical_notes=[
            _FakeLogical(
                note_id="n_high",
                pitch_midi=79,
                onset=Fraction(0),
                duration=Fraction(8),
                hand="right",
                source_note_ids=("n_high",),
                xml_order=0,
            ),
            _FakeLogical(
                note_id="n_low1",
                pitch_midi=48,
                onset=Fraction(2),
                duration=Fraction(1),
                hand="left",
                source_note_ids=("n_low1",),
                xml_order=1,
            ),
            _FakeLogical(
                note_id="n_low2",
                pitch_midi=50,
                onset=Fraction(3),
                duration=Fraction(1),
                hand="left",
                source_note_ids=("n_low2",),
                xml_order=2,
            ),
        ],
    )
    passage = _passage(
        "cross_boundary",
        (
            SourceRef(id="n_low1", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="n_low2", kind=SourceKind.LOGICAL_NOTE),
        ),
        start=Fraction(2),
        end=Fraction(4),
    )
    view = build_salience_view(passage, score)
    by_id = {e.source_ref.id: e for e in view.events}
    assert set(by_id) == {"n_low1", "n_low2"}
    assert not by_id["n_low1"].is_onset_top_note
    assert not by_id["n_low2"].is_onset_top_note
    assert view.summary()["top_note_refs"] == []


def test_register_only_salience_loses_on_left_hand_melody():
    # Sustained higher RH whole note keeps every LH quarter from being
    # register-top; register-only salience must not pick the LH line here.
    view = _view("semantic_left_hand_melody.musicxml", Fraction(0), Fraction(4))
    by_id = {e.source_ref.id: e for e in view.events}
    assert by_id["n1"].is_onset_top_note and by_id["n1"].is_longest_in_passage
    for ident in ("n2", "n3", "n4", "n5"):
        assert not by_id[ident].is_onset_top_note


# --- longest-duration salience ---


def test_dotted_hold_is_the_longest_duration_cue():
    view = _view("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    by_id = {e.source_ref.id: e for e in view.events}
    assert by_id["n2"].duration == Fraction(3, 2)
    assert by_id["n2"].is_longest_in_passage
    assert view.summary()["longest_duration_refs"] == ["n2"]


# --- metric accent ---


def test_off_beat_attack_exposes_metric_accent_fact():
    view = _view("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    off = next(e for e in view.events if e.onset == Fraction(5, 2))
    assert off.beat_index == 2
    assert off.offset_in_beat == Fraction(1, 2)
    assert off.on_beat is False
    on_beats = [e for e in view.events if e.onset != Fraction(5, 2)]
    assert all(e.on_beat is True and e.offset_in_beat == Fraction(0) for e in on_beats)
    assert all(
        isinstance(e.onset, Fraction)
        and isinstance(e.duration, Fraction)
        and isinstance(e.offset_in_beat, Fraction)
        for e in view.events
    )


# --- explicit accent and dynamic evidence ---


def test_accent_marks_come_from_written_articulations():
    view = build_salience_view(_simple_passage(), _simple_score(articulations=("accent",)))
    by_id = {e.source_ref.id: e for e in view.events}
    assert by_id["n2"].accent_marks == ("accent",)
    assert by_id["n1"].accent_marks == ()
    assert view.summary()["events_with_accent_marks"] == 1


def test_strong_accent_is_also_a_mark():
    view = build_salience_view(
        _simple_passage(),
        _simple_score(articulations=("staccato", "strong-accent")),
    )
    by_id = {e.source_ref.id: e for e in view.events}
    assert by_id["n2"].accent_marks == ("strong-accent",)


def test_dynamic_levels_apply_latest_at_or_before_onset():
    view = build_salience_view(
        _simple_passage(),
        _simple_score(dynamics=((Fraction(0), "f"), (Fraction(2), "p"))),
    )
    by_id = {e.source_ref.id: e for e in view.events}
    # Both events are at onset 0; the latest dynamics at/before 0 is "f".
    assert by_id["n1"].dynamic_levels == ("f",)
    assert by_id["n2"].dynamic_levels == ("f",)


def test_missing_dynamic_evidence_is_recorded_not_zeroed():
    view = _view("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    assert all(e.dynamic_levels == () for e in view.events)
    diagnostic = next(d for d in view.diagnostics if d.code == "missing_dynamic_evidence")
    assert {r.id for r in diagnostic.source_refs} == {
        e.source_ref.id for e in view.events
    }
    assert view.summary()["events_without_dynamic_evidence"] == len(view.events)


# --- unavailable evidence is declared, never silently zeroed ---


def test_slur_evidence_unavailable_with_diagnostic():
    view = _view("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    assert all(e.slur_evidence == () for e in view.events)
    assert any(d.code == "slur_evidence_unavailable" for d in view.diagnostics)


def test_pattern_exclusion_not_available_with_diagnostic():
    view = _view("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    assert all(e.pattern_exclusion_markers == () for e in view.events)
    assert any(d.code == "pattern_exclusion_not_available" for d in view.diagnostics)


# --- contradictory cues are preserved ---


def test_contradictory_cues_survive_side_by_side():
    # Register-top (high short n1) and duration/accent (low long n2)
    # point at different events; the view keeps both candidate markers.
    view = build_salience_view(
        _simple_passage(),
        _simple_score(articulations=("accent",)),
    )
    by_id = {e.source_ref.id: e for e in view.events}
    assert by_id["n1"].is_onset_top_note and not by_id["n1"].is_longest_in_passage
    assert by_id["n2"].is_longest_in_passage and not by_id["n2"].is_onset_top_note
    assert by_id["n2"].accent_marks == ("accent",)
    assert view.summary()["top_note_refs"] == ["n1"]
    assert view.summary()["longest_duration_refs"] == ["n2"]


# --- unknown meter ---


def test_unknown_meter_omits_beats_without_guessing():
    score = _simple_score()
    score.measures = [
        _FakeMeasure(
            measure_index=0,
            start=Fraction(0),
            end=Fraction(4),
            time_beats=None,
            time_beat_type=None,
        )
    ]
    view = build_salience_view(_simple_passage(), score)
    assert all(
        e.beat_index is None
        and e.offset_in_beat is None
        and e.on_beat is None
        for e in view.events
    )
    diagnostic = next(d for d in view.diagnostics if d.code == "unknown_meter")
    assert {r.id for r in diagnostic.source_refs} == {"n1", "n2"}


# --- empty, unresolvable, immutability ---


def test_empty_interval_selects_empty_view_with_diagnostic():
    view = _view("attack_stream_rests.musicxml", Fraction(1), Fraction(2))
    assert view.events == ()
    assert any(d.code == "no_salience_events" for d in view.diagnostics)
    assert view.summary() == {
        "event_count": 0,
        "onset_count": 0,
        "top_note_refs": [],
        "longest_duration_refs": [],
        "events_with_accent_marks": 0,
        "events_with_dynamic_evidence": 0,
        "events_without_dynamic_evidence": 0,
    }


def test_unresolvable_ref_warns_without_failing():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    ghost = dataclasses.replace(
        selected.passage,
        event_refs=(SourceRef(id="n999", kind=SourceKind.LOGICAL_NOTE),),
    )
    view = build_salience_view(ghost, score)
    assert view.events == ()
    assert any(d.code == "unresolvable_attack_ref" for d in view.diagnostics)
    assert any(d.code == "no_salience_events" for d in view.diagnostics)


def test_builder_does_not_mutate_source():
    score = _load("semantic_syncopation.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    before_score = [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.logical_notes
    ]
    before_passage = selected.passage.to_dict()
    build_salience_view(selected.passage, score)
    assert [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.logical_notes
    ] == before_score
    assert selected.passage.to_dict() == before_passage
    view = build_salience_view(selected.passage, score)
    with pytest.raises(Exception):
        view.events = ()


def test_non_logical_refs_skipped():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    passage = dataclasses.replace(
        selected.passage,
        event_refs=(
            SourceRef(id="r2", kind=SourceKind.REST),
            *selected.passage.event_refs,
        ),
    )
    view = build_salience_view(passage, score)
    assert len(view.events) == len(selected.passage.event_refs)
    assert any(d.code == "non_logical_refs_skipped" for d in view.diagnostics)


# --- serialization and contract shape ---


def test_serialization_is_deterministic_with_exact_fractions():
    view = _view("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    assert view.view_type == ViewType.SALIENCE_VIEW
    assert view.to_dict()["schema_version"] == SALIENCE_VIEW_SCHEMA_VERSION
    assert _dump(view.to_dict()) == _dump(
        _view("semantic_syncopation.musicxml", Fraction(0), Fraction(4)).to_dict()
    )
    revived = SalienceView.from_dict(json.loads(_dump(view.to_dict())))
    assert revived == view
    assert all(isinstance(e.onset, Fraction) for e in revived.events)
    assert all(
        isinstance(e.offset_in_beat, Fraction)
        for e in revived.events
        if e.offset_in_beat is not None
    )


def test_serialization_round_trips_unavailable_and_contradiction_fields():
    view = build_salience_view(
        _simple_passage(),
        _simple_score(articulations=("accent",)),
    )
    revived = SalienceView.from_dict(json.loads(_dump(view.to_dict())))
    assert revived == view
    by_id = {e.source_ref.id: e for e in revived.events}
    assert by_id["n2"].accent_marks == ("accent",)
    assert all(e.slur_evidence == () for e in revived.events)
    assert all(e.pattern_exclusion_markers == () for e in revived.events)


def test_bad_version_rejected():
    view = _view("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    payload = view.to_dict()
    payload["schema_version"] = "salience_view.v99"
    with pytest.raises(ValueError):
        SalienceView.from_dict(payload)
    event_payload = view.to_dict()
    event_payload["events"][0]["schema_version"] = "salience_event.v99"
    with pytest.raises(ValueError):
        SalienceView.from_dict(event_payload)


def test_omissions_cover_layout_harmony_rests():
    view = _view("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    assert set(("layout", "harmony", "rests")) <= set(view.omissions)
    assert view.ordering == "onset,xml_order,note_id"
    assert view.grouping is None