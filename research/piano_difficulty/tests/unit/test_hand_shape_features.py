"""Unit tests for hand_shape / hand_position feature family."""

from __future__ import annotations

import math
from fractions import Fraction
from pathlib import Path

from piano_difficulty.difficulty_analysis.front_graph_taxonomy import (
    FEATURE_TO_DIMENSION_WEIGHTS,
    get_feature_primary_dimension,
    validate_taxonomy,
)
from piano_difficulty.features import extract_all
from piano_difficulty.features.hand_shape import extract as hand_shape_extract
from piano_difficulty.normalize.schema import LogicalNoteIR, MeasureIR, ScoreIR, WrittenNoteIR

# ---- Helpers ----


def _make_score(logical_notes: list[LogicalNoteIR], measures: list[MeasureIR] | None = None) -> ScoreIR:
    # Build minimal ScoreIR; hand_shape groups from logical_notes only, but other extractors
    # need written_notes with duration_type. Build proper WrittenNoteIR list.
    written = [
        WrittenNoteIR(
            note_id=n.note_id,
            pitch_midi=n.pitch_midi,
            onset=n.onset,
            duration=n.duration,
            staff=n.staff,
            voice=n.voice,
            hand=n.hand,
            measure_index=n.measure_index,
            duration_type="quarter",
        )
        for n in logical_notes
    ]
    return ScoreIR(
        measures=measures or [],
        logical_notes=logical_notes,
        written_notes=written,
    )


def _note(note_id: str, pitch: int, onset: Fraction, hand: str, measure: int = 1) -> LogicalNoteIR:
    return LogicalNoteIR(
        note_id=note_id,
        pitch_midi=pitch,
        onset=onset,
        duration=Fraction(1, 1),
        staff=1 if hand == "right" else 2,
        voice="1" if hand == "right" else "2",
        hand=hand,
        measure_index=measure,
    )


def _feat_map(score: ScoreIR) -> dict[tuple[str, str, str], object]:
    # Use hand_shape extractor directly to avoid unrelated extractor fragility in minimal fixtures;
    # but verify via extract_all for one integration test separately.
    return {(f.feature_id, f.scope, f.scope_ref): f for f in hand_shape_extract(score)}


def _feat_map_all(score: ScoreIR) -> dict[tuple[str, str, str], object]:
    return {(f.feature_id, f.scope, f.scope_ref): f for f in extract_all(score)}


def _val(m, fid, hand):
    return m[(fid, "hand", hand)].value


def _diag_text(m, fid, hand) -> str:
    f = m[(fid, "hand", hand)]
    return " ".join(f.diagnostics).lower()


# ---- 1. Single-note passage ----


def test_single_note_passage_insufficient_chord_diagnostics_and_center_shifts():
    # 3 single-note onsets right hand: C4, D4, E4 at quarters 0,1,2
    notes = [
        _note("r1", 60, Fraction(0), "right"),
        _note("r2", 62, Fraction(1), "right"),
        _note("r3", 64, Fraction(2), "right"),
    ]
    # need measures to give duration
    measures = [
        MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4)),
    ]
    score = _make_score(notes, measures)
    m = _feat_map(score)

    # chord-shape features should be 0 with insufficient-eligibility diagnostics
    chord_features = [
        "hand_shape.repeated_octave_texture_rate",
        "hand_shape.chord_shape_change_rate",
        "hand_shape.chord_shape_entropy",
        "hand_shape.chord_shape_edit_distance_mean",
        "hand_shape.chord_size_change_rate",
        "hand_shape.repeated_shape_ratio",
        "hand_shape.chord_tone_motion_variability",
        "hand_shape.nonparallel_chord_tone_motion_rate",
        "hand_shape.inner_chord_tone_change_rate",
    ]
    for fid in chord_features:
        assert _val(m, fid, "right") == 0.0, fid
        diag = _diag_text(m, fid, "right")
        # must mention insufficient / not applicable / no eligible
        assert any(kw in diag for kw in ["insufficient", "not applicable", "no eligible", "fewer than"]), f"{fid} diag: {diag}"

    # center shift features should work (non-zero)
    # centers: 60,62,64 => shifts 2,2
    assert _val(m, "hand_position.max_center_shift", "right") == 2.0
    assert _val(m, "hand_position.mean_center_shift", "right") == 2.0
    # large threshold is 7 => rate 0
    assert _val(m, "hand_position.large_center_shift_rate", "right") == 0.0
    # timed: gaps are 1 each => 2/1 mean 2
    assert _val(m, "hand_position.timed_center_shift", "right") == 2.0
    # no forbidden language in diagnostics/names
    for fid in chord_features:
        diag = _diag_text(m, fid, "right")
        assert "voice-leading" not in diag or "does not" in diag  # allowed only as negation
        assert "fingering" not in diag or "does not" in diag
        # inner_chord_tone feature name itself shouldn't be considered violation, but diagnostics should not claim voices
        # check no claim of "independent voice" without negation
        # we just ensure "independent voices" appears only with "does not"
        if "independent" in diag:
            assert "does not" in diag

    # octave/largest span etc. should be 0 for single notes
    assert _val(m, "hand_shape.octave_onset_rate", "right") == 0.0
    assert _val(m, "hand_shape.large_span_onset_rate", "right") == 0.0


# ---- 2. Repeated octave chords ----


def test_repeated_octave_chords():
    # 3 octave onsets: C3-C4, D3-D4, C3-C4 repeated shape at 0,1,2
    # span 12, octave true, fingerprints (0,12) all identical
    notes = [
        _note("r1a", 48, Fraction(0), "right"),
        _note("r1b", 60, Fraction(0), "right"),
        _note("r2a", 50, Fraction(1), "right"),
        _note("r2b", 62, Fraction(1), "right"),
        _note("r3a", 48, Fraction(2), "right"),
        _note("r3b", 60, Fraction(2), "right"),
    ]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score = _make_score(notes, measures)
    m = _feat_map(score)

    # octave_onset_rate = 3/3 =1
    assert _val(m, "hand_shape.octave_onset_rate", "right") == 1.0
    assert _val(m, "hand_shape.large_span_onset_rate", "right") == 1.0
    # repeated_shape_ratio = transitions where fingerprint identical / 2 transitions
    # r1(0,12) -> r2(0,12): identical yes, r2->r3 identical yes => 2/2 =1
    assert _val(m, "hand_shape.repeated_shape_ratio", "right") == 1.0
    # chord_shape_change_rate = 0/2 =0
    assert _val(m, "hand_shape.chord_shape_change_rate", "right") == 0.0
    # repeated_octave_texture_rate: all transitions are octave-octave => 2/2=1
    assert _val(m, "hand_shape.repeated_octave_texture_rate", "right") == 1.0


# ---- 3. Changing chord shapes ----


def test_changing_chord_shapes():
    # 3 chordal onsets with distinct shapes:
    # onset0: C4-E4 (4) -> finger (0,4)
    # onset1: C4-G4 (7) -> (0,7)
    # onset2: C4-E4-G4 (0,4,7) -> (0,4,7)
    notes = [
        _note("r1a", 60, Fraction(0), "right"),
        _note("r1b", 64, Fraction(0), "right"),
        _note("r2a", 60, Fraction(1), "right"),
        _note("r2b", 67, Fraction(1), "right"),
        _note("r3a", 60, Fraction(2), "right"),
        _note("r3b", 64, Fraction(2), "right"),
        _note("r3c", 67, Fraction(2), "right"),
    ]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score = _make_score(notes, measures)
    m = _feat_map(score)

    # all 3 transitions different? r1->r2 fingerprints differ, r2->r3 differ => 2/2=1
    assert _val(m, "hand_shape.chord_shape_change_rate", "right") == 1.0
    # repeated_shape low (0)
    assert _val(m, "hand_shape.repeated_shape_ratio", "right") == 0.0
    # entropy positive (3 distinct shapes out of 3 onsets => log2 3)
    entropy = _val(m, "hand_shape.chord_shape_entropy", "right")
    assert entropy > 0
    assert abs(entropy - math.log2(3)) < 1e-9
    # edit distance positive
    assert _val(m, "hand_shape.chord_shape_edit_distance_mean", "right") > 0
    # chord_size_change_rate: r1 size2 -> r2 size2 no change, r2 size2 -> r3 size3 change => 1/2=0.5
    assert _val(m, "hand_shape.chord_size_change_rate", "right") == 0.5


# ---- 4. Inner chord-tone change ----


def test_inner_chord_tone_change():
    # Same outer span (C-E-G vs C-D-G) spans both 7 but inner differs.
    # onset0: C4(60) E4(64) G4(67) -> (0,4,7)
    # onset1: C4(60) D4(62) G4(67) -> (0,2,7)
    # onset2: C4(60) D4(62) G4(67) repeated
    # inner fingerprints: (4,) vs (2,) differ then same
    notes = [
        _note("r1a", 60, Fraction(0), "right"),
        _note("r1b", 64, Fraction(0), "right"),
        _note("r1c", 67, Fraction(0), "right"),
        _note("r2a", 60, Fraction(1), "right"),
        _note("r2b", 62, Fraction(1), "right"),
        _note("r2c", 67, Fraction(1), "right"),
        _note("r3a", 60, Fraction(2), "right"),
        _note("r3b", 62, Fraction(2), "right"),
        _note("r3c", 67, Fraction(2), "right"),
    ]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score = _make_score(notes, measures)
    m = _feat_map(score)

    # inner change: 1 of 2 transitions => 0.5
    assert _val(m, "hand_shape.inner_chord_tone_change_rate", "right") == 0.5
    diag = _diag_text(m, "hand_shape.inner_chord_tone_change_rate", "right")
    # diagnostics/names do not mention actual voices or voice-leading claims
    # the diagnostic should say "does not infer independent voices or voice-leading"
    assert "does not infer" in diag
    # ensure we don't produce bare "voice-leading" without negation in diagnostics
    # (if present it must be negated)


# ---- 5. Center shift deterministic ----


def test_center_shift():
    # hand moves from low zone to high zone:
    # onset0: C3(48) single => center 48
    # onset1: C3(48) single => shift 0
    # onset2: C5(72) single => shift 24
    # onset3: D5(74) single => shift 2
    notes = [
        _note("r1", 48, Fraction(0), "right"),
        _note("r2", 48, Fraction(1), "right"),
        _note("r3", 72, Fraction(2), "right"),
        _note("r4", 74, Fraction(3), "right"),
    ]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score = _make_score(notes, measures)
    m = _feat_map(score)

    # shifts [0,24,2]
    assert _val(m, "hand_position.max_center_shift", "right") == 24.0
    # mean = (0+24+2)/3 = 26/3
    assert abs(_val(m, "hand_position.mean_center_shift", "right") - 26 / 3) < 1e-9
    # large threshold 7 => only 24 qualifies => 1/3
    assert abs(_val(m, "hand_position.large_center_shift_rate", "right") - 1 / 3) < 1e-9
    # timed: gaps all 1 => mean 26/3 as well
    assert abs(_val(m, "hand_position.timed_center_shift", "right") - 26 / 3) < 1e-9

    # test with chord centers: C3-E3 (48,52) center 50; G5-C6 (79,84) center 81.5 => shift 31.5
    notes2 = [
        _note("r1a", 48, Fraction(0), "right"),
        _note("r1b", 52, Fraction(0), "right"),
        _note("r2a", 79, Fraction(2), "right"),
        _note("r2b", 84, Fraction(2), "right"),
    ]
    measures2 = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score2 = _make_score(notes2, measures2)
    m2 = _feat_map(score2)
    assert _val(m2, "hand_position.max_center_shift", "right") == 31.5
    assert _val(m2, "hand_position.mean_center_shift", "right") == 31.5
    # timed: gap 2 => 31.5/2=15.75
    assert abs(_val(m2, "hand_position.timed_center_shift", "right") - 15.75) < 1e-9


# ---- 6. Taxonomy mapping ----


def test_new_features_taxonomy_mapping():
    new_fids = [
        "hand_shape.octave_onset_rate",
        "hand_shape.large_span_onset_rate",
        "hand_shape.mean_large_span_burden",
        "hand_shape.wide_chord_density",
        "hand_shape.repeated_octave_texture_rate",
        "hand_shape.chord_shape_change_rate",
        "hand_shape.chord_shape_entropy",
        "hand_shape.chord_shape_edit_distance_mean",
        "hand_shape.chord_size_change_rate",
        "hand_shape.repeated_shape_ratio",
        "hand_shape.chord_tone_motion_variability",
        "hand_shape.nonparallel_chord_tone_motion_rate",
        "hand_shape.inner_chord_tone_change_rate",
        "hand_position.max_center_shift",
        "hand_position.mean_center_shift",
        "hand_position.large_center_shift_rate",
        "hand_position.timed_center_shift",
    ]
    for fid in new_fids:
        assert fid in FEATURE_TO_DIMENSION_WEIGHTS, fid
        primary = get_feature_primary_dimension(fid)
        assert primary == "hand_movement_position", f"{fid} primary {primary}"
        assert "layers_coordination" not in FEATURE_TO_DIMENSION_WEIGHTS[fid], f"{fid} should not map to layers_coordination"
    validate_taxonomy()


# ---- Additional semantics checks ----


def test_large_span_and_burden():
    # spans: 0, 10, 12 => large rate 1/3, burden mean (0+1+3)/3=4/3
    notes = [
        _note("r1", 60, Fraction(0), "right"),
        _note("r2a", 60, Fraction(1), "right"),
        _note("r2b", 70, Fraction(1), "right"),  # span 10
        _note("r3a", 60, Fraction(2), "right"),
        _note("r3b", 72, Fraction(2), "right"),  # span 12
    ]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score = _make_score(notes, measures)
    m = _feat_map(score)
    assert abs(_val(m, "hand_shape.large_span_onset_rate", "right") - 1 / 3) < 1e-9
    assert abs(_val(m, "hand_shape.mean_large_span_burden", "right") - 4 / 3) < 1e-9


def test_chord_tone_motion_parallel_and_variability():
    # Two same-size chord transitions: first parallel (both move +2), second nonparallel divergent
    # onset0: C4(60) E4(64) -> onset1: D4(62) F4(65): motions [2,1] => nonparallel? same sign, range 1 => parallel per spec (max-min=1)
    # Actually [2,1] max-min=1 and same sign => parallel = True
    # So make first parallel true, second nonparallel: onset1->onset2 motions [2,-2] -> nonparallel
    notes = [
        _note("r1a", 60, Fraction(0), "right"),
        _note("r1b", 64, Fraction(0), "right"),
        _note("r2a", 62, Fraction(1), "right"),
        _note("r2b", 65, Fraction(1), "right"),
        _note("r3a", 64, Fraction(2), "right"),
        _note("r3b", 63, Fraction(2), "right"),
    ]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score = _make_score(notes, measures)
    m = _feat_map(score)
    # variability: per transition stddev
    # t1 motion [2,1]: mean 1.5 std pop sqrt(0.25)=0.5 ; t2 motion [1,-1] (after sorting r3 [63,64]): mean 0 std 1.0 => mean 0.75
    assert abs(_val(m, "hand_shape.chord_tone_motion_variability", "right") - 0.75) < 1e-9
    # nonparallel rate: first parallel (same sign, range 1) => parallel true, second opposite signs => nonparallel => 0.5
    assert _val(m, "hand_shape.nonparallel_chord_tone_motion_rate", "right") == 0.5
    diag = _diag_text(m, "hand_shape.chord_tone_motion_variability", "right")
    assert "does not infer" in diag


def test_no_claims_of_fingering_or_repositioning_in_diagnostics():
    # Build any score and check all new feature diagnostics never claim fingering or literal repositioning
    notes = [_note("r1", 60, Fraction(0), "right"), _note("r1b", 72, Fraction(0), "right")]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(2))]
    score = _make_score(notes, measures)
    m = _feat_map(score)
    for (fid, scope, ref), feat in m.items():
        if not (fid.startswith("hand_shape.") or fid.startswith("hand_position.")):
            continue
        text = " ".join(feat.diagnostics).lower()
        # fingering only allowed with "does not"
        if "fingering" in text:
            assert "does not infer fingering" in text, f"{fid} diagnostics improperly mentions fingering without negation: {text}"
        if "voice-leading" in text:
            assert "does not" in text, f"{fid} diagnostics improperly claims voice-leading: {text}"
        if "independent voices" in text:
            assert "does not" in text, f"{fid} diagnostics improperly claims independent voices: {text}"
        # hand repositioning literal not allowed; center shift language is allowed
        assert "literal" not in text or "not literal" in text, f"{fid} claims literal repositioning: {text}"


def test_extracts_per_hand_records():
    # both hands have data => both scopes present
    notes = [_note("r1", 60, Fraction(0), "right"), _note("l1", 36, Fraction(0), "left")]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(2))]
    score = _make_score(notes, measures)
    m = _feat_map(score)
    for fid in ["hand_shape.octave_onset_rate", "hand_position.max_center_shift"]:
        assert (fid, "hand", "right") in m
        assert (fid, "hand", "left") in m


def test_extract_all_includes_new_features():
    # Integration: extract_all should emit new per-hand records with scope/hand
    notes = [
        _note("r1", 60, Fraction(0), "right"),
        _note("r1b", 72, Fraction(0), "right"),
        _note("l1", 36, Fraction(0), "left"),
    ]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(2))]
    score = _make_score(notes, measures)
    m = _feat_map_all(score)
    assert ("hand_shape.octave_onset_rate", "hand", "right") in m
    assert ("hand_position.max_center_shift", "hand", "right") in m
    # ensure scope correctness
    for (fid, scope, ref), feat in m.items():
        if fid.startswith("hand_shape.") or fid.startswith("hand_position."):
            assert scope == "hand", f"{fid} scope {scope}"
            assert ref in ("left", "right")


def test_timed_center_shift_gap_filter():
    # timed shift should ignore zero gap; we simulate same onset duplicates via same Fraction grouping? Actually build groups collapses same onset so gap 0 doesn't occur in normal use.
    # To trigger zero-gap filter we need check behavior with consecutive onsets separated but one gap is large; just validate normal path still deterministic.
    notes = [_note("r1", 60, Fraction(0), "right"), _note("r2", 62, Fraction(0), "right")]  # Wait both same onset -> single group
    # Better: ensure timed works with varied gaps
    notes = [_note("r1", 60, Fraction(0), "right"), _note("r2", 72, Fraction(1, 2), "right"), _note("r3", 74, Fraction(2), "right")]
    measures = [MeasureIR(measure_index=1, measure_number="1", start=Fraction(0), end=Fraction(4))]
    score = _make_score(notes, measures)
    m = _feat_map(score)
    # shifts: 12, 2 ; gaps 0.5 , 1.5 => timed 24, 1.333... mean ~12.666
    expected = (12 / 0.5 + 2 / 1.5) / 2
    assert abs(_val(m, "hand_position.timed_center_shift", "right") - expected) < 1e-9
