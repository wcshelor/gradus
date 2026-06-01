"""Shared reference-style metrics used by direct features and analysis profiles."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

from piano_difficulty.analysis.compatibility import StaffEvent, build_php_compatibility_view
from piano_difficulty.normalize.schema import MeasureIR, ScoreIR, WrittenNoteIR

_DURATION_DENOMINATORS = {
    "whole": 1,
    "half": 2,
    "quarter": 4,
    "eighth": 8,
    "16th": 16,
    "32nd": 32,
    "64th": 64,
    "128th": 128,
    "256th": 256,
}

_HAND_TO_STAFF = {
    "right": 1,
    "left": 2,
}


@dataclass(slots=True)
class DurationValueStat:
    duration_value: Fraction
    count: int
    ratio: float
    notes: tuple[WrittenNoteIR, ...]

    @property
    def scope_ref(self) -> str:
        if self.duration_value.denominator == 1:
            return str(self.duration_value.numerator)
        return f"{self.duration_value.numerator}/{self.duration_value.denominator}"


@dataclass(slots=True)
class DisplacementEvent:
    measure_index: int
    note_id: str
    semitones: int


@dataclass(slots=True)
class HandReferenceMetrics:
    hand: str
    note_count: int
    position_count: int
    chord_count: int
    chord_ratio: float
    octave_chord_count: int
    octave_chord_ratio: float
    accidental_count: int
    accidental_ratio: float
    timed_difficult_displacement_count: int
    timed_difficult_displacement_ratio: float
    max_timed_difficult_displacement: int
    chord_measure_counts: dict[int, int] = field(default_factory=dict)
    accidental_measure_counts: dict[int, int] = field(default_factory=dict)
    displacement_measure_counts: dict[int, int] = field(default_factory=dict)
    displacement_events: tuple[DisplacementEvent, ...] = ()
    notes: tuple[WrittenNoteIR, ...] = ()


@dataclass(slots=True)
class ReferenceMetrics:
    page_count: int
    duration_distribution: tuple[DurationValueStat, ...]
    significant_shortest_value: Fraction
    asymmetric_tuplet_measures: tuple[int, ...]
    polyrhythm_measures: tuple[int, ...]
    hand_metrics: dict[str, HandReferenceMetrics]
    initial_tempo_bpm: float | None
    initial_key_fifths: int | None


def compute_reference_metrics(score: ScoreIR) -> ReferenceMetrics:
    """Compute reference-style raw metrics from one normalized score."""

    duration_distribution = _duration_distribution(score)
    significant_shortest_value = _significant_shortest_value(duration_distribution)
    asymmetric_tuplet_measures, polyrhythm_measures = _tuplet_measure_sets(score)

    hand_metrics = {
        hand: _hand_metrics(score, hand)
        for hand in ("right", "left")
    }

    return ReferenceMetrics(
        page_count=_page_count(score.measures),
        duration_distribution=duration_distribution,
        significant_shortest_value=significant_shortest_value,
        asymmetric_tuplet_measures=tuple(sorted(asymmetric_tuplet_measures)),
        polyrhythm_measures=tuple(sorted(polyrhythm_measures)),
        hand_metrics=hand_metrics,
        initial_tempo_bpm=_initial_tempo_bpm(score.measures),
        initial_key_fifths=_initial_key_fifths(score.measures),
    )


def _page_count(measures: list[MeasureIR]) -> int:
    page_numbers = {measure.page_number for measure in measures if measure.page_number is not None}
    if page_numbers:
        return len(page_numbers)
    new_page_markers = sum(1 for measure in measures if measure.starts_new_page)
    if new_page_markers:
        return new_page_markers + 1
    return 1 if measures else 0


def _duration_distribution(score: ScoreIR) -> tuple[DurationValueStat, ...]:
    counts: dict[Fraction, int] = defaultdict(int)
    notes_by_value: dict[Fraction, list[WrittenNoteIR]] = defaultdict(list)
    note_count = len(score.written_notes)

    for note in score.written_notes:
        duration_value = _duration_value(note)
        counts[duration_value] += 1
        notes_by_value[duration_value].append(note)

    stats = [
        DurationValueStat(
            duration_value=value,
            count=counts[value],
            ratio=(counts[value] / note_count) if note_count else 0.0,
            notes=tuple(notes_by_value[value]),
        )
        for value in sorted(counts, key=float)
    ]
    return tuple(stats)


def _duration_value(note: WrittenNoteIR) -> Fraction:
    base = Fraction(_DURATION_DENOMINATORS.get(note.duration_type or "", 0), 1)
    if base <= 0:
        if note.duration <= 0:
            return Fraction(0, 1)
        return Fraction(4, 1) / note.duration
    if note.tuplet_actual and note.tuplet_normal:
        return base * Fraction(note.tuplet_actual, note.tuplet_normal)
    return base


def _significant_shortest_value(
    duration_distribution: tuple[DurationValueStat, ...],
) -> Fraction:
    significant = Fraction(1, 1)
    for stat in duration_distribution:
        if stat.duration_value > significant and stat.ratio > 0.15:
            significant = stat.duration_value
    return significant


def _tuplet_measure_sets(score: ScoreIR) -> tuple[set[int], set[int]]:
    by_measure_and_hand: dict[int, dict[str, set[tuple[int, int]]]] = defaultdict(
        lambda: defaultdict(set)
    )
    asymmetric: set[int] = set()

    for note in score.written_notes:
        if note.measure_index is None:
            continue
        if note.tuplet_actual is None or note.tuplet_normal is None:
            continue

        signature = (note.tuplet_actual, note.tuplet_normal)
        hand = note.hand or "unknown"
        by_measure_and_hand[note.measure_index][hand].add(signature)
        if note.tuplet_actual != note.tuplet_normal:
            asymmetric.add(note.measure_index)

    polyrhythm: set[int] = set()
    for measure_index, hand_signatures in by_measure_and_hand.items():
        right = hand_signatures.get("right", set())
        left = hand_signatures.get("left", set())
        if right != left:
            polyrhythm.add(measure_index)

    return asymmetric, polyrhythm


def _hand_metrics(score: ScoreIR, hand: str) -> HandReferenceMetrics:
    view = build_php_compatibility_view(score)
    staff = _HAND_TO_STAFF[hand]
    notes = list(view.notes_for_staff(staff))
    events = list(view.events_for_staff(staff))

    position_count = 0
    chord_count = 0
    octave_chord_count = 0
    accidental_count = 0
    chord_measure_counts: dict[int, int] = defaultdict(int)
    accidental_measure_counts: dict[int, int] = defaultdict(int)
    displacement_measure_counts: dict[int, int] = defaultdict(int)
    displacement_events: list[DisplacementEvent] = []

    onset_notes: list[WrittenNoteIR] = []
    for note in notes:
        if note.accidental:
            accidental_count += 1
            if note.measure_index is not None:
                accidental_measure_counts[note.measure_index] += 1

        if not note.is_chord_continuation:
            onset_notes.append(note)
            continue

    for index, note in enumerate(onset_notes):
        chord_size = _chord_size(note, notes)
        if chord_size > 1:
            chord_count += 1
            if note.measure_index is not None:
                chord_measure_counts[note.measure_index] += 1
            if _has_octave_above_base(note, notes):
                octave_chord_count += 1
        if index > 0:
            position_count += 1
            previous = onset_notes[index - 1]
            displacement = abs(note.pitch_midi - previous.pitch_midi)
            if displacement > 12 and _short_gap(previous, note, events, score.measures):
                displacement_events.append(
                    DisplacementEvent(
                        measure_index=note.measure_index or previous.measure_index or 0,
                        note_id=note.note_id,
                        semitones=displacement,
                    )
                )
                if note.measure_index is not None:
                    displacement_measure_counts[note.measure_index] += 1

    difficult_count = len(displacement_events)
    return HandReferenceMetrics(
        hand=hand,
        note_count=len(notes),
        position_count=position_count,
        chord_count=chord_count,
        chord_ratio=(chord_count / position_count * 100.0) if position_count else 0.0,
        octave_chord_count=octave_chord_count,
        octave_chord_ratio=(octave_chord_count / chord_count * 100.0) if chord_count else 0.0,
        accidental_count=accidental_count,
        accidental_ratio=(accidental_count / len(notes) * 100.0) if notes else 0.0,
        timed_difficult_displacement_count=difficult_count,
        timed_difficult_displacement_ratio=(
            difficult_count / position_count * 100.0 if position_count else 0.0
        ),
        max_timed_difficult_displacement=max(
            (event.semitones for event in displacement_events),
            default=0,
        ),
        chord_measure_counts=dict(sorted(chord_measure_counts.items())),
        accidental_measure_counts=dict(sorted(accidental_measure_counts.items())),
        displacement_measure_counts=dict(sorted(displacement_measure_counts.items())),
        displacement_events=tuple(displacement_events),
        notes=tuple(notes),
    )


def _chord_size(base_note: WrittenNoteIR, notes: list[WrittenNoteIR]) -> int:
    size = 0
    for note in notes:
        if note.measure_index != base_note.measure_index:
            continue
        if note.onset != base_note.onset:
            continue
        size += 1
    return size


def _has_octave_above_base(base_note: WrittenNoteIR, notes: list[WrittenNoteIR]) -> bool:
    for note in notes:
        if note.measure_index != base_note.measure_index:
            continue
        if note.onset != base_note.onset:
            continue
        if note.pitch_midi == base_note.pitch_midi + 12:
            return True
    return False


def _short_gap(
    previous_note: WrittenNoteIR,
    current_note: WrittenNoteIR,
    events: list[StaffEvent],
    measures: list[MeasureIR],
) -> bool:
    gap_duration = Fraction(0, 1)
    for event in reversed(events):
        if event.onset >= current_note.onset:
            continue
        gap_duration += event.duration
        if isinstance(event, WrittenNoteIR) and not event.is_chord_continuation:
            previous_beat_type = _measure_beat_type(measures, event.measure_index)
            beat_type = _measure_beat_type(measures, current_note.measure_index)
            effective_beat_type = beat_type or previous_beat_type or 4
            return gap_duration <= Fraction(8, effective_beat_type)
    return abs(current_note.onset - previous_note.onset) <= Fraction(2, 1)


def _measure_beat_type(measures: list[MeasureIR], measure_index: int | None) -> int | None:
    if measure_index is None:
        return None
    for measure in measures:
        if measure.measure_index == measure_index:
            return measure.time_beat_type
    return None


def _initial_tempo_bpm(measures: list[MeasureIR]) -> float | None:
    for measure in measures:
        if measure.tempo_bpm is not None:
            return measure.tempo_bpm
    return None


def _initial_key_fifths(measures: list[MeasureIR]) -> int | None:
    for measure in measures:
        if measure.key_fifths is not None:
            return measure.key_fifths
    return None
