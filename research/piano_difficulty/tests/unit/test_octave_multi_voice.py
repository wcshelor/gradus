"""Focused unit coverage for octave-doubled melody and single-hand multi-voice texture."""

from __future__ import annotations

from fractions import Fraction

from piano_difficulty.semantic_tokens.models import ScoreEvent, SemanticBundle
from piano_difficulty.semantic_tokens.musical_objects import _detect_octave_doubled_melody, _detect_single_hand_multi_voice, build_musical_objects
from piano_difficulty.semantic_tokens import build_semantic_bundle
from piano_difficulty.normalize.schema import ScoreIR, LogicalNoteIR, MeasureIR
from piano_difficulty.analysis.grouping import group_onsets, group_onsets_by_hand
from piano_difficulty.semantic_tokens.local_inspection import build_local_inspection
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir


def _ev(eid, onset, midi, hand="right", measure=0, dur=Fraction(1, 2), dur_type="quarter"):
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
        duration_type=dur_type,
        key_signature=None,
        time_signature="4/4",
        clef="G",
        tempo_bpm=None,
        dynamics=None,
        articulation=(),
        tuplet=None,
    )


def test_octave_doubled_melody_detects_consecutive_parallel_octaves():
    # 3 consecutive octave pairs moving in parallel ascending 2 semitones
    events = [
        _ev("e1_low", Fraction(0), 60, "right", 0), _ev("e1_high", Fraction(0), 72, "right", 0),
        _ev("e2_low", Fraction(1), 62, "right", 0), _ev("e2_high", Fraction(1), 74, "right", 0),
        _ev("e3_low", Fraction(2), 64, "right", 0), _ev("e3_high", Fraction(2), 76, "right", 0),
    ]
    objs = _detect_octave_doubled_melody(events, [], [])
    assert len(objs) == 1
    o = objs[0]
    assert o.object_id == "octave_doubled_melody"
    assert o.hand == "right"
    # evidence includes both notes of each doubled octave
    assert len(o.evidence_event_ids) == 6
    assert set(o.evidence_event_ids) == {"e1_low", "e1_high", "e2_low", "e2_high", "e3_low", "e3_high"}
    # payload includes octave count, direction, pitch span, exact/mixed
    assert o.payload["octave_count"] == 3
    assert o.payload["direction"] == "ascending"
    assert o.payload["pitch_span_semitones"] == 16  # 60..76
    assert o.payload["is_exact_doubling"] is True
    assert o.payload["doubling_type"] == "exact_octave"
    assert o.confidence >= 0.6
    # ensure component collection works
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(o,), score_id="test")
    from piano_difficulty.semantic_tokens.object_components import build_object_components
    comps = build_object_components(bundle)
    types = {c.component_type for c in comps}
    assert "octave_pair_sequence" in types
    assert "octave_direction" in types
    assert "octave_span" in types
    # local inspection should describe as one structural unit
    insp = build_local_inspection(bundle, report_span=(1, 1), flagged_measures=("1",), source_score="test")
    assert any(u.object_id == "octave_doubled_melody" for u in insp.instruction_units)
    iu = next(u for u in insp.instruction_units if u.object_id == "octave_doubled_melody")
    assert "one structural" in iu.instruction.lower()
    assert "octave-doubled" in iu.instruction.lower()


def test_octave_doubled_melody_mixed_octave_plus_inner():
    # Mixed: octave plus inner tone at each onset
    events = [
        _ev("e1_low", Fraction(0), 60, "right", 0), _ev("e1_mid", Fraction(0), 64, "right", 0), _ev("e1_high", Fraction(0), 72, "right", 0),
        _ev("e2_low", Fraction(1), 62, "right", 0), _ev("e2_mid", Fraction(1), 65, "right", 0), _ev("e2_high", Fraction(1), 74, "right", 0),
        _ev("e3_low", Fraction(2), 64, "right", 0), _ev("e3_mid", Fraction(2), 67, "right", 0), _ev("e3_high", Fraction(2), 76, "right", 0),
    ]
    objs = _detect_octave_doubled_melody(events, [], [])
    assert len(objs) == 1
    o = objs[0]
    assert o.payload["is_exact_doubling"] is False
    assert o.payload["is_mixed"] is True
    assert "mixed_octave_plus_other_tones" in o.caveats
    assert o.payload["doubling_type"] == "mixed_octave_plus_other_tones"
    # evidence includes inner tones as well but still guarantees octave pair
    assert "e1_low" in o.evidence_event_ids and "e1_high" in o.evidence_event_ids

def test_octave_doubled_melody_isolated_octave_not_promoted():
    # Only one isolated octave interval should not produce full melodic object
    events = [
        _ev("e1_low", Fraction(0), 60, "right", 0), _ev("e1_high", Fraction(0), 72, "right", 0),
        _ev("e2_single", Fraction(1), 62, "right", 0),
    ]
    objs = _detect_octave_doubled_melody(events, [], [])
    assert len(objs) == 0, "isolated octave should not produce octave_doubled_melody"


def test_octave_doubling_does_not_inflate_leap_to_chord():
    # Create events where octave doubling exists but should not create leap_to_chord
    # Use ScoreIR to get full pipeline with leap detection suppressed
    score = ScoreIR(title="octave-leap", measures=[MeasureIR(0, "1", Fraction(0), Fraction(4)), MeasureIR(1, "2", Fraction(4), Fraction(8))])
    score.logical_notes.append(LogicalNoteIR("n1_low", 60, Fraction(0), Fraction(1, 2), 1, "1", hand="right", measure_index=0))
    score.logical_notes.append(LogicalNoteIR("n1_high", 72, Fraction(0), Fraction(1, 2), 1, "1", hand="right", measure_index=0))
    score.logical_notes.append(LogicalNoteIR("n2_low", 62, Fraction(1, 2), Fraction(1, 2), 1, "1", hand="right", measure_index=0))
    score.logical_notes.append(LogicalNoteIR("n2_high", 74, Fraction(1, 2), Fraction(1, 2), 1, "1", hand="right", measure_index=0))
    score.logical_notes.append(LogicalNoteIR("n3_low", 64, Fraction(1), Fraction(1, 2), 1, "1", hand="right", measure_index=0))
    score.logical_notes.append(LogicalNoteIR("n3_high", 76, Fraction(1), Fraction(1, 2), 1, "1", hand="right", measure_index=0))
    score.onset_groups = [*group_onsets(score.logical_notes), *group_onsets_by_hand(score.logical_notes)]
    bundle = build_semantic_bundle(score)
    # Should have octave_doubled_melody but not leap_to_chord inflated from octave motion
    oct_objs = [o for o in bundle.musical_objects if o.object_id == "octave_doubled_melody"]
    assert oct_objs
    leap_objs = [o for o in bundle.musical_objects if o.object_id == "leap_to_chord" and o.hand == "right"]
    # If leap exists, it should not overlap octave evidence with 12 semitone movement inflated
    for leap in leap_objs:
        shared = set(leap.evidence_event_ids) & set(oct_objs[0].evidence_event_ids)
        # If sharing >=2, then it would be inflation — should be suppressed
        assert len(shared) < 2 or leap.payload.get("movement") != 12


def test_single_hand_multi_voice_sustained_low_plus_moving_upper():
    # Left hand: sustained low note plus moving upper notes
    # Use 4 onsets: low repeated/sustained, upper 4 distinct pitches gap >=12
    events = [
        _ev("low1", Fraction(0), 36, "left", 0, Fraction(2)),  # sustained
        _ev("up1", Fraction(0), 60, "left", 0, Fraction(1, 2)),
        _ev("up2", Fraction(1, 2), 62, "left", 0, Fraction(1, 2)),
        _ev("up3", Fraction(1), 64, "left", 0, Fraction(1, 2)),
        _ev("up4", Fraction(3, 2), 65, "left", 0, Fraction(1, 2)),
        _ev("up5", Fraction(2), 67, "left", 0, Fraction(1, 2)),
    ]
    objs = _detect_single_hand_multi_voice(events, [], [])
    assert len(objs) >= 1
    o = next(x for x in objs if x.hand == "left")
    assert o.object_id == "single_hand_multi_voice_texture"
    assert "voice_assignment_inferred" in o.caveats
    assert o.payload["pitch_band_gap_semitones"] >= 12
    # Should have components
    bundle = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=(o,), score_id="test")
    from piano_difficulty.semantic_tokens.object_components import build_object_components
    comps = build_object_components(bundle)
    assert any(c.component_type == "voice_band_gap" for c in comps)
    # Local inspection rendering
    insp = build_local_inspection(bundle, report_span=(1, 1), flagged_measures=("1",), source_score="test")
    # Should appear either as instruction unit or supporting local object
    found = any(u.object_id == "single_hand_multi_voice_texture" for u in insp.instruction_units) or any(s.object_id == "single_hand_multi_voice_texture" for s in insp.supporting_local_objects)
    assert found


def test_single_hand_multi_voice_negative_ordinary_block_chords():
    # Ordinary block chords: 3-note chords per onset, same rhythm, should NOT produce multi-voice
    events = [
        _ev("c1_1", Fraction(0), 60, "right", 0), _ev("c1_2", Fraction(0), 64, "right", 0), _ev("c1_3", Fraction(0), 67, "right", 0),
        _ev("c2_1", Fraction(1), 62, "right", 0), _ev("c2_2", Fraction(1), 65, "right", 0), _ev("c2_3", Fraction(1), 69, "right", 0),
        _ev("c3_1", Fraction(2), 64, "right", 0), _ev("c3_2", Fraction(2), 67, "right", 0), _ev("c3_3", Fraction(2), 71, "right", 0),
        _ev("c4_1", Fraction(3), 65, "right", 0), _ev("c4_2", Fraction(3), 69, "right", 0), _ev("c4_3", Fraction(3), 72, "right", 0),
    ]
    objs = _detect_single_hand_multi_voice(events, [], [])
    assert len(objs) == 0, f"ordinary block chords should not produce multi-voice, got {objs}"
    # Also octave detector should not fire
    oct_objs = _detect_octave_doubled_melody(events, [], [])
    assert len(oct_objs) == 0
    # Full pipeline should not produce multi-voice for this chord-only texture
    score = ScoreIR(title="chords", measures=[MeasureIR(0, "1", Fraction(0), Fraction(4)), MeasureIR(1, "2", Fraction(4), Fraction(8))])
    for idx, (on, m1, m2, m3) in enumerate([(0,60,64,67),(1,62,65,69),(2,64,67,71),(3,65,69,72)]):
        score.logical_notes.append(LogicalNoteIR(f"n{idx}_1", m1, Fraction(on), Fraction(1), 1, "1", hand="right", measure_index=0))
        score.logical_notes.append(LogicalNoteIR(f"n{idx}_2", m2, Fraction(on), Fraction(1), 1, "1", hand="right", measure_index=0))
        score.logical_notes.append(LogicalNoteIR(f"n{idx}_3", m3, Fraction(on), Fraction(1), 1, "1", hand="right", measure_index=0))
    score.onset_groups = [*group_onsets(score.logical_notes), *group_onsets_by_hand(score.logical_notes)]
    bundle = build_semantic_bundle(score)
    assert not any(o.object_id == "single_hand_multi_voice_texture" for o in bundle.musical_objects)
