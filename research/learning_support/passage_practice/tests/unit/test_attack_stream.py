"""Tests for the S2.4 attack stream view.

Covers ties, rests, chords, ordering, source immutability, and
serialization using the S2.3 semantic fixtures plus the selection ties
fixture and one rests fixture. No observations, detectors, or confidence
logic here — only passage-to-view projection.
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
from passage_practice.views.attack_stream import (
    ATTACK_STREAM_SCHEMA_VERSION,
    AttackStream,
    build_attack_stream,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _stream(name: str, start: Fraction, end: Fraction) -> AttackStream:
    score = _load(name)
    selected = select_passage(
        score, score_id=name, start=start, end=end
    )
    return build_attack_stream(selected.passage, score)


def _dump(data) -> str:
    return json.dumps(data, sort_keys=True)


def test_tie_collapses_to_single_attack():
    stream = _stream("selection_ties.musicxml", Fraction(4), Fraction(8))
    assert [a.pitch_midi for a in stream.attacks] == [67, 69]
    tied = stream.attacks[0]
    assert tied.onset == Fraction(4)
    assert tied.duration == Fraction(2)
    assert set(tied.source_note_ids) == {"n4", "n5"}
    assert tied.source_ref == SourceRef(id="n4", kind=SourceKind.LOGICAL_NOTE)


def test_rests_are_documented_omissions_not_attacks():
    stream = _stream("attack_stream_rests.musicxml", Fraction(0), Fraction(4))
    assert [a.onset for a in stream.attacks] == [
        Fraction(0),
        Fraction(0),
        Fraction(2),
        Fraction(3),
    ]
    assert len(stream.omitted_rest_refs) == 1
    (rest_ref,) = stream.omitted_rest_refs
    assert rest_ref.kind == SourceKind.REST
    assert any(d.code == "rests_omitted" for d in stream.diagnostics)
    assert "rests" in stream.omissions


def test_rest_gap_selects_empty_stream_with_diagnostic():
    stream = _stream("attack_stream_rests.musicxml", Fraction(1), Fraction(2))
    assert stream.attacks == ()
    assert len(stream.omitted_rest_refs) == 1
    assert any(d.code == "no_attacks" for d in stream.diagnostics)


def test_chords_share_onsets_in_document_order():
    stream = _stream("semantic_ambiguity.musicxml", Fraction(0), Fraction(4))
    assert len(stream.attacks) == 8
    assert [a.onset for a in stream.attacks] == [
        Fraction(0),
        Fraction(0),
        Fraction(1),
        Fraction(1),
        Fraction(2),
        Fraction(2),
        Fraction(3),
        Fraction(3),
    ]
    first_pair = stream.attacks[:2]
    assert [a.voice for a in first_pair] == ["1", "2"]
    assert first_pair[0].pitch_midi > first_pair[1].pitch_midi


def test_ordering_is_deterministic_across_builds():
    first = _stream("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    second = _stream("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    assert [a.onset for a in first.attacks] == [
        Fraction(0),
        Fraction(0),
        Fraction(1),
        Fraction(2),
        Fraction(3),
    ]
    assert first == second
    assert first.attacks is not second.attacks


def test_unresolvable_ref_warns_without_failing():
    score = _load("semantic_top_voice_melody.musicxml")
    selected = select_passage(
        score, score_id="t", start=Fraction(0), end=Fraction(4)
    )
    ghost = dataclasses.replace(
        selected.passage,
        event_refs=(
            SourceRef(id="n999", kind=SourceKind.LOGICAL_NOTE),
        ),
    )
    stream = build_attack_stream(ghost, score)
    assert stream.attacks == ()
    assert any(d.code == "unresolvable_attack_ref" for d in stream.diagnostics)


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
    build_attack_stream(selected.passage, score)
    assert [
        (n.note_id, n.onset, n.duration, n.pitch_midi)
        for n in score.logical_notes
    ] == before_score
    assert selected.passage.to_dict() == before_passage
    stream = build_attack_stream(selected.passage, score)
    with pytest.raises(Exception):
        stream.attacks = ()


def test_serialization_is_deterministic_with_exact_fractions():
    stream = _stream("semantic_syncopation.musicxml", Fraction(0), Fraction(4))
    assert stream.view_type == ViewType.LOGICAL_ATTACK_STREAM
    assert stream.to_dict()["schema_version"] == ATTACK_STREAM_SCHEMA_VERSION
    assert _dump(stream.to_dict()) == _dump(
        _stream("semantic_syncopation.musicxml", Fraction(0), Fraction(4)).to_dict()
    )
    revived = AttackStream.from_dict(json.loads(_dump(stream.to_dict())))
    assert revived == stream
    assert all(isinstance(a.onset, Fraction) for a in revived.attacks)


def test_bad_version_rejected():
    stream = _stream("semantic_top_voice_melody.musicxml", Fraction(0), Fraction(4))
    payload = stream.to_dict()
    payload["schema_version"] = "attack_stream.v99"
    with pytest.raises(ValueError):
        AttackStream.from_dict(payload)
