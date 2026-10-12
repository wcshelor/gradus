"""Derived gesture tokens from normalized event table.

Covers milestone 2:
 melodic interval, harmonic simultaneity, hand movement, leap, repeated note,
 density spike, register shift, onset alignment, chord shape/span,
 pattern repetition/break.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from typing import Any

from .models import DerivedToken, ScoreEvent

# thresholds
LEAP_SEMITONES = 7  # >= major fifth counts as leap
REPEATED_NOTE_MAX_INTERVAL = 0  # exact pitch
DENSITY_SPIKE_NOTES_PER_QUARTER = 3.0
REGISTER_SHIFT_SEMITONES = 12
PATTERN_WINDOW = 4  # notes


def _events_by_hand(events: list[ScoreEvent], hand: str | None) -> list[ScoreEvent]:
    if hand is None:
        return [e for e in events if not e.is_rest]
    return [e for e in events if e.hand == hand and not e.is_rest]


def derive_all(events: list[ScoreEvent]) -> list[DerivedToken]:
    """Derive tokens of all kinds. Sorted by start_onset."""
    tokens: list[DerivedToken] = []
    tokens.extend(_melodic_intervals(events))
    tokens.extend(_harmonic_simultaneities(events))
    tokens.extend(_hand_movements(events))
    tokens.extend(_leaps(events))
    tokens.extend(_repeated_notes(events))
    tokens.extend(_density_spikes(events))
    tokens.extend(_register_shifts(events))
    tokens.extend(_onset_alignments(events))
    tokens.extend(_chord_shapes(events))
    tokens.extend(_pattern_tokens(events))
    # sort stable
    tokens.sort(key=lambda t: (t.start_onset, t.kind, t.hand or ""))
    # reassign ids ordered
    retyped: list[DerivedToken] = []
    for idx, tok in enumerate(tokens):
        retyped.append(
            DerivedToken(
                token_id=f"tok{idx+1}:{tok.kind}",
                kind=tok.kind,
                hand=tok.hand,
                staff=tok.staff,
                start_onset=tok.start_onset,
                end_onset=tok.end_onset,
                measure_start=tok.measure_start,
                measure_end=tok.measure_end,
                measure_numbers=tok.measure_numbers,
                evidence_event_ids=tok.evidence_event_ids,
                confidence=tok.confidence,
                payload=dict(tok.payload),
            )
        )
    return retyped


def _melodic_intervals(events: list[ScoreEvent]) -> list[DerivedToken]:
    """Per-hand melodic intervals between successive onsets."""
    tokens: list[DerivedToken] = []
    for hand in ("right", "left", None):
        seq = sorted(_events_by_hand(events, hand if hand in ("right", "left") else None), key=lambda e: (e.onset, e.pitch_midi or 0))
        # Group by onset: pick median pitch per onset for monophonic line
        onset_to_pitches: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in seq:
            onset_to_pitches[e.onset].append(e)
        sorted_onsets = sorted(onset_to_pitches.keys())
        # Build representative pitch per onset (median)
        rep: list[tuple[Fraction, int, tuple[str, ...], int | None, str | None]] = []
        for o in sorted_onsets:
            evts = onset_to_pitches[o]
            mids = sorted([e.pitch_midi for e in evts if e.pitch_midi is not None])
            if not mids:
                continue
            median = mids[len(mids)//2]
            ids = tuple(e.event_id for e in evts)
            m = evts[0].measure_index
            mn = evts[0].measure_number
            rep.append((o, median, ids, m, mn))
        for i in range(len(rep)-1):
            o1, p1, ids1, m1, mn1 = rep[i]
            o2, p2, ids2, m2, mn2 = rep[i+1]
            interval = p2 - p1
            direction = "up" if interval > 0 else "down" if interval < 0 else "repeat"
            tokens.append(
                DerivedToken(
                    token_id="tmp",
                    kind="melodic_interval",
                    hand=hand if hand in ("right","left") else None,
                    staff=seq[0].staff if seq else None,
                    start_onset=o1,
                    end_onset=o2,
                    measure_start=m1,
                    measure_end=m2,
                    measure_numbers=tuple(filter(None, [mn1, mn2])) if mn1 != mn2 else (mn1,) if mn1 else (),
                    evidence_event_ids=tuple(list(ids1)+list(ids2)),
                    confidence=0.9 if interval != 0 else 0.85,
                    payload={"interval_semitones": interval, "direction": direction, "from_midi": p1, "to_midi": p2},
                )
            )
    return tokens


def _harmonic_simultaneities(events: list[ScoreEvent]) -> list[DerivedToken]:
    """Chord-like simultaneities: multiple pitches same onset same hand."""
    tokens: list[DerivedToken] = []
    by_onset: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        if not e.is_rest:
            by_onset[e.onset].append(e)
    for onset, evts in sorted(by_onset.items()):
        if len(evts) < 2:
            continue
        # split by hand
        for hand in ("right","left", None):
            filtered = [e for e in evts if e.hand == hand] if hand in ("right","left") else ([e for e in evts if e.hand is None] if any(e.hand is None for e in evts) else [])
            if len(filtered) < 2:
                continue
            mids = sorted([e.pitch_midi for e in filtered if e.pitch_midi is not None])
            span = max(mids)-min(mids) if len(mids)>=2 else 0
            tokens.append(
                DerivedToken(
                    token_id="tmp",
                    kind="harmonic_simultaneity",
                    hand=hand if hand in ("right","left") else None,
                    staff=filtered[0].staff,
                    start_onset=onset,
                    end_onset=filtered[0].end,
                    measure_start=filtered[0].measure_index,
                    measure_end=filtered[0].measure_index,
                    measure_numbers=(filtered[0].measure_number,) if filtered[0].measure_number else (),
                    evidence_event_ids=tuple(e.event_id for e in filtered),
                    confidence=0.95 if len(mids)>=3 else 0.88,
                    payload={"note_count": len(filtered), "span_semitones": span, "midi_pitches": tuple(mids)},
                )
            )
        # also generic cross-hand simultaneity if both hands present at same onset
        hands_present = {e.hand for e in evts if e.hand in ("right","left")}
        if len(hands_present) >= 2:
            mids_all = sorted([e.pitch_midi for e in evts if e.pitch_midi is not None])
            tokens.append(
                DerivedToken(
                    token_id="tmp",
                    kind="harmonic_simultaneity",
                    hand=None,
                    staff=None,
                    start_onset=onset,
                    end_onset=max(e.end for e in evts),
                    measure_start=min(e.measure_index for e in evts if e.measure_index is not None),
                    measure_end=max(e.measure_index for e in evts if e.measure_index is not None),
                    measure_numbers=tuple(sorted({e.measure_number for e in evts if e.measure_number})),
                    evidence_event_ids=tuple(e.event_id for e in evts),
                    confidence=0.7,
                    payload={"note_count": len(evts), "hands": tuple(sorted(hands_present)), "span_semitones": max(mids_all)-min(mids_all) if len(mids_all)>=2 else 0, "midi_pitches": tuple(mids_all)},
                )
            )
    return tokens


def _hand_movements(events: list[ScoreEvent]) -> list[DerivedToken]:
    """Hand movement between successive onsets per hand."""
    tokens: list[DerivedToken] = []
    for hand in ("right","left"):
        seq = sorted(_events_by_hand(events, hand), key=lambda e: e.onset)
        # group by onset median as before
        onset_groups: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in seq:
            onset_groups[e.onset].append(e)
        sorted_onsets = sorted(onset_groups.keys())
        reps: list[tuple[Fraction, float, tuple[str,...], int|None, str|None, Fraction]] = []
        for o in sorted_onsets:
            evts = onset_groups[o]
            mids = [e.pitch_midi for e in evts if e.pitch_midi is not None]
            if not mids:
                continue
            avg = sum(mids)/len(mids)
            reps.append((o, avg, tuple(e.event_id for e in evts), evts[0].measure_index, evts[0].measure_number, evts[0].end))
        for i in range(len(reps)-1):
            o1, avg1, ids1, m1, mn1, end1 = reps[i]
            o2, avg2, ids2, m2, mn2, end2 = reps[i+1]
            movement = avg2 - avg1
            tokens.append(
                DerivedToken(
                    token_id="tmp",
                    kind="hand_movement",
                    hand=hand,
                    staff=seq[0].staff if seq else None,
                    start_onset=o1,
                    end_onset=o2,
                    measure_start=m1,
                    measure_end=m2,
                    measure_numbers=tuple(filter(None, [mn1,mn2])) if mn1 != mn2 else (mn1,) if mn1 else (),
                    evidence_event_ids=tuple(list(ids1)+list(ids2)),
                    confidence=min(0.95, 0.6 + abs(movement)/24),
                    payload={"movement_semitones": round(movement,2), "from_avg_midi": round(avg1,1), "to_avg_midi": round(avg2,1)},
                )
            )
    return tokens


def _leaps(events: list[ScoreEvent]) -> list[DerivedToken]:
    tokens: list[DerivedToken] = []
    for hand in ("right","left"):
        seq = sorted(_events_by_hand(events, hand), key=lambda e: (e.onset, e.pitch_midi or 0))
        # per-onset representative
        groups: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in seq:
            groups[e.onset].append(e)
        onsets = sorted(groups.keys())
        reps: list[tuple[Fraction, int, tuple[str,...], int|None, str|None, Fraction]] = []
        for o in onsets:
            evts = groups[o]
            # for leap detection, use extreme? median of group
            mids = sorted([e.pitch_midi for e in evts if e.pitch_midi is not None])
            if not mids:
                continue
            med = mids[len(mids)//2]
            reps.append((o, med, tuple(e.event_id for e in evts), evts[0].measure_index, evts[0].measure_number, evts[0].end))
        for i in range(len(reps)-1):
            o1, p1, ids1, m1, mn1, e1 = reps[i]
            o2, p2, ids2, m2, mn2, e2 = reps[i+1]
            interval = p2 - p1
            if abs(interval) >= LEAP_SEMITONES:
                tokens.append(
                    DerivedToken(
                        token_id="tmp",
                        kind="leap",
                        hand=hand,
                        staff=seq[0].staff if seq else None,
                        start_onset=o1,
                        end_onset=o2,
                        measure_start=m1,
                        measure_end=m2,
                        measure_numbers=tuple(sorted(set(filter(None, [mn1,mn2])))) if mn1 != mn2 else (mn1,) if mn1 else (),
                        evidence_event_ids=tuple(list(ids1)+list(ids2)),
                        confidence=min(0.95, 0.65 + abs(interval)/24),
                        payload={"interval_semitones": interval, "abs_interval": abs(interval), "from_midi": p1, "to_midi": p2},
                    )
                )
    return tokens


def _repeated_notes(events: list[ScoreEvent]) -> list[DerivedToken]:
    tokens: list[DerivedToken] = []
    for hand in ("right","left"):
        seq = sorted(_events_by_hand(events, hand), key=lambda e: (e.onset, e.pitch_midi or 0))
        groups: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in seq:
            groups[e.onset].append(e)
        onsets = sorted(groups.keys())
        reps: list[tuple[Fraction, int, tuple[str,...], int|None, str|None]] = []
        for o in onsets:
            evts = groups[o]
            mids = sorted([e.pitch_midi for e in evts if e.pitch_midi is not None])
            if not mids:
                continue
            # for repeated note, check if single pitch repeats; if chord, check set equality?
            reps.append((o, mids[0] if len(mids)==1 else -1, tuple(e.event_id for e in evts), evts[0].measure_index, evts[0].measure_number))
        for i in range(len(reps)-1):
            o1, p1, ids1, m1, mn1 = reps[i]
            o2, p2, ids2, m2, mn2 = reps[i+1]
            if p1 != -1 and p1 == p2:
                tokens.append(
                    DerivedToken(
                        token_id="tmp",
                        kind="repeated_note",
                        hand=hand,
                        staff=seq[0].staff if seq else None,
                        start_onset=o1,
                        end_onset=o2,
                        measure_start=m1,
                        measure_end=m2,
                        measure_numbers=tuple(sorted(set(filter(None,[mn1,mn2])))) if mn1!=mn2 else (mn1,) if mn1 else (),
                        evidence_event_ids=tuple(list(ids1)+list(ids2)),
                        confidence=0.92,
                        payload={"pitch_midi": p1},
                    )
                )
    return tokens


def _density_spikes(events: list[ScoreEvent]) -> list[DerivedToken]:
    tokens: list[DerivedToken] = []
    # sliding window per hand and global
    for hand in ("right","left", None):
        seq = sorted(_events_by_hand(events, hand if hand in ("right","left") else None), key=lambda e: e.onset) if hand in ("right","left") else sorted([e for e in events if not e.is_rest], key=lambda e: e.onset)
        if not seq:
            continue
        # Group by onset counts
        onset_counts: dict[Fraction, int] = defaultdict(int)
        for e in seq:
            onset_counts[e.onset] += 1
        # For density, consider quarter window? Use 1-quarter bins
        # Build bins of 1 quarter
        min_onset = min(e.onset for e in seq)
        max_end = max(e.end for e in seq)
        # step 0.5 quarter? Simplify 1 quarter bins
        bin_start = Fraction(int(min_onset))
        # Use float for iteration but keep Fraction where possible
        # We'll use quarter as Fraction(1)
        current = bin_start
        while current < max_end:
            window_end = current + Fraction(1)
            count = sum(1 for e in seq if current <= e.onset < window_end)
            density = float(count)  # per quarter
            if density >= DENSITY_SPIKE_NOTES_PER_QUARTER:
                # find measure numbers
                evts_in_window = [e for e in seq if current <= e.onset < window_end]
                m_start = min((e.measure_index for e in evts_in_window if e.measure_index is not None), default=None)
                m_end = max((e.measure_index for e in evts_in_window if e.measure_index is not None), default=None)
                mn = tuple(sorted({e.measure_number for e in evts_in_window if e.measure_number}))
                tokens.append(
                    DerivedToken(
                        token_id="tmp",
                        kind="density_spike",
                        hand=hand if hand in ("right","left") else None,
                        staff=None,
                        start_onset=current,
                        end_onset=window_end,
                        measure_start=m_start,
                        measure_end=m_end,
                        measure_numbers=mn,
                        evidence_event_ids=tuple(e.event_id for e in evts_in_window),
                        confidence=min(0.9, 0.5 + density/8),
                        payload={"notes_in_quarter": count, "density_per_quarter": density},
                    )
                )
            current += Fraction(1,2)  # hop 0.5 quarter
    return tokens


def _register_shifts(events: list[ScoreEvent]) -> list[DerivedToken]:
    tokens: list[DerivedToken] = []
    for hand in ("right","left"):
        seq = sorted(_events_by_hand(events, hand), key=lambda e: e.onset)
        groups: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in seq:
            groups[e.onset].append(e)
        onsets = sorted(groups.keys())
        # average per onset
        avgs: list[tuple[Fraction, float, tuple[str,...], int|None, str|None]] = []
        for o in onsets:
            evts = groups[o]
            mids = [e.pitch_midi for e in evts if e.pitch_midi is not None]
            if not mids:
                continue
            avgs.append((o, sum(mids)/len(mids), tuple(e.event_id for e in evts), evts[0].measure_index, evts[0].measure_number))
        # Detect shifts: compare windows of 2-3 onsets avg vs next window
        for i in range(1, len(avgs)):
            prev_avg = avgs[i-1][1]
            cur_avg = avgs[i][1]
            diff = cur_avg - prev_avg
            if abs(diff) >= REGISTER_SHIFT_SEMITONES:
                tokens.append(
                    DerivedToken(
                        token_id="tmp",
                        kind="register_shift",
                        hand=hand,
                        staff=seq[0].staff if seq else None,
                        start_onset=avgs[i-1][0],
                        end_onset=avgs[i][0],
                        measure_start=avgs[i-1][3],
                        measure_end=avgs[i][3],
                        measure_numbers=tuple(sorted(set(filter(None,[avgs[i-1][4], avgs[i][4]])))) if avgs[i-1][4]!=avgs[i][4] else (avgs[i][4],) if avgs[i][4] else (),
                        evidence_event_ids=tuple(list(avgs[i-1][2])+list(avgs[i][2])),
                        confidence=min(0.95, 0.6 + abs(diff)/24),
                        payload={"shift_semitones": round(diff,1), "from_avg": round(prev_avg,1), "to_avg": round(cur_avg,1)},
                    )
                )
    return tokens


def _onset_alignments(events: list[ScoreEvent]) -> list[DerivedToken]:
    tokens: list[DerivedToken] = []
    # Find onsets where both hands have events aligned exactly
    right_onsets = {e.onset for e in events if e.hand=="right" and not e.is_rest}
    left_onsets = {e.onset for e in events if e.hand=="left" and not e.is_rest}
    aligned = sorted(right_onsets & left_onsets)
    for onset in aligned:
        evts = [e for e in events if e.onset==onset and not e.is_rest]
        mids = sorted([e.pitch_midi for e in evts if e.pitch_midi is not None])
        m_start = min((e.measure_index for e in evts if e.measure_index is not None), default=None)
        m_end = max((e.measure_index for e in evts if e.measure_index is not None), default=None)
        mn = tuple(sorted({e.measure_number for e in evts if e.measure_number}))
        tokens.append(
            DerivedToken(
                token_id="tmp",
                kind="onset_alignment",
                hand=None,
                staff=None,
                start_onset=onset,
                end_onset=max(e.end for e in evts),
                measure_start=m_start,
                measure_end=m_end,
                measure_numbers=mn,
                evidence_event_ids=tuple(e.event_id for e in evts),
                confidence=0.9 if len(evts)>=3 else 0.8,
                payload={"aligned_hands": ("right","left"), "note_count": len(evts), "span_semitones": (max(mids)-min(mids) if len(mids)>=2 else 0)},
            )
        )
    # Also detect misaligned density: left vs right onset ratio mismatched
    # Simple: if window has both but not aligned -> not tokenized as alignment; skip for milestone 3
    return tokens


def _chord_shapes(events: list[ScoreEvent]) -> list[DerivedToken]:
    tokens: list[DerivedToken] = []
    by_onset: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
    for e in events:
        if not e.is_rest:
            by_onset[e.onset].append(e)
    for onset, evts in sorted(by_onset.items()):
        # per hand chord
        for hand in ("right","left"):
            filtered = [e for e in evts if e.hand==hand]
            if len(filtered) < 2:
                continue
            mids = sorted([e.pitch_midi for e in filtered if e.pitch_midi is not None])
            intervals = [mids[i+1]-mids[i] for i in range(len(mids)-1)]
            shape = "unknown"
            if len(mids)==3 and intervals==[4,3]:
                shape="major_triad"
            elif len(mids)==3 and intervals==[3,4]:
                shape="minor_triad"
            elif len(mids)>=3 and all(v==4 for v in intervals) or all(v==3 for v in intervals):
                shape="thirds_stack"
            elif max(mids)-min(mids) <= 4:
                shape="cluster_tight"
            elif len(mids)>=4 and max(mids)-min(mids) >= 12:
                shape="wide_span"
            else:
                shape="mid_span"
            tokens.append(
                DerivedToken(
                    token_id="tmp",
                    kind="chord_shape",
                    hand=hand,
                    staff=filtered[0].staff,
                    start_onset=onset,
                    end_onset=filtered[0].end,
                    measure_start=filtered[0].measure_index,
                    measure_end=filtered[0].measure_index,
                    measure_numbers=(filtered[0].measure_number,) if filtered[0].measure_number else (),
                    evidence_event_ids=tuple(e.event_id for e in filtered),
                    confidence=0.88 if shape in ("major_triad","minor_triad") else 0.75,
                    payload={"shape": shape, "span_semitones": max(mids)-min(mids), "intervals": tuple(intervals), "midi_pitches": tuple(mids), "note_count": len(mids)},
                )
            )
    return tokens


def _pattern_tokens(events: list[ScoreEvent]) -> list[DerivedToken]:
    """Pattern repetition and break detection via interval contour n-grams."""
    tokens: list[DerivedToken] = []
    for hand in ("right","left"):
        seq = sorted(_events_by_hand(events, hand), key=lambda e: e.onset)
        # Build per-onset reps
        groups: dict[Fraction, list[ScoreEvent]] = defaultdict(list)
        for e in seq:
            groups[e.onset].append(e)
        onsets = sorted(groups.keys())
        reps: list[tuple[Fraction, int, tuple[str,...], int|None, str|None]] = []
        for o in onsets:
            evts = groups[o]
            mids = sorted([e.pitch_midi for e in evts if e.pitch_midi is not None])
            if not mids:
                continue
            med = mids[len(mids)//2]
            reps.append((o, med, tuple(e.event_id for e in evts), evts[0].measure_index, evts[0].measure_number))
        if len(reps) < PATTERN_WINDOW*2:
            continue
        intervals = [reps[i+1][1]-reps[i][1] for i in range(len(reps)-1)]
        # Find repeating interval patterns of length 2-3
        seen: dict[tuple[int,...], list[int]] = defaultdict(list)
        for window in (2,3):
            for start in range(len(intervals)-window+1):
                pat = tuple(intervals[start:start+window])
                seen[pat].append(start)
        for pat, positions in seen.items():
            if len(positions) >= 2:
                # Check that positions are non-overlapping and separated?
                # Create repetition tokens for each occurrence after first
                for pos in positions[1:]:
                    start_onset = reps[pos][0]
                    end_onset = reps[pos+len(pat)][0] if pos+len(pat) < len(reps) else reps[-1][0]
                    m_start = reps[pos][3]
                    m_end = reps[pos+len(pat)][3] if pos+len(pat) < len(reps) else reps[-1][3]
                    mns = tuple(sorted({reps[i][4] for i in range(pos, min(pos+len(pat)+1, len(reps))) if reps[i][4]}))
                    ev_ids = tuple(eid for i in range(pos, min(pos+len(pat)+1, len(reps))) for eid in reps[i][2])
                    tokens.append(
                        DerivedToken(
                            token_id="tmp",
                            kind="pattern_repetition",
                            hand=hand,
                            staff=seq[0].staff if seq else None,
                            start_onset=start_onset,
                            end_onset=end_onset,
                            measure_start=m_start,
                            measure_end=m_end,
                            measure_numbers=mns,
                            evidence_event_ids=ev_ids,
                            confidence=min(0.92, 0.6 + len(pat)*0.1 + len(positions)*0.05),
                            payload={"pattern_intervals": pat, "occurrence": pos, "total_occurrences": len(positions)},
                        )
                    )
                # Detect pattern break: after repetition, next interval deviates
                last_pos = positions[-1]
                next_idx = last_pos + len(pat)
                if next_idx < len(intervals):
                    expected = pat[next_idx % len(pat)] if pat else None
                    actual = intervals[next_idx]
                    if expected is not None and abs(actual - expected) > 2:
                        # break token
                        br_start = reps[next_idx][0]
                        br_end = reps[next_idx+1][0] if next_idx+1 < len(reps) else br_start + Fraction(1)
                        m_start = reps[next_idx][3]
                        m_end = reps[next_idx+1][3] if next_idx+1 < len(reps) else m_start
                        mns = tuple(sorted(set(filter(None, [reps[next_idx][4], reps[next_idx+1][4] if next_idx+1 < len(reps) else None]))))
                        ev_ids = tuple(list(reps[next_idx][2])+list(reps[next_idx+1][2] if next_idx+1 < len(reps) else []))
                        tokens.append(
                            DerivedToken(
                                token_id="tmp",
                                kind="pattern_break",
                                hand=hand,
                                staff=seq[0].staff if seq else None,
                                start_onset=br_start,
                                end_onset=br_end,
                                measure_start=m_start,
                                measure_end=m_end,
                                measure_numbers=mns,
                                evidence_event_ids=ev_ids,
                                confidence=0.72,
                                payload={"expected_interval": expected, "actual_interval": actual, "pattern_intervals": pat},
                            )
                        )
    return tokens
