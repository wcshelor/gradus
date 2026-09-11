"""Tests for S2.12 direct notation-readability observations.

Covers accidental density, ledger-line proxy, clef-change presence
(unavailable), articulation density, ornament/grace-note diagnostic.
Consumes only written_stream facts.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from passage_practice.observations import (
    ACCIDENTAL_DENSITY_METHOD_ID,
    ARTICULATION_DENSITY_METHOD_ID,
    CLEF_CHANGE_METHOD_ID,
    LEDGER_LINE_PROXY_METHOD_ID,
    ORNAMENT_GRACE_METHOD_ID,
    observe_accidental_density,
    observe_articulation_density,
    observe_clef_change_presence,
    observe_ledger_line_proxy,
    observe_ornament_grace_notes,
)
from passage_practice.passages.selection import select_passage
from passage_practice.passages.investigate import manual_investigation
from passage_practice.views.written_stream import build_written_stream

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _inv(name: str, start: Fraction, end: Fraction):
    score = _load(name)
    inv = manual_investigation(score, score_id=name, start=start, end=end, investigation_id=f"inv.notation.{name}")
    return score, inv


def _notation_inv_and_score():
    from dataclasses import dataclass, field

    @dataclass
    class FakeWritten:
        note_id: str
        pitch_midi: int
        onset: Fraction
        duration: Fraction
        staff: int | None = 1
        voice: str | None = "1"
        hand: str | None = "right"
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
    class FakeLogical:
        note_id: str
        source_note_ids: tuple[str, ...] = ()

    @dataclass
    class FakeScore:
        written_notes: list = field(default_factory=list)
        rests: list = field(default_factory=list)
        logical_notes: list = field(default_factory=list)

    # Mix of accidentals, ledger extremes, articulations, grace
    score = FakeScore(
        written_notes=[
            FakeWritten(note_id="n1", pitch_midi=61, onset=Fraction(0), duration=Fraction(1), staff=1, articulations=("staccato",), accidental="sharp", pitch_step="C", pitch_octave=4, alter=1, xml_order=1),
            FakeWritten(note_id="n2", pitch_midi=36, onset=Fraction(1), duration=Fraction(1), staff=1, pitch_step="C", pitch_octave=2, xml_order=2),  # low ledger for staff 1
            FakeWritten(note_id="n3", pitch_midi=90, onset=Fraction(2), duration=Fraction(1), staff=1, pitch_step="C", pitch_octave=6, xml_order=3),  # high ledger
            FakeWritten(note_id="n4", pitch_midi=64, onset=Fraction(3), duration=Fraction(1, 4), staff=1, is_grace=True, xml_order=4),
            FakeWritten(note_id="n5", pitch_midi=60, onset=Fraction(3), duration=Fraction(1), staff=1, articulations=("accent",), xml_order=5),
        ],
        logical_notes=[
            FakeLogical(note_id="a1", source_note_ids=("n1",)),
            FakeLogical(note_id="a2", source_note_ids=("n2",)),
            FakeLogical(note_id="a3", source_note_ids=("n3",)),
            FakeLogical(note_id="a4", source_note_ids=("n4",)),
            FakeLogical(note_id="a5", source_note_ids=("n5",)),
        ],
    )
    from passage_practice.models.passage import Passage
    from passage_practice.models.investigation import PassageInvestigation, SelectionOrigin

    passage = Passage(
        passage_id="p.notation",
        score_id="synthetic",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(
            SourceRef(id="a1", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="a2", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="a3", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="a4", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="a5", kind=SourceKind.LOGICAL_NOTE),
        ),
    )
    inv = PassageInvestigation(investigation_id="inv.notation", passage=passage, selection_origin=SelectionOrigin.USER_SELECTED, method_id="test", method_version="v1")
    return score, inv


def test_accidental_density_counts_synthetic():
    score, inv = _notation_inv_and_score()
    result = observe_accidental_density(inv, score)
    assert result.observations[0].value == 1
    assert result.observations[0].observation_type == "accidental_count"
    assert result.observations[0].units == "count"
    assert result.observations[0].method_id == ACCIDENTAL_DENSITY_METHOD_ID
    assert {r.id for r in result.observations[0].source_refs} == {"n1"}


def test_ledger_line_proxy_counts_extremes():
    score, inv = _notation_inv_and_score()
    result = observe_ledger_line_proxy(inv, score)
    # n2 (36 <60 staff1) and n3 (90>84 staff1) are ledger
    assert result.observations[0].value == 2
    assert result.observations[0].observation_type == "ledger_line_proxy_count"
    assert any(d.code == "ledger_line_proxy_heuristic" for d in result.diagnostics)
    # Non-ledger passage should give 0 with placeholder ref
    score2, inv2 = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    result2 = observe_ledger_line_proxy(inv2, score2)
    # ambiguity fixture is mid-range, should be 0
    assert result2.observations[0].value == 0


def test_clef_change_presence_is_unavailable_not_zero():
    score, inv = _notation_inv_and_score()
    result = observe_clef_change_presence(inv, score)
    assert result.observations == ()
    assert any(d.code == "clef_data_unavailable" for d in result.diagnostics)
    assert any(d.code == "layout_data_unavailable" for d in result.diagnostics)
    # Must not fabricate zero count when data missing
    assert not any(o.value == 0 for o in result.observations)
    # Real fixture also unavailable
    score2, inv2 = _inv("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    result2 = observe_clef_change_presence(inv2, score2)
    assert result2.observations == ()
    assert any(d.code == "clef_data_unavailable" for d in result2.diagnostics)


def test_articulation_density_counts_synthetic():
    score, inv = _notation_inv_and_score()
    result = observe_articulation_density(inv, score)
    assert result.observations[0].value == 2  # n1 staccato, n5 accent
    assert result.observations[0].observation_type == "articulation_count"


def test_ornament_grace_counts_and_limits():
    score, inv = _notation_inv_and_score()
    result = observe_ornament_grace_notes(inv, score)
    assert result.observations[0].value == 1
    assert result.observations[0].observation_type == "grace_note_count"
    assert result.observations[0].method_id == ORNAMENT_GRACE_METHOD_ID
    # Non-grace passage should give 0 with limited-data diagnostic
    score2, inv2 = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    result2 = observe_ornament_grace_notes(inv2, score2)
    assert result2.observations[0].value == 0
    assert any(d.code == "ornament_data_limited" for d in result2.diagnostics)


def test_hand_scoped_notation_is_inference():
    score, inv = _inv("selection_two_staff.musicxml", Fraction(0), Fraction(4))
    for fn in (observe_accidental_density, observe_ledger_line_proxy, observe_articulation_density, observe_ornament_grace_notes):
        result = fn(inv, score, hand="right")
        if result.observations:
            assert result.observations[0].basis.value == "inference"
            assert any(d.code == "hand_scoped_inference" for d in result.diagnostics)


def test_notation_observations_abstain_on_empty_and_reject_bad_inputs():
    score, _ = _inv("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    empty_inv = manual_investigation(score, score_id="t", start=Fraction(7, 2), end=Fraction(4, 1), investigation_id="inv.notation.empty")
    for fn in (observe_accidental_density, observe_ledger_line_proxy, observe_articulation_density, observe_ornament_grace_notes):
        result = fn(empty_inv, score)
        assert result.observations == ()
        assert any(d.code == "insufficient_attacks" for d in result.diagnostics)
        with pytest.raises(ValueError):
            fn(empty_inv, score, hand="middle")  # type: ignore
        with pytest.raises(TypeError):
            fn("not-an-investigation", score)  # type: ignore
    # clef also rejects bad hand/type but remains unavailable
    with pytest.raises(ValueError):
        observe_clef_change_presence(empty_inv, score, hand="middle")  # type: ignore
    with pytest.raises(TypeError):
        observe_clef_change_presence("bad", score)  # type: ignore


def test_notation_observation_serialization_round_trips():
    score, inv = _notation_inv_and_score()
    for fn in (observe_accidental_density, observe_ledger_line_proxy, observe_articulation_density, observe_ornament_grace_notes):
        result = fn(inv, score)
        payload = result.to_dict()
        from passage_practice.models.observations import ObservationResult

        revived = ObservationResult.from_dict(payload)
        assert revived == result


def test_clef_and_layout_unavailable_diagnostics_present():
    # Ensures missing layout is never zeroed: the observation payload must be empty
    # and carry both unavailable diagnostics, not a silent 0.
    score, inv = _inv("selection_two_staff.musicxml", Fraction(0), Fraction(4))
    stream = build_written_stream(inv.passage, score)
    assert "clefs" in stream.omissions and "layout" in stream.omissions
    result = observe_clef_change_presence(inv, score)
    assert result.observations == ()
    codes = {d.code for d in result.diagnostics}
    assert "clef_data_unavailable" in codes
    assert "layout_data_unavailable" in codes
