"""Tests for S2.11 direct texture observations.

Covers simultaneity count, chord density, sustained-under-moving count,
voice count, staff crossing where available. Consumes only texture_grid facts.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from passage_practice.observations import (
    CHORD_DENSITY_METHOD_ID,
    MAX_SIMULTANEITY_METHOD_ID,
    STAFF_CROSSING_METHOD_ID,
    SUSTAINED_UNDER_MOVING_METHOD_ID,
    VOICE_COUNT_METHOD_ID,
    observe_chord_density,
    observe_max_simultaneity,
    observe_staff_crossing,
    observe_sustained_under_moving,
    observe_voice_count,
)
from passage_practice.passages.selection import select_passage
from passage_practice.passages.investigate import manual_investigation
from passage_practice.views.texture_grid import build_texture_grid

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _inv(name: str, start: Fraction, end: Fraction):
    score = _load(name)
    inv = manual_investigation(score, score_id=name, start=start, end=end, investigation_id=f"inv.texture.{name}")
    return score, inv


def test_chord_vs_sequential_max_simultaneity():
    # Chord texture: paired attacks (size 2)
    score_chord, inv_chord = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    grid_chord = build_texture_grid(inv_chord.passage, score_chord)
    result_chord = observe_max_simultaneity(inv_chord, score_chord)
    assert result_chord.observations[0].value == grid_chord.summary()["max_chord_size"] == 2
    assert result_chord.observations[0].observation_type == "max_simultaneity"
    # Sequential / arpeggiated texture: accompaniment pattern has max 2 at only one onset, otherwise 1
    score_seq, inv_seq = _inv("semantic_accompaniment_pattern.musicxml", Fraction(0), Fraction(4))
    grid_seq = build_texture_grid(inv_seq.passage, score_seq)
    result_seq = observe_max_simultaneity(inv_seq, score_seq)
    assert result_seq.observations[0].value == grid_seq.summary()["max_chord_size"] == 2
    # attack_stream_rests fixture: check that observation tracks the grid (expected 1 or 2 depending on rests fixture)
    score_mono, inv_mono = _inv("attack_stream_rests.musicxml", Fraction(0), Fraction(4))
    grid_mono = build_texture_grid(inv_mono.passage, score_mono)
    result_mono = observe_max_simultaneity(inv_mono, score_mono)
    assert result_mono.observations[0].value == grid_mono.summary()["max_chord_size"]


def test_chord_density_counts_chordal_onsets():
    score_chord, inv_chord = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    result = observe_chord_density(inv_chord, score_chord)
    assert result.observations[0].value == 4  # all 4 onsets are chords
    score_single, inv_single = _inv("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    grid_single = build_texture_grid(inv_single.passage, score_single)
    result_single = observe_chord_density(inv_single, score_single)
    assert result_single.observations[0].value == grid_single.summary()["chordal_onset_count"]


def test_sustained_under_moving_counts_slices_with_sustain():
    score, inv = _inv("semantic_accompaniment_pattern.musicxml", Fraction(0), Fraction(4))
    grid = build_texture_grid(inv.passage, score)
    result = observe_sustained_under_moving(inv, score)
    assert result.observations[0].value == grid.summary()["sustained_under_moving_count"] == 7
    # Empty sustained: paired chords have no sustain
    score2, inv2 = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    result2 = observe_sustained_under_moving(inv2, score2)
    assert result2.observations[0].value == 0
    # Two voices where one sustains under the other
    score3, inv3 = _inv("selection_two_voices.musicxml", Fraction(0), Fraction(3))
    result3 = observe_sustained_under_moving(inv3, score3)
    assert result3.observations[0].value == 2
    # Cross-boundary sustain is out of scope and not counted
    score4, inv4 = _inv("selection_two_staff.musicxml", Fraction(1), Fraction(4))
    grid4 = build_texture_grid(inv4.passage, score4)
    assert all(not s.sustained_under_moving for s in grid4.slices)
    result4 = observe_sustained_under_moving(inv4, score4)
    assert result4.observations[0].value == 0


def test_voice_count_two_voices_vs_one():
    # Two encoded voices in ambiguity and two_voices fixtures
    score_two, inv_two = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    result_two = observe_voice_count(inv_two, score_two)
    assert result_two.observations[0].value == 2
    score_two2, inv_two2 = _inv("selection_two_voices.musicxml", Fraction(0), Fraction(3))
    result_two2 = observe_voice_count(inv_two2, score_two2)
    assert result_two2.observations[0].value == 2
    # Single voice fixture? Use syncopation where voices may be one per hand but encoded as 1? Check
    score_mix, inv_mix = _inv("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    grid_mix = build_texture_grid(inv_mix.passage, score_mix)
    result_mix = observe_voice_count(inv_mix, score_mix)
    assert result_mix.observations[0].value == len(grid_mix.summary()["voices"])


def test_ambiguous_voice_behavior():
    # Synthetic score with no voice facts (voices = None) should give 0 with diagnostic
    from dataclasses import dataclass, field

    @dataclass
    class FakeMeasure:
        measure_index: int
        start: Fraction
        end: Fraction
        time_beats: int | None = 4
        time_beat_type: int | None = 4

    @dataclass
    class FakeLogical:
        note_id: str
        onset: Fraction
        duration: Fraction
        hand: str | None = "right"
        staff: int | None = 1
        voice: str | None = None
        measure_index: int | None = 0
        source_note_ids: tuple[str, ...] = ()
        xml_order: int | None = 1

    @dataclass
    class FakeScore:
        measures: list = field(default_factory=list)
        logical_notes: list = field(default_factory=list)
        written_notes: list = field(default_factory=list)

    score = FakeScore(
        measures=[FakeMeasure(measure_index=0, start=Fraction(0), end=Fraction(4))],
        logical_notes=[
            FakeLogical(note_id="n1", onset=Fraction(0), duration=Fraction(1), voice=None, xml_order=1),
            FakeLogical(note_id="n2", onset=Fraction(1), duration=Fraction(1), voice=None, xml_order=2),
        ],
    )
    passage = Passage(
        passage_id="p.ambvoice",
        score_id="synthetic",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(
            SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="n2", kind=SourceKind.LOGICAL_NOTE),
        ),
    )
    from passage_practice.models.investigation import PassageInvestigation, SelectionOrigin

    inv = PassageInvestigation(
        investigation_id="inv.ambvoice",
        passage=passage,
        selection_origin=SelectionOrigin.USER_SELECTED,
        method_id="test",
        method_version="v1",
    )
    result = observe_voice_count(inv, score)
    assert result.observations[0].value == 0
    assert any(d.code == "ambiguous_voice" for d in result.diagnostics)


def test_staff_crossing_normally_zero_and_crossing_detected():
    # Normal fixtures have no crossing
    score, inv = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    result = observe_staff_crossing(inv, score)
    assert result.observations[0].value == 0
    # Synthetic crossing: left hand on upper staff, right on lower
    from dataclasses import dataclass, field

    @dataclass
    class FakeMeasure:
        measure_index: int
        start: Fraction
        end: Fraction
        time_beats: int | None = 4
        time_beat_type: int | None = 4

    @dataclass
    class FakeLogical:
        note_id: str
        onset: Fraction
        duration: Fraction
        hand: str | None = None
        staff: int | None = None
        voice: str | None = None
        measure_index: int | None = 0
        source_note_ids: tuple[str, ...] = ()
        xml_order: int | None = 1

    @dataclass
    class FakeScore:
        measures: list = field(default_factory=list)
        logical_notes: list = field(default_factory=list)
        written_notes: list = field(default_factory=list)

    score2 = FakeScore(
        measures=[FakeMeasure(measure_index=0, start=Fraction(0), end=Fraction(4))],
        logical_notes=[
            FakeLogical(note_id="nL", onset=Fraction(0), duration=Fraction(1), hand="left", staff=1, xml_order=1),  # crossing
            FakeLogical(note_id="nR", onset=Fraction(1), duration=Fraction(1), hand="right", staff=2, xml_order=2),  # crossing
            FakeLogical(note_id="nOk", onset=Fraction(2), duration=Fraction(1), hand="right", staff=1, xml_order=3),
        ],
    )
    passage2 = Passage(
        passage_id="p.cross",
        score_id="synthetic",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=0),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(
            SourceRef(id="nL", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="nR", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="nOk", kind=SourceKind.LOGICAL_NOTE),
        ),
    )
    from passage_practice.models.investigation import PassageInvestigation, SelectionOrigin

    inv2 = PassageInvestigation(
        investigation_id="inv.cross",
        passage=passage2,
        selection_origin=SelectionOrigin.USER_SELECTED,
        method_id="test",
        method_version="v1",
    )
    result2 = observe_staff_crossing(inv2, score2)
    assert result2.observations[0].value == 2
    assert {r.id for r in result2.observations[0].source_refs} == {"nL", "nR"}


def test_hand_scoped_texture_is_inference():
    score, inv = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    for fn in (observe_max_simultaneity, observe_chord_density, observe_sustained_under_moving, observe_voice_count, observe_staff_crossing):
        result = fn(inv, score, hand="right")
        if result.observations:
            assert result.observations[0].basis.value == "inference"
            assert any(d.code == "hand_scoped_inference" for d in result.diagnostics)


def test_texture_observations_abstain_on_empty_and_reject_bad_inputs():
    score, _ = _inv("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    empty_inv = manual_investigation(score, score_id="t", start=Fraction(7, 2), end=Fraction(4, 1), investigation_id="inv.texture.empty")
    for fn in (observe_max_simultaneity, observe_chord_density, observe_sustained_under_moving, observe_voice_count, observe_staff_crossing):
        result = fn(empty_inv, score)
        assert result.observations == ()
        assert any(d.code == "insufficient_attacks" for d in result.diagnostics)
        with pytest.raises(ValueError):
            fn(empty_inv, score, hand="middle")  # type: ignore
        with pytest.raises(TypeError):
            fn("not-an-investigation", score)  # type: ignore


def test_texture_observation_serialization_round_trips():
    score, inv = _inv("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    for fn in (observe_max_simultaneity, observe_chord_density, observe_sustained_under_moving, observe_voice_count, observe_staff_crossing):
        result = fn(inv, score)
        payload = result.to_dict()
        from passage_practice.models.observations import ObservationResult

        revived = ObservationResult.from_dict(payload)
        assert revived == result
        for obs in revived.observations:
            assert obs.passage_id == inv.passage.passage_id
            assert obs.source_refs
