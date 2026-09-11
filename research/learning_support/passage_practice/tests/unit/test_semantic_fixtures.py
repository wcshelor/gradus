"""Loader smoke checks for the S2.3 semantic fixture manifest.

Mirrors the T02.2 manifest-validity pattern: the manifest lists every
fixture, every file exists and parses, and counts match the manifest.
Two score-fact-level musical invariants pin the syncopation off-beat and
the ambiguity voice design. No views, observations, contracts, detectors,
confidence, or diagnosis logic here — only loader + ScoreIR field reads.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

SEMANTIC_FIXTURES = (
    "semantic_top_voice_melody.musicxml",
    "semantic_left_hand_melody.musicxml",
    "semantic_accompaniment_pattern.musicxml",
    "selection_two_voices.musicxml",
    "semantic_syncopation.musicxml",
    "semantic_ambiguity.musicxml",
)


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def test_semantic_manifest_lists_all_fixtures():
    manifest = (FIXTURES / "semantic_manifest.md").read_text()
    for name in SEMANTIC_FIXTURES:
        assert name in manifest
        assert (FIXTURES / name).is_file()


def test_loader_smoke_counts():
    top = _load("semantic_top_voice_melody.musicxml")
    assert len(top.measures) == 1
    assert len(top.written_notes) == 5
    assert len(top.logical_notes) == 5
    assert {n.staff for n in top.written_notes} == {1, 2}

    left = _load("semantic_left_hand_melody.musicxml")
    assert len(left.measures) == 1
    assert len(left.written_notes) == 5
    assert len(left.logical_notes) == 5
    left_hand_notes = [n for n in left.logical_notes if n.hand == "left"]
    assert len(left_hand_notes) == 4

    accompaniment = _load("semantic_accompaniment_pattern.musicxml")
    assert len(accompaniment.measures) == 1
    assert len(accompaniment.written_notes) == 9
    assert len(accompaniment.logical_notes) == 9
    right_eighths = [
        n for n in accompaniment.logical_notes
        if n.staff == 1 and n.duration == Fraction(1, 2)
    ]
    assert len(right_eighths) == 8

    voices = _load("selection_two_voices.musicxml")
    assert {n.voice for n in voices.written_notes} == {"1", "2"}

    syncopation = _load("semantic_syncopation.musicxml")
    assert len(syncopation.measures) == 1
    assert len(syncopation.written_notes) == 8

    ambiguity = _load("semantic_ambiguity.musicxml")
    assert len(ambiguity.measures) == 1
    assert len(ambiguity.written_notes) == 8
    assert {n.voice for n in ambiguity.written_notes} == {"1", "2"}


def test_syncopation_has_off_beat_attack():
    syncopation = _load("semantic_syncopation.musicxml")
    onsets = {n.onset for n in syncopation.logical_notes}
    assert Fraction(5, 2) in onsets
    left_onsets = sorted(
        n.onset for n in syncopation.logical_notes if n.hand == "left"
    )
    assert left_onsets == [Fraction(0), Fraction(1), Fraction(2), Fraction(3)]


def test_ambiguity_static_top_vs_moving_lower_voice():
    ambiguity = _load("semantic_ambiguity.musicxml")
    by_voice: dict[str, list[int]] = {}
    for note in ambiguity.written_notes:
        by_voice.setdefault(note.voice, []).append(note.pitch_midi)
    assert len(set(by_voice["1"])) == 1
    assert len(set(by_voice["2"])) == 4
    assert min(by_voice["1"]) > max(by_voice["2"])
