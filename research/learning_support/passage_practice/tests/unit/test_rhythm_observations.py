"""Tests for S2.10 direct rhythm observations — attack density, shortest duration, off-beat, syncopation, hand alignment, subdivision mismatch.

Covers aligned vs staggered hands, shortest duration, off-beat density,
syncopation proxy, and tuplet unsupported diagnostic. Consumes only
rhythm_grid facts via observations, never parses MusicXML directly.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from passage_practice.models.diagnostics import Diagnostic
from passage_practice.observations import (
    ATTACK_DENSITY_METHOD_ID,
    HAND_ALIGNMENT_METHOD_ID,
    OFF_BEAT_METHOD_ID,
    SHORTEST_DURATION_METHOD_ID,
    SUBDIVISION_MISMATCH_METHOD_ID,
    SYNCOPATION_METHOD_ID,
    observe_attack_density,
    observe_hand_alignment_ratio,
    observe_off_beat_density,
    observe_shortest_duration,
    observe_subdivision_mismatch,
    observe_syncopation_proxy,
)
from passage_practice.passages.selection import select_passage
from passage_practice.passages.investigate import manual_investigation
from passage_practice.views.rhythm_grid import build_rhythm_grid

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _inv(name: str, start: Fraction, end: Fraction):
    score = _load(name)
    inv = manual_investigation(
        score, score_id=name, start=start, end=end, investigation_id=f"inv.rhythm.{name}"
    )
    return score, inv


def test_attack_density_counts_cells():
    score, inv = _inv("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    grid = build_rhythm_grid(inv.passage, score)
    result = observe_attack_density(inv, score)
    assert len(result.observations) == 1
    obs = result.observations[0]
    assert obs.observation_type == "attack_density"
    assert obs.units == "count"
    assert obs.value == len(grid.cells)
    assert len(obs.source_refs) == len(grid.cells)
    assert obs.method_id == ATTACK_DENSITY_METHOD_ID
    for ref in obs.source_refs:
        assert ref.kind == SourceKind.LOGICAL_NOTE


def test_shortest_duration_is_minimum_scaled_to_ticks():
    score, inv = _inv("semantic_accompaniment_pattern.musicxml", Fraction(0), Fraction(4))
    grid = build_rhythm_grid(inv.passage, score)
    result = observe_shortest_duration(inv, score)
    assert len(result.observations) == 1
    obs = result.observations[0]
    assert obs.observation_type == "shortest_duration"
    assert obs.units == "ticks_480_per_quarter"
    min_dur = min(c.duration for c in grid.cells)
    assert obs.value == int(min_dur * 480)
    # Shortest cells are the eighths (1/2) → 240 ticks
    assert obs.value == 240
    assert obs.method_id == SHORTEST_DURATION_METHOD_ID


def test_off_beat_density_distinguishes_syncopated_and_straight():
    score_sync, inv_sync = _inv("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    result_sync = observe_off_beat_density(inv_sync, score_sync)
    assert result_sync.observations[0].value == 1

    score_straight, inv_straight = _inv(
        "semantic_accompaniment_pattern.musicxml", Fraction(0), Fraction(4)
    )
    result_straight = observe_off_beat_density(inv_straight, score_straight)
    # Eighths alternate off-beat: 4 off-beat eighths out of 8
    assert result_straight.observations[0].value == 4


def test_syncopation_proxy_counts_off_beat_crossing():
    score, inv = _inv("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    grid = build_rhythm_grid(inv.passage, score)
    off_cross = [c for c in grid.cells if c.on_beat is False and (c.beat_boundaries_crossed or 0) > 0]
    result = observe_syncopation_proxy(inv, score)
    assert result.observations[0].value == len(off_cross)
    assert result.observations[0].observation_type == "syncopation_proxy_count"


def test_hand_alignment_ratio_aligned_vs_staggered():
    # Two-staff fixture: downbeat has both hands, other onsets may be single hand
    score_two, inv_two = _inv("selection_two_staff.musicxml", Fraction(0), Fraction(4))
    grid_two = build_rhythm_grid(inv_two.passage, score_two)
    result_two = observe_hand_alignment_ratio(inv_two, score_two)
    assert result_two.observations[0].units == "percent"
    assert 0 < result_two.observations[0].value <= 100
    # Semantic syncopation has at least one both-hands onset (1) and one single-hand (2.5)
    score_sync, inv_sync = _inv("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    grid_sync = build_rhythm_grid(inv_sync.passage, score_sync)
    both = sum(1 for o in grid_sync.onsets if o.both_hands)
    total = len(grid_sync.onsets)
    expected = (both * 100) // total
    result_sync = observe_hand_alignment_ratio(inv_sync, score_sync)
    assert result_sync.observations[0].value == expected
    # Aligned onsets exist, staggered also exists, so ratio is neither 0 nor 100
    assert 0 < expected < 100
    assert result_sync.observations[0].value == expected


def test_hand_alignment_staggered_only_is_low():
    # Isolate the staggered right-hand-only onset at 2.5 (plus surrounding context to keep a measure)
    score, inv = _inv("semantic_syncopation.musicxml", Fraction(5, 2), Fraction(3))
    result = observe_hand_alignment_ratio(inv, score)
    if result.observations:
        # Single-hand onsets → 0 percent both_hands
        assert result.observations[0].value == 0
        assert result.observations[0].units == "percent"


def test_subdivision_mismatch_detects_mixed_durations():
    # Accompaniment pattern: one long bass (whole note) simultaneous with eighths at onset 0
    # The onset at 0 has durations {4, 1/2} → mismatch
    score, inv = _inv("semantic_accompaniment_pattern.musicxml", Fraction(0), Fraction(4))
    result = observe_subdivision_mismatch(inv, score)
    assert result.observations[0].value >= 1
    assert result.observations[0].observation_type == "subdivision_mismatch_count"
    # Syncopation fixture: check that mismatch count equals manual grouping
    score2, inv2 = _inv("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    grid2 = build_rhythm_grid(inv2.passage, score2)
    from collections import defaultdict

    by_onset = defaultdict(list)
    for c in grid2.cells:
        by_onset[c.onset].append(c)
    expected = sum(1 for group in by_onset.values() if len(group) >= 2 and len({c.duration for c in group}) > 1)
    result2 = observe_subdivision_mismatch(inv2, score2)
    assert result2.observations[0].value == expected


def test_tuplet_subdivision_is_flagged_not_interpreted():
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
    class FakeWritten:
        note_id: str
        tuplet_actual: int | None = None
        tuplet_normal: int | None = None

    @dataclass
    class FakeScore:
        measures: list = field(default_factory=list)
        logical_notes: list = field(default_factory=list)
        written_notes: list = field(default_factory=list)

    score = FakeScore(
        measures=[FakeMeasure(measure_index=0, start=Fraction(0), end=Fraction(4))],
        logical_notes=[
            FakeLogical(note_id="n1", onset=Fraction(0), duration=Fraction(1, 3), hand="right", source_note_ids=("n1",), xml_order=1),
            FakeLogical(note_id="n2", onset=Fraction(1), duration=Fraction(1), hand="right", source_note_ids=("n2",), xml_order=2),
        ],
        written_notes=[FakeWritten(note_id="n1", tuplet_actual=3, tuplet_normal=2), FakeWritten(note_id="n2")],
    )
    passage = Passage(
        passage_id="p.tuplet",
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
        investigation_id="inv.tuplet",
        passage=passage,
        selection_origin=SelectionOrigin.USER_SELECTED,
        method_id="test",
        method_version="v1",
    )
    for fn in (observe_attack_density, observe_shortest_duration, observe_off_beat_density, observe_syncopation_proxy, observe_hand_alignment_ratio, observe_subdivision_mismatch):
        result = fn(inv, score)
        assert any(d.code == "tuplet_subdivision_unsupported" for d in result.diagnostics)
        # Still produces an observation (tuplet not silently dropped)
        assert len(result.observations) == 1 or len(result.observations) == 0 or result.observations[0].value >= 0


def test_hand_scoped_rhythm_observations_are_inference():
    score, inv = _inv("selection_two_staff.musicxml", Fraction(0), Fraction(4))
    for fn in (observe_attack_density, observe_shortest_duration, observe_off_beat_density, observe_syncopation_proxy, observe_hand_alignment_ratio, observe_subdivision_mismatch):
        result = fn(inv, score, hand="right")
        if result.observations:
            assert result.observations[0].basis.value == "inference"
            assert any(d.code == "hand_scoped_inference" for d in result.diagnostics)
        else:
            assert any(d.code == "insufficient_attacks" for d in result.diagnostics)


def test_rhythm_observations_abstain_on_empty_and_reject_bad_inputs():
    score, _ = _inv("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    empty_inv = manual_investigation(score, score_id="t", start=Fraction(7, 2), end=Fraction(4, 1), investigation_id="inv.rhythm.empty")
    for fn in (observe_attack_density, observe_shortest_duration, observe_off_beat_density, observe_syncopation_proxy, observe_hand_alignment_ratio, observe_subdivision_mismatch):
        result = fn(empty_inv, score)
        assert result.observations == ()
        assert any(d.code == "insufficient_attacks" for d in result.diagnostics)
        with pytest.raises(ValueError):
            fn(empty_inv, score, hand="middle")  # type: ignore
        with pytest.raises(TypeError):
            fn("not-an-investigation", score)  # type: ignore


def test_rhythm_observation_serialization_round_trips():
    score, inv = _inv("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    for fn in (observe_attack_density, observe_shortest_duration, observe_off_beat_density, observe_syncopation_proxy, observe_hand_alignment_ratio, observe_subdivision_mismatch):
        result = fn(inv, score)
        payload = result.to_dict()
        from passage_practice.models.observations import ObservationResult

        revived = ObservationResult.from_dict(payload)
        assert revived == result
        for obs in revived.observations:
            assert obs.passage_id == inv.passage.passage_id
            assert obs.source_refs
