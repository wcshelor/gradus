"""Tests for S4.7 semantic-to-strategy compatibility table."""

from __future__ import annotations

import pytest

from passage_practice.pedagogy.compatibility import (
    COMPATIBILITY_TABLE,
    get_compatible_objectives,
    get_compatible_strategies,
    is_strategy_compatible,
)
from passage_practice.pedagogy.compatibility import (
    CADENCE_FOCUS_HYPOTHESIS_TYPE,
    HARMONIC_SKELETON_HYPOTHESIS_TYPE,
    PHRASE_SHAPE_HYPOTHESIS_TYPE,
    SEQUENCE_CHUNKING_HYPOTHESIS_TYPE,
)
from passage_practice.pedagogy.melody_projection import MELODY_PROJECTION_HYPOTHESIS_TYPE
from passage_practice.pedagogy.bass_leap import BASS_LEAP_HYPOTHESIS_TYPE
from passage_practice.pedagogy.rhythmic_coordination import RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE
from passage_practice.pedagogy.reading_load import READING_LOAD_HYPOTHESIS_TYPE


def test_compatible_strategies_present():
    assert "strategy.melody_accent" in get_compatible_strategies(MELODY_PROJECTION_HYPOTHESIS_TYPE)
    assert "strategy.blocked_bass" in get_compatible_strategies(BASS_LEAP_HYPOTHESIS_TYPE)
    assert "strategy.hands_separate_then_together" in get_compatible_strategies(RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE)
    assert "strategy.blocked_harmony" in get_compatible_strategies(READING_LOAD_HYPOTHESIS_TYPE)
    assert "strategy.blocked_harmony" in get_compatible_strategies(HARMONIC_SKELETON_HYPOTHESIS_TYPE)
    assert "strategy.cadence_preparation" in get_compatible_strategies(CADENCE_FOCUS_HYPOTHESIS_TYPE)
    assert "strategy.phrase_shaping" in get_compatible_strategies(PHRASE_SHAPE_HYPOTHESIS_TYPE)
    assert "strategy.sequence_practice" in get_compatible_strategies(SEQUENCE_CHUNKING_HYPOTHESIS_TYPE)


def test_compatible_objectives_present():
    assert "objective.project_melody" in get_compatible_objectives(MELODY_PROJECTION_HYPOTHESIS_TYPE)
    assert "objective.landing_target" in get_compatible_objectives(BASS_LEAP_HYPOTHESIS_TYPE)
    assert "objective.hand_coordination" in get_compatible_objectives(RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE)
    assert "objective.reading_chunking" in get_compatible_objectives(READING_LOAD_HYPOTHESIS_TYPE)
    assert "objective.harmonic_skeleton" in get_compatible_objectives(HARMONIC_SKELETON_HYPOTHESIS_TYPE)
    assert "objective.cadence_preparation" in get_compatible_objectives(CADENCE_FOCUS_HYPOTHESIS_TYPE)
    assert "objective.phrase_shaping" in get_compatible_objectives(PHRASE_SHAPE_HYPOTHESIS_TYPE)
    assert "objective.sequence_chunking" in get_compatible_objectives(SEQUENCE_CHUNKING_HYPOTHESIS_TYPE)


def test_incompatible_strategies_absent():
    # Melody projection should not be compatible with bass strategies
    assert not is_strategy_compatible(MELODY_PROJECTION_HYPOTHESIS_TYPE, "strategy.blocked_bass")
    assert not is_strategy_compatible(BASS_LEAP_HYPOTHESIS_TYPE, "strategy.melody_accent")
    assert not is_strategy_compatible(RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE, "strategy.blocked_harmony")
    assert not is_strategy_compatible(READING_LOAD_HYPOTHESIS_TYPE, "strategy.hands_separate_then_together")


def test_unknown_hypothesis_returns_empty():
    assert get_compatible_strategies("pedagogy.unknown") == ()
    assert get_compatible_objectives("pedagogy.unknown") == ()


def test_no_action_for_unsupported_harmony():
    from passage_practice.pedagogy.compatibility import get_strategies_for_harmony_view
    from passage_practice.views.harmony_view import HarmonyView
    from passage_practice.models.passage import ViewType
    from passage_practice.models.diagnostics import Diagnostic, Severity

    # Unsupported harmony view with insufficient evidence
    view = HarmonyView(
        view_type=ViewType.HARMONY_VIEW,
        source_passage_id="test.unsupported",
        method_id="harmony_view",
        method_version="v1",
        pitch_class_counts=tuple(0 for _ in range(12)),
        pitch_class_duration_ticks=tuple(0 for _ in range(12)),
        diagnostics=(Diagnostic(code="insufficient_harmony_evidence", severity=Severity.INFO, message="empty"),),
    )
    assert get_strategies_for_harmony_view(view) == ()
    # Supported view should return strategies
    from fractions import Fraction
    from passage_practice.models.passage import Passage, PassagePurpose
    from passage_practice.models.time import ScorePosition
    from passage_practice.models.source import SourceKind, SourceRef
    from passage_practice.views.harmony_view import build_harmony_view

    def _pos(q):
        return ScorePosition(quarters=q, measure_index=0, measure_number="1", offset_in_measure=q)

    class Note:
        def __init__(self, nid, midi, onset, dur):
            self.note_id = nid
            self.pitch_midi = midi
            self.onset = onset
            self.duration = dur
            self.xml_order = 0

    notes = [Note(f"n{i}", 60 + (i % 7)*2, Fraction(i), Fraction(1)) for i in range(4)]
    refs = tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in notes)
    passage = Passage(
        passage_id="test.supported",
        score_id="test.supported",
        start=_pos(Fraction(0)),
        end=_pos(Fraction(4)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=refs,
    )
    class Score:
        logical_notes = notes
        measures = []
        written_notes = []
        directions = []
    view2 = build_harmony_view(passage, Score())
    # May still be insufficient if only 4 notes, but check that supported case with diatonic notes returns strategies
    # Use a clear C major passage
    notes_c = [Note(f"n{i}", midi, Fraction(i), Fraction(1)) for i, midi in enumerate([60, 62, 64, 65, 67, 69, 71, 72])]
    refs_c = tuple(SourceRef(id=n.note_id, kind=SourceKind.LOGICAL_NOTE) for n in notes_c)
    passage_c = Passage(
        passage_id="test.c",
        score_id="test.c",
        start=_pos(Fraction(0)),
        end=_pos(Fraction(8)),
        purpose=PassagePurpose.EVIDENCE,
        method_id="test",
        method_version="v1",
        event_refs=refs_c,
    )
    class ScoreC:
        logical_notes = notes_c
        measures = []
        written_notes = []
        directions = []
    view_c = build_harmony_view(passage_c, ScoreC())
    assert get_strategies_for_harmony_view(view_c) == ("strategy.blocked_harmony", "strategy.harmonic_skeleton")


def test_table_is_deterministic_and_complete():
    assert set(COMPATIBILITY_TABLE.keys()) == {
        MELODY_PROJECTION_HYPOTHESIS_TYPE,
        BASS_LEAP_HYPOTHESIS_TYPE,
        RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE,
        READING_LOAD_HYPOTHESIS_TYPE,
        HARMONIC_SKELETON_HYPOTHESIS_TYPE,
        CADENCE_FOCUS_HYPOTHESIS_TYPE,
        PHRASE_SHAPE_HYPOTHESIS_TYPE,
        SEQUENCE_CHUNKING_HYPOTHESIS_TYPE,
    }
    for hyp_type, entry in COMPATIBILITY_TABLE.items():
        assert entry["objectives"]
        assert entry["strategies"]
        # No transformation invocation — table is pure data
        for strat in entry["strategies"]:
            assert strat.startswith("strategy.")
