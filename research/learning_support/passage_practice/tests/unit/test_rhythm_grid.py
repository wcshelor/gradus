"""Tests for the S2.6 rhythm grid view.

Covers off-beat attacks, ties across beats, mixed subdivisions, and exact
fractions using the S2.3 semantic fixtures plus the selection ties
fixture. Meterless-measure and tuplet edges use tiny in-memory ScoreIR
doubles over real `Passage` objects so fixture provenance rules are
untouched. No observations, detectors, or confidence logic here — only
passage-to-view projection.
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
from passage_practice.views.rhythm_grid import (
    RHYTHM_GRID_SCHEMA_VERSION,
    RhythmGrid,
    build_rhythm_grid,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _grid(name: str, start: Fraction, end: Fraction) -> RhythmGrid:
    score = _load(name)
    selected = select_passage(score, score_id=name, start=start, end=end)
    return build_rhythm_grid(selected.passage, score)


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
    tuplet_actual: int | None = None
    tuplet_normal: int | None = None


@dataclass
class _FakeScore:
    measures: list = field(default_factory=list)
    logical_notes: list = field(default_factory=list)
    written_notes: list = field(default_factory=list)


def _meterless_score() -> _FakeScore:
    return _FakeScore(
        measures=[
            _FakeMeasure(
                measure_index=0,
                start=Fraction(0),
                end=Fraction(4),
                time_beats=None,
                time_beat_type=None,
            )
        ],
        logical_notes=[
            _FakeLogical(
                note_id="n1",
                onset=Fraction(0),
                duration=Fraction(1),
                hand="right",
                source_note_ids=("n1",),
                xml_order=1,
            )
        ],
    )


def _tuplet_score() -> _FakeScore:
    return _FakeScore(
        measures=[
            _FakeMeasure(measure_index=0, start=Fraction(0), end=Fraction(4))
        ],
        logical_notes=[
            _FakeLogical(
                note_id="n1",
                onset=Fraction(0),
                duration=Fraction(1, 3),
                hand="right",
                source_note_ids=("n1",),
                xml_order=1,
            ),
            _FakeLogical(
                note_id="n2",
                onset=Fraction(1),
                duration=Fraction(1),
                hand="right",
                source_note_ids=("n2",),
                xml_order=2,
            ),
        ],
        written_notes=[
            _FakeWritten(note_id="n1", tuplet_actual=3, tuplet_normal=2),
            _FakeWritten(note_id="n2"),
        ],
    )


# --- off-beat attacks ---


def test_off_beat_attack_placement_is_exact():
    grid = _grid("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    assert len(grid.cells) == 8
    by_id = {c.source_ref.id: c for c in grid.cells}
    off = next(c for c in grid.cells if c.onset == Fraction(5, 2))
    assert off.beat_index == 2
    assert off.offset_in_beat == Fraction(1, 2)
    assert off.on_beat is False
    assert off.beats_per_measure == 4 and off.beat_unit == 4
    for cell in grid.cells:
        if cell.onset != Fraction(5, 2):
            assert cell.on_beat is True
            assert cell.offset_in_beat == Fraction(0)
    assert all(
        isinstance(c.onset, Fraction)
        and isinstance(c.duration, Fraction)
        and isinstance(c.offset_in_beat, Fraction)
        and isinstance(c.beats_spanned, Fraction)
        for c in grid.cells
    )


# --- ties across beats ---


def test_sustained_notes_span_beats():
    grid = _grid("selection_ties.musicxml", Fraction(0), Fraction(4))
    by_id = {c.source_ref.id: c for c in grid.cells}
    half = by_id["n3"]
    assert half.beats_spanned == Fraction(2)
    assert half.beat_boundaries_crossed == 1
    quarter = by_id["n1"]
    assert quarter.beats_spanned == Fraction(1)
    assert quarter.beat_boundaries_crossed == 0
    assert quarter.end == Fraction(1)


def test_tie_chain_sounds_through_the_beat_line():
    grid = _grid("selection_ties.musicxml", Fraction(4), Fraction(8))
    tied = grid.cells[0]
    assert tied.source_ref == SourceRef(id="n4", kind=SourceKind.LOGICAL_NOTE)
    assert tied.onset == Fraction(4) and tied.duration == Fraction(2)
    assert tied.beat_index == 0
    assert tied.on_beat is True
    assert tied.beats_spanned == Fraction(2)
    assert tied.beat_boundaries_crossed == 1


def test_note_ending_on_the_beat_claims_no_crossing():
    grid = _grid("attack_stream_rests.musicxml", Fraction(0), Fraction(4))
    first = next(c for c in grid.cells if c.onset == Fraction(0) and c.hand == "right")
    assert first.duration == Fraction(1)
    assert first.beat_boundaries_crossed == 0


# --- mixed subdivisions ---


def test_mixed_subdivisions_share_one_grid():
    grid = _grid(
        "semantic_accompaniment_pattern.musicxml", Fraction(0), Fraction(4)
    )
    assert len(grid.cells) == 9
    eighths = [c for c in grid.cells if c.duration == Fraction(1, 2)]
    assert len(eighths) == 8
    assert {c.offset_in_beat for c in eighths} == {Fraction(0), Fraction(1, 2)}
    assert [c.on_beat for c in eighths] == [
        True,
        False,
        True,
        False,
        True,
        False,
        True,
        False,
    ]
    bass = next(c for c in grid.cells if c.duration == Fraction(4))
    assert bass.beats_spanned == Fraction(4)
    assert bass.beat_boundaries_crossed == 3
    assert bass.on_beat is True


# --- hand alignment ---


def test_per_onset_hands_distinguish_aligned_and_staggered():
    grid = _grid("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    by_onset = {o.onset: o for o in grid.onsets}
    assert [o.onset for o in grid.onsets] == sorted(by_onset)
    aligned = by_onset[Fraction(1)]
    assert aligned.hands == ("left", "right")
    assert aligned.both_hands is True
    assert {r.id for r in aligned.cell_refs} == {
        c.source_ref.id
        for c in grid.cells
        if c.onset == Fraction(1)
    }
    staggered = by_onset[Fraction(5, 2)]
    assert staggered.hands == ("right",)
    assert staggered.both_hands is False


def test_two_staff_downbeat_aligns_both_hands():
    grid = _grid("selection_two_staff.musicxml", Fraction(0), Fraction(4))
    downbeat = grid.onsets[0]
    assert downbeat.onset == Fraction(0)
    assert downbeat.hands == ("left", "right")
    assert downbeat.both_hands is True


# --- meterless measures and tuplets ---


def test_unknown_meter_omits_beats_without_guessing():
    passage = _passage(
        "meterless",
        (SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )
    grid = build_rhythm_grid(passage, _meterless_score())
    (cell,) = grid.cells
    assert cell.beat_index is None
    assert cell.offset_in_beat is None
    assert cell.on_beat is None
    assert cell.beats_spanned is None
    assert cell.beat_boundaries_crossed is None
    assert cell.measure_index == 0
    diagnostic = next(d for d in grid.diagnostics if d.code == "unknown_meter")
    assert [r.id for r in diagnostic.source_refs] == ["n1"]


def test_tuplet_derived_subdivision_is_flagged():
    passage = _passage(
        "tuplet",
        (
            SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id="n2", kind=SourceKind.LOGICAL_NOTE),
        ),
    )
    grid = build_rhythm_grid(passage, _tuplet_score())
    by_id = {c.source_ref.id: c for c in grid.cells}
    assert by_id["n1"].from_tuplet is True
    assert by_id["n2"].from_tuplet is False
    diagnostic = next(
        d for d in grid.diagnostics if d.code == "tuplet_subdivision"
    )
    assert [r.id for r in diagnostic.source_refs] == ["n1"]


# --- empty, unresolvable, immutability ---


def test_rest_gap_selects_empty_grid_with_diagnostic():
    grid = _grid("attack_stream_rests.musicxml", Fraction(1), Fraction(2))
    assert grid.cells == () and grid.onsets == ()
    assert any(d.code == "no_rhythm_cells" for d in grid.diagnostics)


def test_unresolvable_ref_warns_without_failing():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    ghost = dataclasses.replace(
        selected.passage,
        event_refs=(SourceRef(id="n999", kind=SourceKind.LOGICAL_NOTE),),
    )
    grid = build_rhythm_grid(ghost, score)
    assert grid.cells == ()
    assert any(d.code == "unresolvable_attack_ref" for d in grid.diagnostics)
    assert any(d.code == "no_rhythm_cells" for d in grid.diagnostics)


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
    build_rhythm_grid(selected.passage, score)
    assert [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.logical_notes
    ] == before_score
    assert selected.passage.to_dict() == before_passage
    grid = build_rhythm_grid(selected.passage, score)
    with pytest.raises(Exception):
        grid.cells = ()


# --- serialization and contract shape ---


def test_serialization_is_deterministic_with_exact_fractions():
    grid = _grid("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    assert grid.view_type == ViewType.RHYTHM_GRID
    assert grid.to_dict()["schema_version"] == RHYTHM_GRID_SCHEMA_VERSION
    assert _dump(grid.to_dict()) == _dump(
        _grid("semantic_syncopation.musicxml", Fraction(0), Fraction(4)).to_dict()
    )
    revived = RhythmGrid.from_dict(json.loads(_dump(grid.to_dict())))
    assert revived == grid
    assert all(isinstance(c.onset, Fraction) for c in revived.cells)
    assert all(isinstance(o.onset, Fraction) for o in revived.onsets)


def test_bad_version_rejected():
    grid = _grid("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    payload = grid.to_dict()
    payload["schema_version"] = "rhythm_grid.v99"
    with pytest.raises(ValueError):
        RhythmGrid.from_dict(payload)
    cell_payload = grid.to_dict()
    cell_payload["cells"][0]["schema_version"] = "rhythm_cell.v99"
    with pytest.raises(ValueError):
        RhythmGrid.from_dict(cell_payload)


def test_omissions_cover_pitch_directions_layout():
    grid = _grid("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    assert set(("pitch", "directions", "layout")) <= set(grid.omissions)
    assert grid.ordering == "onset,xml_order,note_id"
    assert grid.grouping is None
