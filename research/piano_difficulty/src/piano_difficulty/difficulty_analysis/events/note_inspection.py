"""Selective note-level inspection for a local span.

Treated as a local tool, not the primary data source.
Called only for flagged spans where metrics are ambiguous or to confirm
what musical thing caused a metric boundary.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Any

from piano_difficulty.normalize.schema import ScoreIR
from piano_difficulty.temporal.selection import select_region
from piano_difficulty.temporal.windows import ScoreRegion

from .models import NoteEvidence, NoteSummary


def _hand_leaps(pitches_per_onset: list[list[int]]) -> tuple[float | None, int | None]:
    if len(pitches_per_onset) < 2:
        return None, None
    leaps: list[int] = []
    for prev, cur in zip(pitches_per_onset, pitches_per_onset[1:]):
        if not prev or not cur:
            continue
        leaps.append(min(abs(a - b) for a in prev for b in cur))
    if not leaps:
        return None, None
    return sum(leaps) / len(leaps), max(leaps)


def inspect_span(score: ScoreIR, region: ScoreRegion) -> NoteEvidence:
    """Build selective note evidence for one region.

    Uses exact attack selection [start, end).  Does not re-extract features.
    Returns bounded data: note ids, per-hand summaries, and diagnostics.
    """
    if region.start_offset is None or region.end_offset is None:
        return NoteEvidence(
            start_offset=None,
            end_offset=None,
            measure_start=region.measure_start,
            measure_end=region.measure_end,
            measure_numbers=tuple(region.measure_numbers),
            diagnostics=("region has no offsets — note inspection unavailable",),
        )
    try:
        sub = select_region(score, region)
    except Exception as exc:  # noqa: BLE001
        return NoteEvidence(
            start_offset=region.start_offset,
            end_offset=region.end_offset,
            measure_start=region.measure_start,
            measure_end=region.measure_end,
            measure_numbers=tuple(region.measure_numbers),
            diagnostics=(f"select_region failed: {exc}",),
        )

    logical = sub.logical_notes
    written = sub.written_notes

    # Per-hand grouping
    onsets_by_hand: dict[str | None, dict[Fraction, list[int]]] = defaultdict(lambda: defaultdict(list))
    voice_by_hand: dict[str | None, set[str]] = defaultdict(set)
    note_count_by_hand: dict[str | None, int] = defaultdict(int)
    onset_sets: dict[str | None, set[Fraction]] = defaultdict(set)

    for n in logical:
        hand = n.hand
        onsets_by_hand[hand][n.onset].append(n.pitch_midi)
        if n.voice is not None:
            voice_by_hand[hand].add(str(n.voice))
        note_count_by_hand[hand] += 1
        onset_sets[hand].add(n.onset)

    summaries: list[NoteSummary] = []
    extra: dict[str, Any] = {}
    diagnostics: list[str] = []

    for hand in ("right", "left", None):
        # None represents score-global if hands missing
        if hand is not None and note_count_by_hand.get(hand, 0) == 0:
            continue
        if hand is None and any(note_count_by_hand.get(h, 0) > 0 for h in ("right", "left")):
            # skip global summary when hand-specific available — keeps payload small
            continue
        pitches = []
        for onset, mids in onsets_by_hand.get(hand, {}).items():
            pitches.extend(mids)
        if not pitches and hand is None:
            pitches = [n.pitch_midi for n in logical]
        if not pitches:
            continue
        # Span = max simultaneous span if available, else pitch range
        # Compute per-onset span
        spans = []
        for mids in onsets_by_hand.get(hand, {}).values():
            if len(mids) >= 2:
                spans.append(max(mids) - min(mids))
        span_val = max(spans) if spans else (max(pitches) - min(pitches) if pitches else None)
        # Leaps
        ordered_onsets = sorted(onsets_by_hand.get(hand, {}).keys())
        pitches_per_onset = [sorted(onsets_by_hand[hand][o]) for o in ordered_onsets] if hand in onsets_by_hand else []
        mean_leap, max_leap = _hand_leaps(pitches_per_onset) if pitches_per_onset else (None, None)
        summaries.append(
            NoteSummary(
                hand=hand,
                note_count=note_count_by_hand.get(hand, len(logical) if hand is None else 0),
                onset_count=len(onset_sets.get(hand, set())) if hand in onset_sets else len({n.onset for n in logical}),
                voice_count=len(voice_by_hand.get(hand, set())) if hand in voice_by_hand else len({str(n.voice) for n in logical if n.voice}),
                pitch_min=min(pitches) if pitches else None,
                pitch_max=max(pitches) if pitches else None,
                span_semitones=span_val,
                mean_leap=mean_leap,
                max_leap=max_leap,
            )
        )

    # Extra heuristics for labeling
    # Detect two-voice texture: any hand has >=2 distinct voices with notes
    has_two_voice = any(s.voice_count >= 2 for s in summaries)
    extra["has_two_voice_texture"] = has_two_voice

    # Detect repeated ascending pattern: check right-hand pitch contour repeats
    # Simplified: look for at least two onsets where pitch sets ascend stepwise and repeat
    right_onsets = sorted(onsets_by_hand.get("right", {}).keys())
    if len(right_onsets) >= 3:
        # Build per-onset representative pitch (median)
        rep_pitches = []
        for o in right_onsets:
            mids = sorted(onsets_by_hand["right"][o])
            rep_pitches.append(sum(mids) / len(mids))
        # Check for repeated interval pattern length 2-3
        has_repeated = False
        for plen in (2, 3):
            if len(rep_pitches) < plen * 2:
                continue
            intervals = [rep_pitches[i + 1] - rep_pitches[i] for i in range(len(rep_pitches) - 1)]
            # Look for repeating interval subsequence
            for start in range(len(intervals) - plen * 2 + 2):
                a = intervals[start : start + plen]
                b = intervals[start + plen : start + plen * 2]
                if len(a) == len(b) and all(abs(x - y) <= 1.5 for x, y in zip(a, b)) and all(x > 0 for x in a):
                    has_repeated = True
                    break
            if has_repeated:
                break
        extra["has_repeated_ascending_pattern"] = has_repeated
    else:
        extra["has_repeated_ascending_pattern"] = False

    # Arpeggiated arrival: wide span in last onset vs earlier narrow
    if right_onsets:
        last_span = 0
        if right_onsets:
            last_mids = onsets_by_hand.get("right", {}).get(right_onsets[-1], [])
            if len(last_mids) >= 2:
                last_span = max(last_mids) - min(last_mids)
        earlier_spans = []
        for o in right_onsets[:-1]:
            mids = onsets_by_hand.get("right", {}).get(o, [])
            if len(mids) >= 2:
                earlier_spans.append(max(mids) - min(mids))
        extra["last_span_semitones"] = last_span
        extra["earlier_max_span"] = max(earlier_spans) if earlier_spans else 0
        extra["is_arpeggiated_arrival"] = last_span >= 12 and (not earlier_spans or last_span >= max(earlier_spans) + 5)

    # Left-hand relocation: large leap in left hand last step
    left_onsets = sorted(onsets_by_hand.get("left", {}).keys())
    if len(left_onsets) >= 2:
        left_rep = []
        for o in left_onsets:
            mids = sorted(onsets_by_hand["left"][o])
            left_rep.append(sum(mids) / len(mids))
        last_leap = abs(left_rep[-1] - left_rep[-2]) if len(left_rep) >= 2 else 0
        extra["left_last_leap_semitones"] = int(last_leap)
        extra["has_left_relocation"] = last_leap >= 7
    else:
        extra["left_last_leap_semitones"] = 0
        extra["has_left_relocation"] = False

    # Dense two-hand coordination: both hands have onset in same window and mismatch
    right_set = set(onsets_by_hand.get("right", {}).keys())
    left_set = set(onsets_by_hand.get("left", {}).keys())
    if right_set and left_set:
        overlap = right_set & left_set
        extra["aligned_onset_count"] = len(overlap)
        extra["union_onset_count"] = len(right_set | left_set)
        extra["has_dense_coordination"] = len(overlap) >= 2 or (len(right_set) >= 3 and len(left_set) >= 2)
    else:
        extra["has_dense_coordination"] = False

    return NoteEvidence(
        start_offset=region.start_offset,
        end_offset=region.end_offset,
        measure_start=region.measure_start,
        measure_end=region.measure_end,
        measure_numbers=tuple(region.measure_numbers),
        logical_note_ids=tuple(n.note_id for n in logical[:24]),
        written_note_ids=tuple(n.note_id for n in written[:24]),
        hand_summaries=tuple(summaries),
        diagnostics=tuple(diagnostics),
        extra=extra,
    )
