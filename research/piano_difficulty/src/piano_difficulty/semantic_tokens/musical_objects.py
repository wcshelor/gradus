"""Detectors for expanded musical object catalog.

Deterministic, no LLM. Every emitted object has non-empty evidence_event_ids.
Confidence lowered when evidence partial; caveats explain.

Keeps logic out of gestures.py to avoid churn. Reuses derived tokens + gestures
where possible and falls back to direct ScoreEvent analysis.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any

from .models import CATALOG_OBJECT_IDS, OBJECT_DIMENSIONS, OBJECT_LABELS, DerivedToken, Gesture, MusicalObject, ScoreEvent


def _measure_sort_key(value: str) -> tuple[int, str | int]:
    try:
        return (0, int(value))
    except Exception:
        return (1, value)


def _merge_measure_numbers(
    items: list[Any],
) -> tuple[int | None, int | None, tuple[str, ...]]:
    mins: list[int] = []
    maxs: list[int] = []
    seen: dict[str, None] = {}
    for it in items:
        if getattr(it, "measure_start", None) is not None:
            mins.append(int(it.measure_start))  # type: ignore[arg-type]
        if getattr(it, "measure_end", None) is not None:
            maxs.append(int(it.measure_end))  # type: ignore[arg-type]
        for mn in getattr(it, "measure_numbers", ()):
            if mn not in seen and mn is not None:
                seen[str(mn)] = None
    # also handle ScoreEvent items (measure_index vs measure_start)
    # ScoreEvent has measure_index, not measure_start, fallback handled by caller mixing
    nums = tuple(sorted(seen.keys(), key=_measure_sort_key)) if seen else ()
    return (min(mins) if mins else None, max(maxs) if maxs else None, nums)


def _events_by_hand(events: list[ScoreEvent], hand: str | None) -> list[ScoreEvent]:
    if hand is None:
        return [e for e in events if not e.is_rest]
    return [e for e in events if e.hand == hand and not e.is_rest]


def _group_by_onset(events: list[ScoreEvent]) -> dict[Fraction, list[ScoreEvent]]:
    g: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        g[e.onset].append(e)
    return g


def _median_pitch(events_at_onset: list[ScoreEvent]) -> int | None:
    mids = sorted([e.pitch_midi for e in events_at_onset if e.pitch_midi is not None])
    if not mids:
        return None
    return mids[len(mids) // 2]


def _rep_sequence(events: list[ScoreEvent]) -> list[tuple[Fraction, int, tuple[str, ...], int | None, str | None, Fraction, Fraction]]:
    """Per-onset reps: (onset, median_midi, event_ids, measure_index, measure_number, end, duration)."""
    if not events:
        return []
    g = _group_by_onset(events)
    reps: list[tuple[Fraction, int, tuple[str, ...], int | None, str | None, Fraction, Fraction]] = []
    for onset in sorted(g.keys()):
        evts = g[onset]
        med = _median_pitch(evts)
        if med is None:
            continue
        reps.append(
            (
                onset,
                med,
                tuple(e.event_id for e in evts),
                evts[0].measure_index,
                evts[0].measure_number,
                max(e.end for e in evts),
                evts[0].duration,
            )
        )
    return reps


def _make_object(
    object_id: str,
    hand: str | None,
    start: Fraction,
    end: Fraction,
    measure_start: int | None,
    measure_end: int | None,
    measure_numbers: tuple[str, ...],
    evidence_event_ids: tuple[str, ...],
    token_ids: tuple[str, ...],
    gesture_ids: tuple[str, ...],
    confidence: float,
    payload_extra: dict[str, Any],
    caveats: tuple[str, ...],
    heuristic: str,
) -> MusicalObject | None:
    if not evidence_event_ids:
        return None
    # clamp confidence
    conf = max(0.0, min(1.0, float(confidence)))
    # deduplicate evidence preserving order
    ev = tuple(dict.fromkeys(evidence_event_ids))
    if not ev:
        return None
    payload: dict[str, Any] = {
        "related_dimensions": list(OBJECT_DIMENSIONS.get(object_id, ())),
        "detection_heuristic": heuristic,
    }
    payload.update(payload_extra)
    return MusicalObject(
        object_id=object_id,
        kind=object_id,
        label=OBJECT_LABELS[object_id],
        hand=hand,
        start_onset=start,
        end_onset=end,
        measure_start=measure_start,
        measure_end=measure_end,
        measure_numbers=measure_numbers,
        evidence_event_ids=ev,
        token_ids=tuple(token_ids),
        gesture_ids=tuple(gesture_ids),
        confidence=conf,
        payload=payload,
        caveats=tuple(caveats),
    )


# ---------------------------------------------------------------------------
# Slice 1 — priority
# ---------------------------------------------------------------------------

def _detect_scalar_runs(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # Reuse scalar_run gestures when available (high confidence)
    for g in gestures:
        if g.kind == "scalar_run":
            direction = g.payload.get("direction")
            oid = "ascending_scalar_run" if direction == "up" else "descending_scalar_run" if direction == "down" else None
            if oid is None:
                # infer from token intervals if available
                continue
            obj = _make_object(
                oid, g.hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                g.evidence_event_ids, g.token_ids, (g.gesture_id,), 0.85,
                {"steps": g.payload.get("steps"), "direction": direction, "source": "gesture_scalar_run"}, (), "scalar_run_gesture")
            if obj:
                out.append(obj)
    # Also detect directly from ScoreEvent melodic intervals if gesture missing
    for hand in ("right", "left"):
        seq = _rep_sequence(_events_by_hand(events, hand))
        if len(seq) < 4:
            continue
        intervals = [seq[i + 1][1] - seq[i][1] for i in range(len(seq) - 1)]
        # Find runs of 1-2 semitone same direction length >=3 intervals
        run_start = None
        run_dir = None
        for idx, iv in enumerate(intervals):
            abs_iv = abs(iv)
            cur_dir = "up" if iv > 0 else "down" if iv < 0 else "flat"
            is_step = 1 <= abs_iv <= 2 and iv != 0
            if is_step and (run_dir is None or cur_dir == run_dir):
                if run_start is None:
                    run_start = idx
                    run_dir = cur_dir
            else:
                if run_start is not None:
                    run_len = idx - run_start
                    if run_len >= 3 and run_dir in ("up", "down"):
                        start_onset = seq[run_start][0]
                        end_onset = seq[idx][0]
                        # Check if already covered by gesture
                        already = any(o.start_onset == start_onset and o.end_onset == end_onset and o.hand == hand for o in out)
                        if not already:
                            ev_ids = tuple(eid for k in range(run_start, idx + 1) for eid in seq[k][2])
                            ms = seq[run_start][3]
                            me = seq[idx][3]
                            mns = tuple(sorted({str(seq[k][4]) for k in range(run_start, idx + 1) if seq[k][4]}, key=_measure_sort_key))
                            oid2 = "ascending_scalar_run" if run_dir == "up" else "descending_scalar_run"
                            obj2 = _make_object(oid2, hand, start_onset, end_onset, ms, me, mns, ev_ids, (), (), 0.72,
                                                {"steps": run_len + 1, "direction": run_dir, "interval_pattern": tuple(intervals[run_start:idx])}, (), "melodic_step_run")
                            if obj2:
                                out.append(obj2)
                run_start = None
                run_dir = None
                if is_step:
                    run_start = idx
                    run_dir = cur_dir
        # tail run
        if run_start is not None:
            run_len = len(intervals) - run_start
            if run_len >= 3 and run_dir in ("up", "down"):
                start_onset = seq[run_start][0]
                end_onset = seq[-1][0]
                already = any(o.start_onset == start_onset and o.end_onset == end_onset and o.hand == hand for o in out)
                if not already:
                    ev_ids = tuple(eid for k in range(run_start, len(seq)) for eid in seq[k][2])
                    ms = seq[run_start][3]
                    me = seq[-1][3]
                    mns = tuple(sorted({str(seq[k][4]) for k in range(run_start, len(seq)) if seq[k][4]}, key=_measure_sort_key))
                    oid2 = "ascending_scalar_run" if run_dir == "up" else "descending_scalar_run"
                    obj2 = _make_object(oid2, hand, start_onset, end_onset, ms, me, mns, ev_ids, (), (), 0.72,
                                        {"steps": run_len + 1, "direction": run_dir, "interval_pattern": tuple(intervals[run_start:])}, (), "melodic_step_run")
                    if obj2:
                        out.append(obj2)
    # Additional: LH fast directional runs with larger steps (for mm.27-28 promotion)
    # Dense, quick, consistently directed runs (e.g., 7,5,4 steps) should still be represented as scalar-like
    # so they can outrank low-confidence leap_to_chord in promotion. This is more permissive than strict 1-2 step scalar.
    for hand in ("left",):
        seq = _rep_sequence(_events_by_hand(events, hand))
        if len(seq) < 4:
            continue
        intervals = [seq[i + 1][1] - seq[i][1] for i in range(len(seq) - 1)]
        # Look for 4-note ascending/descending segments with intervals 2-7 and high density (avoid 3-note false positives like 25-26)
        for start_idx in range(len(seq) - 3):
            for win_len in (4,):  # 4 notes -> 3 intervals
                if start_idx + win_len >= len(seq):
                    continue
                window_intervals = intervals[start_idx:start_idx + win_len - 1]
                if not window_intervals:
                    continue
                # All intervals same direction and 2-7 semitones (allows fast run, not just 1-2)
                dirs = ["up" if iv > 0 else "down" if iv < 0 else "flat" for iv in window_intervals]
                if len(set(dirs)) != 1 or dirs[0] not in ("up", "down"):
                    continue
                if not all(2 <= abs(iv) <= 7 for iv in window_intervals):
                    continue
                # Check density: at least 3 notes per quarter in this window
                start_onset = seq[start_idx][0]
                end_onset = seq[start_idx + win_len - 1][0]
                duration = end_onset - start_onset
                # Avoid division by zero; use notes per quarter
                notes_per_quarter = win_len / float(duration) if duration > 0 else 0
                if notes_per_quarter < 2.5:  # need dense
                    continue
                # Check if already covered by a strict scalar run
                already = any(o.hand == hand and abs(o.start_onset - start_onset) < Fraction(1, 4) and o.object_id in ("ascending_scalar_run", "descending_scalar_run") for o in out)
                if already:
                    continue
                mns = tuple(sorted({str(seq[k][4]) for k in range(start_idx, start_idx + win_len) if seq[k][4]}, key=_measure_sort_key))
                ms = seq[start_idx][3]
                me = seq[start_idx + win_len - 1][3]
                ev_ids = tuple(eid for k in range(start_idx, start_idx + win_len) for eid in seq[k][2])
                oid2 = "ascending_scalar_run" if dirs[0] == "up" else "descending_scalar_run"
                # Slightly lower confidence than strict scalar, but high enough to be promoted over weak leaps
                obj2 = _make_object(oid2, hand, start_onset, end_onset, ms, me, mns, ev_ids, (), (), 0.78,
                                    {"steps": win_len, "direction": dirs[0], "interval_pattern": tuple(window_intervals), "fast_run": True, "notes_per_quarter": round(notes_per_quarter, 2)}, ("fast_run_permissive_intervals",), "fast_directional_run")
                if obj2:
                    out.append(obj2)
                    # Only emit one fast run per dense passage to avoid flooding; break after first in this window
                    break
            # limit total fast runs
            if len([o for o in out if o.hand == "left" and o.payload.get("fast_run")]) >= 3:
                break
    return out


def _detect_melody_with_accompaniment(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture], score_ir: Any | None = None) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    for g in gestures:
        if g.kind == "melody_with_accompaniment":
            obj = _make_object("melody_with_accompaniment", g.hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                               g.evidence_event_ids, g.token_ids, (g.gesture_id,), float(g.confidence), {"source": "gesture_melody_with_accompaniment"}, (), "gesture_melody_accompaniment")
            if obj:
                out.append(obj)
    # fallback: check onset_alignment tokens paired with melodic_interval right hand
    alignments = [t for t in tokens if t.kind == "onset_alignment"]
    rh_mel = [t for t in tokens if t.hand == "right" and t.kind == "melodic_interval"]
    for al in alignments:
        win = [t for t in rh_mel if al.start_onset - Fraction(1) <= t.start_onset <= al.end_onset + Fraction(1)]
        if win and not any(o.start_onset == min(al.start_onset, win[0].start_onset) for o in out):
            ms, me, mns = _merge_measure_numbers([al] + win[:2])  # type: ignore[arg-type]
            ev = tuple(dict.fromkeys(list(al.evidence_event_ids) + [eid for t in win[:3] for eid in t.evidence_event_ids]))
            tids = tuple([al.token_id] + [t.token_id for t in win[:3]])
            start = min(al.start_onset, min(t.start_onset for t in win))
            end = max(al.end_onset, max(t.end_onset for t in win))
            obj = _make_object("melody_with_accompaniment", None, start, end, ms, me, mns, ev, tids, (), 0.68, {"aligned_onset": str(al.start_onset)}, (), "alignment_plus_melodic")
            if obj:
                out.append(obj)
    return out


def _detect_melody_voicing_over_accompaniment(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture], score_ir: Any | None = None) -> list[MusicalObject]:
    # Conservative: same as melody_with_accompaniment but requires balance cue (higher salience)
    objs = _detect_melody_with_accompaniment(events, tokens, gestures, score_ir)
    out: list[MusicalObject] = []
    for o in objs:
        # reuse but with different ID and slightly lower confidence, require extra evidence: right hand melody + left support
        # Only emit if we have both hands evidence
        has_both = any(e.hand == "right" for e in events if e.event_id in o.evidence_event_ids) and any(e.hand == "left" for e in events if e.event_id in o.evidence_event_ids)
        if has_both or o.hand is None:
            out.append(_make_object("melody_voicing_over_accompaniment", o.hand, o.start_onset, o.end_onset, o.measure_start, o.measure_end, o.measure_numbers,
                                    o.evidence_event_ids, o.token_ids, o.gesture_ids, max(0.45, float(o.confidence) * 0.85),
                                    {"source_object": o.object_id, "voicing": "melody_prominent"}, ("voicing_inferred_from_texture" if not has_both else ()), "melody_voicing") or o)
    return [x for x in out if x is not None]


def _detect_broken_arpeggiated(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    for g in gestures:
        if g.kind == "arpeggio":
            # broken_chord_accompaniment vs arpeggiated_accompaniment distinction by span/hand role
            span = g.payload.get("span_semitones") or 0
            # Use hand role heuristic: if left hand accompaniment -> broken
            # Both get emitted as separate objects sharing evidence (allowed)
            for oid in ("broken_chord_accompaniment", "arpeggiated_accompaniment"):
                # arpeggiated requires wider span or more notes
                if oid == "arpeggiated_accompaniment" and (g.payload.get("interval_pattern") is None and span < 7):
                    # still emit but lower confidence
                    conf = 0.55
                    caveat = ("span_not_wide",)
                else:
                    conf = float(g.confidence) * (0.88 if oid == "broken_chord_accompaniment" else 0.82)
                    caveat = ()
                obj = _make_object(oid, g.hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                                   g.evidence_event_ids, g.token_ids, (g.gesture_id,), conf,
                                   {"type": g.payload.get("type"), "interval_pattern": g.payload.get("interval_pattern") or g.payload.get("interval_pattern")}, caveat, "arpeggio_gesture")
                if obj:
                    out.append(obj)
    # Direct from melodic intervals of 3-4 semitones (thirds)
    for hand in ("right", "left"):
        mels = sorted([t for t in tokens if t.hand == hand and t.kind == "melodic_interval"], key=lambda t: t.start_onset)
        run: list[DerivedToken] = []
        for tok in mels:
            iv = abs(tok.payload.get("interval_semitones", 0))
            if iv in (3, 4):
                run.append(tok)
            else:
                if len(run) >= 3 and not any(o.hand == hand and abs(o.start_onset - run[0].start_onset) < Fraction(1) for o in out):
                    ms, me, mns = _merge_measure_numbers(run)  # type: ignore[arg-type]
                    ev = tuple(eid for t in run for eid in t.evidence_event_ids)
                    tids = tuple(t.token_id for t in run)
                    start = run[0].start_onset
                    end = run[-1].end_onset
                    obj = _make_object("broken_chord_accompaniment", hand, start, end, ms, me, mns, ev, tids, (), 0.58, {"interval_pattern": tuple(t.payload.get("interval_semitones") for t in run)}, ("heuristic_only_no_harmony",), "melodic_third_run")
                    if obj:
                        out.append(obj)
                run = []
        if len(run) >= 3 and not any(o.hand == hand and abs(o.start_onset - run[0].start_onset) < Fraction(1) for o in out):
            ms, me, mns = _merge_measure_numbers(run)  # type: ignore[arg-type]
            ev = tuple(eid for t in run for eid in t.evidence_event_ids)
            tids = tuple(t.token_id for t in run)
            start = run[0].start_onset
            end = run[-1].end_onset
            obj = _make_object("broken_chord_accompaniment", hand, start, end, ms, me, mns, ev, tids, (), 0.58, {"interval_pattern": tuple(t.payload.get("interval_semitones") for t in run)}, ("heuristic_only_no_harmony",), "melodic_third_run")
            if obj:
                out.append(obj)
    return out


def _detect_alberti_bass(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture], score_ir: Any | None = None) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # Alberti: left hand 4-note cells low-high-middle-high or similar triadic pattern repeated
    left_events = sorted(_events_by_hand(events, "left"), key=lambda e: e.onset)
    if len(left_events) < 8:
        return out
    # Group by onset: alberti has single notes per onset (not chords)
    g = _group_by_onset(left_events)
    onsets = sorted(g.keys())
    # Need single-note onsets (filter chord onsets out)
    single_onsets: list[tuple[Fraction, ScoreEvent]] = []
    for o in onsets:
        evts = g[o]
        if len(evts) == 1 and evts[0].pitch_midi is not None:
            single_onsets.append((o, evts[0]))
    if len(single_onsets) < 8:
        return out
    # Sliding window of 8 notes (2 cycles) look for repeating 4-cycle of pitches
    for i in range(len(single_onsets) - 7):
        window = single_onsets[i:i+8]
        pitches = [e.pitch_midi for _, e in window]
        # Check for 4-note repeating pattern: pitches[0:4] == pitches[4:8] or same harmony set
        # Harmony set: same 3 pitch classes rotated
        pcs = [{p % 12 for p in pitches[0:4]}, {p % 12 for p in pitches[4:8]}]
        if pcs[0] == pcs[1] and len(pcs[0]) == 3:
            # Check low-high-middle-high ordering: validate low is lowest, high highest
            # For alberti typical: low (bass) lowest, middle middle, high highest
            # Simple: pitch[0] is lowest of first 4, pitch[2] middle
            first_four = pitches[0:4]
            if min(first_four) == first_four[0] and max(first_four) == first_four[1]:
                # plausible alberti
                start = window[0][0]
                end = window[-1][1].end
                ev_ids = tuple(e.event_id for _, e in window)
                ms = min(e.measure_index for _, e in window if e.measure_index is not None)
                me = max(e.measure_index for _, e in window if e.measure_index is not None)
                mns = tuple(sorted({str(e.measure_number) for _, e in window if e.measure_number}, key=_measure_sort_key))
                obj = _make_object("alberti_bass", "left", start, end, ms, me, mns, ev_ids, (), (), 0.62,
                                   {"pattern": "low-high-middle-high", "harmony_pcs": tuple(sorted(pcs[0]))}, (), "alberti_four_cycle")
                if obj:
                    out.append(obj)
                    # only one per overlapping window to avoid flood; break after first to keep deterministic but allow spaced repeats
                    # continue scanning after this window
                    # skip ahead 4
                    # we don't break; but dedupe by not overlapping same start
    # Deduplicate overlapping alberti objects (keep earliest)
    if len(out) > 3:
        out = sorted(out, key=lambda o: o.start_onset)[:3]
    return out


def _detect_leap_to_chord_and_landing(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # Use bass_to_chord gestures for leap_to_chord high confidence — but only if gesture represents a genuine difficult leap
    for g in gestures:
        if g.kind == "bass_to_chord":
            movement = g.payload.get("movement")
            # movement may be None or small; require at least 7 semitones for true leap_to_chord
            try:
                mv = abs(int(movement)) if movement is not None else None
            except Exception:
                mv = None
            # Check target chord size from gesture's chord payload or from evidence: look up chord token span/note_count via gesture evidence is not directly available, so check gesture confidence and movement
            # Require movement >=7; stricter for promotional confidence
            if mv is not None and mv < 7:
                # Still allow chord_landing from this gesture, but not leap_to_chord
                obj2 = _make_object("chord_landing", g.hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                                    g.evidence_event_ids, g.token_ids, (g.gesture_id,), float(g.confidence) * 0.82, {"chord_shape": g.payload.get("chord_shape")}, (), "bass_to_chord_as_landing")
                if obj2:
                    out.append(obj2)
                continue
            obj = _make_object("leap_to_chord", g.hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                               g.evidence_event_ids, g.token_ids, (g.gesture_id,), float(g.confidence) * 0.9,
                               {"movement": g.payload.get("movement"), "chord_shape": g.payload.get("chord_shape")}, (), "bass_to_chord_gesture")
            if obj:
                out.append(obj)
            # chord_landing also from same gesture
            obj2 = _make_object("chord_landing", g.hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                                g.evidence_event_ids, g.token_ids, (g.gesture_id,), float(g.confidence) * 0.82, {"chord_shape": g.payload.get("chord_shape")}, (), "bass_to_chord_as_landing")
            if obj2:
                out.append(obj2)
    # Direct leap + chord detection per hand — only genuine leaps and real chords
    for hand in ("right", "left"):
        leaps = [t for t in tokens if t.hand == hand and t.kind == "leap" and abs(t.payload.get("interval_semitones", 0) or 0) >= 7]
        chords = [t for t in tokens if t.hand == hand and t.kind in ("chord_shape", "harmonic_simultaneity") and (t.payload.get("note_count", 0) >= 3 or t.payload.get("span_semitones", 0) >= 7)]
        for leap in leaps:
            for chord in chords:
                gap = chord.start_onset - leap.end_onset
                if chord.start_onset >= leap.end_onset and gap <= Fraction(1):
                    # Stricter window for minimal leap (7 semitones)
                    if abs(leap.payload.get("interval_semitones", 0) or 0) == 7 and gap > Fraction(1, 2):
                        continue
                    # avoid duplicates already covered
                    if any(o.hand == hand and o.start_onset == leap.start_onset and "leap_to_chord" == o.object_id for o in out):
                        continue
                    ms, me, mns = _merge_measure_numbers([leap, chord])  # type: ignore[arg-type]
                    ev = tuple(dict.fromkeys(list(leap.evidence_event_ids) + list(chord.evidence_event_ids)))
                    tids = (leap.token_id, chord.token_id)
                    obj = _make_object("leap_to_chord", hand, leap.start_onset, chord.end_onset, ms, me, mns, ev, tids, (), 0.62,
                                       {"movement_semitones": leap.payload.get("interval_semitones") or leap.payload.get("movement_semitones") or leap.payload.get("shift_semitones"),
                                        "span": chord.payload.get("span_semitones")}, ("heuristic_only",), "leap_plus_chord")
                    if obj:
                        out.append(obj)
                # chord_landing: chord preceded by any melodic movement within 2 quarters
                # handled below broader
        # chord_landing generic: any chord with prior movement within 2 quarters
        chord_tokens = chords
        move_tokens = [t for t in tokens if t.hand == hand and t.kind in ("melodic_interval", "leap", "hand_movement", "register_shift")]
        for ch in chord_tokens:
            has_prior = any(t.end_onset <= ch.start_onset and ch.start_onset - t.end_onset <= Fraction(2) for t in move_tokens)
            if has_prior and not any(o.hand == hand and o.start_onset == ch.start_onset and o.object_id == "chord_landing" for o in out):
                # For landing, span is chord alone but evidence includes prior movement for causality? Keep evidence as chord alone to stay concrete
                obj2 = _make_object("chord_landing", hand, ch.start_onset, ch.end_onset, ch.measure_start, ch.measure_end, ch.measure_numbers,
                                    ch.evidence_event_ids, (ch.token_id,), (), 0.58, {"span_semitones": ch.payload.get("span_semitones"), "note_count": ch.payload.get("note_count"), "preceded_by_movement": True}, (), "chord_preceded_by_movement")
                if obj2:
                    out.append(obj2)
    return out


def _detect_repeated_position_and_rhythm(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # repeated_position_pattern from pattern_repetition where span limited
    for t in tokens:
        if t.kind == "pattern_repetition":
            span = t.payload.get("span_semitones", 0) if "span_semitones" in t.payload else None
            # Use chord_shape span if available; otherwise hand_movement span
            # Heuristic: repeated_position_pattern requires stable hand span/register (not wide shift)
            # Check associated chord shapes: if pattern intervals repeat within stable span
            # We can map pattern_repetition directly but with narrower confidence
            # Use leap tokens to check stability: no large leaps inside pattern span
            is_stable = True
            # Check if any leap inside pattern span for same hand
            for leap in [x for x in tokens if x.hand == t.hand and x.kind == "leap" and x.start_onset >= t.start_onset and x.end_onset <= t.end_onset]:
                if abs(leap.payload.get("interval_semitones", 0)) >= 7:
                    is_stable = False
            if is_stable:
                obj = _make_object("repeated_position_pattern", t.hand, t.start_onset, t.end_onset, t.measure_start, t.measure_end, t.measure_numbers,
                                   t.evidence_event_ids, (t.token_id,), (), float(t.confidence) * 0.78,
                                   {"pattern_intervals": t.payload.get("pattern_intervals"), "total_occurrences": t.payload.get("total_occurrences")}, (), "pattern_repetition_stable")
                if obj:
                    out.append(obj)
    # also from accompaniment_pattern gestures
    for g in gestures:
        if g.kind == "accompaniment_pattern":
            obj = _make_object("repeated_position_pattern", g.hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                               g.evidence_event_ids, g.token_ids, (g.gesture_id,), float(g.confidence) * 0.72,
                               {"pattern_intervals": g.payload.get("pattern_intervals")}, (), "accompaniment_pattern")
            if obj:
                out.append(obj)
    # repeated_rhythm_cell: look for duration/onset patterns repeated
    for hand in ("right", "left", None):
        reps = _rep_sequence(_events_by_hand(events, hand) if hand is not None else [e for e in events if not e.is_rest])
        if len(reps) < 4:
            continue
        # Build duration cells (duration quarters as fraction)
        durs = [r[6] for r in reps]
        # Look for repeating 2-3 duration patterns
        for pat_len in (2, 3):
            for start in range(len(durs) - pat_len * 2 + 1):
                pat = tuple(durs[start:start + pat_len])
                # check next occurrence
                if tuple(durs[start + pat_len:start + pat_len * 2]) == pat:
                    # Found repeated rhythm cell
                    start_onset = reps[start][0]
                    end_onset = reps[start + pat_len * 2 - 1][0] + reps[start + pat_len * 2 - 1][6] if start + pat_len * 2 - 1 < len(reps) else reps[start + pat_len * 2 - 1][0] + Fraction(1)
                    # measure numbers
                    mns = tuple(sorted({str(reps[k][4]) for k in range(start, start + pat_len * 2) if reps[k][4]}, key=_measure_sort_key))
                    ms = min((reps[k][3] for k in range(start, start + pat_len * 2) if reps[k][3] is not None), default=None)
                    me = max((reps[k][3] for k in range(start, start + pat_len * 2) if reps[k][3] is not None), default=None)
                    ev_ids = tuple(eid for k in range(start, start + pat_len * 2) for eid in reps[k][2])
                    obj = _make_object("repeated_rhythm_cell", hand, start_onset, end_onset, ms, me, mns, ev_ids, (), (), 0.62,
                                       {"rhythm_pattern": tuple(str(d) for d in pat), "occurrences": 2}, (), "duration_cell_repeat")
                    if obj and not any(o.start_onset == start_onset and o.hand == hand and o.object_id == "repeated_rhythm_cell" for o in out):
                        out.append(obj)
                    break
            if any(o.hand == hand and o.object_id == "repeated_rhythm_cell" for o in out):
                break
    return out


def _detect_syncopation(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture], score_ir: Any | None = None) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # Heuristic: onsets on weak beats (e.g., beat not 0) with held ties across strong beats, or articulation accent on weak beat
    for e in events:
        if e.is_rest or e.beat is None:
            continue
        # beat 0 is strong; syncopation if onset at 0.5, 1.5 etc inside measure and duration crosses beat
        # Use time_signature to determine strong beats: for 4/4 strong at 0,2; for 3/4 at 0
        ts = e.time_signature or "4/4"
        try:
            beats_per = int(ts.split("/")[0]) if "/" in ts else 4
        except Exception:
            beats_per = 4
        beat_frac = e.beat
        # weak if not on 0 mod 1
        is_off = (beat_frac % 1 != 0)
        # accent articulation on weak beat
        has_accent = any(a.lower() in ("accent", "strong-accent", ">", "^") for a in e.articulation)
        tied = e.tie_merged
        # duration crossing barline proxy: end beyond measure end? Use measure boundary not directly available; use beat + duration > beats_per
        crosses = (beat_frac + e.duration) > beats_per if beats_per else False
        if (is_off and (tied or crosses or has_accent or e.duration >= Fraction(1, 2))) or (has_accent and is_off):
            # Emit per-event but group nearby
            # Group consecutive syncopated events within 1 quarter into one object
            if out and out[-1].hand == e.hand and e.onset - out[-1].end_onset <= Fraction(1) and e.measure_number == out[-1].measure_numbers[-1]:
                # extend existing
                prev = out[-1]
                new_ev = tuple(dict.fromkeys(list(prev.evidence_event_ids) + [e.event_id]))
                new_end = max(prev.end_onset, e.end)
                # recreate
                out[-1] = _make_object("syncopation", prev.hand, prev.start_onset, new_end, prev.measure_start, prev.measure_end, prev.measure_numbers, new_ev, prev.token_ids, prev.gesture_ids, max(0.4, float(prev.confidence) * 0.96), {"syncopation_count": len(new_ev)}, (), "syncopation_extend") or prev
            else:
                obj = _make_object("syncopation", e.hand, e.onset, e.end, e.measure_index, e.measure_index, (e.measure_number,) if e.measure_number else (), (e.event_id,), (), (), 0.58,
                                   {"beat": str(e.beat), "duration": str(e.duration), "articulation": list(e.articulation)}, ("heuristic_weak_beat" if not has_accent else ()), "syncopation_single")
                if obj:
                    out.append(obj)
    # Limit
    if len(out) > 6:
        out = out[:6]
    return out


# ---------------------------------------------------------------------------
# Slice 2 — remaining melodic
# ---------------------------------------------------------------------------

def _detect_stepwise_intervallic(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    for hand in ("right", "left"):
        reps = _rep_sequence(_events_by_hand(events, hand))
        if len(reps) < 4:
            continue
        intervals = [reps[i + 1][1] - reps[i][1] for i in range(len(reps) - 1)]
        # sliding windows of 4-8 notes
        for win_len in (4, 6, 8):
            for start in range(len(reps) - win_len + 1):
                window_intervals = intervals[start:start + win_len - 1]
                if not window_intervals:
                    continue
                steps = sum(1 for iv in window_intervals if abs(iv) <= 2)
                ratio = steps / len(window_intervals)
                start_onset = reps[start][0]
                end_onset = reps[start + win_len - 1][0]
                mns = tuple(sorted({str(reps[k][4]) for k in range(start, start + win_len) if reps[k][4]}, key=_measure_sort_key))
                ms = reps[start][3]
                me = reps[start + win_len - 1][3]
                ev = tuple(eid for k in range(start, start + win_len) for eid in reps[k][2])
                if ratio >= 0.7 and len(window_intervals) >= 3:
                    # stepwise_melody, but avoid duplicating scalar runs (which are directional)
                    # Check net contour not strongly directional? For stepwise we allow varied direction
                    obj = _make_object("stepwise_melody", hand, start_onset, end_onset, ms, me, mns, ev, (), (), 0.58, {"step_ratio": round(ratio, 2), "intervals": tuple(window_intervals[:6])}, (), "stepwise_window")
                    if obj and not any(o.hand == hand and o.start_onset == start_onset and o.object_id == "stepwise_melody" for o in out):
                        # avoid overlap with scalar runs already emitted
                        out.append(obj)
                elif ratio <= 0.3 and len(window_intervals) >= 3:
                    obj = _make_object("intervallic_melody", hand, start_onset, end_onset, ms, me, mns, ev, (), (), 0.58, {"step_ratio": round(ratio, 2), "intervals": tuple(window_intervals[:6])}, (), "intervallic_window")
                    if obj and not any(o.hand == hand and o.start_onset == start_onset and o.object_id == "intervallic_melody" for o in out):
                        out.append(obj)
                if len(out) > 8:
                    break
            if len(out) > 8:
                break
    # deduplicate keep earliest per hand per measure
    uniq: dict[tuple, MusicalObject] = {}
    for o in out:
        key = (o.object_id, o.hand, o.measure_numbers)
        if key not in uniq:
            uniq[key] = o
    return list(uniq.values())[:6]


def _detect_sequence(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # Look for pattern_repetition transposed by consistent offset (sequence)
    for t in tokens:
        if t.kind == "pattern_repetition":
            pat = t.payload.get("pattern_intervals")
            if not isinstance(pat, (tuple, list)) or len(pat) < 2:
                continue
            # Find another repetition with same pattern but offset in pitch (check surrounding reps)
            # Use reps sequence to estimate transposition
            hand = t.hand
            reps = _rep_sequence(_events_by_hand(events, hand) if hand in ("right", "left") else [e for e in events if not e.is_rest])
            # Find positions of pattern: we already have occurrence indices in payload? occurrence gives start index
            # Heuristic: if pattern occurs at least twice with consistent pitch offset, it's a sequence
            # For simplicity, if pattern_repetition confidence high and at least 2 occurrences, emit sequence
            occ = t.payload.get("total_occurrences", 1)
            if occ >= 2:
                obj = _make_object("sequence", hand, t.start_onset, t.end_onset, t.measure_start, t.measure_end, t.measure_numbers,
                                   t.evidence_event_ids, (t.token_id,), (), 0.62, {"pattern_intervals": pat, "occurrences": occ}, (), "pattern_repetition_as_sequence")
                if obj:
                    out.append(obj)
    # Direct detection via interval groups: look for repeated interval pattern transposed
    for hand in ("right", "left"):
        reps = _rep_sequence(_events_by_hand(events, hand))
        if len(reps) < 6:
            continue
        intervals = [reps[i + 1][1] - reps[i][1] for i in range(len(reps) - 1)]
        # Look for pattern length 2-3 repeating with consistent offset (transposition)
        for pat_len in (2, 3):
            for start in range(len(intervals) - pat_len * 2 + 1):
                pat1 = tuple(intervals[start:start + pat_len])
                pat2 = tuple(intervals[start + pat_len:start + pat_len * 2])
                if pat1 == pat2:
                    # Check pitch offset between start reps
                    offset = reps[start + pat_len][1] - reps[start][1]
                    if offset != 0 and abs(offset) <= 12:
                        start_onset = reps[start][0]
                        end_onset = reps[start + pat_len * 2][0]
                        mns = tuple(sorted({str(reps[k][4]) for k in range(start, start + pat_len * 2 + 1) if reps[k][4]}, key=_measure_sort_key))
                        ms = reps[start][3]
                        me = reps[start + pat_len * 2][3]
                        ev = tuple(eid for k in range(start, start + pat_len * 2 + 1) for eid in reps[k][2])
                        obj = _make_object("sequence", hand, start_onset, end_onset, ms, me, mns, ev, (), (), 0.55, {"pattern_intervals": pat1, "transposition": offset}, (), "interval_sequence")
                        if obj and not any(o.hand == hand and o.start_onset == start_onset for o in out):
                            out.append(obj)
                        break
            if out:
                break
    return out[:3]


def _detect_repeated_note_melody(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    for hand in ("right", "left"):
        reps = [t for t in tokens if t.hand == hand and t.kind == "repeated_note"]
        # Group consecutive repeats
        if not reps:
            continue
        # Check for repeated_note_figure gestures too
        for g in gestures:
            if g.kind == "repeated_note_figure" and g.hand == hand:
                obj = _make_object("repeated_note_melody", hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                                   g.evidence_event_ids, g.token_ids, (g.gesture_id,), 0.72, {"repeat_count": g.payload.get("repeat_count"), "pitch": g.payload.get("pitch")}, (), "repeated_note_gesture")
                if obj:
                    out.append(obj)
        # Direct per-hand repeated notes: need at least 2 consecutive repeats (3 notes)
        sorted_reps = sorted(reps, key=lambda t: t.start_onset)
        run: list[DerivedToken] = []
        for tok in sorted_reps:
            if not run or tok.start_onset == run[-1].end_onset:
                run.append(tok)
            else:
                if len(run) >= 2 and not any(o.hand == hand and o.start_onset == run[0].start_onset for o in out):
                    ms, me, mns = _merge_measure_numbers(run)  # type: ignore[arg-type]
                    ev = tuple(eid for t in run for eid in t.evidence_event_ids)
                    tids = tuple(t.token_id for t in run)
                    obj = _make_object("repeated_note_melody", hand, run[0].start_onset, run[-1].end_onset, ms, me, mns, ev, tids, (), 0.62, {"repeat_count": len(run) + 1}, (), "repeated_note_run")
                    if obj:
                        out.append(obj)
                run = [tok]
        if len(run) >= 2 and not any(o.hand == hand and o.start_onset == run[0].start_onset for o in out):
            ms, me, mns = _merge_measure_numbers(run)  # type: ignore[arg-type]
            ev = tuple(eid for t in run for eid in t.evidence_event_ids)
            tids = tuple(t.token_id for t in run)
            obj = _make_object("repeated_note_melody", hand, run[0].start_onset, run[-1].end_onset, ms, me, mns, ev, tids, (), 0.62, {"repeat_count": len(run) + 1}, (), "repeated_note_run")
            if obj:
                out.append(obj)
    return out


def _detect_chromatic_line(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    for hand in ("right", "left"):
        reps = _rep_sequence(_events_by_hand(events, hand))
        if len(reps) < 3:
            continue
        for i in range(len(reps) - 2):
            # Look for 3 consecutive semitone steps or frequent accidentals
            iv1 = reps[i + 1][1] - reps[i][1]
            iv2 = reps[i + 2][1] - reps[i + 1][1]
            has_acc = any(e.accidental not in (None, "natural") or (e.alter is not None and e.alter != 0) for e in _events_by_hand(events, hand) if e.event_id in reps[i][2] + reps[i + 1][2] + reps[i + 2][2])
            if (abs(iv1) == 1 and abs(iv2) == 1) or (abs(iv1) == 1 and has_acc) or (has_acc and abs(iv1) <= 2 and abs(iv2) <= 2):
                start = reps[i][0]
                end = reps[i + 2][0]
                mns = tuple(sorted({str(reps[k][4]) for k in (i, i + 1, i + 2) if reps[k][4]}, key=_measure_sort_key))
                ms = reps[i][3]
                me = reps[i + 2][3]
                ev = tuple(eid for k in (i, i + 1, i + 2) for eid in reps[k][2])
                obj = _make_object("chromatic_line", hand, start, end, ms, me, mns, ev, (), (), 0.60, {"intervals": (iv1, iv2), "has_accidental": has_acc}, ("heuristic_chromatic",) if not has_acc else (), "semitone_plus_accidental")
                if obj and not any(o.hand == hand and o.start_onset == start for o in out):
                    out.append(obj)
                    if len(out) >= 3:
                        break
        if len(out) >= 3:
            break
    return out


def _detect_ornamented_and_trill(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture], score_ir: Any | None = None) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # ornamented_melody: grace notes, short neighbor notes, trills/turn markings
    grace_events = [e for e in events if e.is_grace]
    for e in grace_events:
        # Each grace groups with following principal
        # Find next non-grace onset in same hand
        candidates = [x for x in events if x.hand == e.hand and not x.is_rest and x.onset > e.onset]
        if not candidates:
            continue
        nxt = min(candidates, key=lambda x: x.onset)
        if nxt.onset - e.onset <= Fraction(1):
            obj = _make_object("ornamented_melody", e.hand, e.onset, nxt.end, e.measure_index, nxt.measure_index,
                               tuple(sorted({str(e.measure_number), str(nxt.measure_number)})) if e.measure_number and nxt.measure_number else (e.measure_number or nxt.measure_number,) if e.measure_number or nxt.measure_number else (),
                               (e.event_id, nxt.event_id), (), (), 0.78, {"grace": True, "principal": nxt.pitch_midi}, (), "grace_note")
            if obj:
                out.append(obj)
        if len(out) >= 4:
            break
    # Articulation-based ornament: check articulation contains trill/mordent/turn
    for e in events:
        if any(a.lower() in ("trill", "mordent", "turn", "inverted-mordent", "shake") for a in e.articulation):
            obj = _make_object("turn_mordent_trill_like_figure", e.hand, e.onset, e.end, e.measure_index, e.measure_index, (e.measure_number,) if e.measure_number else (), (e.event_id,), (), (), 0.82,
                               {"articulation": list(e.articulation)}, (), "articulation_ornament")
            if obj:
                out.append(obj)
            obj2 = _make_object("ornamented_melody", e.hand, e.onset, e.end, e.measure_index, e.measure_index, (e.measure_number,) if e.measure_number else (), (e.event_id,), (), (), 0.75,
                                {"articulation": list(e.articulation)}, (), "articulation_ornament_melody")
            if obj2:
                out.append(obj2)
    # Heuristic neighbor motion: rapid alternation around principal (e.g., C-D-C or C-B-C within short duration)
    for hand in ("right", "left"):
        reps = _rep_sequence(_events_by_hand(events, hand))
        if len(reps) < 3:
            continue
        for i in range(len(reps) - 2):
            p0, p1, p2 = reps[i][1], reps[i + 1][1], reps[i + 2][1]
            # Neighbor: p2 == p0 and abs(p1-p0) <=2 and duration short (<1 quarter)
            dur_short = reps[i][6] <= Fraction(1, 2) and reps[i + 1][6] <= Fraction(1, 2)
            if p2 == p0 and abs(p1 - p0) in (1, 2) and dur_short:
                # Check grace not already covered
                if any(o.start_onset == reps[i][0] for o in out):
                    continue
                # For trill-like, need at least 3 alternations or short span; we emit with caveat if no explicit marking
                has_marking = any(e.event_id in reps[i][2] + reps[i+1][2] + reps[i+2][2] and any(a.lower() in ("trill","mordent","turn") for a in e.articulation) for e in events)
                caveats = () if has_marking else ("no_explicit_ornament_marking", "heuristic_neighbor_motion_only")
                conf = 0.72 if has_marking else 0.52
                start = reps[i][0]
                end = reps[i + 2][0] + reps[i + 2][6] if i + 2 < len(reps) else reps[i + 2][0] + Fraction(1, 4)
                mns = tuple(sorted({str(reps[k][4]) for k in (i, i+1, i+2) if reps[k][4]}, key=_measure_sort_key))
                ms = reps[i][3]
                me = reps[i+2][3]
                ev = tuple(eid for k in (i, i+1, i+2) for eid in reps[k][2])
                obj = _make_object("turn_mordent_trill_like_figure", hand, start, end, ms, me, mns, ev, (), (), conf, {"figure": "neighbor", "principal": p0, "neighbor": p1}, caveats, "neighbor_heuristic")
                if obj:
                    out.append(obj)
                obj2 = _make_object("ornamented_melody", hand, start, end, ms, me, mns, ev, (), (), min(0.55, conf+0.03), {"figure": "neighbor"}, caveats, "neighbor_melody")
                if obj2:
                    out.append(obj2)
                if len([x for x in out if x.object_id == "turn_mordent_trill_like_figure"]) >= 3:
                    break
    # Deduplicate and limit
    # Filter ornamented without strong evidence: if no grace and no marking and not neighbor, suppress (handled)
    # For turn-like, if still no grace and no short neighbor, suppress already
    return out[:6]


# ---------------------------------------------------------------------------
# Slice 3 — accompaniment/texture
# ---------------------------------------------------------------------------

def _detect_waltz_and_oom_pah(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # Group left hand onsets by measure
    left_events = sorted(_events_by_hand(events, "left"), key=lambda e: (e.measure_index or 0, e.onset))
    if not left_events:
        return out
    by_measure: dict[int, list[ScoreEvent]] = defaultdict(list)
    for e in left_events:
        if e.measure_index is not None:
            by_measure[e.measure_index].append(e)
    for mi, evts in by_measure.items():
        # Need time signature
        ts = next((e.time_signature for e in evts if e.time_signature), None)
        if ts is None:
            # try from events overall for that measure
            ts = next((e.time_signature for e in events if e.measure_index == mi and e.time_signature), None)
        evts_sorted = sorted(evts, key=lambda e: e.onset)
        onset_groups = _group_by_onset(evts_sorted)
        onsets_sorted = sorted(onset_groups.keys())
        if len(onsets_sorted) < 2:
            continue
        # Classify each onset as bass (single low note) vs chord (2+ notes)
        types: list[str] = []
        for o in onsets_sorted:
            g = onset_groups[o]
            mids = [e.pitch_midi for e in g if e.pitch_midi is not None]
            if len(g) == 1 and mids and mids[0] is not None:
                types.append("bass")
            elif len(g) >= 2:
                types.append("chord")
            else:
                types.append("other")
        # Waltz: 3/4 with bass then 2 chords
        if ts == "3/4" and len(types) >= 3 and types[0] == "bass" and types[1] == "chord" and types[2] == "chord":
            start = onsets_sorted[0]
            end = max(e.end for e in onset_groups[onsets_sorted[2]])
            mns = (evts_sorted[0].measure_number,) if evts_sorted[0].measure_number else ()
            ev = tuple(e.event_id for o in onsets_sorted[:3] for e in onset_groups[o])
            obj = _make_object("waltz_bass", "left", start, end, mi, mi, mns, ev, (), (), 0.68, {"time_signature": ts, "pattern": "bass-chord-chord"}, (), "waltz_344")
            if obj:
                out.append(obj)
        # Oom-pah: duple (2/4, 4/4, 2/2, 6/8) with alternating bass/chord
        elif ts in ("2/4", "4/4", "2/2", "6/8", "4/4", None) and len(types) >= 2:
            # Check alternating bass-chord-bass-chord for at least 4 onsets or 2 cycles
            alt_ok = True
            for i in range(min(4, len(types))):
                expected = "bass" if i % 2 == 0 else "chord"
                if types[i] != expected:
                    alt_ok = False
                    break
            if alt_ok and len([t for t in types[:4] if t in ("bass", "chord")]) >= 4:
                start = onsets_sorted[0]
                end = max(e.end for e in onset_groups[onsets_sorted[3]])
                mns = (evts_sorted[0].measure_number,) if evts_sorted[0].measure_number else ()
                ev = tuple(e.event_id for o in onsets_sorted[:4] for e in onset_groups[o])
                obj = _make_object("oom_pah_bass_chord_pattern", "left", start, end, mi, mi, mns, ev, (), (), 0.64, {"time_signature": ts or "4/4", "pattern": "bass-chord-bass-chord"}, (), "oom_pah_alternation")
                if obj:
                    out.append(obj)
            elif len(types) >= 2 and types[0] == "bass" and types[1] == "chord":
                # weaker single bar oom-pah (2 onsets)
                start = onsets_sorted[0]
                end = max(e.end for e in onset_groups[onsets_sorted[1]])
                mns = (evts_sorted[0].measure_number,) if evts_sorted[0].measure_number else ()
                ev = tuple(e.event_id for o in onsets_sorted[:2] for e in onset_groups[o])
                obj = _make_object("oom_pah_bass_chord_pattern", "left", start, end, mi, mi, mns, ev, (), (), 0.52, {"time_signature": ts or "4/4", "pattern": "bass-chord"}, ("heuristic_two_onset_only",), "oom_pah_two")
                if obj:
                    out.append(obj)
    return out[:4]


def _detect_repeated_chord_accompaniment(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # Detect recurring chord sonorities with repeated rhythm
    # Use chord_shape tokens with same midi pitches repeating
    for hand in ("right", "left"):
        chords = [t for t in tokens if t.hand == hand and t.kind in ("chord_shape", "harmonic_simultaneity") and t.payload.get("note_count", 0) >= 2]
        if len(chords) < 2:
            continue
        # Group by pitch set
        by_pitches: dict[tuple[int, ...], list[DerivedToken]] = defaultdict(list)
        for c in chords:
            pcs = c.payload.get("midi_pitches") or c.payload.get("midi_pitches") or ()
            if not pcs:
                pcs = tuple(sorted([e.pitch_midi for e in events if e.event_id in c.evidence_event_ids and e.pitch_midi is not None]))
            key = tuple(sorted(pcs)) if pcs else ()
            if key:
                by_pitches[key].append(c)
        for pcs, lst in by_pitches.items():
            if len(lst) >= 2:
                # check rhythm repetition: duration similar
                lst_sorted = sorted(lst, key=lambda t: t.start_onset)
                start = lst_sorted[0].start_onset
                end = lst_sorted[-1].end_onset
                ev = tuple(eid for t in lst_sorted for eid in t.evidence_event_ids)
                tids = tuple(t.token_id for t in lst_sorted)
                ms = min(t.measure_start for t in lst_sorted if t.measure_start is not None)
                me = max(t.measure_end for t in lst_sorted if t.measure_end is not None)
                mns = tuple(sorted({m for t in lst_sorted for m in t.measure_numbers}, key=_measure_sort_key))
                obj = _make_object("repeated_chord_accompaniment", hand, start, end, ms, me, mns, ev, tids, (), 0.62, {"pitches": pcs, "occurrences": len(lst)}, (), "repeated_chord_sonority")
                if obj:
                    out.append(obj)
                    if len(out) >= 3:
                        break
    return out[:3]


def _detect_stride_pedal_tremolo(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # left_hand_stride_like_motion: large register shifts between bass and chordal events in left hand
    for hand in ("left",):
        shifts = [t for t in tokens if t.hand == hand and t.kind in ("hand_movement", "register_shift", "leap")]
        if len(shifts) >= 2:
            large = [t for t in shifts if abs(t.payload.get("movement_semitones", 0) or t.payload.get("shift_semitones", 0) or t.payload.get("interval_semitones", 0)) >= 7]
            if len(large) >= 2:
                # Group into object spanning across shifts
                sorted_large = sorted(large, key=lambda t: t.start_onset)
                start = sorted_large[0].start_onset
                end = sorted_large[-1].end_onset
                ev = tuple(eid for t in sorted_large for eid in t.evidence_event_ids)
                tids = tuple(t.token_id for t in sorted_large)
                ms = min(t.measure_start for t in sorted_large if t.measure_start is not None)
                me = max(t.measure_end for t in sorted_large if t.measure_end is not None)
                mns = tuple(sorted({m for t in sorted_large for m in t.measure_numbers}, key=_measure_sort_key))
                obj = _make_object("left_hand_stride_like_motion", hand, start, end, ms, me, mns, ev, tids, (), 0.60, {"large_shifts": len(large)}, (), "stride_large_shifts")
                if obj:
                    out.append(obj)
    # pedal_point_accompaniment: repeated pitch while harmony changes elsewhere
    for hand in ("right", "left"):
        reps = _rep_sequence(_events_by_hand(events, hand))
        if len(reps) < 4:
            continue
        # Find pitch that repeats at least 3 times while other hand changes
        from collections import Counter
        pitch_counts = Counter(r[1] for r in reps)
        for pitch, cnt in pitch_counts.items():
            if cnt >= 3:
                # Check that other hand has changing harmony (at least 2 different pitches)
                other_hand = "left" if hand == "right" else "right"
                other_reps = _rep_sequence(_events_by_hand(events, other_hand))
                if len(other_reps) < 2 or len({r[1] for r in other_reps}) < 2:
                    continue
                # Collect pedal occurrences
                pedal_reps = [r for r in reps if r[1] == pitch]
                start = pedal_reps[0][0]
                end = pedal_reps[-1][0] + pedal_reps[-1][6]
                ev = tuple(eid for r in pedal_reps for eid in r[2])
                mns = tuple(sorted({str(r[4]) for r in pedal_reps if r[4]}, key=_measure_sort_key))
                ms = min(r[3] for r in pedal_reps if r[3] is not None)
                me = max(r[3] for r in pedal_reps if r[3] is not None)
                obj = _make_object("pedal_point_accompaniment", hand, start, end, ms, me, mns, ev, (), (), 0.58, {"pedal_pitch": pitch, "occurrences": cnt}, (), "pedal_point")
                if obj:
                    out.append(obj)
                    break
        if out and out[-1].object_id == "pedal_point_accompaniment":
            # allow one per hand
            continue
    # tremolo_accompaniment: rapid alternation between two pitches/chords
    for hand in ("right", "left"):
        reps = _rep_sequence(_events_by_hand(events, hand))
        if len(reps) < 4:
            continue
        # Look for alternation ABAB with short durations
        for i in range(len(reps) - 3):
            p0, p1, p2, p3 = reps[i][1], reps[i+1][1], reps[i+2][1], reps[i+3][1]
            durs_short = all(reps[k][6] <= Fraction(1, 2) for k in (i, i+1, i+2, i+3))
            if p0 == p2 and p1 == p3 and p0 != p1 and durs_short:
                start = reps[i][0]
                end = reps[i+3][0] + reps[i+3][6]
                ev = tuple(eid for k in (i, i+1, i+2, i+3) for eid in reps[k][2])
                mns = tuple(sorted({str(reps[k][4]) for k in (i, i+1, i+2, i+3) if reps[k][4]}, key=_measure_sort_key))
                ms = reps[i][3]
                me = reps[i+3][3]
                obj = _make_object("tremolo_accompaniment", hand, start, end, ms, me, mns, ev, (), (), 0.66, {"alternation": (p0, p1)}, (), "tremolo_ABAB")
                if obj and not any(o.hand == hand and o.start_onset == start for o in out):
                    out.append(obj)
                if len([x for x in out if x.object_id == "tremolo_accompaniment"]) >= 2:
                    break
    return out[:6]


def _detect_texture_objects(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # chordal_homophonic_texture: high simultaneity aligned rhythms block chords
    # Need multiple onsets where simultaneity >=3 notes and shared duration
    by_onset = _group_by_onset([e for e in events if not e.is_rest])
    homoph_onsets: list[Fraction] = []
    for o, evts in by_onset.items():
        if len(evts) >= 3:
            # check both hands maybe but require aligned
            durs = {e.duration for e in evts}
            if len(durs) == 1:
                homoph_onsets.append(o)
    if len(homoph_onsets) >= 2:
        # group consecutive homophonic onsets into one object
        homoph_onsets_sorted = sorted(homoph_onsets)
        start = homoph_onsets_sorted[0]
        end = homoph_onsets_sorted[-1] + Fraction(1)  # approximate
        ev = tuple(e.event_id for o in homoph_onsets_sorted for e in by_onset[o])
        # measures
        all_evts = [e for o in homoph_onsets_sorted for e in by_onset[o]]
        ms = min((e.measure_index for e in all_evts if e.measure_index is not None), default=None)
        me = max((e.measure_index for e in all_evts if e.measure_index is not None), default=None)
        mns = tuple(sorted({str(e.measure_number) for e in all_evts if e.measure_number}, key=_measure_sort_key))
        obj = _make_object("chordal_homophonic_texture", None, start, end, ms, me, mns, ev, (), (), 0.64, {"homophonic_onsets": len(homoph_onsets_sorted)}, (), "homophonic_block")
        if obj:
            out.append(obj)
    # two_voice_counterpoint: two sustained voice streams separate contours
    voices = defaultdict(list)
    for e in events:
        if not e.is_rest and e.voice is not None:
            voices[e.voice].append(e)
    if len(voices) >= 2:
        voice_ids = list(voices.keys())[:2]
        # Check overlapping time and separate contours
        v0_onsets = sorted({e.onset for e in voices[voice_ids[0]]})
        v1_onsets = sorted({e.onset for e in voices[voice_ids[1]]})
        overlap = any(o in v1_onsets for o in v0_onsets)
        if overlap:
            # Need at least 3 notes each
            if len(voices[voice_ids[0]]) >= 3 and len(voices[voice_ids[1]]) >= 3:
                all_v = voices[voice_ids[0]] + voices[voice_ids[1]]
                start = min(e.onset for e in all_v)
                end = max(e.end for e in all_v)
                ev = tuple(e.event_id for e in all_v)
                mns = tuple(sorted({str(e.measure_number) for e in all_v if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in all_v if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in all_v if e.measure_index is not None), default=None)
                obj = _make_object("two_voice_counterpoint", None, start, end, ms, me, mns, ev, (), (), 0.60, {"voices": tuple(voice_ids)}, (), "two_voice")
                if obj:
                    out.append(obj)
    # inner_voice_movement: middle voice moves inside chordal texture — heuristic from chord-span middle voice
    for hand in ("right", "left"):
        chords = [t for t in tokens if t.hand == hand and t.kind in ("chord_shape", "harmonic_simultaneity") and t.payload.get("note_count", 0) >= 3]
        if len(chords) < 2:
            continue
        # Check if middle pitch changes while outer stays
        for i in range(len(chords) - 1):
            c1, c2 = chords[i], chords[i+1]
            mids1 = sorted([e.pitch_midi for e in events if e.event_id in c1.evidence_event_ids and e.pitch_midi is not None])
            mids2 = sorted([e.pitch_midi for e in events if e.event_id in c2.evidence_event_ids and e.pitch_midi is not None])
            if len(mids1) >= 3 and len(mids2) >= 3 and mids1[0] == mids2[0] and mids1[-1] == mids2[-1] and mids1[1] != mids2[1]:
                start = c1.start_onset
                end = c2.end_onset
                ev = tuple(dict.fromkeys(list(c1.evidence_event_ids) + list(c2.evidence_event_ids)))
                mns = tuple(sorted(set(c1.measure_numbers + c2.measure_numbers), key=_measure_sort_key))
                ms = c1.measure_start
                me = c2.measure_end
                obj = _make_object("inner_voice_movement", hand, start, end, ms, me, mns, ev, (c1.token_id, c2.token_id), (), 0.48, {"outer_stable": True, "middle_change": (mids1[1], mids2[1])}, ("heuristic_middle_voice", "polyphony_inferred_from_chord"), "inner_voice")
                if obj and not any(o.object_id == "inner_voice_movement" and o.hand == hand and o.start_onset == start for o in out):
                    out.append(obj)
    # parallel_thirds / sixths / octaves
    for interval, oid, semitone, label in [(3, "parallel_thirds", 3, "third"), (4, "parallel_sixths", 8, "sixth"), (12, "octaves", 12, "octave")]:
        # Check successive simultaneities or paired notes maintaining interval
        # Use harmonic_simultaneity with 2 notes at interval ~3-4 or 8-9 or 12
        candidates = []
        for t in tokens:
            if t.kind in ("harmonic_simultaneity", "chord_shape") and t.payload.get("note_count", 0) == 2:
                span = t.payload.get("span_semitones", 0)
                # For thirds: 3 or 4, sixths 8 or 9, octaves 12
                if oid == "parallel_thirds" and span in (3, 4):
                    candidates.append(t)
                elif oid == "parallel_sixths" and span in (8, 9):
                    candidates.append(t)
                elif oid == "octaves" and span == 12:
                    candidates.append(t)
        if len(candidates) >= 2:
            # Need at least 2 consecutive with same hand
            for hand in ("right", "left", None):
                hand_cands = [c for c in candidates if c.hand == hand] if hand is not None else [c for c in candidates if c.hand is None]
                if len(hand_cands) < 2:
                    continue
                hand_cands_sorted = sorted(hand_cands, key=lambda t: t.start_onset)
                # Check consecutive
                for i in range(len(hand_cands_sorted) - 1):
                    if hand_cands_sorted[i+1].start_onset - hand_cands_sorted[i].end_onset <= Fraction(1):
                        start = hand_cands_sorted[i].start_onset
                        end = hand_cands_sorted[i+1].end_onset
                        ev = tuple(dict.fromkeys(list(hand_cands_sorted[i].evidence_event_ids) + list(hand_cands_sorted[i+1].evidence_event_ids)))
                        mns = tuple(sorted(set(hand_cands_sorted[i].measure_numbers + hand_cands_sorted[i+1].measure_numbers), key=_measure_sort_key))
                        ms = hand_cands_sorted[i].measure_start
                        me = hand_cands_sorted[i+1].measure_end
                        obj = _make_object(oid, hand, start, end, ms, me, mns, ev, (hand_cands_sorted[i].token_id, hand_cands_sorted[i+1].token_id), (), 0.64, {"interval": label, "span": semitone}, (), f"parallel_{label}")
                        if obj:
                            out.append(obj)
                            break
        # Also detect melodic parallel via paired notes? For octaves, also consider repeated octave shapes per onset
        if oid == "octaves" and not any(o.object_id == "octaves" for o in out):
            # Look for single hand events where successive notes are 12 apart but also chord tone octave?
            # Check events hand-specific two notes at same onset with octave
            for onset, evts in _group_by_onset([e for e in events if not e.is_rest]).items():
                for hand in ("right", "left"):
                    hand_evts = [e for e in evts if e.hand == hand and e.pitch_midi is not None]
                    if len(hand_evts) >= 2:
                        mids = sorted([e.pitch_midi for e in hand_evts])
                        # Check any pair 12 apart
                        for i in range(len(mids)):
                            for j in range(i+1, len(mids)):
                                if mids[j] - mids[i] == 12:
                                    obj = _make_object("octaves", hand, onset, max(e.end for e in hand_evts), hand_evts[0].measure_index, hand_evts[0].measure_index, (hand_evts[0].measure_number,) if hand_evts[0].measure_number else (), tuple(e.event_id for e in hand_evts), (), (), 0.60, {"octave_span": 12}, (), "octave_simultaneity")
                                    if obj and not any(o.hand == hand and o.start_onset == onset for o in out if o.object_id == "octaves"):
                                        out.append(obj)
                                    break
    # hand_to_hand_imitation / call_and_response + melody_embedded_in_chords
    # hand_to_hand_imitation: similar interval/rhythm cells opposite hands delayed
    for hand_pair in [("right", "left")]:
        for pat_len in (2, 3):
            # Get reps per hand
            reps_r = _rep_sequence(_events_by_hand(events, "right"))
            reps_l = _rep_sequence(_events_by_hand(events, "left"))
            if len(reps_r) < pat_len or len(reps_l) < pat_len:
                continue
            # Extract interval patterns
            def pat_intervals(reps: list) -> list[tuple[int, ...]]:
                ints = [reps[i+1][1] - reps[i][1] for i in range(len(reps)-1)]
                return [tuple(ints[i:i+pat_len-1]) if pat_len >1 else () for i in range(len(ints)-pat_len+2)]
            # For simplicity, check first pattern equality
            if reps_r and reps_l:
                r_ints = [reps_r[i+1][1] - reps_r[i][1] for i in range(len(reps_r)-1)]
                l_ints = [reps_l[i+1][1] - reps_l[i][1] for i in range(len(reps_l)-1)]
                # Compare first pat_len-1 intervals
                if pat_len-1 <= len(r_ints) and pat_len-1 <= len(l_ints) and tuple(r_ints[:pat_len-1]) == tuple(l_ints[:pat_len-1]) and tuple(r_ints[:pat_len-1]) != ():
                    # Imitation
                    start_r = reps_r[0][0]
                    start_l = reps_l[0][0]
                    # Require delay
                    delay = abs(start_r - start_l)
                    if delay > Fraction(0) and delay <= Fraction(4):
                        start = min(start_r, start_l)
                        end = max(reps_r[pat_len-1][0], reps_l[pat_len-1][0])
                        ev = tuple(eid for r in (reps_r[:pat_len], reps_l[:pat_len]) for rep in r for eid in rep[2])
                        mns = tuple(sorted({str(rep[4]) for r in (reps_r[:pat_len], reps_l[:pat_len]) for rep in r if rep[4]}, key=_measure_sort_key))
                        ms = min((rep[3] for r in (reps_r[:pat_len], reps_l[:pat_len]) for rep in r if rep[3] is not None), default=None)
                        me = max((rep[3] for r in (reps_r[:pat_len], reps_l[:pat_len]) for rep in r if rep[3] is not None), default=None)
                        obj = _make_object("hand_to_hand_imitation", None, start, end, ms, me, mns, ev, (), (), 0.58, {"pattern_intervals": tuple(r_ints[:pat_len-1]), "delay": str(delay)}, ("hand_alternation_heuristic" if delay <= Fraction(1) else ()), "imitation")
                        if obj:
                            out.append(obj)
                        # call_and_response similar but distinct locations (longer delay or motive)
                        if delay >= Fraction(1):
                            obj2 = _make_object("call_and_response", None, start, end, ms, me, mns, ev, (), (), 0.52, {"pattern": tuple(r_ints[:pat_len-1])}, ("heuristic_call_response",), "call_response")
                            if obj2:
                                out.append(obj2)
                        break
    # melody_embedded_in_chords: chordal texture with moving top voice
    for hand in ("right", "left"):
        chords = [t for t in tokens if t.hand == hand and t.kind in ("chord_shape", "harmonic_simultaneity") and t.payload.get("note_count", 0) >= 3]
        if len(chords) < 2:
            continue
        # Check top notes moving stepwise while harmony stable
        tops = []
        for c in sorted(chords, key=lambda t: t.start_onset):
            mids = sorted([e.pitch_midi for e in events if e.event_id in c.evidence_event_ids and e.pitch_midi is not None])
            if mids:
                tops.append((c, mids[-1]))
        if len(tops) >= 2:
            moving = any(tops[i+1][1] != tops[i][1] and abs(tops[i+1][1] - tops[i][1]) <= 4 for i in range(len(tops)-1))
            if moving:
                start = tops[0][0].start_onset
                end = tops[-1][0].end_onset
                ev = tuple(eid for c, _ in tops for eid in c.evidence_event_ids)
                tids = tuple(c.token_id for c, _ in tops)
                mns = tuple(sorted({m for c, _ in tops for m in c.measure_numbers}, key=_measure_sort_key))
                ms = min(c.measure_start for c, _ in tops if c.measure_start is not None)
                me = max(c.measure_end for c, _ in tops if c.measure_end is not None)
                obj = _make_object("melody_embedded_in_chords", hand, start, end, ms, me, mns, ev, tids, (), 0.60, {"top_voice_intervals": tuple(tops[i+1][1] - tops[i][1] for i in range(len(tops)-1))}, (), "melody_in_chords")
                if obj:
                    out.append(obj)
    return out[:10]


# ---------------------------------------------------------------------------
# Slice 4 — physical
# ---------------------------------------------------------------------------

def _detect_physical(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # hand_shift: sustained pitch center movement, register_shift, or large movement
    for hand in ("right", "left"):
        shifts = [t for t in tokens if t.hand == hand and t.kind in ("register_shift", "hand_movement", "leap")]
        if shifts:
            # Group shifts within 4 quarters into one hand_shift object
            sorted_shifts = sorted(shifts, key=lambda t: t.start_onset)
            # Emit per shift as separate object if large
            for s in sorted_shifts:
                shift_val = s.payload.get("shift_semitones") or s.payload.get("movement_semitones") or s.payload.get("interval_semitones") or 0
                if abs(shift_val) >= 7:
                    obj = _make_object("hand_shift", hand, s.start_onset, s.end_onset, s.measure_start, s.measure_end, s.measure_numbers,
                                       s.evidence_event_ids, (s.token_id,), (), 0.60, {"shift": shift_val}, (), "hand_shift_large")
                    if obj:
                        out.append(obj)
                        if len([x for x in out if x.object_id == "hand_shift"]) >= 3:
                            break
    # hand_expansion_contraction: changing simultaneous span within hand
    for hand in ("right", "left"):
        chords = sorted([t for t in tokens if t.hand == hand and t.kind in ("chord_shape", "harmonic_simultaneity")], key=lambda t: t.start_onset)
        if len(chords) >= 2:
            for i in range(len(chords)-1):
                s1 = chords[i].payload.get("span_semitones", 0)
                s2 = chords[i+1].payload.get("span_semitones", 0)
                if isinstance(s1, (int, float)) and isinstance(s2, (int, float)) and abs(s2 - s1) >= 4:
                    start = chords[i].start_onset
                    end = chords[i+1].end_onset
                    ev = tuple(dict.fromkeys(list(chords[i].evidence_event_ids) + list(chords[i+1].evidence_event_ids)))
                    mns = tuple(sorted(set(chords[i].measure_numbers + chords[i+1].measure_numbers), key=_measure_sort_key))
                    ms = chords[i].measure_start
                    me = chords[i+1].measure_end
                    obj = _make_object("hand_expansion_contraction", hand, start, end, ms, me, mns, ev, (chords[i].token_id, chords[i+1].token_id), (), 0.58, {"span_change": s2 - s1, "from_span": s1, "to_span": s2}, (), "expansion_contraction")
                    if obj and not any(o.hand == hand and o.start_onset == start for o in out if o.object_id == "hand_expansion_contraction"):
                        out.append(obj)
                        if len([x for x in out if x.object_id == "hand_expansion_contraction"]) >= 2:
                            break
    # thumb_under_scale_passage: longer scalar runs spanning > octave or >5 notes, always caveated
    for o in [x for x in _detect_scalar_runs(events, tokens, gestures) if x.object_id in ("ascending_scalar_run", "descending_scalar_run")]:
        steps = o.payload.get("steps", 0)
        # Check span
        # Estimate pitch span from evidence
        mids = [e.pitch_midi for e in events if e.event_id in o.evidence_event_ids and e.pitch_midi is not None]
        span = max(mids) - min(mids) if len(mids) >= 2 else 0
        if steps >= 6 or span >= 7:
            obj = _make_object("thumb_under_scale_passage", o.hand, o.start_onset, o.end_onset, o.measure_start, o.measure_end, o.measure_numbers,
                               o.evidence_event_ids, o.token_ids, o.gesture_ids, 0.52, {"steps": steps, "span": span, "source": o.object_id}, ("fingering_not_in_score", "hand_position_inferred_from_span"), "thumb_under")
            if obj:
                out.append(obj)
    # repeated_finger_substitution_candidate: repeated pitch sustained while other moves, caveated
    for hand in ("right", "left"):
        # Find repeated pitch events in same hand within short window while other voices continue
        reps = _rep_sequence(_events_by_hand(events, hand))
        if len(reps) < 3:
            continue
        # Look for same pitch repeating with gap <=2 quarters and intervening different pitches in other hand or same hand other notes?
        for i in range(len(reps)-1):
            if reps[i][1] == reps[i+1][1]:
                # Check if between these two, there is other activity (either hand)
                between_onset = reps[i][0] + Fraction(1, 8)
                between_end = reps[i+1][0]
                other_activity = any(e.onset >= between_onset and e.onset < between_end and not e.is_rest for e in events)
                if other_activity:
                    start = reps[i][0]
                    end = reps[i+1][0] + reps[i+1][6]
                    ev = tuple(dict.fromkeys(list(reps[i][2]) + list(reps[i+1][2])))
                    mns = tuple(sorted({str(reps[i][4]), str(reps[i+1][4])} if reps[i][4] and reps[i+1][4] else [str(reps[i][4] or reps[i+1][4])], key=_measure_sort_key))
                    ms = reps[i][3]
                    me = reps[i+1][3]
                    obj = _make_object("repeated_finger_substitution_candidate", hand, start, end, ms, me, mns, ev, (), (), 0.48, {"pitch": reps[i][1]}, ("fingering_not_in_score", "hand_position_inferred_from_span"), "finger_substitution")
                    if obj and not any(o.hand == hand and o.start_onset == start for o in out if o.object_id == "repeated_finger_substitution_candidate"):
                        out.append(obj)
                        if len([x for x in out if x.object_id == "repeated_finger_substitution_candidate"]) >= 2:
                            break
    # wide_broken_chord: arpeggiated chord tones large span >12
    for hand in ("right", "left"):
        for g in gestures:
            if g.kind == "arpeggio" and g.hand == hand:
                mids = [e.pitch_midi for e in events if e.event_id in g.evidence_event_ids and e.pitch_midi is not None]
                span = max(mids) - min(mids) if len(mids) >= 2 else 0
                if span >= 12:
                    obj = _make_object("wide_broken_chord", hand, g.start_onset, g.end_onset, g.measure_start, g.measure_end, g.measure_numbers,
                                       g.evidence_event_ids, g.token_ids, (g.gesture_id,), 0.62, {"span": span}, (), "wide_broken")
                    if obj:
                        out.append(obj)
        # Also from broken chord tokens
        for t in tokens:
            if t.hand == hand and t.kind == "melodic_interval" and abs(t.payload.get("interval_semitones", 0)) in (3, 4):
                # Not sufficient alone; need span check via run
                pass
    # awkward_redistribution_cross_staff_passage: cross-staff notation, hand/staff mismatch, interleaved registers
    # Heuristic: check events where hand != expected staff (right expects staff 1, left expects staff 2)
    cross_events = []
    for e in events:
        if not e.is_rest and e.hand is not None and e.staff is not None:
            if (e.hand == "right" and e.staff == 2) or (e.hand == "left" and e.staff == 1):
                cross_events.append(e)
    if cross_events:
        # Group contiguous cross-staff events
        cross_events_sorted = sorted(cross_events, key=lambda e: e.onset)
        # Create one object spanning all cross-staff events if within 4 quarters
        start = cross_events_sorted[0].onset
        end = max(e.end for e in cross_events_sorted)
        if end - start <= Fraction(8):
            ev = tuple(e.event_id for e in cross_events_sorted)
            mns = tuple(sorted({str(e.measure_number) for e in cross_events_sorted if e.measure_number}, key=_measure_sort_key))
            ms = min((e.measure_index for e in cross_events_sorted if e.measure_index is not None), default=None)
            me = max((e.measure_index for e in cross_events_sorted if e.measure_index is not None), default=None)
            obj = _make_object("awkward_redistribution_cross_staff_passage", None, start, end, ms, me, mns, ev, (), (), 0.55, {"cross_staff_count": len(cross_events_sorted)}, ("fingering_not_in_score", "hand_position_inferred_from_span"), "cross_staff")
            if obj:
                out.append(obj)
        else:
            # Split into chunks
            chunk: list[ScoreEvent] = [cross_events_sorted[0]]
            for e in cross_events_sorted[1:]:
                if e.onset - chunk[-1].onset <= Fraction(4):
                    chunk.append(e)
                else:
                    if chunk:
                        start = chunk[0].onset
                        end = max(x.end for x in chunk)
                        ev = tuple(x.event_id for x in chunk)
                        mns = tuple(sorted({str(x.measure_number) for x in chunk if x.measure_number}, key=_measure_sort_key))
                        ms = min((x.measure_index for x in chunk if x.measure_index is not None), default=None)
                        me = max((x.measure_index for x in chunk if x.measure_index is not None), default=None)
                        obj = _make_object("awkward_redistribution_cross_staff_passage", None, start, end, ms, me, mns, ev, (), (), 0.55, {"cross_staff_count": len(chunk)}, ("fingering_not_in_score", "hand_position_inferred_from_span"), "cross_staff_chunk")
                        if obj:
                            out.append(obj)
                    chunk = [e]
            if chunk:
                start = chunk[0].onset
                end = max(x.end for x in chunk)
                ev = tuple(x.event_id for x in chunk)
                mns = tuple(sorted({str(x.measure_number) for x in chunk if x.measure_number}, key=_measure_sort_key))
                ms = min((x.measure_index for x in chunk if x.measure_index is not None), default=None)
                me = max((x.measure_index for x in chunk if x.measure_index is not None), default=None)
                obj = _make_object("awkward_redistribution_cross_staff_passage", None, start, end, ms, me, mns, ev, (), (), 0.55, {"cross_staff_count": len(chunk)}, ("fingering_not_in_score", "hand_position_inferred_from_span"), "cross_staff_chunk")
                if obj:
                    out.append(obj)
    # Also check for interleaved registers between hands: right hand low notes overlapping left hand high notes
    # Simple: at same onset, right pitch < left pitch + 12 ?
    for onset, evts in _group_by_onset([e for e in events if not e.is_rest]).items():
        right_mids = [e.pitch_midi for e in evts if e.hand == "right" and e.pitch_midi is not None]
        left_mids = [e.pitch_midi for e in evts if e.hand == "left" and e.pitch_midi is not None]
        if right_mids and left_mids and min(right_mids) < max(left_mids) - 3:
            # interleaved
            if not any(o.object_id == "awkward_redistribution_cross_staff_passage" and o.start_onset == onset for o in out):
                ev = tuple(e.event_id for e in evts)
                mns = tuple(sorted({str(e.measure_number) for e in evts if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in evts if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in evts if e.measure_index is not None), default=None)
                obj = _make_object("awkward_redistribution_cross_staff_passage", None, onset, max(e.end for e in evts), ms, me, mns, ev, (), (), 0.48, {"interleaved": True}, ("fingering_not_in_score", "hand_position_inferred_from_span"), "interleaved_register")
                if obj:
                    out.append(obj)
                    if len([x for x in out if x.object_id == "awkward_redistribution_cross_staff_passage"]) >= 2:
                        break
    return out[:10]


# ---------------------------------------------------------------------------
# Slice 5 — rhythm/coordination
# ---------------------------------------------------------------------------

def _detect_rhythm_coordination(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture], score_ir: Any | None = None) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    # dotted_rhythm: dotted durations or ratio 3:1
    for e in events:
        if e.is_rest:
            continue
        is_dotted = (
            (e.duration_type is not None and "dotted" in e.duration_type.lower())
            or e.duration in (Fraction(3, 2), Fraction(3, 4), Fraction(3, 8))
        )
        # Also check duration ratio 3:1 with next note same hand
        if is_dotted:
            obj = _make_object("dotted_rhythm", e.hand, e.onset, e.end, e.measure_index, e.measure_index, (e.measure_number,) if e.measure_number else (), (e.event_id,), (), (), 0.66, {"duration": str(e.duration), "duration_type": e.duration_type}, (), "dotted_duration")
            if obj and not any(o.hand == e.hand and o.start_onset == e.onset for o in out if o.object_id == "dotted_rhythm"):
                out.append(obj)
        # Check pair long-short 3:1
        nxt_candidates = [x for x in events if x.hand == e.hand and not x.is_rest and x.onset == e.end]
        if nxt_candidates:
            nxt = nxt_candidates[0]
            if e.duration == nxt.duration * 3 or nxt.duration == e.duration * 3:
                start = e.onset
                end = nxt.end
                ev = (e.event_id, nxt.event_id)
                mns = tuple(sorted({str(e.measure_number), str(nxt.measure_number)} if e.measure_number and nxt.measure_number else [str(e.measure_number or nxt.measure_number)], key=_measure_sort_key))
                ms = e.measure_index
                me = nxt.measure_index
                obj = _make_object("dotted_rhythm", e.hand, start, end, ms, me, mns, ev, (), (), 0.60, {"ratio": "3:1", "durations": (str(e.duration), str(nxt.duration))}, (), "ratio_3_1")
                if obj and not any(o.hand == e.hand and o.start_onset == start for o in out if o.object_id == "dotted_rhythm"):
                    out.append(obj)
    # offbeat_accompaniment: accompaniment enters between main beats
    left_onsets = sorted({e.onset for e in _events_by_hand(events, "left")})
    right_onsets = sorted({e.onset for e in _events_by_hand(events, "right")})
    # Main beats: assume quarter beats at integer quarters; offbeat if 0.5 offset
    for onset in left_onsets:
        if onset % 1 == Fraction(1, 2):
            # Check if right hand has onbeat at floor
            has_main = any(abs(r - (onset - Fraction(1, 2))) < Fraction(1, 4) for r in right_onsets)
            if has_main:
                # Find event at this onset left
                evts = [e for e in events if e.hand == "left" and e.onset == onset and not e.is_rest]
                if evts:
                    ev = tuple(e.event_id for e in evts)
                    mns = tuple(sorted({str(e.measure_number) for e in evts if e.measure_number}, key=_measure_sort_key))
                    ms = min((e.measure_index for e in evts if e.measure_index is not None), default=None)
                    me = max((e.measure_index for e in evts if e.measure_index is not None), default=None)
                    obj = _make_object("offbeat_accompaniment", "left", onset, max(e.end for e in evts), ms, me, mns, ev, (), (), 0.58, {"offbeat": str(onset % 1)}, (), "offbeat_left")
                    if obj:
                        out.append(obj)
                        if len([x for x in out if x.object_id == "offbeat_accompaniment"]) >= 3:
                            break
    # polyrhythm: tuplets conflicting grids
    tu_events = [e for e in events if e.tuplet is not None]
    if tu_events:
        # Group by onset: need both hands with different tuplet at same time
        by_onset = defaultdict(list)
        for e in tu_events:
            by_onset[e.onset].append(e)
        for onset, evts in by_onset.items():
            hands = {e.hand for e in evts if e.hand in ("right", "left")}
            tup_vals = {e.tuplet for e in evts}
            if len(hands) >= 2 and len(tup_vals) >= 2:
                mns = tuple(sorted({str(e.measure_number) for e in evts if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in evts if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in evts if e.measure_index is not None), default=None)
                obj = _make_object("polyrhythm", None, onset, max(e.end for e in evts), ms, me, mns, tuple(e.event_id for e in evts), (), (), 0.72, {"tuplets": tuple(sorted(tup_vals))}, (), "polyrhythm_both_hands")
                if obj:
                    out.append(obj)
        # Single-hand polyrhythm with tuplet 3:2 vs straight
        if not any(o.object_id == "polyrhythm" for o in out):
            for e in tu_events:
                # Check if other hand at same quarter has non-tuplet
                other_hand = "right" if e.hand == "left" else "left"
                other_has_straight = any(x.hand == other_hand and x.onset == e.onset and x.tuplet is None for x in events)
                if other_has_straight:
                    obj = _make_object("polyrhythm", None, e.onset, e.end, e.measure_index, e.measure_index, (e.measure_number,) if e.measure_number else (), (e.event_id,), (), (), 0.60, {"tuplet": e.tuplet}, ("heuristic_tuplet_vs_straight",), "polyrhythm_vs_straight")
                    if obj:
                        out.append(obj)
                        if len([x for x in out if x.object_id == "polyrhythm"]) >= 2:
                            break
    else:
        # No tuplet info -> caveat no_tuplet_encoding, do not emit polyrhythm (preserve no object without concrete evidence)
        pass
    # hand_alternation: regular alternation of onsets between hands
    # Build sorted onset list with hand tags
    onset_hand_seq: list[tuple[Fraction, str]] = []
    for onset in sorted({e.onset for e in events if not e.is_rest and e.hand in ("right", "left")}):
        # Determine dominant hand at onset (most events)
        evts_at = [e for e in events if e.onset == onset and e.hand in ("right", "left") and not e.is_rest]
        if len(evts_at) == 1:
            onset_hand_seq.append((onset, evts_at[0].hand))  # type: ignore[arg-type]
        elif len(evts_at) > 1:
            # Both hands same onset -> not alternation
            onset_hand_seq.append((onset, "both"))
        else:
            continue
    # Look for alternation patterns of length >=4 (e.g., R L R L)
    for i in range(len(onset_hand_seq) - 3):
        seq = onset_hand_seq[i:i+4]
        hands = [h for _, h in seq]
        if hands == ["right", "left", "right", "left"] or hands == ["left", "right", "left", "right"]:
            # Check onset regularity (roughly equal spacing within 1.5 factor)
            gaps = [seq[k+1][0] - seq[k][0] for k in range(3)]
            if max(gaps) <= Fraction(2) and min(gaps) > Fraction(0) and max(gaps) / min(gaps) <= Fraction(3, 2):
                start = seq[0][0]
                end = seq[-1][0] + Fraction(1, 4)
                ev = tuple(e.event_id for onset, _ in seq for e in events if e.onset == onset and not e.is_rest)
                # measures
                all_evts = [e for onset, _ in seq for e in events if e.onset == onset]
                mns = tuple(sorted({str(e.measure_number) for e in all_evts if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in all_evts if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in all_evts if e.measure_index is not None), default=None)
                obj = _make_object("hand_alternation", None, start, end, ms, me, mns, ev, (), (), 0.62, {"alternation": tuple(hands)}, (), "hand_alternation")
                if obj and not any(o.start_onset == start for o in out if o.object_id == "hand_alternation"):
                    out.append(obj)
                    if len([x for x in out if x.object_id == "hand_alternation"]) >= 2:
                        break
    # contrary_rhythmic_layers: hands use different rhythmic profiles at same time (duration mismatch)
    # Compare average durations per hand in overlapping windows
    # For each quarter window where both hands active
    if _events_by_hand(events, "right") and _events_by_hand(events, "left"):
        # Sliding window 2 quarters
        all_onsets = sorted({e.onset for e in events if not e.is_rest})
        if all_onsets:
            min_o = min(all_onsets)
            max_o = max(e.end for e in events if not e.is_rest)
            win = Fraction(2)
            cur = min_o
            while cur < max_o:
                w_end = cur + win
                right_durs = [e.duration for e in events if e.hand == "right" and not e.is_rest and cur <= e.onset < w_end]
                left_durs = [e.duration for e in events if e.hand == "left" and not e.is_rest and cur <= e.onset < w_end]
                if right_durs and left_durs:
                    avg_r = sum(right_durs, Fraction(0)) / len(right_durs)
                    avg_l = sum(left_durs, Fraction(0)) / len(left_durs)
                    # Mismatch if ratio >1.5
                    if max(avg_r, avg_l) / min(avg_r, avg_l) >= Fraction(3, 2):
                        # Emit
                        ev = tuple(e.event_id for e in events if not e.is_rest and e.hand in ("right", "left") and cur <= e.onset < w_end)
                        all_w = [e for e in events if not e.is_rest and cur <= e.onset < w_end]
                        mns = tuple(sorted({str(e.measure_number) for e in all_w if e.measure_number}, key=_measure_sort_key))
                        ms = min((e.measure_index for e in all_w if e.measure_index is not None), default=None)
                        me = max((e.measure_index for e in all_w if e.measure_index is not None), default=None)
                        obj = _make_object("contrary_rhythmic_layers", None, cur, w_end, ms, me, mns, ev, (), (), 0.58, {"avg_r": str(avg_r), "avg_l": str(avg_l)}, ("heuristic_duration_mismatch",), "contrary_layers")
                        if obj:
                            out.append(obj)
                            if len([x for x in out if x.object_id == "contrary_rhythmic_layers"]) >= 2:
                                break
                cur += Fraction(1)
    # tied_over_barline_pattern: ties crossing measure boundaries or strong beats
    for e in events:
        if e.is_rest or not e.tie_merged:
            continue
        # Check if tie crosses barline: need measure boundary not directly in event but infer from measure_index change?
        # Use source_note_ids length >1 and duration crosses quarter? Simple: if onset + duration > measure end? We don't have measure end readily
        # Fallback: if event spans across integer measure boundary approximated by 4 quarters? Use time_signature beats
        # For simplicity, if tie_merged and duration >= 2 quarters -> likely ties over barline if near measure end
        if e.duration >= Fraction(2) and e.beat is not None:
            ts = e.time_signature or "4/4"
            try:
                beats_per = int(ts.split("/")[0]) if "/" in ts else 4
            except Exception:
                beats_per = 4
            if e.beat + e.duration > beats_per or e.beat + e.duration > Fraction(4):
                obj = _make_object("tied_over_barline_pattern", e.hand, e.onset, e.end, e.measure_index, e.measure_index, (e.measure_number,) if e.measure_number else (), (e.event_id,), (), (), 0.60, {"tie_merged": True, "duration": str(e.duration)}, (), "tie_barline")
                if obj:
                    out.append(obj)
                    if len([x for x in out if x.object_id == "tied_over_barline_pattern"]) >= 3:
                        break
    # rhythm_pattern_break already part of repeated_position? Do separate
    for t in tokens:
        if t.kind == "pattern_break":
            # Map to rhythm_pattern_break as well (not just pitch)
            obj = _make_object("rhythm_pattern_break", t.hand, t.start_onset, t.end_onset, t.measure_start, t.measure_end, t.measure_numbers,
                               t.evidence_event_ids, (t.token_id,), (), 0.58, {"expected": t.payload.get("expected_interval"), "actual": t.payload.get("actual_interval")}, (), "pattern_break_rhythm")
            if obj:
                out.append(obj)
    # Also detect via repeated_rhythm_cell break: after repeated rhythm, contrasting duration
    # Find repeated_rhythm_cell objects and look for break
    rpt_cells = [o for o in out if o.object_id == "repeated_rhythm_cell"]
    # For each cell, check next onset duration breaks pattern
    # Simplified: if repeated_rhythm_cell exists and next duration different, emit break
    for cell in rpt_cells:
        # Find next event after cell
        nxt = [e for e in events if e.onset >= cell.end_onset and not e.is_rest]
        if nxt:
            nxt_e = min(nxt, key=lambda e: e.onset)
            cell_dur_str = cell.payload.get("rhythm_pattern", ())
            # If next duration not in pattern, emit break
            if cell_dur_str and str(nxt_e.duration) not in cell_dur_str and nxt_e.duration != Fraction(0):
                obj = _make_object("rhythm_pattern_break", nxt_e.hand, nxt_e.onset, nxt_e.end, nxt_e.measure_index, nxt_e.measure_index, (nxt_e.measure_number,) if nxt_e.measure_number else (), (nxt_e.event_id,), (), (), 0.52, {"cell_pattern": cell_dur_str, "break_duration": str(nxt_e.duration)}, ("heuristic_rhythm_break",), "rhythm_break_after_cell")
                if obj:
                    out.append(obj)
    return out[:12]


# ---------------------------------------------------------------------------
# Slice 6 — expression/control (only when markings present)
# ---------------------------------------------------------------------------

def _detect_expression(
    events: list[ScoreEvent],
    tokens: list[DerivedToken],
    gestures: list[Gesture],
    score_ir: Any | None = None,
    prior_objects: list[MusicalObject] | None = None,
) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    prior_objects = prior_objects or []
    # Gather ScoreIR directions if available for expressive text etc.
    directions: list[Any] = []
    if score_ir is not None:
        directions = getattr(score_ir, "directions", []) or []
    # Helper to check articulation
    def has_articulation(kind: str) -> list[ScoreEvent]:
        return [e for e in events if any(a.lower() == kind.lower() for a in e.articulation)]

    # legato_with_detached_accompaniment: one layer legato while another detached
    # Check for slur/cantabile/legato markings vs staccato
    leg_candidates = [e for e in events if any(a.lower() in ("legato", "tenuto", "slur") for a in e.articulation)]  # slur not in articulation but placeholder
    stacc_candidates = [e for e in events if any(a.lower() in ("staccato", "spiccato") for a in e.articulation)]
    if leg_candidates and stacc_candidates:
        # Need both hands with contrasting
        leg_hands = {e.hand for e in leg_candidates if e.hand in ("right", "left")}
        stacc_hands = {e.hand for e in stacc_candidates if e.hand in ("right", "left")}
        if leg_hands and stacc_hands and leg_hands != stacc_hands:
            # Find overlapping time
            leg_onsets = sorted({e.onset for e in leg_candidates})
            stacc_onsets = sorted({e.onset for e in stacc_candidates})
            overlap = any(abs(l - s) <= Fraction(2) for l in leg_onsets for s in stacc_onsets)
            if overlap:
                all_ev = leg_candidates + stacc_candidates
                start = min(e.onset for e in all_ev)
                end = max(e.end for e in all_ev)
                ev = tuple(e.event_id for e in all_ev)
                mns = tuple(sorted({str(e.measure_number) for e in all_ev if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in all_ev if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in all_ev if e.measure_index is not None), default=None)
                obj = _make_object("legato_with_detached_accompaniment", None, start, end, ms, me, mns, ev, (), (), 0.60, {"legato_hands": tuple(leg_hands), "staccato_hands": tuple(stacc_hands)}, (), "legato_detached")
                if obj:
                    out.append(obj)
    # dynamic_swell_across_phrase: hairpins, dynamic changes
    # Check dynamics changes or wedge directions
    dyn_values = [(e.onset, e.dynamics) for e in events if e.dynamics is not None]
    # Also directions with kind dynamics/wedge
    wedge_dirs = [d for d in directions if getattr(d, "kind", None) in ("dynamics", "wedge")]
    if len(wedge_dirs) >= 1 or len({d for _, d in dyn_values}) >= 2:
        # Need at least 2 dynamics or wedge within span
        if wedge_dirs:
            start = min(getattr(d, "start", Fraction(0)) for d in wedge_dirs)
            end = max(getattr(d, "end", getattr(d, "start", Fraction(0)) + Fraction(2)) or getattr(d, "start", Fraction(0)) + Fraction(2) for d in wedge_dirs)
            # Find evidence events near wedge
            ev = tuple(e.event_id for e in events if not e.is_rest and start - Fraction(1) <= e.onset <= end + Fraction(1))
            if ev:
                # measure numbers from those events
                mns = tuple(sorted({str(e.measure_number) for e in events if e.event_id in ev and e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in events if e.event_id in ev and e.measure_index is not None), default=None)
                me = max((e.measure_index for e in events if e.event_id in ev and e.measure_index is not None), default=None)
                obj = _make_object("dynamic_swell_across_phrase", None, start, end, ms, me, mns, ev[:8], (), (), 0.62, {"wedge_count": len(wedge_dirs), "dynamics": list({d for _, d in dyn_values})[:3]}, (), "dynamics_swell_wedge")
                if obj:
                    out.append(obj)
        elif len({d for _, d in dyn_values}) >= 2:
            start = min(o for o, _ in dyn_values)
            end = max(e.end for e in events if e.dynamics is not None)
            ev = tuple(e.event_id for e in events if e.dynamics is not None)[:8]
            mns = tuple(sorted({str(e.measure_number) for e in events if e.event_id in ev and e.measure_number}, key=_measure_sort_key))
            ms = min((e.measure_index for e in events if e.event_id in ev and e.measure_index is not None), default=None)
            me = max((e.measure_index for e in events if e.event_id in ev and e.measure_index is not None), default=None)
            obj = _make_object("dynamic_swell_across_phrase", None, start, end, ms, me, mns, ev, (), (), 0.58, {"dynamics": list({d for _, d in dyn_values})}, ("no_explicit_wedge",), "dynamics_change")
            if obj:
                out.append(obj)
    # accent_pattern: accents recur
    accent_events = has_articulation("accent") + has_articulation("strong-accent")
    if len(accent_events) >= 2:
        # Group nearby accents within 4 quarters
        accent_sorted = sorted(accent_events, key=lambda e: e.onset)
        start = accent_sorted[0].onset
        end = accent_sorted[-1].end
        if end - start <= Fraction(8):
            ev = tuple(e.event_id for e in accent_sorted)
            mns = tuple(sorted({str(e.measure_number) for e in accent_sorted if e.measure_number}, key=_measure_sort_key))
            ms = min((e.measure_index for e in accent_sorted if e.measure_index is not None), default=None)
            me = max((e.measure_index for e in accent_sorted if e.measure_index is not None), default=None)
            obj = _make_object("accent_pattern", None, start, end, ms, me, mns, ev, (), (), 0.64, {"accent_count": len(accent_sorted)}, (), "accent_pattern")
            if obj:
                out.append(obj)
    # articulation_contrast_between_hands: different articulation per hand
    # Collect articulation types per hand
    hand_artics: dict[str, set[str]] = {"right": set(), "left": set()}
    for e in events:
        if e.hand in ("right", "left"):
            for a in e.articulation:
                hand_artics[e.hand].add(a.lower())
    if hand_artics["right"] and hand_artics["left"] and hand_artics["right"] != hand_artics["left"]:
        # Need overlapping time where both hands have distinct articulations
        # Simple: emit if both hands have at least one articulation event within 4 quarters
        right_art_events = [e for e in events if e.hand == "right" and e.articulation]
        left_art_events = [e for e in events if e.hand == "left" and e.articulation]
        if right_art_events and left_art_events:
            start = min(min(e.onset for e in right_art_events), min(e.onset for e in left_art_events))
            end = max(max(e.end for e in right_art_events), max(e.end for e in left_art_events))
            if end - start <= Fraction(8):
                ev = tuple(e.event_id for e in (right_art_events + left_art_events)[:8])
                mns = tuple(sorted({str(e.measure_number) for e in (right_art_events + left_art_events) if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in (right_art_events + left_art_events) if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in (right_art_events + left_art_events) if e.measure_index is not None), default=None)
                obj = _make_object("articulation_contrast_between_hands", None, start, end, ms, me, mns, ev, (), (), 0.60, {"right_articulations": tuple(sorted(hand_artics["right"])), "left_articulations": tuple(sorted(hand_artics["left"]))}, (), "articulation_contrast")
                if obj:
                    out.append(obj)
    # balance_between_voices: polyphonic texture etc. Requires multiple voices or staff_specific dynamics
    has_poly = any(t.kind in ("chord_shape", "harmonic_simultaneity") and t.payload.get("note_count", 0) >= 3 for t in tokens) or len([e for e in events if not e.is_rest]) >= 6
    staff_specific_dyn = any(getattr(d, "kind", None) == "dynamics" and getattr(d, "staff", None) is not None for d in directions) or any(e.dynamics is not None and e.hand is not None for e in events)
    if has_poly and staff_specific_dyn:
        # Use chordal texture as evidence
        chord_events = [e for e in events if e.is_chord_tone]
        if chord_events:
            start = min(e.onset for e in chord_events)
            end = max(e.end for e in chord_events)
            ev = tuple(e.event_id for e in chord_events[:8])
            mns = tuple(sorted({str(e.measure_number) for e in chord_events if e.measure_number}, key=_measure_sort_key))
            ms = min((e.measure_index for e in chord_events if e.measure_index is not None), default=None)
            me = max((e.measure_index for e in chord_events if e.measure_index is not None), default=None)
            obj = _make_object("balance_between_voices", None, start, end, ms, me, mns, ev, (), (), 0.52, {"polyphonic": True}, ("heuristic_balance",), "balance_poly")
            if obj:
                out.append(obj)
    # cantabile_line: expressive text cantabile/dolce, long melodic contour
    expressive_texts = [d for d in directions if getattr(d, "kind", None) in ("words", "expression", "direction") and any(w in (getattr(d, "value", "") or "").lower() for w in ("cantabile", "dolce", "espress", "legato", "sostenuto", "marcato"))]
    # Also check if any event with cantabile in extra? For now check directions value
    if expressive_texts:
        for d in expressive_texts:
            val = getattr(d, "value", "") or ""
            is_cantabile = "cantabile" in val.lower()
            start = getattr(d, "start", Fraction(0))
            end = getattr(d, "end", start + Fraction(4)) or start + Fraction(4)
            # Find melody events nearby (right hand long contour)
            nearby = [e for e in events if e.hand == "right" and not e.is_rest and start - Fraction(2) <= e.onset <= end + Fraction(2)]
            if nearby:
                ev = tuple(e.event_id for e in nearby[:8])
                mns = tuple(sorted({str(e.measure_number) for e in nearby if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in nearby if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in nearby if e.measure_index is not None), default=None)
                obj = _make_object("cantabile_line", "right", start, end, ms, me, mns, ev, (), (), 0.62 if is_cantabile else 0.48, {"expressive_text": val}, () if is_cantabile else ("no_explicit_cantabile", "heuristic_long_line"), "cantabile")
                if obj:
                    out.append(obj)
                    if len([x for x in out if x.object_id == "cantabile_line"]) >= 2:
                        break
    # phrase_shaping_over_repeated_pattern: repeated cells under longer slur/dynamic shape
    # Need repeated_position_pattern + dynamic_swell or expressive text
    repeated_context = [
        o
        for o in prior_objects
        if o.object_id in ("repeated_position_pattern", "repeated_rhythm_cell")
    ]
    has_repeated = bool(repeated_context) or any(t.kind == "pattern_repetition" for t in tokens)
    has_shape = any(o.object_id == "dynamic_swell_across_phrase" for o in out) or any(d for d in directions if getattr(d, "kind", None) == "wedge")
    if has_repeated and has_shape:
        # Find overlapping span between repeated and swell
        repeated_objs = repeated_context
        swell_objs = [o for o in out if o.object_id == "dynamic_swell_across_phrase"]
        if repeated_objs and swell_objs:
            for ro in repeated_objs:
                for so in swell_objs:
                    if ro.end_onset > so.start_onset and ro.start_onset < so.end_onset:
                        start = min(ro.start_onset, so.start_onset)
                        end = max(ro.end_onset, so.end_onset)
                        ev = tuple(dict.fromkeys(list(ro.evidence_event_ids) + list(so.evidence_event_ids)))[:8]
                        mns = tuple(sorted(set(ro.measure_numbers + so.measure_numbers), key=_measure_sort_key))
                        ms = ro.measure_start or so.measure_start
                        me = ro.measure_end or so.measure_end
                        obj = _make_object("phrase_shaping_over_repeated_pattern", ro.hand, start, end, ms, me, mns, ev, ro.token_ids, ro.gesture_ids, 0.50, {"repeated": ro.object_id, "shape": so.object_id}, ("heuristic_phrase_shape",), "phrase_shape")
                        if obj:
                            out.append(obj)
                            break
                if any(o.object_id == "phrase_shaping_over_repeated_pattern" for o in out):
                    break
    return out[:10]


# ---------------------------------------------------------------------------
# Octave-doubled melody & single-hand multi-voice detectors
# ---------------------------------------------------------------------------

def _detect_octave_doubled_melody(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    for hand in ("right", "left"):
        hand_events = [e for e in events if e.hand == hand and not e.is_rest and e.pitch_midi is not None]
        if len(hand_events) < 4:  # need at least 2 octave events (4 notes) to form run, but keep minimal
            continue
        groups: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in hand_events:
            groups[e.onset].append(e)
        # Collect onsets that contain an octave pair
        octave_onsets: list[tuple[Fraction, int, int, list[ScoreEvent], bool, bool, tuple[int, ...]]] = []
        for onset in sorted(groups.keys()):
            evts = groups[onset]
            mids = tuple(sorted(e.pitch_midi for e in evts if e.pitch_midi is not None))
            if len(mids) < 2:
                continue
            # find any pair exactly 12 apart
            pair: tuple[int, int] | None = None
            for i in range(len(mids)):
                for j in range(i + 1, len(mids)):
                    if mids[j] - mids[i] == 12:
                        pair = (mids[i], mids[j])
                        break
                if pair:
                    break
            if pair is None:
                continue
            is_exact = len(mids) == 2 and mids[1] - mids[0] == 12
            is_mixed = not is_exact  # mixed if extra tones present
            octave_onsets.append((onset, pair[0], pair[1], evts, is_exact, is_mixed, mids))
        if len(octave_onsets) < 2:
            continue
        # Build parallel runs
        runs: list[list[tuple[Fraction, int, int, list[ScoreEvent], bool, bool, tuple[int, ...]]]] = []
        cur_run: list[tuple[Fraction, int, int, list[ScoreEvent], bool, bool, tuple[int, ...]]] = []
        for entry in octave_onsets:
            if not cur_run:
                cur_run = [entry]
                continue
            prev = cur_run[-1]
            cur = entry
            gap = cur[0] - prev[0]
            if gap > Fraction(2) or gap <= Fraction(0):
                # gap too large -> break
                if len(cur_run) >= 2:
                    runs.append(cur_run)
                cur_run = [cur]
                continue
            low_iv = cur[1] - prev[1]
            high_iv = cur[2] - prev[2]
            parallel = False
            if low_iv == high_iv:
                parallel = True
            elif abs(low_iv - high_iv) <= 1 and (low_iv * high_iv >= 0 or low_iv == 0 or high_iv == 0):
                parallel = True
            if low_iv == 0 and high_iv == 0:
                parallel = True
            if parallel:
                cur_run.append(cur)
            else:
                if len(cur_run) >= 2:
                    runs.append(cur_run)
                cur_run = [cur]
        if len(cur_run) >= 2:
            runs.append(cur_run)
        # Filter and emit
        for run in runs:
            # salience filter: need at least 3 events, or 2 with strong exact parallel movement
            if len(run) < 3:
                if len(run) == 2:
                    low_iv = run[1][1] - run[0][1]
                    high_iv = run[1][2] - run[0][2]
                    # require exact parallel and non-zero motion for 2-event case to be salient
                    if not (low_iv == high_iv and low_iv != 0):
                        continue
                    # also require gap <=1 for 2-event minimal case to be melodic
                    if (run[1][0] - run[0][0]) > Fraction(1):
                        continue
                else:
                    continue
            octave_count = len(run)
            intervals_low = [run[i + 1][1] - run[i][1] for i in range(len(run) - 1)]
            intervals_high = [run[i + 1][2] - run[i][2] for i in range(len(run) - 1)]
            total_low = sum(intervals_low)
            total_high = sum(intervals_high)
            if total_low > 0 and total_high > 0:
                direction = "ascending"
            elif total_low < 0 and total_high < 0:
                direction = "descending"
            elif total_low == 0 and total_high == 0:
                direction = "static"
            else:
                direction = "mixed"
            # Light melodic filter: need some motion, but allow one repeat
            non_zero = sum(1 for iv in intervals_low if iv != 0)
            if non_zero < 1:
                continue
            # If static direction with all zeros, skip
            if direction == "static":
                continue
            all_mids = [m for entry in run for m in entry[6]]
            pitch_span = max(all_mids) - min(all_mids) if len(all_mids) >= 2 else 12
            is_exact_run = all(e[4] for e in run)
            is_mixed_run = any(e[5] for e in run)
            # Mixed octave plus inner tones: be conservative — sprawling mixed texture is likely chords not melody
            if is_mixed_run and (octave_count > 8 or pitch_span > 24):
                continue
            doubling_type = "exact_octave" if is_exact_run else "mixed_octave_plus_other_tones"
            start_onset = run[0][0]
            last_evts = run[-1][3]
            end_onset = max(e.end for e in last_evts)
            mns = tuple(sorted({str(e.measure_number) for entry in run for e in entry[3] if e.measure_number}, key=_measure_sort_key))
            ms = min((e.measure_index for entry in run for e in entry[3] if e.measure_index is not None), default=None)
            me = max((e.measure_index for entry in run for e in entry[3] if e.measure_index is not None), default=None)
            # Evidence must include both notes of each doubled octave; for mixed we include all notes to preserve context but guarantee octave pair included
            ev_ids = tuple(e.event_id for entry in run for e in entry[3])
            # dedup preserve order
            ev_ids = tuple(dict.fromkeys(ev_ids))
            payload_extra: dict[str, Any] = {
                "octave_count": octave_count,
                "direction": direction,
                "contour": tuple(intervals_low),
                "contour_high": tuple(intervals_high),
                "pitch_span_semitones": pitch_span,
                "span_semitones": pitch_span,
                "doubling_type": doubling_type,
                "is_exact_doubling": is_exact_run,
                "is_mixed": is_mixed_run,
                "octave_interval": 12,
            }
            caveats: tuple[str, ...] = ()
            if is_mixed_run:
                caveats = ("mixed_octave_plus_other_tones",)
            # confidence: exact + longer + stable direction boosts
            conf = 0.72 if octave_count >= 3 and is_exact_run else (0.68 if octave_count >= 3 else 0.62)
            if direction in ("ascending", "descending") and octave_count >= 3:
                conf = min(0.85, conf + 0.06)
            if is_mixed_run:
                conf = max(0.55, conf - 0.08)
            obj = _make_object(
                "octave_doubled_melody", hand, start_onset, end_onset, ms, me, mns, ev_ids, (), (), conf, payload_extra, caveats, "octave_parallel_run"
            )
            if obj and not any(o.hand == hand and o.start_onset == obj.start_onset and o.end_onset == obj.end_onset for o in out):
                out.append(obj)
    return out


def _detect_single_hand_multi_voice(events: list[ScoreEvent], tokens: list[DerivedToken], gestures: list[Gesture]) -> list[MusicalObject]:
    out: list[MusicalObject] = []
    for hand in ("right", "left"):
        hand_events = sorted([e for e in events if e.hand == hand and not e.is_rest and e.pitch_midi is not None], key=lambda e: e.onset)
        if len(hand_events) < 5:
            continue
        # Overall pitch stats for band thresholds
        mids_all = sorted(e.pitch_midi for e in hand_events)
        if len(mids_all) < 4:
            continue
        # Try sliding windows of 4-6 onsets (cover ~2-3 quarters)
        by_onset: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in hand_events:
            by_onset[e.onset].append(e)
        onsets_sorted = sorted(by_onset.keys())
        # Need at least 4 distinct onsets
        if len(onsets_sorted) < 4:
            continue
        # candidate windows: sliding with size 4 and 5
        candidates: list[tuple[Fraction, Fraction, list[ScoreEvent], dict[str, Any], tuple[str, ...]]] = []
        for win_size in (4, 5, 6):
            for start_idx in range(len(onsets_sorted) - win_size + 1):
                window_onsets = onsets_sorted[start_idx:start_idx + win_size]
                window_events = [e for o in window_onsets for e in by_onset[o]]
                if len(window_events) < win_size:
                    continue
                # Compute pitch split
                window_mids = sorted(e.pitch_midi for e in window_events)
                if len(window_mids) < 4:
                    continue
                # Determine bands via largest pitch gap (>=10) — robust for octave-separated textures
                # Find largest gap between consecutive sorted mids
                sorted_unique = sorted(set(window_mids))
                largest_gap = -1
                split_idx = -1
                for i in range(len(sorted_unique) - 1):
                    gap_tmp = sorted_unique[i + 1] - sorted_unique[i]
                    if gap_tmp > largest_gap:
                        largest_gap = gap_tmp
                        split_idx = i
                if largest_gap >= 10 and split_idx != -1:
                    threshold_low = sorted_unique[split_idx]
                    threshold_high = sorted_unique[split_idx + 1]
                    low_candidates = [e for e in window_events if e.pitch_midi is not None and e.pitch_midi <= threshold_low]
                    high_candidates = [e for e in window_events if e.pitch_midi is not None and e.pitch_midi >= threshold_high]
                else:
                    # Fallback to median split
                    median = window_mids[len(window_mids) // 2]
                    low_candidates = [e for e in window_events if e.pitch_midi is not None and e.pitch_midi < median - 2]
                    high_candidates = [e for e in window_events if e.pitch_midi is not None and e.pitch_midi > median + 2]
                    if not low_candidates or not high_candidates:
                        q1 = window_mids[len(window_mids) // 4]
                        q3 = window_mids[3 * len(window_mids) // 4]
                        low_candidates = [e for e in window_events if e.pitch_midi <= q1]
                        high_candidates = [e for e in window_events if e.pitch_midi >= q3]
                if not low_candidates or not high_candidates:
                    continue
                low_mids = sorted(e.pitch_midi for e in low_candidates)
                high_mids = sorted(e.pitch_midi for e in high_candidates)
                if not low_mids or not high_mids:
                    continue
                gap = min(high_mids) - max(low_mids)
                if gap < 10:  # need roughly octave separation (require >=10 to be permissive, 12 ideal)
                    continue
                # Check not block-chord coincident: low and high should not be fully synchronized at same onsets
                low_onsets = {e.onset for e in low_candidates}
                high_onsets = {e.onset for e in high_candidates}
                overlap = len(low_onsets & high_onsets) / max(len(low_onsets | high_onsets), 1)
                if overlap >= 0.85:
                    # block chord like: both bands appear together at same onsets -> not multi-voice
                    continue
                # Check distinct rhythmic behavior
                # Heuristic A: sustained/repeated low while high moves
                # low has repeated pitch or long duration
                low_pitch_counts: dict[int, int] = {}
                for e in low_candidates:
                    low_pitch_counts[e.pitch_midi] = low_pitch_counts.get(e.pitch_midi, 0) + 1
                low_repeated = any(cnt >= 2 for cnt in low_pitch_counts.values())
                low_sustained = any(e.duration >= Fraction(3, 2) for e in low_candidates)
                # high moves: at least 3 distinct pitches, varying
                high_distinct = len({e.pitch_midi for e in high_candidates})
                high_moves = high_distinct >= 3 or len({e.pitch_midi for e in window_events if e.pitch_midi is not None}) >= 4
                # Heuristic B: two bands independent rhythmic behavior (different avg durations)
                low_avg_dur = sum((e.duration for e in low_candidates), Fraction(0)) / len(low_candidates) if low_candidates else Fraction(0)
                high_avg_dur = sum((e.duration for e in high_candidates), Fraction(0)) / len(high_candidates) if high_candidates else Fraction(0)
                # avoid div by zero
                try:
                    ratio = float(max(low_avg_dur, high_avg_dur) / min(low_avg_dur, high_avg_dur)) if min(low_avg_dur, high_avg_dur) > 0 else 1.0
                except Exception:
                    ratio = 1.0
                rhythmic_independent = ratio >= 1.6 or (low_sustained and high_moves)
                # Heuristic C: simultaneous octave plus inner (mixed octave case)
                has_mixed_octave = False
                for o in window_onsets:
                    evts = by_onset[o]
                    mids_o = sorted(e.pitch_midi for e in evts if e.pitch_midi is not None)
                    if len(mids_o) >= 3:
                        # check if contains octave pair plus inner
                        has_oct = any(mids_o[j] - mids_o[i] == 12 for i in range(len(mids_o)) for j in range(i + 1, len(mids_o)))
                        if has_oct:
                            has_mixed_octave = True
                            break
                # Heuristic D: alternation between bass/support and melody-range
                # Check median per onset alternates low/high
                per_onset_median = []
                for o in window_onsets:
                    evts = by_onset[o]
                    mids_o = sorted(e.pitch_midi for e in evts if e.pitch_midi is not None)
                    if mids_o:
                        per_onset_median.append(mids_o[len(mids_o) // 2])
                alternation = False
                if len(per_onset_median) >= 4:
                    # Count alternations of high vs low (threshold median of window)
                    win_median = sorted(per_onset_median)[len(per_onset_median) // 2]
                    tags = ["low" if p < win_median - 4 else "high" if p > win_median + 4 else "mid" for p in per_onset_median]
                    # need at least 2 low and 2 high and alternating pattern
                    if tags.count("low") >= 2 and tags.count("high") >= 2:
                        # check not all low first then all high (needs interleaving)
                        transitions = sum(1 for i in range(len(tags) - 1) if tags[i] != tags[i + 1] and tags[i] in ("low", "high") and tags[i + 1] in ("low", "high"))
                        if transitions >= 2:
                            alternation = True
                # Combine: need at least one strong multi-voice signal plus conservative checks
                is_multi = False
                reasons: list[str] = []
                if (low_repeated or low_sustained) and high_moves and gap >= 10:
                    is_multi = True
                    reasons.append("sustained_or_repeated_low_plus_moving_upper")
                low_distinct = len({e.pitch_midi for e in low_candidates})
                if rhythmic_independent and gap >= 10 and high_distinct >= 2 and low_distinct >= 1:
                    # second check: if rhythmic independent and gap big, count
                    if ratio >= 1.6:
                        is_multi = True
                        reasons.append("pitch_bands_separated_octave_independent_rhythm")
                if has_mixed_octave and gap >= 10:
                    is_multi = True
                    reasons.append("octave_melody_plus_inner_chord_tones")
                if alternation and gap >= 10:
                    is_multi = True
                    reasons.append("alternates_bass_support_and_melody_range")
                if gap >= 12 and rhythmic_independent and (low_repeated or alternation or has_mixed_octave):
                    # strong gap
                    is_multi = True
                # Final conservative gate: require at least 2 onsets per band and not ordinary chord
                if not is_multi:
                    continue
                # Allow single sustained low note covering window (long duration)
                low_onset_ok = len(low_onsets) >= 2 or (len(low_onsets) >= 1 and low_sustained)
                if not low_onset_ok or len(high_onsets) < 2:
                    continue
                # Block chord guard: if every onset in window is a chord with 3+ notes and synchronization high, skip
                chord_onsets = sum(1 for o in window_onsets if len(by_onset[o]) >= 3)
                if chord_onsets == win_size and overlap >= 0.6:
                    # ordinary block chords alone should not produce multi-voice
                    continue
                start_onset = window_onsets[0]
                end_onset = max(e.end for e in window_events)
                # measures
                mns = tuple(sorted({str(e.measure_number) for e in window_events if e.measure_number}, key=_measure_sort_key))
                ms = min((e.measure_index for e in window_events if e.measure_index is not None), default=None)
                me = max((e.measure_index for e in window_events if e.measure_index is not None), default=None)
                ev_ids = tuple(e.event_id for e in window_events)
                ev_ids = tuple(dict.fromkeys(ev_ids))
                payload_extra = {
                    "pitch_band_gap_semitones": gap,
                    "low_band_range": [min(low_mids), max(low_mids)] if low_mids else [],
                    "high_band_range": [min(high_mids), max(high_mids)] if high_mids else [],
                    "window_onsets": win_size,
                    "reasons": tuple(reasons),
                    "low_avg_duration": str(low_avg_dur),
                    "high_avg_duration": str(high_avg_dur),
                    "duration_ratio": round(ratio, 2) if isinstance(ratio, float) else str(ratio),
                    "overlap_ratio": round(overlap, 3),
                }
                caveats = ("voice_assignment_inferred",)
                # add specific caveat for each reason? keep primary
                conf = 0.58
                if gap >= 12 and rhythmic_independent:
                    conf = 0.68
                if has_mixed_octave:
                    conf = max(conf, 0.66)
                # penalize if only alternation without strong sustain
                if len(reasons) == 1 and "alternates_bass_support_and_melody_range" in reasons:
                    conf = min(conf, 0.62)
                candidate = (start_onset, end_onset, window_events, payload_extra, caveats, conf, mns, ms, me, ev_ids)
                candidates.append(candidate)
        # Deduplicate overlapping candidates: keep earliest or highest confidence
        if not candidates:
            continue
        # Sort by confidence desc then start
        candidates.sort(key=lambda x: (-x[5], x[0]))
        # Keep at most 1-2 non-overlapping per hand
        selected: list[tuple] = []
        for cand in candidates:
            s, e = cand[0], cand[1]
            overlaps = any(not (e <= sel[0] or s >= sel[1]) for sel in selected)
            if not overlaps:
                selected.append(cand)
            if len(selected) >= 2:
                break
        for cand in selected:
            start_onset, end_onset, window_events, payload_extra, caveats, conf, mns, ms, me, ev_ids = cand
            obj = _make_object("single_hand_multi_voice_texture", hand, start_onset, end_onset, ms, me, mns, ev_ids, (), (), conf, payload_extra, caveats, "single_hand_multi_voice")
            if obj:
                out.append(obj)
    return out


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def build_musical_objects(
    events: list[ScoreEvent],
    tokens: list[DerivedToken],
    gestures: list[Gesture],
    score_ir: Any | None = None,
) -> list[MusicalObject]:
    """Build all 56 musical objects deterministically.

    Each detector is evidence-backed; objects with empty evidence are dropped.
    Deterministic sorting by (start_onset, object_id).
    """
    all_objs: list[MusicalObject] = []

    # Octave-doubled melody early — so leap suppression can use it
    octave_doubled = _detect_octave_doubled_melody(events, tokens, gestures)
    all_objs.extend(octave_doubled)

    # Slice 1 priority
    all_objs.extend(_detect_scalar_runs(events, tokens, gestures))
    all_objs.extend(_detect_melody_with_accompaniment(events, tokens, gestures, score_ir))
    all_objs.extend(_detect_broken_arpeggiated(events, tokens, gestures))
    all_objs.extend(_detect_alberti_bass(events, tokens, gestures, score_ir))
    all_objs.extend(_detect_leap_to_chord_and_landing(events, tokens, gestures))
    all_objs.extend(_detect_repeated_position_and_rhythm(events, tokens, gestures))
    all_objs.extend(_detect_syncopation(events, tokens, gestures, score_ir))
    all_objs.extend(_detect_melody_voicing_over_accompaniment(events, tokens, gestures, score_ir))

    # Slice 2
    all_objs.extend(_detect_stepwise_intervallic(events, tokens, gestures))
    all_objs.extend(_detect_sequence(events, tokens, gestures))
    all_objs.extend(_detect_repeated_note_melody(events, tokens, gestures))
    all_objs.extend(_detect_chromatic_line(events, tokens, gestures))
    all_objs.extend(_detect_ornamented_and_trill(events, tokens, gestures, score_ir))

    # Slice 3
    all_objs.extend(_detect_waltz_and_oom_pah(events, tokens, gestures))
    all_objs.extend(_detect_repeated_chord_accompaniment(events, tokens, gestures))
    all_objs.extend(_detect_stride_pedal_tremolo(events, tokens, gestures))
    all_objs.extend(_detect_texture_objects(events, tokens, gestures))

    # Slice 4
    all_objs.extend(_detect_physical(events, tokens, gestures))

    # Slice 5
    all_objs.extend(_detect_rhythm_coordination(events, tokens, gestures, score_ir))

    # Slice 6
    all_objs.extend(_detect_expression(events, tokens, gestures, score_ir, prior_objects=all_objs))

    # Single-hand multi-voice (needs comprehensive context, place after slices but before suppression)
    all_objs.extend(_detect_single_hand_multi_voice(events, tokens, gestures))

    # Suppress leap_to_chord inflation from octave doubling: remove leap objects overlapping octave runs
    if octave_doubled:
        octave_spans = [(o.hand, o.start_onset, o.end_onset, set(o.evidence_event_ids)) for o in octave_doubled]
        filtered_leap: list[MusicalObject] = []
        for o in all_objs:
            if o.object_id != "leap_to_chord":
                filtered_leap.append(o)
                continue
            # Check overlap with any octave span same hand and shared evidence
            is_inflated = False
            for hand, o_start, o_end, o_ev in octave_spans:
                if hand is not None and o.hand != hand:
                    continue
                # overlap in time
                if not (o.end_onset <= o_start or o.start_onset >= o_end):
                    # shared evidence check: at least 2 shared or interval small? Use shared
                    shared = len(set(o.evidence_event_ids) & o_ev)
                    if shared >= 2:
                        is_inflated = True
                        break
                    # also if leap interval is actually octave doubling motion (12 semitones)
                    mv = o.payload.get("movement") or o.payload.get("movement_semitones") or o.payload.get("interval_semitones")
                    try:
                        if mv is not None and abs(int(mv)) == 12:
                            is_inflated = True
                            break
                    except Exception:
                        pass
            if not is_inflated:
                filtered_leap.append(o)
        all_objs = filtered_leap

    # Filter empty evidence (already ensured) and sort deterministically
    filtered = [o for o in all_objs if o.evidence_event_ids]
    # Deduplicate exact duplicates by (object_id, hand, start, end) keep highest confidence
    dedup: dict[tuple, MusicalObject] = {}
    for o in filtered:
        key = (o.object_id, o.hand, o.start_onset, o.end_onset)
        existing = dedup.get(key)
        if existing is None or float(o.confidence) > float(existing.confidence):
            dedup[key] = o
    filtered = list(dedup.values())
    filtered.sort(key=lambda o: (o.start_onset, o.object_id, o.hand or ""))
    # Reassign stable ordering but keep confidences
    return filtered
