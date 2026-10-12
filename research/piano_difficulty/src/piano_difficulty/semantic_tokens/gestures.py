"""Group derived tokens into musical gestures (milestone 3).

Gestures are compositional: bass-to-chord, melody+accompaniment, block chord
landing, arpeggio/broken chord, scalar run, repeated-note figure, cadence-like
arrival, accompaniment pattern.

Implementation is heuristic and evidence-preserving: each gesture cites token_ids
and underlying event_ids.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

from .models import DerivedToken, Gesture, ScoreEvent


def build_gestures(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Group tokens into gestures. Deterministic, evidence-linked."""
    gestures: list[Gesture] = []
    gestures.extend(_bass_to_chord_gestures(events, tokens))
    gestures.extend(_melody_with_accompaniment_gestures(events, tokens))
    gestures.extend(_block_chord_landings(events, tokens))
    gestures.extend(_arpeggio_gestures(events, tokens))
    gestures.extend(_scalar_runs(events, tokens))
    gestures.extend(_repeated_note_figures(events, tokens))
    gestures.extend(_cadence_arrivals(events, tokens))
    gestures.extend(_accompaniment_patterns(events, tokens))

    gestures.sort(key=lambda g: (g.start_onset, g.kind))
    # reassign stable ids sorted order
    out: list[Gesture] = []
    for idx, g in enumerate(gestures):
        out.append(
            Gesture(
                gesture_id=f"ges{idx+1}:{g.kind}",
                kind=g.kind,
                hand=g.hand,
                start_onset=g.start_onset,
                end_onset=g.end_onset,
                measure_start=g.measure_start,
                measure_end=g.measure_end,
                measure_numbers=g.measure_numbers,
                token_ids=g.token_ids,
                evidence_event_ids=g.evidence_event_ids,
                confidence=g.confidence,
                payload=dict(g.payload),
            )
        )
    return out


def _tokens_by_kind(tokens: list[DerivedToken], kind: str) -> list[DerivedToken]:
    return [t for t in tokens if t.kind == kind]


def _merge_measure_numbers(toks: list[DerivedToken]) -> tuple[int|None, int|None, tuple[str,...]]:
    mins = [t.measure_start for t in toks if t.measure_start is not None]
    maxs = [t.measure_end for t in toks if t.measure_end is not None]
    nums_seen: set[str] = set()
    nums: list[str] = []
    for t in toks:
        for n in t.measure_numbers:
            if n not in nums_seen:
                nums_seen.add(n)
                nums.append(n)
    nums.sort(key=_measure_sort_key)
    return (min(mins) if mins else None, max(maxs) if maxs else None, tuple(nums))


def _measure_sort_key(value: str) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, value)


def _bass_to_chord_gestures(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Bass note followed by chord on same hand (LH typical)."""
    gestures: list[Gesture] = []
    # Only genuine leaps (not generic hand_movement/register_shift) qualify as launch for leap_to_chord
    left_leaps = [t for t in tokens if t.hand=="left" and t.kind == "leap" and abs(t.payload.get("interval_semitones", 0) or 0) >= 7]
    # Target must be a real chord (>=3 notes or wide span)
    left_chords = [t for t in tokens if t.hand=="left" and t.kind in ("chord_shape","harmonic_simultaneity") and (t.payload.get("note_count", 0) >= 3 or t.payload.get("span_semitones", 0) >= 7)]
    # pair if chord onset within 1 quarter after leap end (stricter for minimal interval)
    for leap in left_leaps:
        for chord in left_chords:
            gap = chord.start_onset - leap.end_onset
            if chord.start_onset >= leap.end_onset and gap <= Fraction(1):
                # Shrink window for minimal leaps (7 semitones) to avoid normal chordal movement
                if abs(leap.payload.get("interval_semitones", 0) or 0) == 7 and gap > Fraction(1, 2):
                    continue
                m_start, m_end, mns = _merge_measure_numbers([leap,chord])
                gestures.append(
                    Gesture(
                        gesture_id="tmp",
                        kind="bass_to_chord",
                        hand="left",
                        start_onset=leap.start_onset,
                        end_onset=chord.end_onset,
                        measure_start=m_start,
                        measure_end=m_end,
                        measure_numbers=mns,
                        token_ids=(leap.token_id, chord.token_id),
                        evidence_event_ids=tuple(dict.fromkeys(list(leap.evidence_event_ids)+list(chord.evidence_event_ids))),
                        confidence=round((leap.confidence + chord.confidence)/2,3),
                        payload={"movement": leap.payload.get("movement_semitones") or leap.payload.get("interval_semitones"), "chord_shape": chord.payload.get("shape")},
                    )
                )
    return gestures


def _melody_with_accompaniment_gestures(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Right-hand melodic intervals while left-hand simultaneity at aligned onsets."""
    gestures: list[Gesture] = []
    alignments = [t for t in tokens if t.kind=="onset_alignment"]
    # For each alignment window, check if there is melodic activity in RH
    rh_melodic = [t for t in tokens if t.hand=="right" and t.kind=="melodic_interval"]
    sorted_melodic = sorted(rh_melodic, key=lambda t: t.start_onset)
    for al in alignments:
        # collect melodic intervals overlapping alignment period +-1 quarter
        window_melodic = [t for t in sorted_melodic if al.start_onset - Fraction(1) <= t.start_onset <= al.end_onset + Fraction(1)]
        if window_melodic:
            m_start, m_end, mns = _merge_measure_numbers([al]+window_melodic[:2])
            gestures.append(
                Gesture(
                    gesture_id="tmp",
                    kind="melody_with_accompaniment",
                    hand=None,
                    start_onset=min(al.start_onset, min(t.start_onset for t in window_melodic)),
                    end_onset=max(al.end_onset, max(t.end_onset for t in window_melodic)),
                    measure_start=m_start,
                    measure_end=m_end,
                    measure_numbers=mns,
                    token_ids=tuple([al.token_id]+[t.token_id for t in window_melodic[:3]]),
                    evidence_event_ids=tuple(dict.fromkeys(list(al.evidence_event_ids)+[eid for t in window_melodic[:3] for eid in t.evidence_event_ids])),
                    confidence=0.78,
                    payload={"aligned_onset": str(al.start_onset), "melodic_intervals": len(window_melodic)},
                )
            )
    return gestures


def _block_chord_landings(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Block chord: harmonic simultaneity with chord_shape wide/major/minor."""
    gestures: list[Gesture] = []
    chords = [t for t in tokens if t.kind in ("chord_shape","harmonic_simultaneity")]
    for ch in chords:
        # Consider landing if span significant or note_count >=3
        count = ch.payload.get("note_count",0)
        span = ch.payload.get("span_semitones",0)
        if count >=3 or span >= 7:
            gestures.append(
                Gesture(
                    gesture_id="tmp",
                    kind="block_chord_landing",
                    hand=ch.hand,
                    start_onset=ch.start_onset,
                    end_onset=ch.end_onset,
                    measure_start=ch.measure_start,
                    measure_end=ch.measure_end,
                    measure_numbers=ch.measure_numbers,
                    token_ids=(ch.token_id,),
                    evidence_event_ids=ch.evidence_event_ids,
                    confidence=0.82 if count>=3 else 0.72,
                    payload=dict(ch.payload),
                )
            )
    return gestures


def _arpeggio_gestures(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Arpeggio/broken chord: series of small melodic intervals with same harmony."""
    gestures: list[Gesture] = []
    # Look for runs of stepwise intervals in same hand with intervals 3-4 semitones (thirds)
    for hand in ("right","left"):
        mels = sorted([t for t in tokens if t.hand==hand and t.kind=="melodic_interval"], key=lambda t: t.start_onset)
        # collect consecutive intervals that are 3 or 4 semitones
        run: list[DerivedToken] = []
        for tok in mels:
            interval = abs(tok.payload.get("interval_semitones",0))
            if interval in (3,4):
                run.append(tok)
            else:
                if len(run) >= 3:
                    m_start, m_end, mns = _merge_measure_numbers(run)
                    gestures.append(
                        Gesture(
                            gesture_id="tmp",
                            kind="arpeggio",
                            hand=hand,
                            start_onset=run[0].start_onset,
                            end_onset=run[-1].end_onset,
                            measure_start=m_start,
                            measure_end=m_end,
                            measure_numbers=mns,
                            token_ids=tuple(t.token_id for t in run),
                            evidence_event_ids=tuple(eid for t in run for eid in t.evidence_event_ids),
                            confidence=0.8,
                            payload={"interval_pattern": tuple(t.payload.get("interval_semitones") for t in run), "type": "broken_chord"},
                        )
                    )
                run = []
        if len(run) >= 3:
            m_start, m_end, mns = _merge_measure_numbers(run)
            gestures.append(
                Gesture(
                    gesture_id="tmp",
                    kind="arpeggio",
                    hand=hand,
                    start_onset=run[0].start_onset,
                    end_onset=run[-1].end_onset,
                    measure_start=m_start,
                    measure_end=m_end,
                    measure_numbers=mns,
                    token_ids=tuple(t.token_id for t in run),
                    evidence_event_ids=tuple(eid for t in run for eid in t.evidence_event_ids),
                    confidence=0.8,
                    payload={"interval_pattern": tuple(t.payload.get("interval_semitones") for t in run), "type": "broken_chord"},
                )
            )
    return gestures


def _scalar_runs(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Scalar run: consecutive melodic intervals of 1-2 semitones directed."""
    gestures: list[Gesture] = []
    for hand in ("right","left"):
        mels = sorted([t for t in tokens if t.hand==hand and t.kind=="melodic_interval"], key=lambda t: t.start_onset)
        run: list[DerivedToken] = []
        direction = None
        for tok in mels:
            iv = tok.payload.get("interval_semitones",0)
            cur_dir = "up" if iv>0 else "down" if iv<0 else "flat"
            if abs(iv) <=2 and iv!=0:
                if direction is None:
                    direction = cur_dir
                if cur_dir == direction:
                    run.append(tok)
                else:
                    if len(run) >=3:
                        m_start, m_end, mns = _merge_measure_numbers(run)
                        gestures.append(
                            Gesture(
                                gesture_id="tmp",
                                kind="scalar_run",
                                hand=hand,
                                start_onset=run[0].start_onset,
                                end_onset=run[-1].end_onset,
                                measure_start=m_start,
                                measure_end=m_end,
                                measure_numbers=mns,
                                token_ids=tuple(t.token_id for t in run),
                                evidence_event_ids=tuple(eid for t in run for eid in t.evidence_event_ids),
                                confidence=0.82,
                                payload={"direction": direction, "steps": len(run)+1},
                            )
                        )
                    run = [tok]
                    direction = cur_dir
            else:
                if len(run) >=3:
                    m_start, m_end, mns = _merge_measure_numbers(run)
                    gestures.append(
                        Gesture(
                            gesture_id="tmp",
                            kind="scalar_run",
                            hand=hand,
                            start_onset=run[0].start_onset,
                            end_onset=run[-1].end_onset,
                            measure_start=m_start,
                            measure_end=m_end,
                            measure_numbers=mns,
                            token_ids=tuple(t.token_id for t in run),
                            evidence_event_ids=tuple(eid for t in run for eid in t.evidence_event_ids),
                            confidence=0.82,
                            payload={"direction": direction, "steps": len(run)+1},
                        )
                    )
                run=[]
                direction=None
        if len(run) >=3:
            m_start, m_end, mns = _merge_measure_numbers(run)
            gestures.append(
                Gesture(
                    gesture_id="tmp",
                    kind="scalar_run",
                    hand=hand,
                    start_onset=run[0].start_onset,
                    end_onset=run[-1].end_onset,
                    measure_start=m_start,
                    measure_end=m_end,
                    measure_numbers=mns,
                    token_ids=tuple(t.token_id for t in run),
                    evidence_event_ids=tuple(eid for t in run for eid in t.evidence_event_ids),
                    confidence=0.82,
                    payload={"direction": direction, "steps": len(run)+1},
                )
            )
    return gestures


def _repeated_note_figures(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    gestures: list[Gesture] = []
    reps = [t for t in tokens if t.kind=="repeated_note"]
    # group consecutive repeats
    for hand in ("right","left"):
        hand_reps = sorted([t for t in reps if t.hand==hand], key=lambda t: t.start_onset)
        run: list[DerivedToken] = []
        for tok in hand_reps:
            if not run or tok.start_onset == run[-1].end_onset:
                run.append(tok)
            else:
                if len(run) >=2:
                    m_start, m_end, mns = _merge_measure_numbers(run)
                    gestures.append(
                        Gesture(
                            gesture_id="tmp",
                            kind="repeated_note_figure",
                            hand=hand,
                            start_onset=run[0].start_onset,
                            end_onset=run[-1].end_onset,
                            measure_start=m_start,
                            measure_end=m_end,
                            measure_numbers=mns,
                            token_ids=tuple(t.token_id for t in run),
                            evidence_event_ids=tuple(eid for t in run for eid in t.evidence_event_ids),
                            confidence=0.88,
                            payload={"repeat_count": len(run)+1, "pitch": run[0].payload.get("pitch_midi")},
                        )
                    )
                run=[tok]
        if len(run) >=2:
            m_start, m_end, mns = _merge_measure_numbers(run)
            gestures.append(
                Gesture(
                    gesture_id="tmp",
                    kind="repeated_note_figure",
                    hand=hand,
                    start_onset=run[0].start_onset,
                    end_onset=run[-1].end_onset,
                    measure_start=m_start,
                    measure_end=m_end,
                    measure_numbers=mns,
                    token_ids=tuple(t.token_id for t in run),
                    evidence_event_ids=tuple(eid for t in run for eid in t.evidence_event_ids),
                    confidence=0.88,
                    payload={"repeat_count": len(run)+1, "pitch": run[0].payload.get("pitch_midi")},
                )
            )
    return gestures


def _cadence_arrivals(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Cadence-like arrival: block chord landing after scalar/arpeggio + density context."""
    gestures: list[Gesture] = []
    chords = [t for t in tokens if t.kind in ("chord_shape","harmonic_simultaneity")]
    # also consider end of score
    max_end = max((e.end for e in events), default=Fraction(0))
    for ch in chords:
        # Heuristic: if chord occurs near end or after movement
        is_near_end = ch.end_onset >= max_end - Fraction(1) if max_end else False
        has_prior_movement = any(t.hand==ch.hand and t.kind in ("melodic_interval","leap","hand_movement") and t.end_onset <= ch.start_onset and ch.start_onset - t.end_onset <= Fraction(2) for t in tokens)
        if is_near_end or has_prior_movement:
            # Check if span large or note_count high
            if ch.payload.get("note_count",0) >=2 or ch.payload.get("span_semitones",0) >=7:
                gestures.append(
                    Gesture(
                        gesture_id="tmp",
                        kind="cadence_like_arrival",
                        hand=ch.hand,
                        start_onset=ch.start_onset,
                        end_onset=ch.end_onset,
                        measure_start=ch.measure_start,
                        measure_end=ch.measure_end,
                        measure_numbers=ch.measure_numbers,
                        token_ids=(ch.token_id,),
                        evidence_event_ids=ch.evidence_event_ids,
                        confidence=0.70,
                        payload=dict(ch.payload, near_end=is_near_end),
                    )
                )
    return gestures


def _accompaniment_patterns(events: list[ScoreEvent], tokens: list[DerivedToken]) -> list[Gesture]:
    """Accompaniment pattern from pattern_repetition tokens plus density."""
    gestures: list[Gesture] = []
    repeats = [t for t in tokens if t.kind=="pattern_repetition"]
    for rep in repeats:
        # Consider accompaniment if hand left or density spike nearby
        left_density_near = any(d.hand in (rep.hand, None) and abs(d.start_onset - rep.start_onset) <= Fraction(1) for d in tokens if d.kind=="density_spike")
        if rep.hand=="left" or left_density_near or True:  # keep heuristic permissive
            gestures.append(
                Gesture(
                    gesture_id="tmp",
                    kind="accompaniment_pattern",
                    hand=rep.hand,
                    start_onset=rep.start_onset,
                    end_onset=rep.end_onset,
                    measure_start=rep.measure_start,
                    measure_end=rep.measure_end,
                    measure_numbers=rep.measure_numbers,
                    token_ids=(rep.token_id,),
                    evidence_event_ids=rep.evidence_event_ids,
                    confidence=rep.confidence * 0.95,
                    payload=dict(rep.payload),
                )
            )
    return gestures
