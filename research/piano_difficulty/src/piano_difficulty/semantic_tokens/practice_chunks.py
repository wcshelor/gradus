"""PracticeChunk builder — evidence-driven, deterministic.

Converts MusicalObject / Gesture / DerivedToken evidence into pianist-meaningful
PracticeChunks with hierarchy, primary/context split, traits and practice affordances.

Design goals:
- Detectors are evidence providers, not final layer.
- Chunks support LLM reasoning, UI highlighting and practice generation.
- Generic heuristics, no passage hacks.
- Overlapping chunks allowed (no single winner).
- Single-hand multi-voice and octave-doubling handled via primary/context.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any

from .models import (
    CHUNK_LABELS,
    MusicalObject,
    PracticeChunk,
    ScoreEvent,
    SemanticBundle,
)

try:
    from .notation_markings import ScoreMarking, extract_markings_from_events, markings_in_span, wedge_span_overlaps
except Exception:  # pragma: no cover - fallback if module missing
    ScoreMarking = Any  # type: ignore
    def extract_markings_from_events(events):  # type: ignore
        return []
    def markings_in_span(*args, **kwargs):  # type: ignore
        return []
    def wedge_span_overlaps(*args, **kwargs):  # type: ignore
        return []

# ---------------------------------------------------------------------------
# Affordance mapping
# ---------------------------------------------------------------------------

_CHUNK_AFFORDANCES: dict[str, tuple[str, ...]] = {
    "phrase": ("isolate", "loop", "split_contour", "add_context"),
    "run": ("isolate", "loop", "split_contour", "reduce_rhythm", "add_context"),
    "scalar_run": ("isolate", "loop", "split_contour", "reduce_rhythm", "add_context"),
    "arpeggio_sweep": ("block", "skeletonize", "split_contour", "loop", "reduce_rhythm"),
    "arpeggio": ("block", "skeletonize", "split_contour", "loop"),
    "ascent": ("isolate", "loop", "reduce_rhythm"),
    "descent": ("isolate", "loop", "reduce_rhythm"),
    "turn": ("isolate", "loop", "reduce_rhythm"),
    "landing": ("isolate", "block", "loop"),
    "leap": ("isolate", "loop", "reduce_rhythm", "add_context"),
    "chord_shape": ("isolate", "block", "skeletonize"),
    "layered_texture": ("isolate", "ghost_accompaniment", "layer_back", "hands_separate"),
    "single_hand_multi_voice": ("isolate", "ghost_accompaniment", "layer_back", "hands_separate"),
    "layer": ("isolate", "ghost_accompaniment"),
    "octave_doubled_melody": ("isolate", "skeletonize", "ghost_accompaniment", "add_context", "loop"),
    "octave_doubled_run": ("isolate", "skeletonize", "loop"),
    "coordination": ("hands_separate", "ghost_accompaniment", "progressive_layer_rebuild"),
    "chordal_texture": ("block_chords", "roll_evenly", "shape_dynamics", "isolate_hands", "add_context", "isolate", "loop"),
    "hand_stream": ("isolate", "loop", "hands_separate", "add_context"),
    "passage": ("isolate", "loop", "add_context"),
    "cell": ("isolate", "loop", "reduce_rhythm", "block"),
    "reset": ("isolate", "loop"),
}

def _affordances_for(kind: str, traits: tuple[str, ...]) -> tuple[str, ...]:
    base = _CHUNK_AFFORDANCES.get(kind, ("isolate", "loop"))
    # augment with trait-driven additions
    extra: list[str] = []
    if "octave_doubled" in traits and "skeletonize" not in base:
        extra.append("skeletonize")
    if "layered" in traits and "layer_back" not in base:
        extra.append("layer_back")
    if "rolled_chord" in traits or "rolled_chords" in traits:
        for e in ("block_then_roll", "roll_evenly"):
            if e not in base and e not in extra:
                extra.append(e)
    if "decrescendo" in traits or "crescendo" in traits or "dynamic_shape" in traits:
        if "shape_dynamics" not in base and "shape_dynamics" not in extra:
            extra.append("shape_dynamics")
    if "chord_sequence" in traits and "block_chords" not in base:
        extra.append("block_chords")
    if not extra:
        return base
    # dedup preserve order
    out = list(base)
    for e in extra:
        if e not in out:
            out.append(e)
    return tuple(out)


def _measure_sort_key(value: str) -> tuple[int, str | int]:
    try:
        return (0, int(value))
    except Exception:
        return (1, value)


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


def _has_rest_between(bundle: SemanticBundle, end_a: Fraction, start_b: Fraction, hand: str | None) -> bool:
    for e in bundle.events:
        if not e.is_rest:
            continue
        # rest separates if its onset is between end_a inclusive and start_b exclusive
        # rests have onset/ end; check overlap with gap interval
        if e.onset >= end_a and e.onset < start_b:
            if hand is None or e.hand == hand or e.hand is None:
                return True
        # also check if rest spans gap
        if e.onset < start_b and e.end > end_a:
            if hand is None or e.hand == hand or e.hand is None:
                return True
    return False


def _events_for_ids(bundle: SemanticBundle, ids: tuple[str, ...]) -> list[ScoreEvent]:
    mp = {e.event_id: e for e in bundle.events}
    out: list[ScoreEvent] = []
    for i in ids:
        ev = mp.get(i)
        if ev is not None:
            out.append(ev)
    return sorted(out, key=lambda e: (e.onset, e.pitch_midi or 0))


def _make_chunk_id(counter: list[int], kind: str, hand: str | None, start: Fraction) -> str:
    counter[0] += 1
    h = hand or "both"
    return f"pc{counter[0]:04d}:{kind}:{h}:{str(start)}"


# ---------------------------------------------------------------------------
# Marking / general evidence helpers
# ---------------------------------------------------------------------------

def _dynamics_vals_in_span(events: list[ScoreEvent]) -> list[str]:
    vals: list[str] = []
    for e in events:
        d = getattr(e, "dynamics", None)
        if d:
            # dynamics may be comma-joined values e.g., "p,f"
            for part in str(d).split(","):
                p = part.strip()
                if p:
                    vals.append(p.lower())
    # dedup preserve order
    seen: dict[str, None] = {}
    for v in vals:
        if v not in seen:
            seen[v] = None
    return list(seen.keys())

def _infer_dynamic_shape(events: list[ScoreEvent]) -> str | None:
    vals = _dynamics_vals_in_span(events)
    if not vals:
        return None
    # map dynamics to numeric level
    order = {"ppp":0, "pp":1, "p":2, "mp":3, "mf":4, "f":5, "ff":6, "fff":7,
             "pppp": -1, "ffff":8}
    # include wedge-derived strings? wedge would have separate marking spans; but infer shape from ordering
    levels: list[int] = []
    for v in vals:
        if v in order:
            levels.append(order[v])
        elif v.replace(" ", "") in order:
            levels.append(order[v.replace(" ","")])
    if len(levels) >=2:
        if levels[-1] < levels[0]:
            return "decrescendo"
        if levels[-1] > levels[0]:
            return "crescendo"
    # also detect wedge markings via event flags? wedge spans are markings separate
    return None

def _has_rolled_chord_evidence(events: list[ScoreEvent], bundle: SemanticBundle) -> tuple[bool, str]:
    """Check for rolled chord evidence: event flag or bundle-derived markings."""
    # Check event arpeggiated flag
    for e in events:
        if getattr(e, "is_arpeggiated", False):
            return True, "arpeggiate_marking"
    # Also check if chunk span contains chordal simultaneities with small gap and wedge-like? Fallback texture
    return False, ""

def _hand_overlap_in_span(events: list[ScoreEvent]) -> bool:
    # Check if both hands present at overlapping onsets within span
    onsets_right = {e.onset for e in events if e.hand == "right"}
    onsets_left = {e.onset for e in events if e.hand == "left"}
    if onsets_right & onsets_left:
        return True
    # also check if events themselves span both hands (mixed)
    hands = {e.hand for e in events if e.hand in ("right","left")}
    if len(hands) >=2:
        return True
    return False

def _chordal_density(events: list[ScoreEvent]) -> tuple[int, int]:
    """Return (chordal_onset_count, total_onset_count)."""
    by_onset: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        if not e.is_rest:
            by_onset[e.onset].append(e)
    total = len(by_onset)
    chordal = sum(1 for evs in by_onset.values() if len(evs) >=2)
    return chordal, total

def _enrich_with_markings(chunk: PracticeChunk, bundle: SemanticBundle, markings: list[Any]) -> PracticeChunk:
    """Attach marking-derived traits/affordances/payload to chunk."""
    events = _events_for_ids(bundle, chunk.primary_event_ids)
    if not events:
        return chunk
    # Gather markings overlapping chunk span
    overlapping = []
    try:
        from fractions import Fraction as _F
        s = chunk.start_onset
        e = chunk.end_onset
        overlapping = [m for m in markings if not (m.end_onset is not None and m.end_onset <= s) and not (m.start_onset >= e)]
    except Exception:
        overlapping = []
    traits = list(chunk.traits)
    payload = dict(chunk.payload)
    caveats = list(chunk.caveats)
    # Dynamics
    dyn_vals = _dynamics_vals_in_span(events)
    if dyn_vals:
        payload["dynamics"] = dyn_vals
        if "has_dynamics" not in traits:
            traits.append("has_dynamics")
        shape = _infer_dynamic_shape(events)
        if shape:
            if shape not in traits:
                traits.append(shape)
                traits.append("dynamic_shape")
            payload["dynamic_shape"] = shape
        # also mark hairpin spans overlapping
        hairpins = [m for m in overlapping if getattr(m, "kind", "") == "wedge_span"]
        if hairpins:
            # pick dominant
            hv = hairpins[0].value.lower()
            if "decrescendo" in hv or "diminuendo" in hv:
                if "decrescento" not in traits and "decrescendo" not in traits:
                    traits.append("decrescendo")
                payload["hairpin"] = hv
            elif "crescendo" in hv:
                if "crescendo" not in traits:
                    traits.append("crescendo")
                payload["hairpin"] = hv
            payload["hairpin_spans"] = [m.to_dict() for m in hairpins]
    # Rolled chords
    has_roll, roll_reason = _has_rolled_chord_evidence(events, bundle)
    # also check markings for arpeggiate in overlapping
    arp_marks = [m for m in overlapping if getattr(m, "kind", "") == "arpeggiate"]
    if has_roll or arp_marks:
        if "rolled_chord" not in traits:
            traits.append("rolled_chord")
        if "rolled_chords" not in traits:
            traits.append("rolled_chords")
        payload["rolled_chord_evidence"] = roll_reason or "arpeggiate_marking_in_span"
        if arp_marks:
            payload["arpeggiate_markings"] = [m.to_dict() for m in arp_marks][:3]
        else:
            # inferred from texture
            caveats.append("inferred_roll_from_texture")
    # Octave shift
    oct_marks = [m for m in overlapping if "octave" in getattr(m, "kind", "")]
    if oct_marks:
        if "octave_shift" not in traits:
            traits.append("octave_shift")
        payload["octave_shift_markings"] = [m.to_dict() for m in oct_marks][:2]
        caveats.append("sounding_vs_written_pitch")
    # Slur/phrase
    slurs = [m for m in overlapping if getattr(m, "kind", "") in ("slur","phrase")]
    if slurs:
        if "slur" not in traits:
            traits.append("slur")
        payload["slur_phrase_markings"] = [m.to_dict() for m in slurs][:2]
        # phrase as boundary prior
        payload["phrase_boundary_prior"] = True
        # also check event flags
        has_slur = any(getattr(e, "has_slur_start", False) or getattr(e, "has_slur_stop", False) for e in events)
        if has_slur:
            payload["has_slur"] = True
    # Chordal / density context
    chordal_cnt, total_cnt = _chordal_density(events)
    if total_cnt:
        payload["chordal_onsets"] = chordal_cnt
        payload["total_onsets"] = total_cnt
        if chordal_cnt >= 3 and "chord_sequence" not in traits:
            traits.append("chord_sequence")
        if chordal_cnt / max(total_cnt,1) >= 0.5:
            if "chordal_texture" not in traits:
                traits.append("chordal_texture")
    # Hand overlap
    if _hand_overlap_in_span(events):
        if "hand_overlap" not in traits:
            traits.append("hand_overlap")
    # Mark fallback inference caveat if generic
    if chunk.kind in ("passage","hand_stream","chordal_texture","phrase"):
        if "fallback_chunk" not in caveats:
            caveats.append("fallback_chunk")
        if "inferred" not in traits:
            traits.append("inferred")
            traits.append("fallback")
    # Deduplicate traits preserve order
    traits = list(dict.fromkeys(traits))
    # Recalculate affordances
    aff = _affordances_for(chunk.kind, tuple(traits))
    # Need to merge with existing affordances (keep previous, add new)
    merged_aff = tuple(dict.fromkeys(list(chunk.practice_affordances) + list(aff)))
    return PracticeChunk(
        chunk_id=chunk.chunk_id,
        kind=chunk.kind,
        label=chunk.label,
        hand=chunk.hand,
        voice=chunk.voice,
        role=chunk.role,
        staff=chunk.staff,
        start_onset=chunk.start_onset,
        end_onset=chunk.end_onset,
        measure_start=chunk.measure_start,
        measure_end=chunk.measure_end,
        measure_numbers=chunk.measure_numbers,
        beat_start=chunk.beat_start,
        beat_end=chunk.beat_end,
        primary_event_ids=chunk.primary_event_ids,
        context_event_ids=chunk.context_event_ids,
        child_chunk_ids=chunk.child_chunk_ids,
        parent_chunk_id=chunk.parent_chunk_id,
        source_object_ids=chunk.source_object_ids,
        source_feature_refs=chunk.source_feature_refs,
        traits=tuple(traits),
        practice_affordances=merged_aff,
        confidence=chunk.confidence,
        caveats=tuple(dict.fromkeys(caveats)),
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Builders per evidence type
# ---------------------------------------------------------------------------

def _chunk_from_scalar_run(obj: MusicalObject, bundle: SemanticBundle, counter: list[int]) -> PracticeChunk:
    events = _events_for_ids(bundle, obj.evidence_event_ids)
    direction = obj.payload.get("direction", "up" if obj.object_id == "ascending_scalar_run" else "down")
    traits: list[str] = ["scalar", direction]
    if obj.payload.get("fast_run"):
        traits.append("fast_run")
    # detect chromatic
    intervals = obj.payload.get("interval_pattern", ())
    if any(abs(int(iv)) == 1 for iv in intervals) if intervals else False:
        traits.append("chromatic_adjacent")
    beat_start, beat_end = _beat_for_events(events)
    afford = _affordances_for("run", tuple(traits))
    # primary = all notes, context empty for scalar runs (exclude chord fill if any)
    # if object evidence includes chord at onset with >1 note, keep outer median? For now keep all as primary
    primary = tuple(obj.evidence_event_ids)
    context: tuple[str, ...] = ()
    # if any onset has >2 notes, move inner tones to context? Keep simple: scalar stays primary-only.
    label = f"{(obj.hand or '').upper() or 'Both'} {CHUNK_LABELS.get('run', 'Run')} — {direction}"
    if obj.hand:
        prefix = "RH" if obj.hand == "right" else "LH" if obj.hand == "left" else obj.hand
        label = f"{prefix} {direction} run"
    else:
        label = f"{direction} run"
    # capitalize first
    label = label[0].upper() + label[1:] if label else "Run"
    return PracticeChunk(
        chunk_id=_make_chunk_id(counter, "run", obj.hand, obj.start_onset),
        kind="run",
        label=label,
        hand=obj.hand,
        voice=None,
        role="run",
        staff=events[0].staff if events else None,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        primary_event_ids=primary,
        context_event_ids=context,
        child_chunk_ids=(),
        parent_chunk_id=None,
        source_object_ids=(obj.object_id,),
        source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
        traits=tuple(traits),
        practice_affordances=afford,
        confidence=float(obj.confidence) * 0.95,
        caveats=tuple(obj.caveats),
        payload={"source_object": obj.object_id, "direction": direction, "steps": obj.payload.get("steps"), "interval_pattern": obj.payload.get("interval_pattern")},
    )


def _chunks_from_scalar_run_split(obj: MusicalObject, bundle: SemanticBundle, counter: list[int]) -> list[PracticeChunk]:
    """Split scalar run object at rest/gap boundaries into multiple run chunks."""
    events = _events_for_ids(bundle, obj.evidence_event_ids)
    if len(events) < 2:
        return [_chunk_from_scalar_run(obj, bundle, counter)]
    # Sort by onset
    events_sorted = sorted(events, key=lambda e: e.onset)
    segments: list[list[ScoreEvent]] = []
    cur: list[ScoreEvent] = [events_sorted[0]]
    for prev, cur_ev in zip(events_sorted, events_sorted[1:]):
        gap = cur_ev.onset - prev.end
        # Rest or large temporal gap indicates boundary
        has_rest = _has_rest_between(bundle, prev.end, cur_ev.onset, obj.hand)
        large_gap = gap > Fraction(3, 2)
        # Also check onset gap >2
        onset_gap = cur_ev.onset - prev.onset
        very_large = onset_gap > Fraction(2)
        if has_rest or large_gap or very_large:
            segments.append(cur)
            cur = [cur_ev]
        else:
            cur.append(cur_ev)
    segments.append(cur)
    if len(segments) == 1:
        return [_chunk_from_scalar_run(obj, bundle, counter)]
    out: list[PracticeChunk] = []
    for seg in segments:
        if len(seg) < 3:
            # need at least 3 notes to be a meaningful run; skip tiny fragments
            continue
        seg_ids = tuple(ev.event_id for ev in seg)
        seg_start = min(ev.onset for ev in seg)
        seg_end = max(ev.end for ev in seg)
        ms = min(ev.measure_index for ev in seg if ev.measure_index is not None) if any(ev.measure_index is not None for ev in seg) else obj.measure_start
        me = max(ev.measure_index for ev in seg if ev.measure_index is not None) if any(ev.measure_index is not None for ev in seg) else obj.measure_end
        mns = tuple(sorted({str(ev.measure_number) for ev in seg if ev.measure_number}, key=_measure_sort_key)) or obj.measure_numbers
        bs, be = _beat_for_events(seg)
        direction = obj.payload.get("direction", "up" if obj.object_id == "ascending_scalar_run" else "down")
        traits = ["scalar", direction]
        afford = _affordances_for("run", tuple(traits))
        label = f"{'RH' if obj.hand=='right' else 'LH' if obj.hand=='left' else ''} {direction} run".strip() or "Run"
        if label:
            label = label[0].upper() + label[1:]
        # confidence slightly lower for split pieces
        out.append(PracticeChunk(
            chunk_id=_make_chunk_id(counter, "run", obj.hand, seg_start),
            kind="run",
            label=label,
            hand=obj.hand,
            voice=None,
            role="run",
            staff=seg[0].staff if seg else None,
            start_onset=seg_start,
            end_onset=seg_end,
            measure_start=ms,
            measure_end=me,
            measure_numbers=mns,
            beat_start=bs,
            beat_end=be,
            primary_event_ids=seg_ids,
            context_event_ids=(),
            child_chunk_ids=(),
            parent_chunk_id=None,
            source_object_ids=(obj.object_id,),
            source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
            traits=tuple(traits),
            practice_affordances=afford,
            confidence=float(obj.confidence) * 0.92,
            caveats=tuple(obj.caveats) + ("split_at_gap_rest",) if len(segments) > 1 else tuple(obj.caveats),
            payload={"source_object": obj.object_id, "direction": direction, "steps": len(seg), "segment": True},
        ))
    return out if out else [_chunk_from_scalar_run(obj, bundle, counter)]


def _chunk_from_arpeggio(obj: MusicalObject, bundle: SemanticBundle, counter: list[int]) -> tuple[PracticeChunk, list[PracticeChunk]]:
    """Return (parent, children) where children are ascent/descent/turn/landing subchunks."""
    events = _events_for_ids(bundle, obj.evidence_event_ids)
    reps = _median_pitch_per_onset(events)
    beat_start, beat_end = _beat_for_events(events)
    intervals = [reps[i+1][1] - reps[i][1] for i in range(len(reps)-1)] if len(reps) >= 2 else []
    # Determine traits
    traits: list[str] = ["arpeggiated"]
    if any(abs(iv) in (3,4) for iv in intervals):
        traits.append("thirds_stack")
    # Build children by direction segments
    children: list[PracticeChunk] = []
    temp_parent_id = _make_chunk_id(counter, "arpeggio_sweep", obj.hand, obj.start_onset)
    # Find peak indices for turn
    if len(reps) >= 3 and intervals:
        # identify direction per interval
        dirs = ["up" if iv > 0 else "down" if iv < 0 else "flat" for iv in intervals]
        # segments: group consecutive same direction
        seg_start = 0
        seg_dir = dirs[0] if dirs else "up"
        segments: list[tuple[int,int,str]] = []  # start_idx, end_idx inclusive reps, dir
        for idx in range(1, len(dirs)):
            if dirs[idx] != seg_dir:
                # end segment at idx (reps idx)
                segments.append((seg_start, idx, seg_dir))
                seg_start = idx
                seg_dir = dirs[idx]
        segments.append((seg_start, len(reps)-1, seg_dir))
        # If only one segment, keep parent without turn children but still split ascent/descent single
        if len(segments) == 1:
            # single direction sweep -> one child ascent or descent
            kind_child = "ascent" if segments[0][2] == "up" else "descent" if segments[0][2] == "down" else "ascent"
            s, e, d = segments[0]
            onset_start = reps[s][0]
            onset_end = reps[e][0]
            ev_ids = tuple(eid for k in range(s, e+1) for eid in reps[k][2] if hasattr(reps[k][2][0], 'event_id') for eid in [reps[k][2][i].event_id for i in range(len(reps[k][2]))])
            # Simpler: collect via rep event objects
            ev_ids2: list[str] = []
            for k in range(s, e+1):
                for ev in reps[k][2]:
                    ev_ids2.append(ev.event_id)
            ev_ids = tuple(dict.fromkeys(ev_ids2))
            if ev_ids:
                ms = min(ev.measure_index for ev in _events_for_ids(bundle, ev_ids) if ev.measure_index is not None) if ev_ids else obj.measure_start
                me = max(ev.measure_index for ev in _events_for_ids(bundle, ev_ids) if ev.measure_index is not None) if ev_ids else obj.measure_end
                mns = tuple(sorted({str(ev.measure_number) for ev in _events_for_ids(bundle, ev_ids) if ev.measure_number}, key=_measure_sort_key)) or obj.measure_numbers
                bs, be = _beat_for_events(_events_for_ids(bundle, ev_ids))
                child = PracticeChunk(
                    chunk_id=_make_chunk_id(counter, kind_child, obj.hand, onset_start),
                    kind=kind_child,
                    label=kind_child.capitalize(),
                    hand=obj.hand,
                    voice=None,
                    role=kind_child,
                    staff=events[0].staff if events else None,
                    start_onset=onset_start,
                    end_onset=onset_end,
                    measure_start=ms,
                    measure_end=me,
                    measure_numbers=mns,
                    beat_start=bs,
                    beat_end=be,
                    primary_event_ids=ev_ids,
                    context_event_ids=(),
                    child_chunk_ids=(),
                    parent_chunk_id=temp_parent_id,
                    source_object_ids=(obj.object_id,),
                    source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
                    traits=(d,),
                    practice_affordances=_affordances_for(kind_child, (d,)),
                    confidence=float(obj.confidence) * 0.9,
                    caveats=(),
                    payload={"segment_intervals": tuple(intervals[s:e]) if s<e else ()},
                )
                children.append(child)
        else:
            # multiple segments -> create child per segment plus turn at boundary
            for idx, (s, e, d) in enumerate(segments):
                kind_child = "ascent" if d == "up" else "descent" if d == "down" else "ascent"
                # For segments that are single peak within longer, boundary is turn
                # we will create segment child covering its reps
                onset_start = reps[s][0]
                onset_end = reps[e][0]
                ev_ids2: list[str] = []
                for k in range(s, e+1):
                    for ev in reps[k][2]:
                        ev_ids2.append(ev.event_id)
                ev_ids = tuple(dict.fromkeys(ev_ids2))
                if not ev_ids:
                    continue
                ms = min(ev.measure_index for ev in _events_for_ids(bundle, ev_ids) if ev.measure_index is not None) if ev_ids else obj.measure_start
                me = max(ev.measure_index for ev in _events_for_ids(bundle, ev_ids) if ev.measure_index is not None) if ev_ids else obj.measure_end
                mns = tuple(sorted({str(ev.measure_number) for ev in _events_for_ids(bundle, ev_ids) if ev.measure_number}, key=_measure_sort_key)) or obj.measure_numbers
                bs, be = _beat_for_events(_events_for_ids(bundle, ev_ids))
                child = PracticeChunk(
                    chunk_id=_make_chunk_id(counter, kind_child, obj.hand, onset_start),
                    kind=kind_child,
                    label=kind_child.capitalize(),
                    hand=obj.hand,
                    voice=None,
                    role=kind_child,
                    staff=events[0].staff if events else None,
                    start_onset=onset_start,
                    end_onset=onset_end,
                    measure_start=ms,
                    measure_end=me,
                    measure_numbers=mns,
                    beat_start=bs,
                    beat_end=be,
                    primary_event_ids=ev_ids,
                    context_event_ids=(),
                    child_chunk_ids=(),
                    parent_chunk_id=temp_parent_id,
                    source_object_ids=(obj.object_id,),
                    source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
                    traits=(d,),
                    practice_affordances=_affordances_for(kind_child, (d,)),
                    confidence=float(obj.confidence) * 0.9,
                    caveats=(),
                    payload={"segment_intervals": tuple(intervals[s:e]) if s<e else ()},
                )
                children.append(child)
                # add turn at boundary if not last
                if idx < len(segments)-1:
                    # turn is the pivot onset (reps[e]) shared
                    turn_onset = reps[e][0]
                    turn_evts = reps[e][2]
                    turn_ids = tuple(ev.event_id for ev in turn_evts)
                    # turn spans minimal duration
                    turn_end = turn_evts[0].end if turn_evts else turn_onset + Fraction(1,4)
                    ms_t = turn_evts[0].measure_index if turn_evts else ms
                    mns_t = (turn_evts[0].measure_number,) if turn_evts and turn_evts[0].measure_number else mns
                    bs_t = turn_evts[0].beat if turn_evts else None
                    turn_child = PracticeChunk(
                        chunk_id=_make_chunk_id(counter, "turn", obj.hand, turn_onset),
                        kind="turn",
                        label="Turn",
                        hand=obj.hand,
                        voice=None,
                        role="turn",
                        staff=events[0].staff if events else None,
                        start_onset=turn_onset,
                        end_onset=turn_end,
                        measure_start=ms_t,
                        measure_end=ms_t,
                        measure_numbers=mns_t if isinstance(mns_t, tuple) else (mns_t,),
                        beat_start=bs_t,
                        beat_end=bs_t,
                        primary_event_ids=turn_ids,
                        context_event_ids=(),
                        child_chunk_ids=(),
                        parent_chunk_id=temp_parent_id,
                        source_object_ids=(obj.object_id,),
                        source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
                        traits=("turn",),
                        practice_affordances=_affordances_for("turn", ("turn",)),
                        confidence=float(obj.confidence) * 0.85,
                        caveats=(),
                        payload={"pivot_midi": reps[e][1]},
                    )
                    children.append(turn_child)
            # optionally add landing as final chord shape if span suggests
            # landing is last onset if it has chord (>=2 notes) and prior sweep
            last_onset = reps[-1][0]
            last_evts = reps[-1][2]
            if len(last_evts) >= 2:
                # already have descent child covering last; landing overlaps but distinct role
                # create landing child covering last onset's chord
                landing_ids = tuple(ev.event_id for ev in last_evts)
                landing_end = max(ev.end for ev in last_evts)
                ms_l = last_evts[0].measure_index
                mns_l = (last_evts[0].measure_number,) if last_evts[0].measure_number else obj.measure_numbers
                bs_l = last_evts[0].beat
                landing_child = PracticeChunk(
                    chunk_id=_make_chunk_id(counter, "landing", obj.hand, last_onset),
                    kind="landing",
                    label="Landing",
                    hand=obj.hand,
                    voice=None,
                    role="landing",
                    staff=events[0].staff if events else None,
                    start_onset=last_onset,
                    end_onset=landing_end,
                    measure_start=ms_l,
                    measure_end=ms_l,
                    measure_numbers=mns_l if isinstance(mns_l, tuple) else (mns_l,),
                    beat_start=bs_l,
                    beat_end=bs_l,
                    primary_event_ids=landing_ids,
                    context_event_ids=(),
                    child_chunk_ids=(),
                    parent_chunk_id=temp_parent_id,
                    source_object_ids=(obj.object_id,),
                    source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
                    traits=("landing",),
                    practice_affordances=_affordances_for("landing", ("landing",)),
                    confidence=float(obj.confidence) * 0.88,
                    caveats=(),
                    payload={"note_count": len(last_evts)},
                )
                children.append(landing_child)
    else:
        # no reps intervals -> children empty
        pass

    # sort children by onset
    children = sorted(children, key=lambda c: c.start_onset)
    # fix child ids after sorting? ids already set; keep parent child list ordered
    child_ids = tuple(c.chunk_id for c in children)
    parent = PracticeChunk(
        chunk_id=temp_parent_id,
        kind="arpeggio_sweep",
        label=f"{(obj.hand or '').upper() or 'Both'} arpeggio sweep" if obj.hand else "Arpeggio sweep",
        hand=obj.hand,
        voice=None,
        role="arpeggio_sweep",
        staff=events[0].staff if events else None,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        primary_event_ids=tuple(obj.evidence_event_ids),
        context_event_ids=(),
        child_chunk_ids=child_ids,
        parent_chunk_id=None,
        source_object_ids=(obj.object_id,),
        source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
        traits=tuple(traits),
        practice_affordances=_affordances_for("arpeggio_sweep", tuple(traits)),
        confidence=float(obj.confidence) * 0.93,
        caveats=tuple(obj.caveats),
        payload={"interval_pattern": tuple(intervals[:8]) if intervals else (), "child_count": len(children)},
    )
    # need to ensure children point to final parent id (already)
    return parent, children


def _chunk_from_octave(obj: MusicalObject, bundle: SemanticBundle, counter: list[int]) -> PracticeChunk:
    events = _events_for_ids(bundle, obj.evidence_event_ids)
    # group by onset
    by_onset: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        by_onset[e.onset].append(e)
    primary_ids: list[str] = []
    context_ids: list[str] = []
    for onset in sorted(by_onset.keys()):
        evts = sorted(by_onset[onset], key=lambda x: x.pitch_midi or 0)
        if len(evts) < 2:
            primary_ids.extend(ev.event_id for ev in evts)
            continue
        mids = [ev.pitch_midi for ev in evts if ev.pitch_midi is not None]
        if len(mids) >= 2 and max(mids) - min(mids) == 12 and len(evts) == 2:
            # exact octave
            primary_ids.extend(ev.event_id for ev in evts)
        elif len(evts) >= 3:
            # mixed: outer octave + inner
            low = min(evts, key=lambda x: x.pitch_midi or 999)
            high = max(evts, key=lambda x: x.pitch_midi or -1)
            # check outer span 12
            if low.pitch_midi is not None and high.pitch_midi is not None and high.pitch_midi - low.pitch_midi == 12:
                primary_ids.extend([low.event_id, high.event_id])
                # inner others are context
                for ev in evts:
                    if ev.event_id not in (low.event_id, high.event_id):
                        context_ids.append(ev.event_id)
            else:
                # fallback preserve outer pair as primary
                primary_ids.extend([low.event_id, high.event_id])
                for ev in evts:
                    if ev.event_id not in (low.event_id, high.event_id):
                        context_ids.append(ev.event_id)
        else:
            # two notes not octave? still primary
            primary_ids.extend(ev.event_id for ev in evts)
    # dedup preserve order
    primary_ids = list(dict.fromkeys(primary_ids))
    context_ids = list(dict.fromkeys(context_ids))
    beat_start, beat_end = _beat_for_events(events)
    traits: list[str] = ["octave_doubled"]
    is_mixed = obj.payload.get("is_mixed") or "mixed_octave_plus_other_tones" in obj.caveats or obj.payload.get("is_exact_doubling") is False
    if is_mixed or context_ids:
        traits.append("mixed_with_inner_voices")
    else:
        traits.append("exact_octave")
    if len(primary_ids) >= 4:
        traits.append("parallel_octaves")
    label = f"{'RH' if obj.hand=='right' else 'LH' if obj.hand=='left' else ''} octave-doubled melody".strip()
    if not label or label == "octave-doubled melody":
        label = "Octave-doubled melody"
    else:
        label = label[0].upper() + label[1:] if label else "Octave-doubled melody"
    afford = _affordances_for("octave_doubled_melody", tuple(traits))
    # source feature refs include object's tokens/gestures
    return PracticeChunk(
        chunk_id=_make_chunk_id(counter, "octave_doubled_melody", obj.hand, obj.start_onset),
        kind="octave_doubled_melody",
        label=label,
        hand=obj.hand,
        voice=None,
        role="melody",
        staff=events[0].staff if events else None,
        start_onset=obj.start_onset,
        end_onset=obj.end_onset,
        measure_start=obj.measure_start,
        measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers,
        beat_start=beat_start,
        beat_end=beat_end,
        primary_event_ids=tuple(primary_ids),
        context_event_ids=tuple(context_ids),
        child_chunk_ids=(),
        parent_chunk_id=None,
        source_object_ids=(obj.object_id,),
        source_feature_refs=tuple(obj.token_ids) + tuple(obj.gesture_ids),
        traits=tuple(traits),
        practice_affordances=afford,
        confidence=float(obj.confidence) * 0.95,
        caveats=tuple(obj.caveats),
        payload={"octave_count": obj.payload.get("octave_count"), "direction": obj.payload.get("direction"), "is_mixed": bool(is_mixed or context_ids)},
    )


def _chunk_from_layered(obj: MusicalObject, bundle: SemanticBundle, counter: list[int]) -> tuple[PracticeChunk, list[PracticeChunk]]:
    events = _events_for_ids(bundle, obj.evidence_event_ids)
    # Determine low vs high bands by pitch gap >=12 or by sustained vs moving
    # Simple: sort mids, median split if gap >=12
    mids = sorted([e.pitch_midi for e in events if e.pitch_midi is not None])
    if not mids:
        # fallback
        beat_start, beat_end = _beat_for_events(events)
        parent = PracticeChunk(
            chunk_id=_make_chunk_id(counter, "layered_texture", obj.hand, obj.start_onset),
            kind="layered_texture",
            label="Layered texture",
            hand=obj.hand, voice=None, role="layered", staff=events[0].staff if events else None,
            start_onset=obj.start_onset, end_onset=obj.end_onset,
            measure_start=obj.measure_start, measure_end=obj.measure_end,
            measure_numbers=obj.measure_numbers, beat_start=beat_start, beat_end=beat_end,
            primary_event_ids=tuple(obj.evidence_event_ids), context_event_ids=(),
            child_chunk_ids=(), parent_chunk_id=None,
            source_object_ids=(obj.object_id,), source_feature_refs=tuple(obj.token_ids)+tuple(obj.gesture_ids),
            traits=("layered",), practice_affordances=_affordances_for("layered_texture", ("layered",)),
            confidence=float(obj.confidence)*0.95, caveats=tuple(obj.caveats), payload={}
        )
        return parent, []
    # Attempt to find gap
    # group by onset to detect sustained low
    by_onset = defaultdict(list)
    for e in events:
        by_onset[e.onset].append(e)
    # Determine low/high threshold: if we have single sustained low note (as in test), low is lowest midi duplicated
    # Use pitch_band_gap_semitones from payload if present
    gap = obj.payload.get("pitch_band_gap_semitones") or obj.payload.get("voice_band_gap_semitones") or 12
    # Find median cut where gap >=12
    # For test: lowest 36 vs upper 60-67 -> gap 24
    # General: split at largest gap >=12
    sorted_unique = sorted(set(mids))
    cut = None
    max_gap = 0
    for i in range(len(sorted_unique)-1):
        g = sorted_unique[i+1]-sorted_unique[i]
        if g >= 12 and g > max_gap:
            max_gap = g
            cut = (sorted_unique[i] + sorted_unique[i+1])//2
    if cut is None:
        # fallback: use median of pitch range
        cut = mids[len(mids)//2]
    low_events = [e for e in events if e.pitch_midi is not None and e.pitch_midi <= cut]
    high_events = [e for e in events if e.pitch_midi is not None and e.pitch_midi > cut]
    if not low_events or not high_events:
        # split by half count
        low_events = events[:len(events)//2]
        high_events = events[len(events)//2:]
    # Create child layer chunks
    parent_id = _make_chunk_id(counter, "layered_texture", obj.hand, obj.start_onset)
    children: list[PracticeChunk] = []
    for role, evs, kind_child in [("low", low_events, "layer"), ("high", high_events, "layer")]:
        if not evs:
            continue
        ev_ids = tuple(ev.event_id for ev in evs)
        evs_sorted = sorted(evs, key=lambda x: x.onset)
        ms = min(ev.measure_index for ev in evs if ev.measure_index is not None) if any(ev.measure_index is not None for ev in evs) else obj.measure_start
        me = max(ev.measure_index for ev in evs if ev.measure_index is not None) if any(ev.measure_index is not None for ev in evs) else obj.measure_end
        mns = tuple(sorted({str(ev.measure_number) for ev in evs if ev.measure_number}, key=_measure_sort_key)) or obj.measure_numbers
        bs, be = _beat_for_events(evs)
        label = f"{role.capitalize()} layer"
        child = PracticeChunk(
            chunk_id=_make_chunk_id(counter, kind_child, obj.hand, evs_sorted[0].onset),
            kind="layer",
            label=label,
            hand=obj.hand,
            voice=None,
            role=role,
            staff=evs[0].staff if evs else None,
            start_onset=min(ev.onset for ev in evs),
            end_onset=max(ev.end for ev in evs),
            measure_start=ms,
            measure_end=me,
            measure_numbers=mns,
            beat_start=bs,
            beat_end=be,
            primary_event_ids=ev_ids,
            context_event_ids=(),
            child_chunk_ids=(),
            parent_chunk_id=parent_id,
            source_object_ids=(obj.object_id,),
            source_feature_refs=tuple(obj.token_ids)+tuple(obj.gesture_ids),
            traits=(role,),
            practice_affordances=_affordances_for("layer", (role,)),
            confidence=float(obj.confidence)*0.9,
            caveats=(),
            payload={"layer_role": role, "note_count": len(evs)},
        )
        children.append(child)
    children = sorted(children, key=lambda c: (c.role != "low", c.start_onset))
    child_ids = tuple(c.chunk_id for c in children)
    beat_start, beat_end = _beat_for_events(events)
    parent = PracticeChunk(
        chunk_id=parent_id,
        kind="layered_texture",
        label=f"{'RH' if obj.hand=='right' else 'LH' if obj.hand=='left' else ''} layered texture".strip() or "Layered texture",
        hand=obj.hand, voice=None, role="layered", staff=events[0].staff if events else None,
        start_onset=obj.start_onset, end_onset=obj.end_onset,
        measure_start=obj.measure_start, measure_end=obj.measure_end,
        measure_numbers=obj.measure_numbers, beat_start=beat_start, beat_end=beat_end,
        primary_event_ids=tuple(obj.evidence_event_ids),
        context_event_ids=(),
        child_chunk_ids=child_ids,
        parent_chunk_id=None,
        source_object_ids=(obj.object_id,),
        source_feature_refs=tuple(obj.token_ids)+tuple(obj.gesture_ids),
        traits=("layered", "same_hand_multi_voice"),
        practice_affordances=_affordances_for("layered_texture", ("layered",)),
        confidence=float(obj.confidence)*0.93,
        caveats=tuple(obj.caveats),
        payload={"pitch_band_gap_semitones": max_gap or gap, "low_count": len(low_events), "high_count": len(high_events)},
    )
    return parent, children


# ---------------------------------------------------------------------------
# General grouping / fallback and chordal texture helpers
# ---------------------------------------------------------------------------

def _detect_chordal_texture_chunks(bundle: SemanticBundle, markings: list[Any], counter: list[int]) -> list[PracticeChunk]:
    """General rolled/chordal texture detection — not passage-specific."""
    events = [e for e in bundle.events if not e.is_rest]
    if len(events) < 4:
        return []
    by_onset: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        by_onset[e.onset].append(e)
    sorted_onsets = sorted(by_onset.keys())
    # Find runs of chordal onsets (ge 2 notes) with gap <=1.5 quarters
    runs: list[list[Fraction]] = []
    cur: list[Fraction] = []
    prev_onset: Fraction | None = None
    for onset in sorted_onsets:
        evs = by_onset[onset]
        is_chordal = len(evs) >= 2
        # also consider per-hand chordality
        if not is_chordal:
            # per-hand check: if any hand has >=2 notes at onset, treat as chordal
            for hand in ("right","left"):
                if len([e for e in evs if e.hand == hand]) >=2:
                    is_chordal = True
                    break
        if is_chordal:
            if prev_onset is not None and cur:
                gap = onset - prev_onset
                if gap > Fraction(4):  # allow up to 4 quarters for slow chordal passages (e.g., 9/8)
                    # break run if large gap
                    if len(cur) >= 3:
                        runs.append(cur)
                    cur = []
            cur.append(onset)
        else:
            # non-chordal breaks unless density still high? keep cur if gap small and next chordal nearby?
            if cur:
                # check if next onset within 1 quarter is chordal; keep tolerant one gap
                # for now close run
                pass
            if cur and len(cur) >= 3:
                # but chordal sequence ended — close if gap to next chordal would be large
                # we'll close immediately
                runs.append(cur)
                cur = []
        prev_onset = onset
    if cur and len(cur) >= 3:
        runs.append(cur)
    # Also consider spans with dense simultaneities across both hands
    # If no run found but overall chordal density high (>=50% onsets chordal), make single texture chunk for whole passage
    if not runs:
        total = len(sorted_onsets)
        chordal_cnt = sum(1 for o in sorted_onsets if len(by_onset[o]) >=2 or any(len([e for e in by_onset[o] if e.hand==h])>=2 for h in ("right","left")))
        if total >= 4 and chordal_cnt / total >= 0.5:
            runs = [sorted_onsets[:]]  # whole passage as one run (but filter to chordal only onsets for primary)
            # keep only chordal onsets for run
            runs[0] = [o for o in sorted_onsets if len(by_onset[o]) >=2 or any(len([e for e in by_onset[o] if e.hand==h])>=2 for h in ("right","left"))]
            if len(runs[0]) < 3:
                runs = []
    # Prioritize runs with rolled evidence / hand_overlap / larger chordal count for practice relevance
    # Compute wscore for each run
    scored_runs: list[tuple[int, int, list[Fraction]]] = []
    for r in runs:
        if len(r) < 3:
            continue
        # count rolled evidence
        rolled = 0
        for o in r:
            if any(getattr(e, "is_arpeggiated", False) for e in by_onset[o]):
                rolled += 1
        scored_runs.append((rolled, len(r), r))
    # sort: rolled first, then longer runs
    scored_runs.sort(key=lambda x: (x[0], x[1]), reverse=True)
    # take top runs but ensure onset order for stable ids is later sorted? We'll create in scored order then sort output later.
    # limit to top 8 runs to avoid flood
    scored_runs = scored_runs[:8]
    out: list[PracticeChunk] = []
    for _, _, onset_run in scored_runs:
        # Collect events for primary (chordal onsets only)
        primary_events: list[ScoreEvent] = []
        for o in onset_run:
            primary_events.extend(by_onset[o])
        if len(primary_events) < 6:
            continue
        # Check for rolled chord evidence: arpeggiated flags present in any primary event
        has_roll = any(getattr(e, "is_arpeggiated", False) for e in primary_events)
        # Hand overlap
        hand_overlap = len({e.hand for e in primary_events if e.hand in ("right","left")}) >=2 and any(by_onset[o] and len({e.hand for e in by_onset[o]})>=2 for o in onset_run)
        if not hand_overlap:
            # check cross-hand simultaneity at any onset
            for o in onset_run:
                evs = by_onset[o]
                if len({e.hand for e in evs if e.hand in ("right","left")}) >=2:
                    hand_overlap = True
                    break
        start = min(o for o in onset_run)
        # compute end as max end among primary_events
        end = max(e.end for e in primary_events)
        ms = min(e.measure_index for e in primary_events if e.measure_index is not None) if any(e.measure_index is not None for e in primary_events) else None
        me = max(e.measure_index for e in primary_events if e.measure_index is not None) if any(e.measure_index is not None for e in primary_events) else None
        mns = tuple(sorted({str(e.measure_number) for e in primary_events if e.measure_number}, key=_measure_sort_key)) or ()
        # Beat
        bs, be = _beat_for_events(primary_events)
        traits: list[str] = ["chord_sequence", "chordal_texture"]
        if has_roll:
            traits.extend(["rolled_chord", "rolled_chords"])
        if hand_overlap:
            traits.append("hand_overlap")
        # dynamics shape across run
        dyn_shape = _infer_dynamic_shape(primary_events)
        if dyn_shape:
            traits.append(dyn_shape)
            traits.append("dynamic_shape")
        # wedge marking check
        try:
            hairpins = [m for m in markings if getattr(m, "kind", "") == "wedge_span" and not (m.end_onset is not None and m.end_onset <= start) and not (m.start_onset >= end)]
            if hairpins:
                hv = hairpins[0].value.lower()
                if "decrescendo" in hv or "diminuendo" in hv:
                    if "decrescendo" not in traits:
                        traits.append("decrescendo")
        except Exception:
            pass
        # Also check per-event dynamics for decrescendo hint (p in payload)
        label = "Chordal texture"
        if has_roll:
            label = "Rolled chordal phrase"
        elif hand_overlap:
            label = "Chordal texture (hands overlapping)"
        # Subchunks: individual chord onsets
        # Create parent id first
        parent_id = _make_chunk_id(counter, "chordal_texture", None if hand_overlap else (primary_events[0].hand if len({e.hand for e in primary_events})==1 else None), start)
        child_ids: list[str] = []
        children: list[PracticeChunk] = []
        for o in onset_run:
            evs = by_onset[o]
            # For chordal texture, keep all notes at onset as primary for child chord
            ev_ids = tuple(e.event_id for e in evs)
            child_bs, child_be = _beat_for_events(evs)
            child_ms = evs[0].measure_index
            child_mns = (evs[0].measure_number,) if evs[0].measure_number else mns[:1] if mns else ()
            child = PracticeChunk(
                chunk_id=_make_chunk_id(counter, "chord_shape", None, o),
                kind="chord_shape",
                label="Chord",
                hand=None if hand_overlap else evs[0].hand,
                voice=None,
                role="chord",
                staff=evs[0].staff,
                start_onset=o,
                end_onset=max(e.end for e in evs),
                measure_start=child_ms,
                measure_end=child_ms,
                measure_numbers=child_mns,
                beat_start=child_bs,
                beat_end=child_be,
                primary_event_ids=ev_ids,
                context_event_ids=(),
                child_chunk_ids=(),
                parent_chunk_id=parent_id,
                source_object_ids=(),
                source_feature_refs=(),
                traits=("chord",) + (("rolled_chord",) if any(getattr(e, "is_arpeggiated", False) for e in evs) else ()),
                practice_affordances=_affordances_for("chord_shape", ("chord",)),
                confidence=0.78,
                caveats=(),
                payload={"onset": str(o), "note_count": len(evs), "boundary_reason": "chordal_onset"},
            )
            child_ids.append(child.chunk_id)
            children.append(child)
        parent = PracticeChunk(
            chunk_id=parent_id,
            kind="chordal_texture",
            label=label,
            hand=None if hand_overlap else primary_events[0].hand,
            voice=None,
            role="texture",
            staff=None if hand_overlap else primary_events[0].staff,
            start_onset=start,
            end_onset=end,
            measure_start=ms,
            measure_end=me,
            measure_numbers=mns,
            beat_start=bs,
            beat_end=be,
            primary_event_ids=tuple(e.event_id for e in primary_events),
            context_event_ids=(),
            child_chunk_ids=tuple(child_ids),
            parent_chunk_id=None,
            source_object_ids=(),
            source_feature_refs=(),
            traits=tuple(dict.fromkeys(traits)),
            practice_affordances=_affordances_for("chordal_texture", tuple(traits)),
            confidence=0.70 if has_roll else 0.65,
            caveats=tuple(),
            payload={"chord_count": len(onset_run), "hand_overlap": hand_overlap, "rolled": has_roll, "boundary_reason": "repeated_chordal_simultaneities"},
        )
        # enrich parent with markings
        parent = _enrich_with_markings(parent, bundle, markings)
        out.append(parent)
        out.extend(children)
        # limit number of chordal parents to avoid flood
        if len([c for c in out if c.kind == "chordal_texture"]) >= 4:
            break
    return out


def _build_fallback_general_chunks(bundle: SemanticBundle, markings: list[Any], counter: list[int]) -> list[PracticeChunk]:
    """Ensure at least one musically coherent chunk for any non-empty passage."""
    events = [e for e in bundle.events if not e.is_rest]
    if not events:
        return []
    # Already have chordal textures? That may suffice, but also ensure passage/hand fallback if still sparse
    # Check if span has meaningful grouping beyond whole passage
    # Strategy: if events span >1 measure or >6 notes, create hand_stream per hand and passage parent
    out: list[PracticeChunk] = []
    by_hand: dict[str, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        key = e.hand if e.hand in ("right","left") else "unknown"
        by_hand[key].append(e)
    # passage bounds
    start = min(e.onset for e in events)
    end = max(e.end for e in events)
    ms = min(e.measure_index for e in events if e.measure_index is not None) if any(e.measure_index is not None for e in events) else None
    me = max(e.measure_index for e in events if e.measure_index is not None) if any(e.measure_index is not None for e in events) else None
    mns = tuple(sorted({str(e.measure_number) for e in events if e.measure_number}, key=_measure_sort_key))
    bs, be = _beat_for_events(events)
    # hand_stream chunks per hand if hand has >=3 notes
    for hand in ("right","left"):
        h_events = by_hand.get(hand, [])
        if len(h_events) < 3:
            continue
        h_start = min(e.onset for e in h_events)
        h_end = max(e.end for e in h_events)
        h_ms = min(e.measure_index for e in h_events if e.measure_index is not None) if any(e.measure_index is not None for e in h_events) else ms
        h_me = max(e.measure_index for e in h_events if e.measure_index is not None) if any(e.measure_index is not None for e in h_events) else me
        h_mns = tuple(sorted({str(e.measure_number) for e in h_events if e.measure_number}, key=_measure_sort_key)) or mns
        h_bs, h_be = _beat_for_events(h_events)
        traits: list[str] = ["hand_stream", hand]
        # rhythmic continuity: density
        duration = h_end - h_start
        density = len(h_events) / float(duration) if duration > 0 else 0
        if density >= 2:
            traits.append("dense")
        # check phrase markings
        phrase_marks = [m for m in markings if getattr(m, "kind", "") in ("slur","phrase") and any(e.onset == m.start_onset for e in h_events)]
        if phrase_marks:
            traits.append("phrase_mark")
        # check chordal
        chordal_cnt, total = _chordal_density(h_events)
        if chordal_cnt >=2:
            traits.append("chordal")
        chunk = PracticeChunk(
            chunk_id=_make_chunk_id(counter, "hand_stream", hand, h_start),
            kind="hand_stream",
            label=f"{'RH' if hand=='right' else 'LH'} stream",
            hand=hand,
            voice=None,
            role="stream",
            staff=h_events[0].staff if h_events else None,
            start_onset=h_start,
            end_onset=h_end,
            measure_start=h_ms,
            measure_end=h_me,
            measure_numbers=h_mns,
            beat_start=h_bs,
            beat_end=h_be,
            primary_event_ids=tuple(e.event_id for e in h_events),
            context_event_ids=(),
            child_chunk_ids=(),
            parent_chunk_id=None,
            source_object_ids=(),
            source_feature_refs=(),
            traits=tuple(dict.fromkeys(traits)),
            practice_affordances=_affordances_for("hand_stream", tuple(traits)),
            confidence=0.55,
            caveats=("fallback_chunk",),
            payload={"hand": hand, "note_count": len(h_events), "density_per_quarter": round(density,2), "boundary_reason": "hand_stream_fallback"},
        )
        chunk = _enrich_with_markings(chunk, bundle, markings)
        out.append(chunk)
    # If still no hand streams (e.g., all unknown hand), create passage chunk
    if not out:
        traits = ["passage", "fallback", "inferred"]
        if any(getattr(e, "is_arpeggiated", False) for e in events):
            traits.append("rolled_chord")
        chordal_cnt, _ = _chordal_density(events)
        if chordal_cnt >=2:
            traits.append("chordal_texture")
            traits.append("chord_sequence")
        # phrase prior
        if any(getattr(e, "has_slur_start", False) for e in events):
            traits.append("phrase_mark")
        # dynamic shape
        shape = _infer_dynamic_shape(events)
        if shape:
            traits.append(shape)
        chunk = PracticeChunk(
            chunk_id=_make_chunk_id(counter, "passage", None, start),
            kind="passage",
            label="Passage",
            hand=None,
            voice=None,
            role="passage",
            staff=None,
            start_onset=start,
            end_onset=end,
            measure_start=ms,
            measure_end=me,
            measure_numbers=mns,
            beat_start=bs,
            beat_end=be,
            primary_event_ids=tuple(e.event_id for e in events),
            context_event_ids=(),
            child_chunk_ids=(),
            parent_chunk_id=None,
            source_object_ids=(),
            source_feature_refs=(),
            traits=tuple(dict.fromkeys(traits)),
            practice_affordances=_affordances_for("passage", tuple(traits)),
            confidence=0.50,
            caveats=("fallback_chunk",),
            payload={"note_count": len(events), "boundary_reason": "passage_fallback"},
        )
        chunk = _enrich_with_markings(chunk, bundle, markings)
        out.append(chunk)
    else:
        # If we have hand streams but want also a passage parent when both hands present
        if len(out) >=2:
            # create passage parent grouping hand streams
            parent_id = _make_chunk_id(counter, "passage", None, start)
            child_ids = tuple(c.chunk_id for c in out)
            # patch children's parent ids
            patched: list[PracticeChunk] = []
            for c in out:
                patched.append(PracticeChunk(
                    chunk_id=c.chunk_id, kind=c.kind, label=c.label, hand=c.hand, voice=c.voice, role=c.role, staff=c.staff,
                    start_onset=c.start_onset, end_onset=c.end_onset, measure_start=c.measure_start, measure_end=c.measure_end,
                    measure_numbers=c.measure_numbers, beat_start=c.beat_start, beat_end=c.beat_end,
                    primary_event_ids=c.primary_event_ids, context_event_ids=c.context_event_ids,
                    child_chunk_ids=c.child_chunk_ids, parent_chunk_id=parent_id,
                    source_object_ids=c.source_object_ids, source_feature_refs=c.source_feature_refs,
                    traits=c.traits, practice_affordances=c.practice_affordances, confidence=c.confidence, caveats=c.caveats, payload=dict(c.payload)
                ))
            out = patched
            parent = PracticeChunk(
                chunk_id=parent_id,
                kind="passage",
                label="Passage",
                hand=None,
                voice=None,
                role="passage",
                staff=None,
                start_onset=start,
                end_onset=end,
                measure_start=ms,
                measure_end=me,
                measure_numbers=mns,
                beat_start=bs,
                beat_end=be,
                primary_event_ids=tuple(e.event_id for e in events),
                context_event_ids=(),
                child_chunk_ids=child_ids,
                parent_chunk_id=None,
                source_object_ids=(),
                source_feature_refs=(),
                traits=("passage", "both_hands", "fallback"),
                practice_affordances=_affordances_for("passage", ("passage","both_hands")),
                confidence=0.52,
                caveats=("fallback_chunk",),
                payload={"child_hands": tuple(sorted({c.hand for c in out if c.hand})), "boundary_reason": "hand_streams_parent"},
            )
            parent = _enrich_with_markings(parent, bundle, markings)
            out.append(parent)
    return out


def _segment_run_into_cells(bundle: SemanticBundle, counter: list[int]) -> list[PracticeChunk]:
    """Generic recursive segmentation of long runs/arpeggiating figures into cells.

    Uses contour reset, large leap/drop after ascent, repeated interval pattern,
    phrase mark boundary, rhythmic grouping, register reset.
    Returns parent+child cell chunks for suitable long dense passages.
    """
    out: list[PracticeChunk] = []
    for hand in ("right", "left"):
        hand_events = [e for e in bundle.events if e.hand == hand and not e.is_rest and e.pitch_midi is not None]
        if len(hand_events) < 6:
            continue
        reps = _median_pitch_per_onset(hand_events)
        if len(reps) < 6:
            continue
        # need high density and span
        onset_span = reps[-1][0] - reps[0][0]
        if onset_span <= 0:
            continue
        density = len(reps) / float(onset_span)
        if density < 1.5:
            continue
        span_pitch = max(r[1] for r in reps) - min(r[1] for r in reps)
        if span_pitch < 7:
            continue
        intervals = [reps[i+1][1] - reps[i][1] for i in range(len(reps)-1)]
        # Find cell boundaries: large drop after ascending run, repeated pattern, phrase mark, register reset
        boundaries: list[int] = [0]  # rep indices
        # heuristic: ascending streak >=3 with drop >5 signals cell end
        asc_start = 0
        for i in range(len(intervals)):
            iv = intervals[i]
            # check for phrase mark boundary at this onset
            has_phrase = any(getattr(e, "has_slur_start", False) or getattr(e, "phrase_start", False) for e in reps[i+1][2])
            # check large leap drop after ascent
            # need preceding run of up intervals
            # look back to find asc streak
            if has_phrase and i+1 not in boundaries:
                # phrase is boundary prior
                boundaries.append(i+1)
                asc_start = i+1
                continue
            if iv < -5:
                # potential reset after ascent
                # check if previous 2 intervals were up (>=2)
                if i >=2 and intervals[i-1] > 0 and intervals[i-2] > 0:
                    # drop magnitude large vs prior ups -> cell boundary
                    if i+1 < len(reps):
                        boundaries.append(i+1)
                        asc_start = i+1
                        continue
                elif i >=1 and intervals[i-1] > 0 and abs(iv) >= 7:
                    boundaries.append(i+1)
                    asc_start = i+1
                    continue
                # register reset: drop from high register >8
                if abs(iv) >= 7:
                    boundaries.append(i+1)
                    asc_start = i+1
                    continue
            # repeated interval pattern detection: check if interval pattern repeats after boundary
            # simple: if intervals[i:i+2] equals intervals[asc_start:asc_start+2] and distance >=3
            # mark as new cell when pattern repeats exactly
            if i - asc_start >= 3 and i+2 < len(intervals):
                pat_len = 2
                if intervals[i:i+pat_len] == intervals[asc_start:asc_start+pat_len] and i - asc_start >= pat_len:
                    # only add if not already close
                    if i+1 - boundaries[-1] >= 3:
                        boundaries.append(i)
                        asc_start = i
        boundaries.append(len(reps))
        # deduplicate and sort
        boundaries = sorted(set(boundaries))
        # need at least 2 cells with each >=3 reps and plausible
        if len(boundaries) < 3:
            continue
        # Filter to cells with >=3 reps
        cells: list[tuple[int,int]] = []
        for b_idx in range(len(boundaries)-1):
            s = boundaries[b_idx]
            e = boundaries[b_idx+1]
            if e - s >= 3:
                cells.append((s, e))
        if len(cells) < 2:
            continue
        # Create parent covering whole reps
        start = reps[0][0]
        end = reps[-1][0]
        # expand end to actual note end
        end = max(e.end for _,_, evs in reps for e in evs) if reps else end
        ms = min(e.measure_index for _,_, evs in reps for e in evs if e.measure_index is not None) if any(e.measure_index is not None for _,_, evs in reps for e in evs) else None
        me = max(e.measure_index for _,_, evs in reps for e in evs if e.measure_index is not None) if any(e.measure_index is not None for _,_, evs in reps for e in evs) else None
        mns = tuple(sorted({str(e.measure_number) for _,_, evs in reps for e in evs if e.measure_number}, key=_measure_sort_key))
        parent_id = _make_chunk_id(counter, "run", hand, start)
        child_ids: list[str] = []
        children: list[PracticeChunk] = []
        for cell_idx, (s,e) in enumerate(cells):
            onset_start = reps[s][0]
            onset_end = reps[e-1][0]
            ev_ids: list[str] = []
            for k in range(s, e):
                for ev in reps[k][2]:
                    ev_ids.append(ev.event_id)
            ev_ids_t = tuple(dict.fromkeys(ev_ids))
            if not ev_ids_t:
                continue
            # determine direction for cell
            cell_intervals = intervals[s:e-1] if s < e-1 else []
            direction = "ascent" if sum(1 for iv in cell_intervals if iv>0) > sum(1 for iv in cell_intervals if iv<0) else "descent"
            kind_child = "cell"
            # choose label
            label = f"Cell {cell_idx+1} ({direction})"
            bs, be = _beat_for_events(_events_for_ids(bundle, ev_ids_t))
            child = PracticeChunk(
                chunk_id=_make_chunk_id(counter, kind_child, hand, onset_start),
                kind=kind_child,
                label=label,
                hand=hand,
                voice=None,
                role="cell",
                staff=reps[s][2][0].staff if reps[s][2] else None,
                start_onset=onset_start,
                end_onset=onset_end,
                measure_start=min(e.measure_index for k in range(s,e) for e in reps[k][2] if e.measure_index is not None) if True else None,
                measure_end=max(e.measure_index for k in range(s,e) for e in reps[k][2] if e.measure_index is not None) if True else None,
                measure_numbers=tuple(sorted({str(e.measure_number) for k in range(s,e) for e in reps[k][2] if e.measure_number}, key=_measure_sort_key)),
                beat_start=bs,
                beat_end=be,
                primary_event_ids=ev_ids_t,
                context_event_ids=(),
                child_chunk_ids=(),
                parent_chunk_id=parent_id,
                source_object_ids=(),
                source_feature_refs=(),
                traits=(direction, "repeated_cell"),
                practice_affordances=_affordances_for(kind_child, (direction,)),
                confidence=0.60,
                caveats=(),
                payload={"cell_index": cell_idx+1, "boundary_reason": "contour_reset_or_leap_drop" if cell_idx>0 else "start", "intervals": tuple(cell_intervals[:6])},
            )
            child_ids.append(child.chunk_id)
            children.append(child)
        if len(children) < 2:
            continue
        # Also ensure we add turn/landing handling? Keep simple: parent + cells
        parent = PracticeChunk(
            chunk_id=parent_id,
            kind="run",
            label=f"{'RH' if hand=='right' else 'LH'} run ({len(cells)} cells)",
            hand=hand,
            voice=None,
            role="run",
            staff=reps[0][2][0].staff if reps[0][2] else None,
            start_onset=start,
            end_onset=end,
            measure_start=ms,
            measure_end=me,
            measure_numbers=mns,
            beat_start=None,
            beat_end=None,
            primary_event_ids=tuple(e.event_id for _,_, evs in reps for e in [ev.event_id for ev in evs]),
            context_event_ids=(),
            child_chunk_ids=tuple(child_ids),
            parent_chunk_id=None,
            source_object_ids=(),
            source_feature_refs=(),
            traits=("run", "segmented", "repeated_cells"),
            practice_affordances=_affordances_for("run", ("run","segmented")),
            confidence=0.62,
            caveats=("segmented_run",),
            payload={"cell_count": len(children), "span_semitones": span_pitch, "boundary_reason": "generic_cell_segmentation"},
        )
        # avoid duplicate if already have an arpeggio parent covering same span (within 1 quarter)
        already = False
        for existing in out:
            if existing.hand == hand and abs(existing.start_onset - parent.start_onset) < Fraction(1) and abs(existing.end_onset - parent.end_onset) < Fraction(1):
                already = True
                break
        if already:
            continue
        out.append(parent)
        out.extend(children)
    return out


def _build_phrase_parents(chunks: list[PracticeChunk], bundle: SemanticBundle, counter: list[int]) -> list[PracticeChunk]:
    """Create phrase parents grouping nearby chunks per hand if gap small and no rest between."""
    if len(chunks) < 2:
        return []
    # Group per hand — exclude fallback background chunks (they cover whole piece)
    filtered = [c for c in chunks if "fallback_chunk" not in c.caveats]
    if len(filtered) < 2:
        return []
    by_hand: dict[str | None, list[PracticeChunk]] = defaultdict(list)
    for c in filtered:
        if c.parent_chunk_id is not None:
            continue  # only top-level
        by_hand[c.hand].append(c)
    new_parents: list[PracticeChunk] = []
    for hand, lst in by_hand.items():
        if len(lst) < 2:
            continue
        lst = sorted(lst, key=lambda x: x.start_onset)
        # sliding window grouping
        window: list[PracticeChunk] = [lst[0]]
        for nxt in lst[1:]:
            prev = window[-1]
            gap = nxt.start_onset - prev.end_onset
            # gap threshold 1.5 quarters or rest; for scalar runs allow larger gap (up to 4 quarters) since they may be separated by measure boundary
            has_rest = _has_rest_between(bundle, prev.end_onset, nxt.start_onset, hand)
            gap_thresh = Fraction(4) if (prev.kind in ("run","scalar_run","arpeggio_sweep") and nxt.kind in ("run","scalar_run","arpeggio_sweep")) else Fraction(3, 2)
            large_gap = gap > gap_thresh
            if has_rest or large_gap:
                # flush window if >=2
                if len(window) >= 2:
                    # ensure not too wide (span < 8 quarters)
                    span = window[-1].end_onset - window[0].start_onset
                    if span <= Fraction(8):
                        parent = _make_phrase_parent(window, counter)
                        if parent is not None:
                            new_parents.append(parent)
                window = [nxt]
            else:
                window.append(nxt)
                # limit window size to avoid huge phrase
                if len(window) >= 4:
                    parent = _make_phrase_parent(window, counter)
                    if parent is not None:
                        new_parents.append(parent)
                    window = [nxt]
        if len(window) >= 2:
            span = window[-1].end_onset - window[0].start_onset
            if span <= Fraction(8) and not _has_rest_between(bundle, window[0].start_onset, window[-1].end_onset, hand):
                # check internal rests already handled; just check gap inside window not large
                parent = _make_phrase_parent(window, counter)
                if parent is not None:
                    new_parents.append(parent)
    return new_parents


def _make_phrase_parent(window: list[PracticeChunk], counter: list[int]) -> PracticeChunk | None:
    if len(window) < 2:
        return None
    # Ensure children are same hand or hand=None not mixed unexpectedly
    # Build parent covering window
    start = min(c.start_onset for c in window)
    end = max(c.end_onset for c in window)
    hand = window[0].hand if all(c.hand == window[0].hand for c in window) else None
    # merge measure numbers
    mns_set: dict[str, None] = {}
    for c in window:
        for m in c.measure_numbers:
            mns_set[m] = None
    mns = tuple(sorted(mns_set.keys(), key=_measure_sort_key)) if mns_set else window[0].measure_numbers
    ms = min((c.measure_start for c in window if c.measure_start is not None), default=window[0].measure_start)
    me = max((c.measure_end for c in window if c.measure_end is not None), default=window[0].measure_end)
    # beat
    beats = [c.beat_start for c in window if c.beat_start is not None] + [c.beat_end for c in window if c.beat_end is not None]
    bs = beats[0] if beats else None
    be = beats[-1] if beats else None
    primary = tuple(dict.fromkeys(eid for c in window for eid in c.primary_event_ids))
    context = tuple(dict.fromkeys(eid for c in window for eid in c.context_event_ids))
    # child ids should be ids of window members
    child_ids = tuple(c.chunk_id for c in window)
    # parent id
    pid = _make_chunk_id(counter, "phrase", hand, start)
    # Need to update children's parent id: we cannot mutate frozen children, so we will need to recreate.
    # However we treat parent as separate grouping; children retain original parent=None but logically are children of phrase.
    # To support hierarchy, we will keep children's parent_chunk_id as original (None) but parent lists them.
    # For UI we can rely on parent child ids only. Type allows this (overlap).
    # But spec says child_chunk_ids + parent_chunk_id — ideal is to re-issue children with updated parent.
    # We will instead store new parents and later patch children in post-process.
    return PracticeChunk(
        chunk_id=pid,
        kind="phrase",
        label="Phrase",
        hand=hand,
        voice=None,
        role="phrase",
        staff=window[0].staff,
        start_onset=start,
        end_onset=end,
        measure_start=ms,
        measure_end=me,
        measure_numbers=mns,
        beat_start=bs,
        beat_end=be,
        primary_event_ids=primary,
        context_event_ids=context,
        child_chunk_ids=child_ids,
        parent_chunk_id=None,
        source_object_ids=tuple(dict.fromkeys(oid for c in window for oid in c.source_object_ids)),
        source_feature_refs=tuple(dict.fromkeys(fid for c in window for fid in c.source_feature_refs)),
        traits=("phrase",),
        practice_affordances=_affordances_for("phrase", ("phrase",)),
        confidence=min(c.confidence for c in window) * 0.9,
        caveats=(),
        payload={"grouped_kinds": tuple(c.kind for c in window), "child_count": len(window)},
    )


def _build_coordination_chunks(bundle: SemanticBundle, chunks: list[PracticeChunk], counter: list[int]) -> list[PracticeChunk]:
    """Create coordination chunk if both hands have overlapping chunks."""
    # Check for onset_alignment tokens
    has_alignment = any(t.kind == "onset_alignment" for t in bundle.derived_tokens)
    if not has_alignment:
        return []
    # Check if we have left and right top-level chunks overlapping in time
    left = [c for c in chunks if c.hand == "left" and c.parent_chunk_id is None]
    right = [c for c in chunks if c.hand == "right" and c.parent_chunk_id is None]
    if not left or not right:
        return []
    # Find overlapping intervals
    out: list[PracticeChunk] = []
    for l in left:
        for r in right:
            # overlap if not disjoint
            if l.end_onset <= r.start_onset or r.end_onset <= l.start_onset:
                continue
            overlap_start = max(l.start_onset, r.start_onset)
            overlap_end = min(l.end_onset, r.end_onset)
            # Require at least some onset_alignment within overlap
            aligned_in_overlap = any(t.kind == "onset_alignment" and overlap_start <= t.start_onset < overlap_end for t in bundle.derived_tokens)
            if not aligned_in_overlap:
                continue
            # avoid duplicate coordination for same pair
            pid = _make_chunk_id(counter, "coordination", None, overlap_start)
            primary = tuple(dict.fromkeys(list(l.primary_event_ids) + list(r.primary_event_ids)))
            context = ()
            # merge measures
            mns = tuple(sorted(set(list(l.measure_numbers) + list(r.measure_numbers)), key=_measure_sort_key))
            ms = min(x for x in (l.measure_start, r.measure_start) if x is not None) if l.measure_start is not None or r.measure_start is not None else None
            me = max(x for x in (l.measure_end, r.measure_end) if x is not None) if l.measure_end is not None or r.measure_end is not None else None
            out.append(PracticeChunk(
                chunk_id=pid,
                kind="coordination",
                label="Coordination",
                hand=None,
                voice=None,
                role="coordination",
                staff=None,
                start_onset=overlap_start,
                end_onset=overlap_end,
                measure_start=ms,
                measure_end=me,
                measure_numbers=mns,
                beat_start=None,
                beat_end=None,
                primary_event_ids=primary,
                context_event_ids=context,
                child_chunk_ids=(l.chunk_id, r.chunk_id),
                parent_chunk_id=None,
                source_object_ids=tuple(dict.fromkeys(list(l.source_object_ids)+list(r.source_object_ids))),
                source_feature_refs=tuple(dict.fromkeys(list(l.source_feature_refs)+list(r.source_feature_refs))),
                traits=("coordination", "hands_together"),
                practice_affordances=_affordances_for("coordination", ("coordination",)),
                confidence=min(l.confidence, r.confidence) * 0.85,
                caveats=(),
                payload={"left_chunk": l.chunk_id, "right_chunk": r.chunk_id},
            ))
            if len(out) >= 2:
                return out
    return out


def _patch_phrase_children(parents: list[PracticeChunk], chunks: list[PracticeChunk]) -> list[PracticeChunk]:
    """Return new chunks list where phrase children get parent_chunk_id set."""
    if not parents:
        return chunks
    # map child_id -> parent_id (first parent that contains it)
    child_to_parent: dict[str, str] = {}
    for p in parents:
        for cid in p.child_chunk_ids:
            if cid not in child_to_parent:
                child_to_parent[cid] = p.chunk_id
    patched: list[PracticeChunk] = []
    for c in chunks:
        if c.chunk_id in child_to_parent and c.parent_chunk_id is None:
            # recreate with parent set
            patched.append(PracticeChunk(
                chunk_id=c.chunk_id,
                kind=c.kind,
                label=c.label,
                hand=c.hand,
                voice=c.voice,
                role=c.role,
                staff=c.staff,
                start_onset=c.start_onset,
                end_onset=c.end_onset,
                measure_start=c.measure_start,
                measure_end=c.measure_end,
                measure_numbers=c.measure_numbers,
                beat_start=c.beat_start,
                beat_end=c.beat_end,
                primary_event_ids=c.primary_event_ids,
                context_event_ids=c.context_event_ids,
                child_chunk_ids=c.child_chunk_ids,
                parent_chunk_id=child_to_parent[c.chunk_id],
                source_object_ids=c.source_object_ids,
                source_feature_refs=c.source_feature_refs,
                traits=c.traits,
                practice_affordances=c.practice_affordances,
                confidence=c.confidence,
                caveats=c.caveats,
                payload=dict(c.payload),
            ))
        else:
            patched.append(c)
    return patched


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def build_practice_chunks(bundle: SemanticBundle) -> tuple[PracticeChunk, ...]:
    """Build PracticeChunks from bundle evidence."""
    counter = [0]
    chunks: list[PracticeChunk] = []
    # Extract markings (thin normalized representation) from events
    try:
        markings = extract_markings_from_events(list(bundle.events))  # type: ignore
    except Exception:
        markings = []

    # 1. Scalar runs -> run chunks (split at rest/gap)
    for obj in bundle.musical_objects:
        if obj.object_id in ("ascending_scalar_run", "descending_scalar_run"):
            try:
                split = _chunks_from_scalar_run_split(obj, bundle, counter)
                # enrich scalar chunks with markings
                for c in split:
                    chunks.append(_enrich_with_markings(c, bundle, markings))
            except Exception:
                try:
                    c = _chunk_from_scalar_run(obj, bundle, counter)
                    chunks.append(_enrich_with_markings(c, bundle, markings))
                except Exception:
                    continue

    # 2. Arpeggio / broken chord -> arpeggio_sweep with subchunks
    for obj in bundle.musical_objects:
        if obj.object_id in ("broken_chord_accompaniment", "arpeggiated_accompaniment", "alberti_bass", "wide_broken_chord"):
            try:
                parent, children = _chunk_from_arpeggio(obj, bundle, counter)
                chunks.extend([_enrich_with_markings(ch, bundle, markings) for ch in children])
                chunks.append(_enrich_with_markings(parent, bundle, markings))
            except Exception:
                continue

    # 3. Octave doubled
    for obj in bundle.musical_objects:
        if obj.object_id == "octave_doubled_melody":
            try:
                c = _chunk_from_octave(obj, bundle, counter)
                chunks.append(_enrich_with_markings(c, bundle, markings))
            except Exception:
                continue

    # 4. Layered texture
    for obj in bundle.musical_objects:
        if obj.object_id == "single_hand_multi_voice_texture":
            try:
                parent, children = _chunk_from_layered(obj, bundle, counter)
                chunks.extend([_enrich_with_markings(ch, bundle, markings) for ch in children])
                chunks.append(_enrich_with_markings(parent, bundle, markings))
            except Exception:
                continue

    # If no chunks yet but we have chord / leap objects, create simple chunks for phrase test coverage
    # Generic fallback: create a run-like chunk from any scalar-like gesture even if object missing?
    # For now, ensure at least fallback from gestures scalar_run if objects empty
    if not chunks:
        from .models import Gesture as _G
        for g in bundle.gestures:
            if g.kind == "scalar_run":
                # create minimal run chunk from gesture
                try:
                    # synthesize a pseudo object
                    pseudo = MusicalObject(
                        object_id="ascending_scalar_run" if g.payload.get("direction")=="up" else "descending_scalar_run",
                        kind=g.payload.get("direction") or "ascending_scalar_run",
                        label="Scalar run",
                        hand=g.hand,
                        start_onset=g.start_onset,
                        end_onset=g.end_onset,
                        measure_start=g.measure_start,
                        measure_end=g.measure_end,
                        measure_numbers=g.measure_numbers,
                        evidence_event_ids=g.evidence_event_ids,
                        token_ids=g.token_ids,
                        gesture_ids=(g.gesture_id,),
                        confidence=g.confidence,
                        payload={"direction": g.payload.get("direction"), "steps": g.payload.get("steps")},
                        caveats=(),
                    )
                    c = _chunk_from_scalar_run(pseudo, bundle, counter)
                    chunks.append(_enrich_with_markings(c, bundle, markings))
                except Exception:
                    continue
    # Direct sweep fallback when no arpeggio_sweep yet but contour suggests sweep (e.g., ascent->descent)
    has_sweep = any(c.kind == "arpeggio_sweep" for c in chunks)
    if not has_sweep:
        for hand in ("right", "left"):
            # collect per-hand non-rest events
            hand_events = [e for e in bundle.events if e.hand == hand and not e.is_rest]
            if len(hand_events) < 5:
                continue
            reps = _median_pitch_per_onset(hand_events)
            if len(reps) < 5:
                continue
            intervals = [reps[i+1][1] - reps[i][1] for i in range(len(reps)-1)]
            if not intervals:
                continue
            # need at least one direction reversal and span >=7
            dirs = ["up" if iv > 0 else "down" if iv < 0 else "flat" for iv in intervals]
            has_reversal = any(dirs[i] != dirs[i+1] for i in range(len(dirs)-1) if dirs[i] != "flat" and dirs[i+1] != "flat")
            span = max(r[1] for r in reps) - min(r[1] for r in reps)
            # count intervals that are plausible arpeggio/triad steps (2-7)
            plausible = sum(1 for iv in intervals if 2 <= abs(iv) <= 7)
            if has_reversal and span >= 7 and plausible >= 3:
                # check temporal density: not too sparse (max gap <= 2)
                max_gap = max(reps[i+1][0] - reps[i][0] for i in range(len(reps)-1))
                if max_gap > Fraction(2):
                    continue
                # need close temporal proximity (span duration <=6)
                duration = reps[-1][0] - reps[0][0]
                if duration > Fraction(6):
                    continue
                # Create pseudo arpeggio object covering reps span
                ev_ids = tuple(eid for _, _, evts in reps for eid in [ev.event_id for ev in evts])
                # measure numbers
                mns_set: dict[str, None] = {}
                for _, _, evts in reps:
                    for ev in evts:
                        if ev.measure_number:
                            mns_set[str(ev.measure_number)] = None
                mns = tuple(sorted(mns_set.keys(), key=_measure_sort_key)) if mns_set else ()
                ms = min(ev.measure_index for _, _, evts in reps for ev in evts if ev.measure_index is not None) if any(ev.measure_index is not None for _, _, evts in reps for ev in evts) else None
                me = max(ev.measure_index for _, _, evts in reps for ev in evts if ev.measure_index is not None) if any(ev.measure_index is not None for _, _, evts in reps for ev in evts) else None
                pseudo_obj = MusicalObject(
                    object_id="arpeggiated_accompaniment",
                    kind="arpeggiated_accompaniment",
                    label="Arpeggiated accompaniment",
                    hand=hand,
                    start_onset=reps[0][0],
                    end_onset=reps[-1][0],
                    measure_start=ms,
                    measure_end=me,
                    measure_numbers=mns,
                    evidence_event_ids=ev_ids,
                    token_ids=(),
                    gesture_ids=(),
                    confidence=0.6,
                    payload={"interval_pattern": tuple(intervals), "direction": "mixed", "span_semitones": span},
                    caveats=("direct_contour_sweep_fallback",),
                )
                try:
                    parent, children = _chunk_from_arpeggio(pseudo_obj, bundle, counter)
                    chunks.extend([_enrich_with_markings(ch, bundle, markings) for ch in children])
                    chunks.append(_enrich_with_markings(parent, bundle, markings))
                    has_sweep = True
                    break  # only one direct sweep per bundle to avoid flood
                except Exception:
                    continue
    # -------------------------------------------------------------------
    # General texture / fallback layers — not passage hacks
    # -------------------------------------------------------------------
    # 5. Rolled/chordal texture chunking (general)
    try:
        chordal_chunks = _detect_chordal_texture_chunks(bundle, markings, counter)
        # chordal_chunks already enriched internally; add them
        chunks.extend(chordal_chunks)
    except Exception:
        pass
    # 6. Recursive segmentation of long runs into cells (generic)
    try:
        cell_chunks = _segment_run_into_cells(bundle, counter)
        # Avoid duplicating if parent already close to existing sweep/run
        for c in cell_chunks:
            # check not duplicate of existing primary
            is_dup = False
            for existing in chunks:
                if existing.kind == c.kind and existing.hand == c.hand and existing.start_onset == c.start_onset and existing.primary_event_ids == c.primary_event_ids:
                    is_dup = True
                    break
            if not is_dup:
                chunks.append(_enrich_with_markings(c, bundle, markings))
    except Exception:
        pass
    # 7. Ensure at least one fallback chunk for any non-empty passage (general grouping)
    has_non_empty = any(not e.is_rest for e in bundle.events)
    if has_non_empty:
        try:
            fallback_chunks = _build_fallback_general_chunks(bundle, markings, counter)
            # add fallback chunks even when specialized chunks exist, to guarantee any span has coverage;
            # they are low-confidence caveated and use general evidence, not cheap whole-passage only
            for fc in fallback_chunks:
                # avoid exact duplicate of existing chunk kind/start/primary
                is_dup = False
                for c in chunks:
                    if c.kind == fc.kind and c.start_onset == fc.start_onset and c.primary_event_ids == fc.primary_event_ids:
                        is_dup = True
                        break
                if not is_dup:
                    chunks.append(fc)
        except Exception:
            pass
    # Also enrich any chunks that were not yet enriched (fallback added later already enriched)
    # Ensure all existing chunks have marking enrichment if not already (chunks from fallback already enriched)
    # For safety, re-enrich any chunk missing dynamic info if it came before markings extraction
    # (No-op if already enriched)
    # -------------------------------------------------------------------

    # Deduplicate chunks that share identical primary and kind/time (e.g., broken+arpeggiated duplicate)
    # Keep highest confidence per (kind, start, hand, primary tuple)
    seen: dict[tuple, PracticeChunk] = {}
    for c in chunks:
        key = (c.kind, c.hand, c.start_onset, c.primary_event_ids)
        if key not in seen or c.confidence > seen[key].confidence:
            seen[key] = c
    # Need to handle arpeggio parent duplicates that were split; they have different child ids but same key different?
    # For arpeggio we kept both parent and children, so key includes primary which may duplicate across broken/arpeggiated pair.
    # For that case, one parent per object will remain per key but we had two objects with same evidence but different object_id.
    # They would have same primary but different source_object_ids. We keep one (highest confidence).
    chunks = list(seen.values())

    # Expand: need to keep children even if parent deduped? Children have distinct kind ascent/descent so not deduped.

    # Phrase grouping
    phrase_parents = _build_phrase_parents(chunks, bundle, counter)
    # Patch children parent ids
    chunks = _patch_phrase_children(phrase_parents, chunks)
    chunks.extend(phrase_parents)

    # Coordination
    coord = _build_coordination_chunks(bundle, chunks, counter)
    chunks.extend(coord)

    # Final sort
    chunks.sort(key=lambda c: (c.start_onset, c.kind, c.hand or ""))

    # Fix parent child consistency: ensure each parent's child ids exist
    valid_ids = {c.chunk_id for c in chunks}
    fixed: list[PracticeChunk] = []
    for c in chunks:
        if c.child_chunk_ids:
            filtered = tuple(cid for cid in c.child_chunk_ids if cid in valid_ids)
            if filtered != c.child_chunk_ids:
                # recreate
                fixed.append(PracticeChunk(
                    chunk_id=c.chunk_id, kind=c.kind, label=c.label, hand=c.hand, voice=c.voice, role=c.role, staff=c.staff,
                    start_onset=c.start_onset, end_onset=c.end_onset, measure_start=c.measure_start, measure_end=c.measure_end,
                    measure_numbers=c.measure_numbers, beat_start=c.beat_start, beat_end=c.beat_end,
                    primary_event_ids=c.primary_event_ids, context_event_ids=c.context_event_ids,
                    child_chunk_ids=filtered, parent_chunk_id=c.parent_chunk_id,
                    source_object_ids=c.source_object_ids, source_feature_refs=c.source_feature_refs,
                    traits=c.traits, practice_affordances=c.practice_affordances, confidence=c.confidence, caveats=c.caveats, payload=dict(c.payload)
                ))
            else:
                fixed.append(c)
        else:
            fixed.append(c)
    chunks = fixed

    # Ensure parent/child linkage after dedup: if phrase parent's children were deduped away, keep as is.
    return tuple(chunks)


# Backwards alias for building from parts
def build_practice_chunks_from_events(
    events: list[ScoreEvent],
    musical_objects: list[MusicalObject],
    bundle: SemanticBundle | None = None,
) -> tuple[PracticeChunk, ...]:
    if bundle is not None:
        return build_practice_chunks(bundle)
    # synthesize minimal bundle
    fake = SemanticBundle(events=tuple(events), derived_tokens=(), gestures=(), musical_objects=tuple(musical_objects), score_id=None)
    return build_practice_chunks(fake)
