"""Tests for the S2.7 texture grid view.

Covers homophonic chords, arpeggiation, sustained notes, and two encoded
voices using the S2.3 semantic fixtures plus the selection fixtures.
No observations, detectors, or confidence logic here — only
passage-to-view projection.
"""

from __future__ import annotations

import dataclasses
import json
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.passage import ViewType
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.passages.selection import select_passage
from passage_practice.views.texture_grid import (
    TEXTURE_GRID_SCHEMA_VERSION,
    TextureGrid,
    build_texture_grid,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _grid(name: str, start: Fraction, end: Fraction) -> TextureGrid:
    score = _load(name)
    selected = select_passage(score, score_id=name, start=start, end=end)
    return build_texture_grid(selected.passage, score)


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


# --- homophonic chords ---


def test_paired_attacks_read_as_chords():
    grid = _grid("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    assert [s.onset for s in grid.slices] == [
        Fraction(0),
        Fraction(1),
        Fraction(2),
        Fraction(3),
    ]
    assert [s.chord_size for s in grid.slices] == [2, 2, 2, 2]
    first = grid.slices[0]
    assert [r.id for r in first.attack_refs] == ["n1", "n5"]
    assert first.sustained_refs == ()
    assert first.sustained_under_moving is False
    assert first.voices == ("1", "2")
    assert first.hands == ("right",)
    summary = grid.summary()
    assert summary["total_attacks"] == 8
    assert summary["onset_count"] == 4
    assert summary["max_chord_size"] == 2
    assert summary["chordal_onset_count"] == 4
    assert summary["sustained_under_moving_count"] == 0
    assert summary["voices"] == ["1", "2"]


# --- arpeggiation over sustained bass ---


def test_broken_chord_stays_sequential_with_sustained_bass():
    grid = _grid(
        "semantic_accompaniment_pattern.musicxml", Fraction(0), Fraction(4)
    )
    assert len(grid.slices) == 8
    assert all(s.chord_size == 1 for s in grid.slices[1:])
    opening = grid.slices[0]
    assert [r.id for r in opening.attack_refs] == ["n1", "n9"]
    assert opening.sustained_refs == ()
    assert opening.sustained_under_moving is False
    for sliver in grid.slices[1:]:
        assert [r.id for r in sliver.sustained_refs] == ["n9"]
        assert sliver.sustained_under_moving is True
    summary = grid.summary()
    assert summary["total_attacks"] == 9
    assert summary["onset_count"] == 8
    assert summary["max_chord_size"] == 2
    assert summary["chordal_onset_count"] == 1
    assert summary["sustained_under_moving_count"] == 7
    assert summary["hands"] == ["left", "right"]


# --- sustained inner voice ---


def test_sustained_voice_under_moving_voice():
    grid = _grid("selection_two_voices.musicxml", Fraction(0), Fraction(3))
    assert [s.onset for s in grid.slices] == [
        Fraction(0),
        Fraction(1),
        Fraction(2),
    ]
    opening = grid.slices[0]
    assert [r.id for r in opening.attack_refs] == ["n1", "n4"]
    assert opening.sustained_refs == ()
    assert opening.voices == ("1", "2")
    for sliver in grid.slices[1:]:
        assert [r.id for r in sliver.sustained_refs] == ["n4"]
        assert sliver.sustained_under_moving is True
        assert sliver.voices == ("1", "2")
    assert grid.summary()["sustained_under_moving_count"] == 2


def test_melody_plus_accompaniment_hands():
    grid = _grid("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    opening = grid.slices[0]
    assert opening.chord_size == 2
    assert opening.hands == ("left", "right")
    assert opening.sustained_under_moving is False
    assert [s.sustained_under_moving for s in grid.slices] == [
        False,
        True,
        True,
        True,
    ]
    assert [[r.id for r in s.sustained_refs] for s in grid.slices[1:]] == [
        ["n5"],
        ["n5"],
        ["n5"],
    ]


def test_pre_passage_sustainer_is_out_of_scope():
    grid = _grid("selection_two_staff.musicxml", Fraction(1), Fraction(4))
    # LH C3 (0..4) sounds through every slice here but started before the
    # passage: boundary context, never a sustained ref.
    assert [s.onset for s in grid.slices] == [
        Fraction(1),
        Fraction(2),
        Fraction(3),
    ]
    assert all(s.sustained_refs == () for s in grid.slices)
    assert all(s.sustained_under_moving is False for s in grid.slices)


# --- empty, unresolvable, strict input, immutability ---


def test_rest_gap_selects_empty_grid_with_diagnostic():
    grid = _grid("attack_stream_rests.musicxml", Fraction(1), Fraction(2))
    assert grid.slices == ()
    assert grid.summary() == {
        "total_attacks": 0,
        "onset_count": 0,
        "max_chord_size": 0,
        "chordal_onset_count": 0,
        "sustained_under_moving_count": 0,
        "voices": [],
        "hands": [],
    }
    assert any(d.code == "no_texture_slices" for d in grid.diagnostics)


def test_unresolvable_ref_warns_without_failing():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    ghost = dataclasses.replace(
        selected.passage,
        event_refs=(SourceRef(id="n999", kind=SourceKind.LOGICAL_NOTE),),
    )
    grid = build_texture_grid(ghost, score)
    assert grid.slices == ()
    assert any(d.code == "unresolvable_attack_ref" for d in grid.diagnostics)
    assert any(d.code == "no_texture_slices" for d in grid.diagnostics)


def test_selection_envelope_rejected():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    with pytest.raises(TypeError):
        build_texture_grid(selected, score)  # type: ignore[arg-type]


def test_builder_does_not_mutate_source():
    score = _load("semantic_ambiguity.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    before_score = [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.logical_notes
    ]
    before_passage = selected.passage.to_dict()
    build_texture_grid(selected.passage, score)
    assert [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.logical_notes
    ] == before_score
    assert selected.passage.to_dict() == before_passage
    grid = build_texture_grid(selected.passage, score)
    with pytest.raises(Exception):
        grid.slices = ()


# --- serialization and contract shape ---


def test_serialization_is_deterministic():
    grid = _grid("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    assert grid.view_type == ViewType.TEXTURE_GRID
    assert grid.to_dict()["schema_version"] == TEXTURE_GRID_SCHEMA_VERSION
    assert _dump(grid.to_dict()) == _dump(
        _grid("semantic_ambiguity.musicxml", Fraction(0), Fraction(4)).to_dict()
    )
    revived = TextureGrid.from_dict(json.loads(_dump(grid.to_dict())))
    assert revived == grid
    assert revived.summary() == grid.summary()
    assert all(isinstance(s.onset, Fraction) for s in revived.slices)


def test_bad_version_rejected():
    grid = _grid("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    payload = grid.to_dict()
    payload["schema_version"] = "texture_grid.v99"
    with pytest.raises(ValueError):
        TextureGrid.from_dict(payload)
    slice_payload = grid.to_dict()
    slice_payload["slices"][0]["schema_version"] = "texture_slice.v99"
    with pytest.raises(ValueError):
        TextureGrid.from_dict(slice_payload)


def test_omissions_cover_pitch_directions_layout():
    grid = _grid("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    assert set(("pitch", "directions", "layout")) <= set(grid.omissions)
    assert grid.ordering == "onset,xml_order,note_id"
    assert grid.grouping is None
