"""Compact Yan-style statistical descriptors, promoted to runtime.

These are score-native, low-risk aggregates already implemented and regression-checked
in ``tests/harness/yan2023/extractor.py``. This runtime module reuses the same
math (mean, population std, Shannon entropy over exact MIDI pitches,
mean absolute distance from C4, adjacent-normalized variability,
black-key pitch-class ratio, compact polyphony rate, typed chord counts)
but emits them as ordinary ``FeatureRecord`` entries with explicit
``statistics.*`` feature_ids, units, and provenance diagnostics.

Blocked or ambiguous Yan features are intentionally not promoted:
pressing_velocity_*, melodic_complexity/originality/melodiousness,
ergonomic hand_stretch beyond the existing ``pitch_geometry`` span,
and anything requiring MIDI/performance data.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from math import log2, sqrt

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import feature_record, score_duration_quarters
from piano_difficulty.normalize.schema import ScoreIR

_BLACK_KEY_PITCH_CLASSES = {1, 3, 6, 8, 10}


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract promoted compact statistical descriptors (piece scope)."""

    logical_notes = list(score.logical_notes)
    written_notes = list(score.written_notes)
    pitch_values = [note.pitch_midi for note in logical_notes]
    duration_values = [float(note.duration) for note in logical_notes if note.duration > 0]

    # Pitch / duration aggregates (logical-note contracts, matching Yan harness)
    pitch_mean = _mean(pitch_values)
    pitch_std = _population_stddev(pitch_values)
    duration_mean = _mean(duration_values)
    duration_std = _population_stddev(duration_values)

    pitch_entropy = _entropy(pitch_values)
    deviation_from_c4 = _mean(abs(pitch - 60) for pitch in pitch_values) if pitch_values else 0.0

    # Variability: adjacent-normalized over ordered written notes (Yan default)
    ordered_written = _ordered_written_notes(written_notes)
    pitch_variability = _adjacent_normalized_variability(
        [float(note.pitch_midi) for note in ordered_written]
    )
    duration_variability = _adjacent_normalized_variability(
        [float(note.duration) for note in ordered_written]
    )

    # Black-key rate: written-note ratio (Yan default black_key_rate_formula=written_note_ratio)
    black_key_rate = _black_key_rate_written(written_notes)

    # Compact polyphony rate: polyphonic onset ratio (Yan default)
    polyphony_rate = _polyphony_rate_onset_ratio(logical_notes)

    # Typed chord counts: distinct pitch-class cardinality per global onset group
    chord_counts = _chord_type_counts(score)

    events = list(score.logical_notes) or list(score.written_notes) or list(score.measures)

    records: list[FeatureRecord] = [
        feature_record(
            "statistics.pitch_mean",
            value=float(pitch_mean),
            units="midi",
            events=events,
            diagnostics=["Yan-harness derived: mean(MIDI pitch) over logical notes"],
        ),
        feature_record(
            "statistics.pitch_std",
            value=float(pitch_std),
            units="midi",
            events=events,
            diagnostics=["Yan-harness derived: population stddev of MIDI pitch over logical notes"],
        ),
        feature_record(
            "statistics.pitch_entropy",
            value=float(pitch_entropy),
            units="bits",
            events=events,
            diagnostics=["Yan-harness derived: Shannon entropy over exact MIDI pitch histogram"],
        ),
        feature_record(
            "statistics.deviation_from_c4",
            value=float(deviation_from_c4),
            units="semitones",
            events=events,
            diagnostics=["Yan-harness derived: mean(abs(MIDI-60)) over logical notes"],
        ),
        feature_record(
            "statistics.duration_mean",
            value=float(duration_mean),
            units="quarter_notes",
            events=events,
            diagnostics=["Yan-harness derived: mean(logical note duration) in quarter notes"],
        ),
        feature_record(
            "statistics.duration_std",
            value=float(duration_std),
            units="quarter_notes",
            events=events,
            diagnostics=["Yan-harness derived: population stddev of logical note duration"],
        ),
        feature_record(
            "statistics.pitch_variability",
            value=float(pitch_variability),
            units="ratio",
            events=events,
            diagnostics=[
                "Yan-harness derived: variability_formula=adjacent_normalized",
                "Variability over ordered written-note MIDI pitches; flattened by onset/measure/xml_order",
            ],
        ),
        feature_record(
            "statistics.duration_variability",
            value=float(duration_variability),
            units="ratio",
            events=events,
            diagnostics=[
                "Yan-harness derived: variability_formula=adjacent_normalized",
                "Variability over ordered written-note durations in quarter notes",
            ],
        ),
        feature_record(
            "statistics.black_key_rate",
            value=float(black_key_rate),
            units="ratio",
            events=events,
            diagnostics=[
                "Yan-harness derived: black_key_rate_formula=written_note_ratio",
                "count(pitch%12 in {1,3,6,8,10}) / N over written notes",
            ],
        ),
        feature_record(
            "statistics.polyphony_rate",
            value=float(polyphony_rate),
            units="ratio",
            events=events,
            diagnostics=[
                "Yan-harness derived: polyphony_rate_formula=polyphonic_onset_ratio",
                "count(onsets with >1 note) / count(distinct onsets) over logical notes",
            ],
        ),
        feature_record(
            "statistics.triad_count",
            value=int(chord_counts["triad"]),
            units="chords",
            events=events,
            diagnostics=["Yan-harness derived: distinct pitch-class set size == 3 per global onset group"],
        ),
        feature_record(
            "statistics.seventh_chord_count",
            value=int(chord_counts["seventh"]),
            units="chords",
            events=events,
            diagnostics=["Yan-harness derived: distinct pitch-class set size == 4 per global onset group"],
        ),
        feature_record(
            "statistics.ninth_chord_count",
            value=int(chord_counts["ninth"]),
            units="chords",
            events=events,
            diagnostics=["Yan-harness derived: distinct pitch-class set size >=5 per global onset group"],
        ),
    ]

    return records


def _mean(values) -> float:
    lst = list(values)
    if not lst:
        return 0.0
    return float(sum(lst)) / len(lst)


def _population_stddev(values) -> float:
    lst = list(values)
    if not lst:
        return 0.0
    avg = _mean(lst)
    return sqrt(sum((float(v) - avg) ** 2 for v in lst) / len(lst))


def _entropy(values: list[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((c / total) * log2(c / total) for c in counts.values() if c > 0)


def _adjacent_normalized_variability(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    terms: list[float] = []
    for left, right in zip(values, values[1:]):
        denom = (abs(left) + abs(right)) / 2
        if denom == 0:
            continue
        terms.append(abs(left - right) / denom)
    if not terms:
        return 0.0
    return sum(terms) / len(terms)


def _is_black_key(pitch_midi: int) -> bool:
    return (pitch_midi % 12) in _BLACK_KEY_PITCH_CLASSES


def _black_key_rate_written(written_notes) -> float:
    if not written_notes:
        return 0.0
    black = sum(1 for n in written_notes if _is_black_key(n.pitch_midi))
    return float(black) / float(len(written_notes)) if written_notes else 0.0


def _polyphony_rate_onset_ratio(logical_notes) -> float:
    if not logical_notes:
        return 0.0
    grouped: dict[Fraction, list[int]] = defaultdict(list)
    for note in logical_notes:
        grouped[note.onset].append(note.pitch_midi)
    total = len(grouped)
    poly = sum(1 for pitches in grouped.values() if len(pitches) > 1)
    return float(poly) / float(total) if total else 0.0


def _ordered_written_notes(written_notes):
    return sorted(
        written_notes,
        key=lambda note: (
            note.onset,
            note.measure_index if note.measure_index is not None else 0,
            note.measure_staff_order if note.measure_staff_order is not None else 0,
            note.xml_order if note.xml_order is not None else 0,
            note.note_id,
        ),
    )


def _chord_type_counts(score: ScoreIR) -> dict[str, int]:
    counts = {"triad": 0, "seventh": 0, "ninth": 0}
    # Global onset groups (hand is None) match Yan's compact whole-score chord typing.
    chord_events = [g for g in score.onset_groups if g.hand is None]
    # Fallback: if no global groups (e.g., synthetic fixtures built with hand groups only),
    # derive from logical notes grouped by onset.
    if not chord_events:
        grouped: dict[Fraction, list[str]] = defaultdict(list)
        for note in score.logical_notes:
            grouped[note.onset].append(note.note_id)
        # Build synthetic groups lazily by pitch class
        note_lookup = {n.note_id: n.pitch_midi for n in score.logical_notes}
        written_lookup = {n.note_id: n.pitch_midi for n in score.written_notes}
        for note_ids in grouped.values():
            if len(note_ids) <= 1:
                continue
            pcs = set()
            for nid in note_ids:
                midi = note_lookup.get(nid)
                if midi is None:
                    midi = written_lookup.get(nid)
                if midi is not None:
                    pcs.add(midi % 12)
            size = len(pcs)
            if size == 3:
                counts["triad"] += 1
            elif size == 4:
                counts["seventh"] += 1
            elif size >= 5:
                counts["ninth"] += 1
        return counts

    logical_lookup = {n.note_id: n.pitch_midi for n in score.logical_notes}
    written_lookup = {n.note_id: n.pitch_midi for n in score.written_notes}
    for event in chord_events:
        pcs = set()
        for nid in event.note_ids:
            midi = logical_lookup.get(nid)
            if midi is None:
                midi = written_lookup.get(nid)
            if midi is not None:
                pcs.add(midi % 12)
        size = len(pcs)
        if size == 3:
            counts["triad"] += 1
        elif size == 4:
            counts["seventh"] += 1
        elif size >= 5:
            counts["ninth"] += 1
    return counts
