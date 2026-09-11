"""Tests for the S2.5 written stream view.

Covers two voices, two staves, ties, and omissions using the selection
fixtures plus the S2.4 rests fixture, with logical-attack links, exact
fractions, source immutability, and serialization. Notation-detail edges
use tiny in-memory ScoreIR doubles over real `Passage` objects so fixture
provenance rules are untouched. No observations, detectors, or confidence
logic here — only passage-to-view projection.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.passage import Passage, PassagePurpose, ViewType
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref
from passage_practice.models.time import ScorePosition
from passage_practice.passages.selection import (
    select_passage,
    whole_piece_range,
)
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.written_stream import (
    WRITTEN_STREAM_SCHEMA_VERSION,
    WrittenStream,
    build_written_stream,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _stream(name: str, start: Fraction, end: Fraction) -> WrittenStream:
    score = _load(name)
    selected = select_passage(score, score_id=name, start=start, end=end)
    return build_written_stream(selected.passage, score)


def _passage(
    passage_id: str,
    refs: tuple,
    start: Fraction = Fraction(0),
    end: Fraction = Fraction(2),
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
class _FakeWritten:
    note_id: str
    pitch_midi: int
    onset: Fraction
    duration: Fraction
    staff: int | None = 1
    voice: str | None = None
    hand: str | None = None
    measure_index: int | None = 0
    articulations: tuple[str, ...] = ()
    accidental: str | None = None
    pitch_step: str | None = None
    pitch_octave: int | None = None
    alter: int | None = None
    duration_type: str | None = None
    is_grace: bool = False
    is_chord_continuation: bool = False
    tuplet_actual: int | None = None
    tuplet_normal: int | None = None
    tie_start: bool = False
    tie_stop: bool = False
    xml_order: int | None = None


@dataclass
class _FakeLogical:
    note_id: str
    source_note_ids: tuple[str, ...] = ()


@dataclass
class _FakeScore:
    written_notes: list = field(default_factory=list)
    rests: list = field(default_factory=list)
    logical_notes: list = field(default_factory=list)


def _notation_score() -> _FakeScore:
    return _FakeScore(
        written_notes=[
            _FakeWritten(
                note_id="n1",
                pitch_midi=61,
                onset=Fraction(0),
                duration=Fraction(1),
                staff=1,
                voice="1",
                hand="right",
                articulations=("staccato", "accent"),
                accidental="sharp",
                pitch_step="C",
                pitch_octave=4,
                alter=1,
                duration_type="quarter",
                tuplet_actual=3,
                tuplet_normal=2,
                xml_order=1,
            ),
            _FakeWritten(
                note_id="n2",
                pitch_midi=64,
                onset=Fraction(0),
                duration=Fraction(1, 4),
                staff=1,
                voice="1",
                hand="right",
                is_grace=True,
                is_chord_continuation=True,
                xml_order=2,
            ),
        ],
        logical_notes=[
            _FakeLogical(note_id="n1", source_note_ids=("n1",)),
            _FakeLogical(note_id="n2", source_note_ids=("n2",)),
        ],
    )


def _notation_passage() -> Passage:
    return _passage(
        "notation",
        (
            SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="n2", kind=SourceKind.LOGICAL_NOTE),
        ),
    )


# --- two staves ---


def test_two_staves_keep_staff_hand_distinct():
    stream = _stream("selection_two_staff.musicxml", Fraction(0), Fraction(4))
    assert [n.source_ref.id for n in stream.notes] == ["n1", "n5", "n2", "n3", "n4"]
    assert stream.rests == ()
    by_id = {n.source_ref.id: n for n in stream.notes}
    assert by_id["n1"].staff == 1 and by_id["n1"].hand == "right"
    assert by_id["n5"].staff == 2 and by_id["n5"].hand == "left"
    assert all(n.attack_in_passage for n in stream.notes)


def test_note_sustaining_across_start_is_excluded():
    stream = _stream("selection_two_staff.musicxml", Fraction(1), Fraction(3))
    # LH C3 (0..4) sustains across the start: boundary context, not a notehead.
    assert [n.source_ref.id for n in stream.notes] == ["n2", "n3"]


# --- two voices ---


def test_two_voices_preserved_without_role_claim():
    stream = _stream("selection_two_voices.musicxml", Fraction(0), Fraction(3))
    assert [n.source_ref.id for n in stream.notes] == ["n1", "n4", "n2", "n3"]
    by_id = {n.source_ref.id: n for n in stream.notes}
    assert by_id["n1"].voice == "1" and by_id["n4"].voice == "2"
    # Sustained voice-2 whole note keeps its written duration, not an attack sum.
    assert by_id["n4"].duration == Fraction(3)
    assert all(n.attack_in_passage for n in stream.notes)


# --- ties ---


def test_tie_chain_keeps_both_noteheads_with_written_durations():
    stream = _stream("selection_ties.musicxml", Fraction(4), Fraction(8))
    assert [n.source_ref.id for n in stream.notes] == ["n4", "n5", "n6"]
    by_id = {n.source_ref.id: n for n in stream.notes}
    # Both constituents link to the one collapsed attack; durations stay written.
    assert by_id["n4"].logical_ref == SourceRef(
        id="n4", kind=SourceKind.LOGICAL_NOTE
    )
    assert by_id["n5"].logical_ref == SourceRef(
        id="n4", kind=SourceKind.LOGICAL_NOTE
    )
    assert by_id["n4"].duration == Fraction(1)
    assert by_id["n5"].duration == Fraction(1)
    assert by_id["n4"].tie_start and not by_id["n4"].tie_stop
    assert by_id["n5"].tie_stop and not by_id["n5"].tie_start
    assert all(n.attack_in_passage for n in stream.notes)


def test_tie_continuation_whose_attack_is_outside_stays_linked():
    score = _load("selection_ties.musicxml")
    selected = select_passage(
        score, score_id="ties", start=Fraction(5), end=Fraction(8)
    )
    assert [r.id for r in selected.passage.event_refs] == ["n6"]
    stream = build_written_stream(selected.passage, score)
    assert [n.source_ref.id for n in stream.notes] == ["n5", "n6"]
    by_id = {n.source_ref.id: n for n in stream.notes}
    assert by_id["n5"].logical_ref == SourceRef(
        id="n4", kind=SourceKind.LOGICAL_NOTE
    )
    assert not by_id["n5"].attack_in_passage
    assert by_id["n6"].attack_in_passage
    diagnostic = next(
        d for d in stream.diagnostics if d.code == "linked_attack_outside_passage"
    )
    assert [r.id for r in diagnostic.source_refs] == ["n5"]


def test_links_resolve_and_match_passage_refs():
    score = _load("selection_ties.musicxml")
    selected = select_passage(
        score, score_id="ties", start=Fraction(4), end=Fraction(8)
    )
    stream = build_written_stream(selected.passage, score)
    passage_ids = {
        r.id for r in selected.passage.event_refs if r.kind == SourceKind.LOGICAL_NOTE
    }
    for note in stream.notes:
        assert note.logical_ref is not None
        assert resolve_ref(score, note.logical_ref) is not None
        assert note.attack_in_passage == (note.logical_ref.id in passage_ids)


# --- rests (S2.4 rests fixture, complementary policy) ---


def test_rests_are_entries_alongside_notes():
    stream = _stream("attack_stream_rests.musicxml", Fraction(0), Fraction(4))
    assert [n.source_ref.id for n in stream.notes] == ["n1", "n5", "n3", "n4"]
    assert [r.source_ref.id for r in stream.rests] == ["r2"]
    rest = stream.rests[0]
    assert rest.onset == Fraction(1) and rest.duration == Fraction(1)
    assert rest.staff == 1
    assert "rests" not in stream.omissions
    assert [e.source_ref.id for e in stream.ordered_events()] == [
        "n1",
        "n5",
        "r2",
        "n3",
        "n4",
    ]


def test_rest_gap_yields_rest_only_stream_not_empty():
    stream = _stream("attack_stream_rests.musicxml", Fraction(1), Fraction(2))
    # The S2.4 attack stream is empty here; the written stream keeps the rest.
    assert stream.notes == ()
    assert [r.source_ref.id for r in stream.rests] == ["r2"]
    assert not any(d.code == "no_written_events" for d in stream.diagnostics)


# --- omissions ---


def test_omissions_cover_directions_clefs_layout():
    score = _load("selection_two_voices.musicxml")
    assert score.directions or score.clefs  # fixture carries context the stream skips
    stream = _stream("selection_two_voices.musicxml", Fraction(0), Fraction(3))
    assert set(("directions", "clefs", "layout")) <= set(stream.omissions)


# --- notation details ---


def test_notation_details_preserved():
    stream = build_written_stream(_notation_passage(), _notation_score())
    first = stream.notes[0]
    assert first.articulations == ("staccato", "accent")
    assert first.accidental == "sharp"
    assert (first.pitch_step, first.pitch_octave, first.alter) == ("C", 4, 1)
    assert first.duration_type == "quarter"
    assert (first.tuplet_actual, first.tuplet_normal) == (3, 2)
    second = stream.notes[1]
    assert second.is_grace and second.is_chord_continuation


# --- exact timing, immutability, diagnostics ---


def test_exact_fractions_and_ordering():
    stream = _stream("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    assert len(stream.notes) == 8
    assert Fraction(5, 2) in {n.onset for n in stream.notes}
    assert all(
        isinstance(n.onset, Fraction) and isinstance(n.duration, Fraction)
        for n in stream.notes
    )
    onsets = [n.onset for n in stream.notes]
    assert onsets == sorted(onsets)


def test_builder_does_not_mutate_source():
    score = _load("semantic_syncopation.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    before_score = [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.written_notes
    ]
    before_passage = selected.passage.to_dict()
    build_written_stream(selected.passage, score)
    assert [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.written_notes
    ] == before_score
    assert selected.passage.to_dict() == before_passage
    stream = build_written_stream(selected.passage, score)
    with pytest.raises(Exception):
        stream.notes = ()


def test_empty_interval_selects_empty_stream_with_diagnostic():
    stream = _stream("selection_two_staff.musicxml", Fraction(15, 2), Fraction(8))
    assert stream.notes == () and stream.rests == ()
    assert any(d.code == "no_written_events" for d in stream.diagnostics)


def test_unresolvable_ref_warns_without_failing():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    ghost = dataclasses.replace(
        selected.passage,
        event_refs=(SourceRef(id="n999", kind=SourceKind.LOGICAL_NOTE),),
    )
    stream = build_written_stream(ghost, score)
    assert [n.source_ref.id for n in stream.notes] == ["n1", "n5", "n2", "n3", "n4"]
    assert any(d.code == "unresolvable_attack_ref" for d in stream.diagnostics)


def test_unmapped_written_note_warns_with_unlinked_entry():
    score = _notation_score()
    score.logical_notes = [
        _FakeLogical(note_id="n1", source_note_ids=("n1",)),
    ]
    stream = build_written_stream(_notation_passage(), score)
    by_id = {n.source_ref.id: n for n in stream.notes}
    assert by_id["n2"].logical_ref is None
    assert not by_id["n2"].attack_in_passage
    assert any(d.code == "unmapped_written_note" for d in stream.diagnostics)


# --- serialization + contract shape ---


def test_serialization_is_deterministic_with_exact_fractions():
    stream = _stream("selection_ties.musicxml", Fraction(4), Fraction(8))
    assert stream.view_type == ViewType.WRITTEN_EVENT_STREAM
    assert stream.to_dict()["schema_version"] == WRITTEN_STREAM_SCHEMA_VERSION
    assert _dump(stream.to_dict()) == _dump(
        _stream("selection_ties.musicxml", Fraction(4), Fraction(8)).to_dict()
    )
    revived = WrittenStream.from_dict(json.loads(_dump(stream.to_dict())))
    assert revived == stream
    assert all(isinstance(n.onset, Fraction) for n in revived.notes)


def test_bad_version_rejected():
    stream = _stream("selection_two_staff.musicxml", Fraction(0), Fraction(4))
    payload = stream.to_dict()
    payload["schema_version"] = "written_stream.v99"
    with pytest.raises(ValueError):
        WrittenStream.from_dict(payload)
    event_payload = stream.to_dict()
    event_payload["notes"][0]["schema_version"] = "written_note_event.v99"
    with pytest.raises(ValueError):
        WrittenStream.from_dict(event_payload)


# --- S2.4 consistency ---


def test_written_note_ids_cover_attack_sources_over_whole_piece():
    score = _load("selection_two_staff.musicxml")
    span = whole_piece_range(score)
    selected = select_passage(
        score,
        score_id="whole",
        start=span.start.quarters,
        end=span.end.quarters,
    )
    attacks = build_attack_stream(selected.passage, score)
    written = build_written_stream(selected.passage, score)
    assert {n.source_ref.id for n in written.notes} == {
        wid for a in attacks.attacks for wid in a.source_note_ids
    }


def test_semantic_fixture_note_counts_match_attacks():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="top", start=Fraction(0), end=Fraction(4)
    )
    stream = build_written_stream(selected.passage, score)
    assert len(stream.notes) == 5 == len(selected.passage.event_refs)
