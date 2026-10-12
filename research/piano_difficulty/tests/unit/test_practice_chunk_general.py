"""Focused tests for general PracticeChunk machinery (not passage hacks)."""

from __future__ import annotations

from fractions import Fraction

import pytest

from piano_difficulty.semantic_tokens.models import ScoreEvent, SemanticBundle
from piano_difficulty.semantic_tokens.practice_chunks import build_practice_chunks
from piano_difficulty.semantic_tokens.notation_markings import marking_support_status


def _ev(eid, onset, midi, hand="right", measure=0, dur=Fraction(1), dynamics=None, arpeggiated=False, slur_start=False, slur_stop=False):
    return ScoreEvent(
        event_id=eid,
        score_id="test",
        measure_index=measure,
        measure_number=str(measure + 1),
        staff=1 if hand == "right" else 2,
        voice="1",
        hand=hand,
        hand_confidence="high",
        beat=Fraction(0),
        offset_quarter=float(onset),
        duration_quarter=float(dur),
        onset=onset,
        end=onset + dur,
        duration=dur,
        is_rest=False,
        is_chord_tone=False,
        chord_id=None,
        pitch_midi=midi,
        pitch_name=None,
        pitch_class=midi % 12,
        octave=midi // 12,
        accidental=None,
        alter=None,
        tie_merged=False,
        source_note_ids=(eid,),
        xml_order=0,
        measure_staff_order=0,
        is_grace=False,
        duration_type="quarter",
        key_signature=None,
        time_signature="4/4",
        clef="G",
        tempo_bpm=None,
        dynamics=dynamics,
        articulation=(),
        tuplet=None,
        is_arpeggiated=arpeggiated,
        has_slur_start=slur_start,
        has_slur_stop=slur_stop,
    )


def test_non_empty_simple_passage_yields_fallback():
    events = [
        _ev("e1", Fraction(0), 60, "right", 0, Fraction(1)),
        _ev("e2", Fraction(1), 62, "right", 0, Fraction(1)),
        _ev("e3", Fraction(2), 64, "right", 0, Fraction(1)),
    ]
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    assert len(chunks) >= 1, "non-empty passage should yield at least one fallback chunk"
    # should be passage or hand_stream with fallback caveat
    assert any("fallback" in c.traits or "fallback_chunk" in c.caveats for c in chunks)


def test_ordinary_chordal_passage_yields_chordal_chunk():
    events = [
        _ev("c1_1", Fraction(0), 60, "right", 0), _ev("c1_2", Fraction(0), 64, "right", 0), _ev("c1_3", Fraction(0), 67, "right", 0),
        _ev("c2_1", Fraction(1), 62, "right", 0), _ev("c2_2", Fraction(1), 65, "right", 0), _ev("c2_3", Fraction(1), 69, "right", 0),
        _ev("c3_1", Fraction(2), 64, "right", 0), _ev("c3_2", Fraction(2), 67, "right", 0), _ev("c3_3", Fraction(2), 71, "right", 0),
        _ev("c4_1", Fraction(3), 65, "right", 0), _ev("c4_2", Fraction(3), 69, "right", 0), _ev("c4_3", Fraction(3), 72, "right", 0),
    ]
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    assert any(c.kind == "chordal_texture" for c in chunks), f"expected chordal_texture, got {[c.kind for c in chunks]}"
    parent = next(c for c in chunks if c.kind == "chordal_texture")
    assert "chord_sequence" in parent.traits
    assert len(parent.child_chunk_ids) >= 3


def test_rolled_chord_marking_produces_trait():
    events = [
        _ev("c1_1", Fraction(0), 60, "right", 0, arpeggiated=True), _ev("c1_2", Fraction(0), 64, "right", 0, arpeggiated=True),
        _ev("c2_1", Fraction(1), 62, "right", 0, arpeggiated=True), _ev("c2_2", Fraction(1), 65, "right", 0, arpeggiated=True),
        _ev("c3_1", Fraction(2), 64, "right", 0, arpeggiated=True), _ev("c3_2", Fraction(2), 67, "right", 0, arpeggiated=True),
    ]
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    # chordal or passage should have rolled_chord
    assert any("rolled_chord" in c.traits for c in chunks), f"expected rolled_chord trait, traits={[c.traits for c in chunks]}"
    assert any("roll_evenly" in c.practice_affordances or "block_then_roll" in c.practice_affordances for c in chunks)


def test_decrescendo_trait_attached():
    events = [
        _ev("e1", Fraction(0), 60, "right", 0, dynamics="f"),
        _ev("e2", Fraction(1), 62, "right", 0, dynamics="mf"),
        _ev("e3", Fraction(2), 64, "right", 0, dynamics="p"),
        _ev("e4", Fraction(3), 65, "right", 0, dynamics="pp"),
    ]
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    assert len(chunks) >= 1
    # any chunk covering span should have decrescendo/dynamic_shape
    has_dec = any("decrescendo" in c.traits or "dynamic_shape" in c.traits for c in chunks)
    assert has_dec, f"expected decrescendo/dynamic_shape, got {[c.traits for c in chunks]} payloads={[c.payload for c in chunks]}"


def test_dynamic_marking_captured_in_payload():
    events = [
        _ev("e1", Fraction(0), 60, "right", 0, dynamics="mf"),
        _ev("e2", Fraction(1), 62, "right", 0, dynamics="mf"),
    ]
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    assert any("has_dynamics" in c.traits for c in chunks)
    # payload dynamics
    assert any(c.payload.get("dynamics") for c in chunks)


def test_octave_shift_supported_or_documented():
    status = marking_support_status()
    assert "octave_shift_span" in status or "octave_shift_start" in status
    # If not supported, doc should mention caveat; we test that status dict mentions sounding_vs_written
    txt = " ".join(status.values()).lower()
    assert "sounding" in txt or "octave" in txt


def test_phrase_mark_as_boundary_prior():
    events = [
        _ev("e1", Fraction(0), 60, "left", 0, slur_start=True),
        _ev("e2", Fraction(1, 2), 62, "left", 0),
        _ev("e3", Fraction(1), 64, "left", 0),
        _ev("e4", Fraction(3, 2), 65, "left", 0, slur_stop=True),
        _ev("e5", Fraction(2), 67, "left", 0),
    ]
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    # any chunk should have phrase payload
    assert any(c.payload.get("phrase_boundary_prior") or "slur" in c.traits for c in chunks)


def test_arpeggiating_figure_parent_plus_cells():
    # LH figure with repeated ascending cells separated by large drop
    # Build reps: 60,64,67,71 then drop to 50, then 53,57,60,64
    events = []
    onsets = [Fraction(i,2) for i in range(8)]
    mids = [60,64,67,71, 50,53,57,60]
    # add duplicate low for drop detection (need at least 6 reps)
    # Actually we need 8 onsets as above
    for idx, (on, midi) in enumerate(zip(onsets, mids)):
        events.append(_ev(f"e{idx}", on, midi, "left", 0, Fraction(1,2)))
    # Add extra to make second cell more than 3
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    # Look for parent with segmented cells (either run/cell or arpeggio_sweep/ascent)
    parents = [c for c in chunks if c.kind in ("run","arpeggio_sweep") and len(c.child_chunk_ids) >= 2]
    assert parents, f"expected parent with segmented children, got {[c.kind+':'+str(len(c.child_chunk_ids)) for c in chunks]}"
    parent = parents[0]
    children = [c for c in chunks if c.parent_chunk_id == parent.chunk_id]
    assert len(children) >= 2
    # children can be cell or ascent/descent/turn; ensure they explain boundary
    assert all("boundary_reason" in c.payload or c.kind in ("cell","ascent","descent","turn") for c in children)


def test_mm25_26_style_passage_produces_at_least_one():
    # Simulate mm25-26 style: repeated chordal simultaneities with decrescendo and rolled marks
    events = []
    for i in range(4):
        onset = Fraction(i)
        base = 60 + i
        for midi_offset in (0,4,7):
            events.append(_ev(f"e{i}_{midi_offset}", onset, base+midi_offset, "right" if i%2==0 else "left", 0, Fraction(1), dynamics="f" if i<2 else "p", arpeggiated=(i>0)))
        # ensure both hands overlap at some onsets? add both-hand chord
        if i == 1:
            events.append(_ev(f"e{i}_extra", onset, 48, "left", 0, Fraction(1)))
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    assert len(chunks) >= 1
    assert any(c.kind in ("chordal_texture","passage","hand_stream","phrase") for c in chunks)


def test_mm27_28_style_has_parent_plus_cells():
    events = []
    # emulate LH arpeggiating figure: 10 onsets ascending stepwise 2-4 then large drop
    mids = [48,50,53,57,60, 36,38,41,45,48]
    for idx, midi in enumerate(mids):
        events.append(_ev(f"e{idx}", Fraction(idx,2), midi, "left", 0, Fraction(1,2)))
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(), score_id="test")
    chunks = build_practice_chunks(bundle)
    # Should have at least parent LH figure plus smaller cells
    parents = [c for c in chunks if c.hand == "left" and len(c.child_chunk_ids) >= 1]
    assert parents, f"expected left parent, got {[ (c.hand,c.kind,len(c.child_chunk_ids)) for c in chunks]}"
    # find segmented parent (run or arpeggio_sweep)
    cell_parents = [c for c in chunks if c.kind in ("run","arpeggio_sweep") and len(c.child_chunk_ids) >= 2]
    assert cell_parents, f"expected segmented run/sweep, got {[(c.kind,len(c.child_chunk_ids)) for c in chunks]}"

