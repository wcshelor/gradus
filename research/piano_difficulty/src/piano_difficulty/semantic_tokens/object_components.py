"""Object-component and micro-moment builders.

Deterministic, no LLM. Conservative caveats when evidence insufficient.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any

from .models import (
    CATALOG_OBJECT_IDS,
    OBJECT_DIMENSIONS,
    OBJECT_LABELS,
    MusicalObject,
    ObjectComponent,
    MicroMoment,
    ScoreEvent,
    SemanticBundle,
)

# ---------------------------------------------------------------------------
# Practice implication mapping per component_type (conservative, deterministic)
# ---------------------------------------------------------------------------
COMPONENT_PRACTICE: dict[str, tuple[str, ...]] = {
    "bass_anchor": ("isolate_one_hand", "block_broken_chords"),
    "upper_chord_landing": ("landing_targets_only", "block_broken_chords"),
    "interval_path": ("loop_cell", "keep_pitch_contour_simplify_intervals"),
    "harmonic_collection": ("block_broken_chords", "keep_rhythm_simplify_pitch"),
    "hand_relocation": ("landing_targets_only", "isolate_one_hand"),
    "rhythm_cell": ("reduce_rhythm", "keep_rhythm_simplify_pitch", "loop_cell"),
    "beat_placement": ("reduce_rhythm",),
    "pattern_cycle": ("loop_cell", "transpose_pattern"),
    "pattern_break": ("loop_cell", "reduce_rhythm"),
    "accompaniment_role": ("isolate_one_hand", "progressive_layer_rebuild"),
    "launch_note": ("isolate_one_hand", "reduce_rhythm"),
    "target_chord": ("landing_targets_only", "block_broken_chords"),
    "landing_onset": ("landing_targets_only",),
    "landing_beat": ("landing_targets_only",),
    "leap_interval": ("isolate_one_hand",),
    "leap_interval_semitones": ("isolate_one_hand",),
    "time_to_land_quarters": ("reduce_rhythm",),
    "target_span": ("isolate_one_hand",),
    "target_span_semitones": ("isolate_one_hand",),
    "chord_note_count": ("landing_targets_only",),
    "other_hand_activity": ("isolate_one_hand", "ghost_accompaniment"),
    "melody_layer": ("remove_accompaniment", "ghost_accompaniment"),
    "accompaniment_layer": ("remove_accompaniment", "ghost_accompaniment"),
    "onset_alignment": ("ghost_accompaniment", "progressive_layer_rebuild"),
    "register_separation": ("remove_accompaniment",),
    "rhythmic_independence": ("ghost_accompaniment",),
    "balance_relation": ("ghost_accompaniment",),
    "accompaniment_pattern_reference": ("loop_cell",),
    "start_anchor": ("loop_cell",),
    "end_anchor": ("loop_cell",),
    "step_pattern": ("loop_cell", "keep_pitch_contour_simplify_intervals", "transpose_pattern"),
    "direction": ("loop_cell",),
    "span_semitones": ("keep_pitch_contour_simplify_intervals",),
    "note_count": ("loop_cell",),
    "duration_total": ("reduce_rhythm",),
    "notes_per_quarter": ("reduce_rhythm",),
    "beat_alignment": ("reduce_rhythm",),
    "thumb_crossing_candidate": ("loop_cell", "reduce_rhythm"),
    "rhythm_pattern": ("reduce_rhythm", "keep_rhythm_simplify_pitch"),
    "repetition_count": ("loop_cell",),
    "break_point": ("loop_cell", "reduce_rhythm"),
    "expected_pattern": ("keep_rhythm_simplify_pitch",),
    "actual_pattern": ("keep_rhythm_simplify_pitch",),
    "duration_pattern": ("reduce_rhythm",),
    "harmonic_set": ("block_broken_chords",),
    "octave_pair_sequence": ("loop_cell", "keep_pitch_contour_simplify_intervals"),
    "octave_direction": ("loop_cell",),
    "octave_span": ("keep_pitch_contour_simplify_intervals",),
    "doubling_type": ("keep_pitch_contour_simplify_intervals",),
    "voice_band_gap": ("isolate_one_hand", "ghost_accompaniment"),
    "low_voice_role": ("isolate_one_hand", "ghost_accompaniment"),
    "high_voice_role": ("isolate_one_hand", "ghost_accompaniment"),
    "rhythmic_independence_multi": ("ghost_accompaniment",),
}

TARGET_FAMILIES = {
    "broken_chord_accompaniment",
    "arpeggiated_accompaniment",
    "wide_broken_chord",
    "alberti_bass",
    "leap_to_chord",
    "chord_landing",
    "melody_with_accompaniment",
    "melody_voicing_over_accompaniment",
    "ascending_scalar_run",
    "descending_scalar_run",
    "repeated_rhythm_cell",
    "rhythm_pattern_break",
    "octave_doubled_melody",
    "single_hand_multi_voice_texture",
}


def _events_for_object(bundle: SemanticBundle, obj: MusicalObject) -> list[ScoreEvent]:
    ev_map: dict[str, ScoreEvent] = {e.event_id: e for e in bundle.events}
    out: list[ScoreEvent] = []
    for eid in obj.evidence_event_ids:
        ev = ev_map.get(eid)
        if ev is not None:
            out.append(ev)
    # fallback: if no events found (should not happen), try onset range
    if not out:
        for e in bundle.events:
            if obj.start_onset <= e.onset < obj.end_onset or (e.onset == obj.start_onset):
                if obj.hand is None or e.hand == obj.hand:
                    out.append(e)
    return sorted(out, key=lambda e: (e.onset, e.pitch_midi or 0, e.event_id))


def _median_pitch_per_onset(events: list[ScoreEvent]) -> list[tuple[Fraction, int, list[ScoreEvent]]]:
    g: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        if e.pitch_midi is not None:
            g[e.onset].append(e)
    reps: list[tuple[Fraction, int, list[ScoreEvent]]] = []
    for onset in sorted(g.keys()):
        evts = g[onset]
        mids = sorted(e.pitch_midi for e in evts if e.pitch_midi is not None)
        if not mids:
            continue
        median = mids[len(mids)//2]
        reps.append((onset, median, evts))
    return reps


def _beat_for_events(events: list[ScoreEvent]) -> tuple[Fraction | None, Fraction | None]:
    beats = [e.beat for e in events if e.beat is not None]
    if not beats:
        return None, None
    return beats[0], beats[-1]


def _measurements_common(events: list[ScoreEvent]) -> dict[str, Any]:
    if not events:
        return {}
    pitch_midis = [e.pitch_midi for e in events if e.pitch_midi is not None]
    pitch_classes = sorted({e.pitch_class for e in events if e.pitch_class is not None})
    reps = _median_pitch_per_onset(events)
    intervals = [reps[i+1][1] - reps[i][1] for i in range(len(reps)-1)] if len(reps) >= 2 else []
    total_span = max(pitch_midis) - min(pitch_midis) if len(pitch_midis) >= 2 else 0
    largest_jump = max((abs(iv) for iv in intervals), default=0)
    onset_pattern = [str(e.onset) for e in sorted(events, key=lambda x: x.onset)]
    duration_pattern = [str(e.duration) for e in sorted(events, key=lambda x: x.onset)]
    beat_positions = [str(e.beat) for e in sorted(events, key=lambda x: x.onset) if e.beat is not None]
    # attack density
    if events:
        duration_total = max(e.end for e in events) - min(e.onset for e in events)
        attack_density = len(events) / float(duration_total) if duration_total > 0 else float(len(events))
        notes_per_quarter = attack_density
    else:
        duration_total = Fraction(0)
        attack_density = 0
        notes_per_quarter = 0
    m: dict[str, Any] = {
        "pitch_midi": pitch_midis,
        "pitch_classes": pitch_classes,
        "interval_sequence": intervals,
        "total_span_semitones": int(total_span),
        "largest_jump_semitones": int(largest_jump),
        "onset_pattern": onset_pattern[:12],
        "duration_pattern": duration_pattern[:12],
        "beat_positions": beat_positions[:12],
        "notes_per_quarter": round(float(notes_per_quarter), 3),
        "attack_density": round(float(attack_density), 3),
        "hand": events[0].hand if events else None,
        "staff": events[0].staff if events else None,
        "duration_total": str(duration_total),
    }
    return m


def _make_component(
    parent: MusicalObject,
    component_type: str,
    label: str,
    role: str | None,
    hand: str | None,
    start_onset: Fraction,
    end_onset: Fraction,
    measure_start: int | None,
    measure_end: int | None,
    measure_numbers: tuple[str, ...],
    beat_start: Fraction | None,
    beat_end: Fraction | None,
    evidence_event_ids: tuple[str, ...],
    token_ids: tuple[str, ...],
    gesture_ids: tuple[str, ...],
    confidence: float,
    measurements: dict[str, Any],
    related_dimensions: tuple[str, ...],
    practice_implications: tuple[str, ...],
    caveats: tuple[str, ...],
) -> ObjectComponent:
    # deterministic id: parent:component_type:start_hand
    base = f"{parent.object_id}:{component_type}:{str(start_onset)}:{hand or 'both'}"
    # add hash suffix to avoid collision if same type multiple per object (rare)
    # Use simple deterministic suffix from measurements keys
    suffix = ""
    if measurements and "pitch_midi" in measurements:
        # tiny suffix from first pitch
        try:
            suffix = f":{measurements['pitch_midi'][0] if measurements['pitch_midi'] else '0'}"
        except Exception:
            suffix = ""
    comp_id = base + suffix
    # ensure uniqueness if duplicate already: caller handles appending index, but for now keep base
    return ObjectComponent(
        component_id=comp_id,
        component_type=component_type,
        parent_object_id=parent.object_id,
        parent_object_kind=parent.object_id,
        label=label,
        hand=hand,
        role=role,
        start_onset=start_onset,
        end_onset=end_onset,
        measure_start=measure_start,
        measure_end=measure_end,
        measure_numbers=measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=evidence_event_ids,
        token_ids=token_ids,
        gesture_ids=gesture_ids,
        confidence=float(max(0.0, min(1.0, confidence))),
        measurements=dict(measurements),
        related_dimensions=related_dimensions,
        practice_implications=practice_implications,
        caveats=caveats,
    )


def _build_broken_chord_family(obj: MusicalObject, events: list[ScoreEvent], bundle: SemanticBundle) -> list[ObjectComponent]:
    out: list[ObjectComponent] = []
    if not events:
        return out
    hand = obj.hand
    rel_dims = tuple(OBJECT_DIMENSIONS.get(obj.object_id, ()))
    # common measurements
    common = _measurements_common(events)
    beat_start, beat_end = _beat_for_events(events)
    # Determine bass anchor: earliest onset's lowest pitch
    sorted_by_onset = sorted(events, key=lambda e: (e.onset, e.pitch_midi or 999))
    earliest_onset = min(e.onset for e in events)
    bass_candidates = [e for e in events if e.onset == earliest_onset and e.pitch_midi is not None]
    bass_anchor_event = min(bass_candidates, key=lambda e: e.pitch_midi) if bass_candidates else None
    # upper chord landing: latest onset's chord (largest onset with 2+ notes or highest pitch)
    latest_onset = max(e.onset for e in events)
    upper_candidates = [e for e in events if e.onset == latest_onset]
    # interval_path
    reps = _median_pitch_per_onset(events)
    intervals = [reps[i+1][1] - reps[i][1] for i in range(len(reps)-1)] if len(reps) >=2 else []
    total_span = common.get("total_span_semitones", 0)
    largest_jump = common.get("largest_jump_semitones", 0)
    # relocation time
    relocation_time = (latest_onset - earliest_onset) if latest_onset > earliest_onset else Fraction(0)
    notes_per_quarter = common.get("notes_per_quarter", 0)
    # pattern cycle count: if harmony set repeats (pitch_class set size 3 and repeated)
    # simple: count distinct onset groups that share same pitch class set
    by_onset_pcs: dict[Fraction, set[int]] = {}
    for e in events:
        if e.pitch_class is not None:
            by_onset_pcs.setdefault(e.onset, set()).add(e.pitch_class)
    # find repeated harmonic set
    pcs_list = list(by_onset_pcs.values())
    repeated_cycle_count = None
    if len(pcs_list) >= 4:
        # if first half set equals second half etc. Use simple distinct counting
        # count occurrences of most common set
        from collections import Counter
        # convert sets to frozensets for hashing
        frozen = [frozenset(s) for s in pcs_list if s]
        if frozen:
            most = Counter(frozen).most_common(1)[0][1]
            if most >= 2:
                repeated_cycle_count = most
    # Build components
    # 1 bass_anchor
    if bass_anchor_event is not None:
        out.append(_make_component(
            parent=obj,
            component_type="bass_anchor",
            label="Bass anchor",
            role="anchor",
            hand=hand,
            start_onset=bass_anchor_event.onset,
            end_onset=bass_anchor_event.end,
            measure_start=bass_anchor_event.measure_index,
            measure_end=bass_anchor_event.measure_index,
            measure_numbers=(bass_anchor_event.measure_number,) if bass_anchor_event.measure_number else obj.measure_numbers,
            beat_start=bass_anchor_event.beat,
            beat_end=bass_anchor_event.beat,
            evidence_event_ids=(bass_anchor_event.event_id,),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.85 if obj.confidence > 0.6 else 0.6,
            measurements={"pitch_midi": [bass_anchor_event.pitch_midi], "beat": str(bass_anchor_event.beat) if bass_anchor_event.beat is not None else None},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("bass_anchor", ()),
            caveats=(),
        ))
    # 2 upper_chord_landing
    if upper_candidates:
        # use all notes at latest onset as chord
        pcs = [e.pitch_midi for e in upper_candidates if e.pitch_midi is not None]
        out.append(_make_component(
            parent=obj,
            component_type="upper_chord_landing",
            label="Upper chord landing",
            role="landing",
            hand=hand,
            start_onset=latest_onset,
            end_onset=max(e.end for e in upper_candidates),
            measure_start=upper_candidates[0].measure_index,
            measure_end=upper_candidates[0].measure_index,
            measure_numbers=(upper_candidates[0].measure_number,) if upper_candidates[0].measure_number else obj.measure_numbers,
            beat_start=upper_candidates[0].beat,
            beat_end=upper_candidates[0].beat,
            evidence_event_ids=tuple(e.event_id for e in upper_candidates),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.82,
            measurements={"pitch_midi": pcs, "note_count": len(upper_candidates)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("upper_chord_landing", ()),
            caveats=(),
        ))
    # 3 interval_path
    out.append(_make_component(
        parent=obj,
        component_type="interval_path",
        label="Interval path",
        role="path",
        hand=hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=float(obj.confidence) * 0.9,
        measurements={
            "interval_sequence": intervals,
            "total_span_semitones": total_span,
            "largest_jump_semitones": largest_jump,
            "pitch_midi": common.get("pitch_midi", []),
        },
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("interval_path", ()),
        caveats=() if intervals else ("insufficient_interval_evidence",),
    ))
    # 4 harmonic_collection
    pitch_classes = common.get("pitch_classes", [])
    out.append(_make_component(
        parent=obj,
        component_type="harmonic_collection",
        label="Harmonic collection",
        role="harmony",
        hand=hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.78,
        measurements={"pitch_classes": pitch_classes, "pitch_midi": common.get("pitch_midi", []), "harmonic_set": sorted(set(pitch_classes))},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("harmonic_collection", ()),
        caveats=() if pitch_classes else ("no_pitch_class_evidence",),
    ))
    # also harmonic_set alias for compatibility
    # 5 hand_relocation
    out.append(_make_component(
        parent=obj,
        component_type="hand_relocation",
        label="Hand relocation",
        role="relocation",
        hand=hand,
        start_onset=earliest_onset,
        end_onset=latest_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events[:2]) if len(events) >=2 else tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.80 if largest_jump >=7 else 0.60,
        measurements={
            "relocation_time_quarters": str(relocation_time),
            "total_span_semitones": total_span,
            "largest_jump_semitones": largest_jump,
            "beat_positions": common.get("beat_positions", []),
        },
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("hand_relocation", ()),
        caveats=() if largest_jump >= 7 else ("relocation_small",),
    ))
    # 6 rhythm_cell
    out.append(_make_component(
        parent=obj,
        component_type="rhythm_cell",
        label="Rhythm cell",
        role="rhythm",
        hand=hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.75,
        measurements={
            "onset_pattern": common.get("onset_pattern", []),
            "duration_pattern": common.get("duration_pattern", []),
            "beat_positions": common.get("beat_positions", []),
            "notes_per_quarter": notes_per_quarter,
            "attack_density": common.get("attack_density", 0),
        },
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("rhythm_cell", ()),
        caveats=(),
    ))
    # 7 beat_placement
    out.append(_make_component(
        parent=obj,
        component_type="beat_placement",
        label="Beat placement",
        role="timing",
        hand=hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.70,
        measurements={"beat_positions": common.get("beat_positions", []), "beat_start": str(beat_start) if beat_start else None},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("beat_placement", ()),
        caveats=() if common.get("beat_positions") else ("beat_not_in_score",),
    ))
    # 8 pattern_cycle
    if repeated_cycle_count is not None:
        out.append(_make_component(
            parent=obj,
            component_type="pattern_cycle",
            label="Pattern cycle",
            role="cycle",
            hand=hand,
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=beat_start,
            beat_end=beat_end,
            evidence_event_ids=tuple(e.event_id for e in events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.72,
            measurements={"repeated_cycle_count": repeated_cycle_count, "harmonic_set": pitch_classes},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("pattern_cycle", ()),
            caveats=(),
        ))
    # 9 pattern_break if expected vs actual available in payload
    if "pattern_break" in obj.object_id or obj.payload.get("pattern_break"):
        # generic
        out.append(_make_component(
            parent=obj,
            component_type="pattern_break",
            label="Pattern break",
            role="break",
            hand=hand,
            start_onset=obj.end_onset - Fraction(1, 2) if obj.end_onset - obj.start_onset > Fraction(1) else obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_end,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=beat_end,
            beat_end=beat_end,
            evidence_event_ids=tuple(e.event_id for e in events[-2:]) if len(events) >=2 else tuple(e.event_id for e in events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.65,
            measurements={"expected": obj.payload.get("expected_interval"), "actual": obj.payload.get("actual_interval")},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("pattern_break", ()),
            caveats=("heuristic_pattern_break",),
        ))
    # 10 accompaniment_role
    out.append(_make_component(
        parent=obj,
        component_type="accompaniment_role",
        label="Accompaniment role",
        role="role",
        hand=hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.70,
        measurements={"hand": hand, "staff": common.get("staff"), "notes_per_quarter": notes_per_quarter},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("accompaniment_role", ()),
        caveats=(),
    ))
    # deduplicate component_id collisions by appending type uniqueness already handled; ensure confidence etc.
    return out


def _build_leap_family(obj: MusicalObject, events: list[ScoreEvent], bundle: SemanticBundle) -> list[ObjectComponent]:
    out: list[ObjectComponent] = []
    if not events:
        return out
    hand = obj.hand
    rel_dims = tuple(OBJECT_DIMENSIONS.get(obj.object_id, ()))
    sorted_events = sorted(events, key=lambda e: (e.onset, e.pitch_midi or 0))
    # launch note: earliest event(s) minimal onset
    earliest_onset = min(e.onset for e in events)
    launch_events = [e for e in events if e.onset == earliest_onset]
    # choose lowest or median? Use first
    launch = launch_events[0] if launch_events else sorted_events[0]
    # target chord: latest onset group (could be chord)
    latest_onset = max(e.onset for e in events)
    target_events = [e for e in events if e.onset == latest_onset]
    if len(target_events) < 1:
        target_events = [sorted_events[-1]]
    target_midis = sorted([e.pitch_midi for e in target_events if e.pitch_midi is not None])
    # other hand activity
    other_hand = "right" if hand == "left" else "left" if hand == "right" else None
    has_other = False
    if other_hand:
        # check bundle events overlapping span
        for e in bundle.events:
            if e.hand == other_hand and not e.is_rest and e.onset >= obj.start_onset and e.onset < obj.end_onset:
                has_other = True
                break
    # measurements
    leap_interval = None
    if launch.pitch_midi is not None and target_midis:
        # use median target or lowest
        target_pitch = target_midis[len(target_midis)//2] if len(target_midis) >=2 else target_midis[0]
        leap_interval = target_pitch - launch.pitch_midi
    time_to_land = latest_onset - earliest_onset
    target_span = (max(target_midis) - min(target_midis)) if len(target_midis) >=2 else 0
    beat_landing = target_events[0].beat if target_events else None

    # launch_note
    out.append(_make_component(
        parent=obj,
        component_type="launch_note",
        label="Launch note",
        role="launch",
        hand=hand,
        start_onset=launch.onset,
        end_onset=launch.end,
        measure_start=launch.measure_index,
        measure_end=launch.measure_index,
        measure_numbers=(launch.measure_number,) if launch.measure_number else obj.measure_numbers,
        beat_start=launch.beat,
        beat_end=launch.beat,
        evidence_event_ids=(launch.event_id,),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.85,
        measurements={"pitch_midi": launch.pitch_midi, "beat": str(launch.beat) if launch.beat else None},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("launch_note", ()),
        caveats=(),
    ))
    # target_chord
    out.append(_make_component(
        parent=obj,
        component_type="target_chord",
        label="Target chord",
        role="target",
        hand=hand,
        start_onset=latest_onset,
        end_onset=max(e.end for e in target_events),
        measure_start=target_events[0].measure_index,
        measure_end=target_events[0].measure_index,
        measure_numbers=(target_events[0].measure_number,) if target_events[0].measure_number else obj.measure_numbers,
        beat_start=target_events[0].beat,
        beat_end=target_events[0].beat,
        evidence_event_ids=tuple(e.event_id for e in target_events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.85,
        measurements={"pitch_midi": target_midis, "chord_note_count": len(target_events), "target_span_semitones": int(target_span)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("target_chord", ()),
        caveats=(),
    ))
    # landing_onset
    out.append(_make_component(
        parent=obj,
        component_type="landing_onset",
        label="Landing onset",
        role="landing",
        hand=hand,
        start_onset=latest_onset,
        end_onset=latest_onset,
        measure_start=target_events[0].measure_index,
        measure_end=target_events[0].measure_index,
        measure_numbers=(target_events[0].measure_number,) if target_events[0].measure_number else obj.measure_numbers,
        beat_start=beat_landing,
        beat_end=beat_landing,
        evidence_event_ids=tuple(e.event_id for e in target_events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.80,
        measurements={"landing_onset": str(latest_onset), "time_to_land_quarters": str(time_to_land)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("landing_onset", ()),
        caveats=(),
    ))
    # landing_beat
    out.append(_make_component(
        parent=obj,
        component_type="landing_beat",
        label="Landing beat",
        role="landing",
        hand=hand,
        start_onset=latest_onset,
        end_onset=latest_onset,
        measure_start=target_events[0].measure_index,
        measure_end=target_events[0].measure_index,
        measure_numbers=(target_events[0].measure_number,) if target_events[0].measure_number else obj.measure_numbers,
        beat_start=beat_landing,
        beat_end=beat_landing,
        evidence_event_ids=tuple(e.event_id for e in target_events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.78 if beat_landing is not None else 0.55,
        measurements={"landing_beat": str(beat_landing) if beat_landing else None, "beat_start": str(beat_landing) if beat_landing else None},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("landing_beat", ()),
        caveats=() if beat_landing is not None else ("beat_not_in_score",),
    ))
    # leap_interval
    if leap_interval is not None:
        out.append(_make_component(
            parent=obj,
            component_type="leap_interval",
            label="Leap interval",
            role="interval",
            hand=hand,
            start_onset=earliest_onset,
            end_onset=latest_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=launch.beat,
            beat_end=beat_landing,
            evidence_event_ids=(launch.event_id,) + tuple(e.event_id for e in target_events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.82,
            measurements={"leap_interval_semitones": int(leap_interval), "time_to_land_quarters": str(time_to_land)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("leap_interval", ()),
            caveats=(),
        ))
        # alias leap_interval_semitones
        out.append(_make_component(
            parent=obj,
            component_type="leap_interval_semitones",
            label="Leap interval semitones",
            role="interval",
            hand=hand,
            start_onset=earliest_onset,
            end_onset=latest_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=launch.beat,
            beat_end=beat_landing,
            evidence_event_ids=(launch.event_id,) + tuple(e.event_id for e in target_events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.80,
            measurements={"leap_interval_semitones": int(leap_interval)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("leap_interval_semitones", ()),
            caveats=(),
        ))
    # target_span
    out.append(_make_component(
        parent=obj,
        component_type="target_span",
        label="Target span",
        role="span",
        hand=hand,
        start_onset=latest_onset,
        end_onset=max(e.end for e in target_events),
        measure_start=target_events[0].measure_index,
        measure_end=target_events[0].measure_index,
        measure_numbers=(target_events[0].measure_number,) if target_events[0].measure_number else obj.measure_numbers,
        beat_start=beat_landing,
        beat_end=beat_landing,
        evidence_event_ids=tuple(e.event_id for e in target_events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.75,
        measurements={"target_span_semitones": int(target_span), "chord_note_count": len(target_events)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("target_span", ()),
        caveats=(),
    ))
    # chord_note_count also as separate? target_span already includes, but add alias
    out.append(_make_component(
        parent=obj,
        component_type="chord_note_count",
        label="Chord note count",
        role="span",
        hand=hand,
        start_onset=latest_onset,
        end_onset=max(e.end for e in target_events),
        measure_start=target_events[0].measure_index,
        measure_end=target_events[0].measure_index,
        measure_numbers=(target_events[0].measure_number,) if target_events[0].measure_number else obj.measure_numbers,
        beat_start=beat_landing,
        beat_end=beat_landing,
        evidence_event_ids=tuple(e.event_id for e in target_events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.75,
        measurements={"chord_note_count": len(target_events)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("chord_note_count", ()),
        caveats=(),
    ))
    # other_hand_activity
    if has_other:
        # collect other hand events in span
        other_events = [e for e in bundle.events if e.hand == other_hand and not e.is_rest and e.onset >= obj.start_onset and e.onset < obj.end_onset]
        out.append(_make_component(
            parent=obj,
            component_type="other_hand_activity",
            label="Other hand activity",
            role="coordination",
            hand=other_hand,
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=None,
            beat_end=None,
            evidence_event_ids=tuple(e.event_id for e in other_events[:4]),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.65,
            measurements={"other_hand": other_hand, "note_count": len(other_events)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("other_hand_activity", ()),
            caveats=(),
        ))
    return out


def _build_melody_accompaniment_family(obj: MusicalObject, events: list[ScoreEvent], bundle: SemanticBundle) -> list[ObjectComponent]:
    out: list[ObjectComponent] = []
    if not events:
        return out
    rel_dims = tuple(OBJECT_DIMENSIONS.get(obj.object_id, ()))
    # Separate melody vs accompaniment by hand or by register
    # Heuristic: right hand = melody, left = accompaniment if both present
    right_events = [e for e in events if e.hand == "right"]
    left_events = [e for e in events if e.hand == "left"]
    if right_events and left_events:
        melody_events = right_events
        acc_events = left_events
        melody_hand = "right"
        acc_hand = "left"
    else:
        # fallback by pitch: higher half = melody
        mids = sorted([e.pitch_midi for e in events if e.pitch_midi is not None])
        if len(mids) >=2:
            median = mids[len(mids)//2]
            melody_events = [e for e in events if e.pitch_midi is not None and e.pitch_midi >= median]
            acc_events = [e for e in events if e.pitch_midi is not None and e.pitch_midi < median]
            melody_hand = melody_events[0].hand if melody_events else obj.hand
            acc_hand = acc_events[0].hand if acc_events else obj.hand
        else:
            melody_events = events
            acc_events = []
            melody_hand = obj.hand
            acc_hand = None
    beat_start, beat_end = _beat_for_events(events)
    # onset_alignment: overlapping onsets count
    mel_onsets = {e.onset for e in melody_events}
    acc_onsets = {e.onset for e in acc_events}
    overlapping = mel_onsets & acc_onsets
    alignment_ratio = len(overlapping) / max(len(mel_onsets), 1) if mel_onsets else 0
    # register separation
    mel_midis = [e.pitch_midi for e in melody_events if e.pitch_midi is not None]
    acc_midis = [e.pitch_midi for e in acc_events if e.pitch_midi is not None]
    register_gap = (min(mel_midis) - max(acc_midis)) if mel_midis and acc_midis else None
    # accompaniment pattern reference: check if accompaniment overlaps known accompaniment object
    acc_pattern_ref = None
    for other_obj in bundle.musical_objects:
        if other_obj.object_id in ("alberti_bass", "broken_chord_accompaniment", "arpeggiated_accompaniment", "waltz_bass", "oom_pah_bass_chord_pattern"):
            if other_obj.start_onset < obj.end_onset and other_obj.end_onset > obj.start_onset:
                # overlap
                acc_pattern_ref = other_obj.object_id
                break

    # melody_layer
    if melody_events:
        out.append(_make_component(
            parent=obj,
            component_type="melody_layer",
            label="Melody layer",
            role="melody",
            hand=melody_hand,
            start_onset=min(e.onset for e in melody_events),
            end_onset=max(e.end for e in melody_events),
            measure_start=min(e.measure_index for e in melody_events if e.measure_index is not None) if melody_events else obj.measure_start,
            measure_end=max(e.measure_index for e in melody_events if e.measure_index is not None) if melody_events else obj.measure_end,
            measure_numbers=tuple(sorted({str(e.measure_number) for e in melody_events if e.measure_number})) or obj.measure_numbers,
            beat_start=melody_events[0].beat,
            beat_end=melody_events[-1].beat,
            evidence_event_ids=tuple(e.event_id for e in melody_events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.80,
            measurements={"melody_hand": melody_hand, "melody_pitch_range": [min(mel_midis), max(mel_midis)] if mel_midis else [], "note_count": len(melody_events)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("melody_layer", ()),
            caveats=(),
        ))
    # accompaniment_layer
    if acc_events:
        out.append(_make_component(
            parent=obj,
            component_type="accompaniment_layer",
            label="Accompaniment layer",
            role="accompaniment",
            hand=acc_hand,
            start_onset=min(e.onset for e in acc_events),
            end_onset=max(e.end for e in acc_events),
            measure_start=min(e.measure_index for e in acc_events if e.measure_index is not None),
            measure_end=max(e.measure_index for e in acc_events if e.measure_index is not None),
            measure_numbers=tuple(sorted({str(e.measure_number) for e in acc_events if e.measure_number})) or obj.measure_numbers,
            beat_start=acc_events[0].beat,
            beat_end=acc_events[-1].beat,
            evidence_event_ids=tuple(e.event_id for e in acc_events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.80,
            measurements={"accompaniment_hand": acc_hand, "accompaniment_pitch_range": [min(acc_midis), max(acc_midis)] if acc_midis else [], "note_count": len(acc_events), "accompaniment_attack_density": round(len(acc_events)/float(max(e.end for e in acc_events)-min(e.onset for e in acc_events)) if len(acc_events)>=2 and max(e.end for e in acc_events)>min(e.onset for e in acc_events) else 0, 3)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("accompaniment_layer", ()),
            caveats=(),
        ))
    # onset_alignment
    out.append(_make_component(
        parent=obj,
        component_type="onset_alignment",
        label="Onset alignment",
        role="alignment",
        hand=None,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in melody_events[:2]) + tuple(e.event_id for e in acc_events[:2]),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.75 if overlapping else 0.55,
        measurements={"overlapping_onsets": len(overlapping), "alignment_ratio": round(float(alignment_ratio), 3), "melody_onsets": len(mel_onsets), "accompaniment_onsets": len(acc_onsets)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("onset_alignment", ()),
        caveats=() if overlapping else ("no_overlapping_onsets",),
    ))
    # register_separation
    if register_gap is not None:
        out.append(_make_component(
            parent=obj,
            component_type="register_separation",
            label="Register separation",
            role="register",
            hand=None,
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=beat_start,
            beat_end=beat_end,
            evidence_event_ids=tuple(e.event_id for e in events[:4]),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.70,
            measurements={"register_gap_semitones": int(register_gap), "melody_pitch_range": [min(mel_midis), max(mel_midis)] if mel_midis else [], "accompaniment_pitch_range": [min(acc_midis), max(acc_midis)] if acc_midis else []},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("register_separation", ()),
            caveats=(),
        ))
    # rhythmic_independence
    # compare onset patterns: if melody and acc have different durations/patterns
    if acc_events and melody_events:
        mel_durs = [str(e.duration) for e in sorted(melody_events, key=lambda x: x.onset)[:4]]
        acc_durs = [str(e.duration) for e in sorted(acc_events, key=lambda x: x.onset)[:4]]
        rhythmic_diff = mel_durs != acc_durs
        out.append(_make_component(
            parent=obj,
            component_type="rhythmic_independence",
            label="Rhythmic independence",
            role="rhythm",
            hand=None,
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=beat_start,
            beat_end=beat_end,
            evidence_event_ids=tuple(e.event_id for e in events[:4]),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.68 if rhythmic_diff else 0.55,
            measurements={"melody_duration_pattern": mel_durs, "accompaniment_duration_pattern": acc_durs, "alignment_ratio": round(float(alignment_ratio),3)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("rhythmic_independence", ()),
            caveats=(),
        ))
    # balance_relation
    out.append(_make_component(
        parent=obj,
        component_type="balance_relation",
        label="Balance relation",
        role="balance",
        hand=None,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events[:4]),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.65,
        measurements={"register_gap_semitones": int(register_gap) if register_gap is not None else None, "melody_note_count": len(melody_events), "accompaniment_note_count": len(acc_events)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("balance_relation", ()),
        caveats=("balance_inferred_from_texture",),
    ))
    # accompaniment_pattern_reference
    if acc_pattern_ref:
        out.append(_make_component(
            parent=obj,
            component_type="accompaniment_pattern_reference",
            label="Accompaniment pattern reference",
            role="reference",
            hand=acc_hand,
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=beat_start,
            beat_end=beat_end,
            evidence_event_ids=tuple(e.event_id for e in acc_events[:3]) if acc_events else tuple(e.event_id for e in events[:2]),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.72,
            measurements={"accompaniment_pattern_reference": acc_pattern_ref, "accompaniment_attack_density": round(len(acc_events)/float(max(e.end for e in acc_events)-min(e.onset for e in acc_events)) if acc_events and len(acc_events)>=2 and max(e.end for e in acc_events)>min(e.onset for e in acc_events) else 0,3)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("accompaniment_pattern_reference", ()),
            caveats=(),
        ))
    return out


def _build_scalar_family(obj: MusicalObject, events: list[ScoreEvent], bundle: SemanticBundle) -> list[ObjectComponent]:
    out: list[ObjectComponent] = []
    if not events:
        return out
    rel_dims = tuple(OBJECT_DIMENSIONS.get(obj.object_id, ()))
    sorted_events = sorted(events, key=lambda e: e.onset)
    reps = _median_pitch_per_onset(events)
    if not reps and sorted_events:
        # fallback single notes
        reps = [(e.onset, e.pitch_midi or 60, [e]) for e in sorted_events if e.pitch_midi is not None]
    if not reps:
        return out
    intervals = [reps[i+1][1] - reps[i][1] for i in range(len(reps)-1)]
    direction = "up" if sum(iv for iv in intervals if iv>0) > abs(sum(iv for iv in intervals if iv<0)) else "down" if any(iv<0 for iv in intervals) else "flat"
    if obj.object_id == "ascending_scalar_run":
        direction = "up"
    elif obj.object_id == "descending_scalar_run":
        direction = "down"
    span = max(r[1] for r in reps) - min(r[1] for r in reps) if reps else 0
    note_count = len(reps)
    duration_total = max(e.end for e in events) - min(e.onset for e in events)
    notes_per_quarter = len(events) / float(duration_total) if duration_total>0 else 0
    beat_start, beat_end = _beat_for_events(events)
    # thumb crossing candidate if note_count >5 and span >5
    thumb_crossing = note_count >= 7 and span >= 7
    # build components
    # start_anchor
    first = reps[0]
    last = reps[-1]
    out.append(_make_component(
        parent=obj,
        component_type="start_anchor",
        label="Start anchor",
        role="anchor",
        hand=obj.hand,
        start_onset=first[0],
        end_onset=first[0] + (first[2][0].duration if first[2] else Fraction(1,4)),
        measure_start=first[2][0].measure_index if first[2] else obj.measure_start,
        measure_end=first[2][0].measure_index if first[2] else obj.measure_start,
        measure_numbers=(first[2][0].measure_number,) if first[2] and first[2][0].measure_number else obj.measure_numbers,
        beat_start=first[2][0].beat if first[2] else None,
        beat_end=first[2][0].beat if first[2] else None,
        evidence_event_ids=tuple(e.event_id for e in first[2]),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.80,
        measurements={"pitch_midi": first[1]},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("start_anchor", ()),
        caveats=(),
    ))
    # end_anchor
    out.append(_make_component(
        parent=obj,
        component_type="end_anchor",
        label="End anchor",
        role="anchor",
        hand=obj.hand,
        start_onset=last[0],
        end_onset=last[0] + (last[2][0].duration if last[2] else Fraction(1,4)),
        measure_start=last[2][0].measure_index if last[2] else obj.measure_end,
        measure_end=last[2][0].measure_index if last[2] else obj.measure_end,
        measure_numbers=(last[2][0].measure_number,) if last[2] and last[2][0].measure_number else obj.measure_numbers,
        beat_start=last[2][0].beat if last[2] else None,
        beat_end=last[2][0].beat if last[2] else None,
        evidence_event_ids=tuple(e.event_id for e in last[2]),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.80,
        measurements={"pitch_midi": last[1]},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("end_anchor", ()),
        caveats=(),
    ))
    # step_pattern
    out.append(_make_component(
        parent=obj,
        component_type="step_pattern",
        label="Step pattern",
        role="path",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.85,
        measurements={"interval_sequence": intervals, "direction": direction, "span_semitones": int(span)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("step_pattern", ()),
        caveats=() if intervals else ("no_interval_evidence",),
    ))
    # direction
    out.append(_make_component(
        parent=obj,
        component_type="direction",
        label="Direction",
        role="contour",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events[:3]),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.85,
        measurements={"direction": direction},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("direction", ()),
        caveats=(),
    ))
    # span_semitones
    out.append(_make_component(
        parent=obj,
        component_type="span_semitones",
        label="Span semitones",
        role="span",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.78,
        measurements={"span_semitones": int(span), "note_count": note_count},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("span_semitones", ()),
        caveats=(),
    ))
    # note_count
    out.append(_make_component(
        parent=obj,
        component_type="note_count",
        label="Note count",
        role="density",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.70,
        measurements={"note_count": note_count, "duration_total": str(duration_total), "notes_per_quarter": round(float(notes_per_quarter),3)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("note_count", ()),
        caveats=(),
    ))
    # thumb_crossing_candidate
    if thumb_crossing:
        out.append(_make_component(
            parent=obj,
            component_type="thumb_crossing_candidate",
            label="Thumb crossing candidate",
            role="fingering",
            hand=obj.hand,
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=beat_start,
            beat_end=beat_end,
            evidence_event_ids=tuple(e.event_id for e in events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.55,
            measurements={"note_count": note_count, "span_semitones": int(span)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("thumb_crossing_candidate", ()),
            caveats=("fingering_not_in_score",),
        ))
    # beat_alignment and others
    out.append(_make_component(
        parent=obj,
        component_type="beat_alignment",
        label="Beat alignment",
        role="timing",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in events[:3]),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.65,
        measurements={"beat_positions": [str(e.beat) for e in events if e.beat is not None][:6], "notes_per_quarter": round(float(notes_per_quarter),3)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("beat_alignment", ()),
        caveats=() if beat_start is not None else ("beat_not_in_score",),
    ))
    return out


def _build_octave_doubled_family(obj: MusicalObject, events: list[ScoreEvent], bundle: SemanticBundle) -> list[ObjectComponent]:
    out: list[ObjectComponent] = []
    if not events:
        return out
    rel_dims = tuple(OBJECT_DIMENSIONS.get(obj.object_id, ()))
    beat_start, beat_end = _beat_for_events(events)
    # Extract octave-specific payload if available
    octave_count = obj.payload.get("octave_count", len({e.onset for e in events if any(e2.onset == e.onset for e2 in events)}))
    direction = obj.payload.get("direction", "mixed")
    span = obj.payload.get("pitch_span_semitones") or obj.payload.get("span_semitones") or 12
    doubling_type = obj.payload.get("doubling_type", "exact_octave" if obj.payload.get("is_exact_doubling") else "mixed_octave_plus_other_tones")
    # interval path derived from events (median per onset would be blurred, so use low note per onset)
    # Group by onset and take min pitch per onset as low voice
    by_onset: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        by_onset[e.onset].append(e)
    sorted_onsets = sorted(by_onset.keys())
    low_pitches: list[int] = []
    high_pitches: list[int] = []
    for o in sorted_onsets:
        mids = sorted(e.pitch_midi for e in by_onset[o] if e.pitch_midi is not None)
        if len(mids) >= 2:
            # find octave pair
            found = None
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    if mids[j] - mids[i] == 12:
                        found = (mids[i], mids[j])
                        break
                if found:
                    break
            if found:
                low_pitches.append(found[0])
                high_pitches.append(found[1])
            else:
                low_pitches.append(mids[0])
                high_pitches.append(mids[-1])
        elif mids:
            low_pitches.append(mids[0])
            high_pitches.append(mids[0])
    intervals_low = [low_pitches[i+1] - low_pitches[i] for i in range(len(low_pitches)-1)] if len(low_pitches) >=2 else []
    intervals_high = [high_pitches[i+1] - high_pitches[i] for i in range(len(high_pitches)-1)] if len(high_pitches) >=2 else []
    # octave_pair_sequence
    out.append(_make_component(
        parent=obj, component_type="octave_pair_sequence", label="Octave pair sequence", role="sequence", hand=obj.hand,
        start_onset=obj.start_onset, end_onset=obj.end_onset, measure_start=obj.measure_start, measure_end=obj.measure_end, measure_numbers=obj.measure_numbers,
        beat_start=beat_start, beat_end=beat_end, evidence_event_ids=tuple(e.event_id for e in events), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
        confidence=float(obj.confidence) * 0.92, measurements={"octave_count": octave_count, "low_pitches": low_pitches[:6], "high_pitches": high_pitches[:6], "interval_sequence_low": intervals_low[:6]},
        related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("octave_pair_sequence", ()), caveats=tuple(obj.caveats),
    ))
    out.append(_make_component(
        parent=obj, component_type="octave_direction", label="Octave direction", role="contour", hand=obj.hand,
        start_onset=obj.start_onset, end_onset=obj.end_onset, measure_start=obj.measure_start, measure_end=obj.measure_end, measure_numbers=obj.measure_numbers,
        beat_start=beat_start, beat_end=beat_end, evidence_event_ids=tuple(e.event_id for e in events[:4]), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
        confidence=0.80, measurements={"direction": direction, "intervals_low": intervals_low[:6], "intervals_high": intervals_high[:6]},
        related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("octave_direction", ()), caveats=(),
    ))
    out.append(_make_component(
        parent=obj, component_type="octave_span", label="Octave span", role="span", hand=obj.hand,
        start_onset=obj.start_onset, end_onset=obj.end_onset, measure_start=obj.measure_start, measure_end=obj.measure_end, measure_numbers=obj.measure_numbers,
        beat_start=beat_start, beat_end=beat_end, evidence_event_ids=tuple(e.event_id for e in events), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
        confidence=0.75, measurements={"span_semitones": int(span) if isinstance(span, (int,float)) else span, "octave_count": octave_count},
        related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("octave_span", ()), caveats=(),
    ))
    out.append(_make_component(
        parent=obj, component_type="doubling_type", label="Doubling type", role="texture", hand=obj.hand,
        start_onset=obj.start_onset, end_onset=obj.end_onset, measure_start=obj.measure_start, measure_end=obj.measure_end, measure_numbers=obj.measure_numbers,
        beat_start=beat_start, beat_end=beat_end, evidence_event_ids=tuple(e.event_id for e in events), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
        confidence=0.78, measurements={"doubling_type": doubling_type, "is_exact": obj.payload.get("is_exact_doubling", True), "is_mixed": obj.payload.get("is_mixed", False)},
        related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("doubling_type", ()), caveats=tuple(obj.caveats),
    ))
    return out


def _build_multi_voice_family(obj: MusicalObject, events: list[ScoreEvent], bundle: SemanticBundle) -> list[ObjectComponent]:
    out: list[ObjectComponent] = []
    if not events:
        return out
    rel_dims = tuple(OBJECT_DIMENSIONS.get(obj.object_id, ()))
    beat_start, beat_end = _beat_for_events(events)
    gap = obj.payload.get("pitch_band_gap_semitones", 12)
    low_range = obj.payload.get("low_band_range", [])
    high_range = obj.payload.get("high_band_range", [])
    reasons = obj.payload.get("reasons", ())
    overlap = obj.payload.get("overlap_ratio", 0)
    ratio = obj.payload.get("duration_ratio", 1.0)
    # voice_band_gap
    out.append(_make_component(
        parent=obj, component_type="voice_band_gap", label="Voice band gap", role="gap", hand=obj.hand,
        start_onset=obj.start_onset, end_onset=obj.end_onset, measure_start=obj.measure_start, measure_end=obj.measure_end, measure_numbers=obj.measure_numbers,
        beat_start=beat_start, beat_end=beat_end, evidence_event_ids=tuple(e.event_id for e in events[:4]), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
        confidence=0.72, measurements={"gap_semitones": gap, "low_range": low_range, "high_range": high_range, "overlap_ratio": overlap},
        related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("voice_band_gap", ()), caveats=tuple(obj.caveats),
    ))
    # low/high roles
    low_events = sorted([e for e in events if low_range and e.pitch_midi is not None and low_range[0] <= e.pitch_midi <= low_range[1]], key=lambda e: e.onset) if low_range and len(low_range)==2 else []
    high_events = sorted([e for e in events if high_range and e.pitch_midi is not None and high_range[0] <= e.pitch_midi <= high_range[1]], key=lambda e: e.onset) if high_range and len(high_range)==2 else []
    if low_events:
        out.append(_make_component(
            parent=obj, component_type="low_voice_role", label="Low voice role", role="voice", hand=obj.hand,
            start_onset=min(e.onset for e in low_events), end_onset=max(e.end for e in low_events), measure_start=min(e.measure_index for e in low_events if e.measure_index is not None), measure_end=max(e.measure_index for e in low_events if e.measure_index is not None),
            measure_numbers=tuple(sorted({str(e.measure_number) for e in low_events if e.measure_number})) or obj.measure_numbers,
            beat_start=low_events[0].beat, beat_end=low_events[-1].beat, evidence_event_ids=tuple(e.event_id for e in low_events), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
            confidence=0.68, measurements={"pitch_range": low_range, "note_count": len(low_events), "avg_duration": obj.payload.get("low_avg_duration")},
            related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("low_voice_role", ()), caveats=tuple(obj.caveats),
        ))
    if high_events:
        out.append(_make_component(
            parent=obj, component_type="high_voice_role", label="High voice role", role="voice", hand=obj.hand,
            start_onset=min(e.onset for e in high_events), end_onset=max(e.end for e in high_events), measure_start=min(e.measure_index for e in high_events if e.measure_index is not None), measure_end=max(e.measure_index for e in high_events if e.measure_index is not None),
            measure_numbers=tuple(sorted({str(e.measure_number) for e in high_events if e.measure_number})) or obj.measure_numbers,
            beat_start=high_events[0].beat, beat_end=high_events[-1].beat, evidence_event_ids=tuple(e.event_id for e in high_events), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
            confidence=0.68, measurements={"pitch_range": high_range, "note_count": len(high_events), "avg_duration": obj.payload.get("high_avg_duration")},
            related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("high_voice_role", ()), caveats=tuple(obj.caveats),
        ))
    out.append(_make_component(
        parent=obj, component_type="rhythmic_independence_multi", label="Rhythmic independence", role="rhythm", hand=obj.hand,
        start_onset=obj.start_onset, end_onset=obj.end_onset, measure_start=obj.measure_start, measure_end=obj.measure_end, measure_numbers=obj.measure_numbers,
        beat_start=beat_start, beat_end=beat_end, evidence_event_ids=tuple(e.event_id for e in events), token_ids=tuple(obj.token_ids), gesture_ids=tuple(obj.gesture_ids),
        confidence=0.65, measurements={"duration_ratio": ratio, "reasons": list(reasons) if isinstance(reasons, (list,tuple)) else [str(reasons)], "overlap_ratio": overlap},
        related_dimensions=rel_dims, practice_implications=COMPONENT_PRACTICE.get("rhythmic_independence_multi", ()), caveats=tuple(obj.caveats),
    ))
    return out


def _build_rhythm_family(obj: MusicalObject, events: list[ScoreEvent], bundle: SemanticBundle) -> list[ObjectComponent]:
    out: list[ObjectComponent] = []
    if not events:
        return out
    rel_dims = tuple(OBJECT_DIMENSIONS.get(obj.object_id, ()))
    sorted_events = sorted(events, key=lambda e: e.onset)
    beat_start, beat_end = _beat_for_events(events)
    # duration pattern
    durations = [str(e.duration) for e in sorted_events]
    beats = [str(e.beat) for e in sorted_events if e.beat is not None]
    # try to detect repeated rhythm cell from tokens: look at derived tokens overlapping object
    # For now use heuristic: find most common duration bigram
    from collections import Counter
    dur_counter = Counter(durations)
    # repetition_count estimation via pattern repetition tokens
    repetition_count = None
    expected_pattern = None
    actual_pattern = None
    break_point = None
    # look at bundle derived tokens that overlap obj span and are pattern_repetition / pattern_break
    overlapping_tokens = [t for t in bundle.derived_tokens if t.start_onset < obj.end_onset and t.end_onset > obj.start_onset and t.hand == obj.hand or (obj.hand is None and t.hand is not None)]
    # Use tighter check
    rep_tokens = [t for t in overlapping_tokens if t.kind == "pattern_repetition" and t.evidence_event_ids and any(eid in obj.evidence_event_ids for eid in t.evidence_event_ids) or (t.kind=="pattern_repetition" and t.hand==obj.hand and obj.start_onset <= t.start_onset < obj.end_onset)]
    break_tokens = [t for t in overlapping_tokens if t.kind == "pattern_break" and t.hand==obj.hand]
    if rep_tokens:
        # take best
        best = max(rep_tokens, key=lambda t: t.confidence)
        repetition_count = best.payload.get("total_occurrences")
        expected_pattern = best.payload.get("pattern_intervals")
        # actual from break token if present
        if break_tokens:
            br = max(break_tokens, key=lambda t: t.confidence)
            actual_pattern = br.payload.get("actual_interval")
            expected_pattern = br.payload.get("expected_interval") or expected_pattern
            break_point = str(br.start_onset)
    else:
        # fallback: count repeats of most common duration
        if durations:
            most_common = dur_counter.most_common(1)[0][1]
            if most_common >=2:
                repetition_count = most_common
    # rhythm_cell component
    out.append(_make_component(
        parent=obj,
        component_type="rhythm_cell",
        label="Rhythm cell",
        role="rhythm",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in sorted_events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.78 if repetition_count and repetition_count>=2 else 0.65,
        measurements={"duration_pattern": durations[:8], "beat_positions": beats[:8], "repetition_count": repetition_count, "note_count": len(sorted_events)},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("rhythm_cell", ()),
        caveats=() if repetition_count else ("heuristic_rhythm_cell",),
    ))
    # repetition_count separate
    if repetition_count is not None:
        out.append(_make_component(
            parent=obj,
            component_type="repetition_count",
            label="Repetition count",
            role="count",
            hand=obj.hand,
            start_onset=obj.start_onset,
            end_onset=obj.end_onset,
            measure_start=obj.measure_start,
            measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers,
            beat_start=beat_start,
            beat_end=beat_end,
            evidence_event_ids=tuple(e.event_id for e in sorted_events),
            token_ids=tuple(obj.token_ids),
            gesture_ids=tuple(obj.gesture_ids),
            confidence=0.70,
            measurements={"repetition_count": repetition_count, "duration_pattern": durations[:6]},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("repetition_count", ()),
            caveats=(),
        ))
    # break_point for rhythm_pattern_break
    if obj.object_id == "rhythm_pattern_break" and break_tokens:
        br = max(break_tokens, key=lambda t: t.confidence)
        out.append(_make_component(
            parent=obj,
            component_type="break_point",
            label="Break point",
            role="break",
            hand=obj.hand,
            start_onset=br.start_onset,
            end_onset=br.end_onset,
            measure_start=br.measure_start,
            measure_end=br.measure_end,
            measure_numbers=br.measure_numbers,
            beat_start=None,
            beat_end=None,
            evidence_event_ids=tuple(br.evidence_event_ids),
            token_ids=(br.token_id,),
            gesture_ids=(),
            confidence=float(br.confidence),
            measurements={"break_point": str(br.start_onset), "expected_pattern": str(expected_pattern), "actual_pattern": str(actual_pattern)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("break_point", ()),
            caveats=(),
        ))
        out.append(_make_component(
            parent=obj,
            component_type="expected_pattern",
            label="Expected pattern",
            role="pattern",
            hand=obj.hand,
            start_onset=br.start_onset,
            end_onset=br.end_onset,
            measure_start=br.measure_start,
            measure_end=br.measure_end,
            measure_numbers=br.measure_numbers,
            beat_start=None,
            beat_end=None,
            evidence_event_ids=tuple(br.evidence_event_ids),
            token_ids=(br.token_id,),
            gesture_ids=(),
            confidence=0.68,
            measurements={"expected_pattern": str(expected_pattern)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("expected_pattern", ()),
            caveats=(),
        ))
        out.append(_make_component(
            parent=obj,
            component_type="actual_pattern",
            label="Actual pattern",
            role="pattern",
            hand=obj.hand,
            start_onset=br.start_onset,
            end_onset=br.end_onset,
            measure_start=br.measure_start,
            measure_end=br.measure_end,
            measure_numbers=br.measure_numbers,
            beat_start=None,
            beat_end=None,
            evidence_event_ids=tuple(br.evidence_event_ids),
            token_ids=(br.token_id,),
            gesture_ids=(),
            confidence=0.68,
            measurements={"actual_pattern": str(actual_pattern)},
            related_dimensions=rel_dims,
            practice_implications=COMPONENT_PRACTICE.get("actual_pattern", ()),
            caveats=(),
        ))
    # beat_positions component
    out.append(_make_component(
        parent=obj,
        component_type="beat_positions",
        label="Beat positions",
        role="timing",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in sorted_events[:4]),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.65,
        measurements={"beat_positions": beats[:8], "duration_pattern": durations[:8]},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("beat_positions", ()),
        caveats=() if beats else ("beat_not_in_score",),
    ))
    # duration_pattern
    out.append(_make_component(
        parent=obj,
        component_type="duration_pattern",
        label="Duration pattern",
        role="rhythm",
        hand=obj.hand,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        evidence_event_ids=tuple(e.event_id for e in sorted_events),
        token_ids=tuple(obj.token_ids),
        gesture_ids=tuple(obj.gesture_ids),
        confidence=0.65,
        measurements={"duration_pattern": durations[:8]},
        related_dimensions=rel_dims,
        practice_implications=COMPONENT_PRACTICE.get("duration_pattern", ()),
        caveats=(),
    ))
    return out


def build_object_components(bundle: SemanticBundle) -> tuple[ObjectComponent, ...]:
    """Build components for high-value object families."""
    out: list[ObjectComponent] = []
    # Only for target families to keep focused per spec
    target_set = TARGET_FAMILIES
    # dedup component_ids
    seen_ids: set[str] = set()
    for obj in bundle.musical_objects:
        if obj.object_id not in target_set:
            continue
        events = _events_for_object(bundle, obj)
        if not events:
            continue
        try:
            if obj.object_id in {"broken_chord_accompaniment", "arpeggiated_accompaniment", "wide_broken_chord", "alberti_bass"}:
                comps = _build_broken_chord_family(obj, events, bundle)
            elif obj.object_id in {"leap_to_chord", "chord_landing"}:
                comps = _build_leap_family(obj, events, bundle)
            elif obj.object_id in {"melody_with_accompaniment", "melody_voicing_over_accompaniment"}:
                comps = _build_melody_accompaniment_family(obj, events, bundle)
            elif obj.object_id in {"ascending_scalar_run", "descending_scalar_run"}:
                comps = _build_scalar_family(obj, events, bundle)
            elif obj.object_id == "octave_doubled_melody":
                comps = _build_octave_doubled_family(obj, events, bundle)
            elif obj.object_id == "single_hand_multi_voice_texture":
                comps = _build_multi_voice_family(obj, events, bundle)
            elif obj.object_id in {"repeated_rhythm_cell", "rhythm_pattern_break"}:
                comps = _build_rhythm_family(obj, events, bundle)
            else:
                comps = []
        except Exception:
            continue
        for c in comps:
            # ensure unique id: if collision, append suffix index
            base_id = c.component_id
            if base_id in seen_ids:
                # append counter
                idx = 2
                new_id = f"{base_id}:{idx}"
                while new_id in seen_ids:
                    idx += 1
                    new_id = f"{base_id}:{idx}"
                # recreate with new id
                c = ObjectComponent(
                    component_id=new_id,
                    component_type=c.component_type,
                    parent_object_id=c.parent_object_id,
                    parent_object_kind=c.parent_object_kind,
                    label=c.label,
                    hand=c.hand,
                    role=c.role,
                    start_onset=c.start_onset,
                    end_onset=c.end_onset,
                    measure_start=c.measure_start,
                    measure_end=c.measure_end,
                    measure_numbers=c.measure_numbers,
                    beat_start=c.beat_start,
                    beat_end=c.beat_end,
                    evidence_event_ids=c.evidence_event_ids,
                    token_ids=c.token_ids,
                    gesture_ids=c.gesture_ids,
                    confidence=c.confidence,
                    measurements=dict(c.measurements),
                    related_dimensions=c.related_dimensions,
                    practice_implications=c.practice_implications,
                    caveats=c.caveats,
                )
            seen_ids.add(c.component_id)
            out.append(c)
    # deterministic ordering by start_onset then component_id
    out.sort(key=lambda c: (c.start_onset, c.component_id))
    return tuple(out)


def build_micro_moments(bundle: SemanticBundle, components: tuple[ObjectComponent, ...]) -> tuple[MicroMoment, ...]:
    """Group nearby/overlapping components into micro-moments.

    Prefer short spans one beat to one measure where possible.
    Deterministic ordering by start_onset then component_id.
    """
    if not components:
        return ()
    # sort deterministic
    sorted_comps = sorted(components, key=lambda c: (c.start_onset, c.component_id))
    groups: list[list[ObjectComponent]] = []
    current: list[ObjectComponent] = []
    current_end: Fraction | None = None
    current_start: Fraction | None = None
    for comp in sorted_comps:
        if not current:
            current = [comp]
            current_start = comp.start_onset
            current_end = comp.end_onset
            continue
        # Check if span would exceed measure length (4 quarters) if added
        proposed_start = current_start if current_start is not None else comp.start_onset
        proposed_end = max(current_end, comp.end_onset) if current_end else comp.end_onset
        would_exceed = (proposed_end - proposed_start) > Fraction(4)
        # overlap or close proximity
        overlap = comp.start_onset < current_end if current_end else False
        close = (comp.start_onset - current_end <= Fraction(1, 2)) if current_end else False
        same_measure = bool(set(comp.measure_numbers) & set(current[0].measure_numbers)) if current else False
        same_beat = False
        if comp.beat_start is not None and current[-1].beat_start is not None:
            try:
                same_beat = abs(comp.beat_start - current[-1].beat_start) <= Fraction(1)
            except Exception:
                same_beat = False
        should_group = (overlap or (close and (same_measure or same_beat))) and not would_exceed
        if should_group:
            current.append(comp)
            if comp.end_onset > current_end:
                current_end = comp.end_onset
        else:
            groups.append(current)
            current = [comp]
            current_start = comp.start_onset
            current_end = comp.end_onset
    if current:
        groups.append(current)

    moments: list[MicroMoment] = []
    for idx, group in enumerate(groups):
        # Derive moment span
        start = min(c.start_onset for c in group)
        end = max(c.end_onset for c in group)
        # keep short: if >1 measure (4 quarters), we already split; but still ensure capped to 4
        if end - start > Fraction(4):
            end = start + Fraction(4)
        measure_numbers: tuple[str, ...] = tuple(sorted({m for c in group for m in c.measure_numbers}, key=lambda x: (0, int(x)) if x.isdigit() else (1, x)))
        if not measure_numbers:
            # fallback to first component's measure numbers
            measure_numbers = group[0].measure_numbers
        beat_start = next((c.beat_start for c in group if c.beat_start is not None), None)
        beat_end = next((c.beat_end for c in reversed(group) if c.beat_end is not None), None)
        musical_object_ids = tuple(sorted({c.parent_object_id for c in group}))
        component_ids = tuple(c.component_id for c in sorted(group, key=lambda x: x.component_id))
        primary_types = tuple(sorted({c.component_type for c in group})[:3])
        related_dims = tuple(sorted({d for c in group for d in c.related_dimensions})[:4])
        evidence_ids = tuple(dict.fromkeys(eid for c in group for eid in c.evidence_event_ids))
        confidence = round(sum(c.confidence for c in group) / len(group), 3) if group else 0.5
        # Summary generation
        hand = group[0].hand or "both hands"
        # Determine summary template
        primary = primary_types[0] if primary_types else group[0].component_type
        # beat clause
        beat_clause = f" on beat {beat_start}" if beat_start is not None else ""
        # measure clause
        meas_clause = f"measure {measure_numbers[0]}" if measure_numbers else "span"
        # Map primary to human phrase
        if primary in ("hand_relocation", "leap_interval", "launch_note", "target_chord", "landing_beat"):
            summary = f"{hand} bass-to-chord relocation{beat_clause} ({meas_clause})"
            label = "Bass-to-chord relocation"
        elif primary in ("interval_path", "harmonic_collection", "bass_anchor", "upper_chord_landing", "accompaniment_role"):
            # broken chord pattern
            if any(c.component_type == "pattern_cycle" for c in group) or any("pattern_break" in c.component_type for c in group) or len(group) >=3:
                summary = f"broken-chord pattern changes after two repetitions ({meas_clause})"
                label = "Broken-chord pattern change"
            else:
                summary = f"{hand} broken-chord interval path{beat_clause} ({meas_clause})"
                label = "Broken-chord interval path"
        elif primary in ("melody_layer", "accompaniment_layer", "onset_alignment", "register_separation"):
            summary = f"{hand} melody enters over accompaniment ({meas_clause})"
            label = "Melody over accompaniment"
        elif primary in ("step_pattern", "direction", "start_anchor", "thumb_crossing_candidate"):
            summary = f"{hand} scalar run {primary}{beat_clause} ({meas_clause})"
            label = "Scalar run moment"
        elif primary in ("rhythm_cell", "repetition_count", "break_point"):
            summary = f"{hand} rhythm cell repetition{beat_clause} ({meas_clause})"
            label = "Rhythm cell moment"
        else:
            summary = f"{hand} {primary} moment{beat_clause} ({meas_clause})"
            label = primary.replace("_", " ").title()
        # Caveats if grouping combines low confidence
        caveats = tuple(sorted({cave for c in group for cave in c.caveats})[:3])
        moment_id = f"mm:{idx}:{str(start)}:{primary}"
        moments.append(MicroMoment(
            moment_id=moment_id,
            label=label,
            start_onset=start,
            end_onset=end,
            measure_numbers=measure_numbers,
            beat_start=beat_start,
            beat_end=beat_end,
            musical_object_ids=musical_object_ids,
            component_ids=component_ids,
            primary_component_types=primary_types,
            related_dimensions=related_dims,
            evidence_event_ids=evidence_ids,
            confidence=float(max(0.0, min(1.0, confidence))),
            summary=summary,
            caveats=caveats,
        ))
    # deterministic ordering by start_onset then component_id (already)
    moments.sort(key=lambda m: (m.start_onset, m.moment_id))
    return tuple(moments)

