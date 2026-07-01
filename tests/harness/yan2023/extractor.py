"""First-pass paper-first feature extraction for the Yan 2023 lane."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from fractions import Fraction
from math import log2, sqrt
from pathlib import Path

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir
from piano_difficulty.normalize.schema import (
    DirectionIR,
    LogicalNoteIR,
    MeasureIR,
    OnsetGroupIR,
    ScoreIR,
    WrittenNoteIR,
)

from tests.harness.yan2023.slot_inventory import FeatureStatus, WORKING_FEATURE_SLOTS

_DURATION_TYPE_QUARTERS = {
    "whole": Fraction(4, 1),
    "half": Fraction(2, 1),
    "quarter": Fraction(1, 1),
    "eighth": Fraction(1, 2),
    "16th": Fraction(1, 4),
    "32nd": Fraction(1, 8),
    "64th": Fraction(1, 16),
    "128th": Fraction(1, 32),
    "256th": Fraction(1, 64),
}
_BLACK_KEY_CLASSES = {1, 3, 6, 8, 10}
_SCOPE_TO_STAFF = {"bs": 2, "ts": 1}


@dataclass(frozen=True, slots=True)
class Yan2023FeatureValue:
    """One extracted or estimated paper-first Yan feature value."""

    slot_id: str
    value: float | int | str | None
    units: str | None
    status: FeatureStatus
    reliability: str
    diagnostics: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _ScopeView:
    code: str
    logical_notes: tuple[LogicalNoteIR, ...]
    written_notes: tuple[WrittenNoteIR, ...]
    chord_events: tuple[OnsetGroupIR, ...]


def extract_first_pass(score: ScoreIR) -> list[Yan2023FeatureValue]:
    """Extract the current supported working subset of paper-derived slots."""

    duration = _score_duration_quarters(score)
    scope_views = _build_scope_views(score)
    logical_lookup = {note.note_id: note for note in score.logical_notes}
    written_lookup = {note.note_id: note for note in score.written_notes}
    metrics = compute_reference_metrics(score)

    values: dict[str, Yan2023FeatureValue] = {}
    for _scope_code, view in scope_views.items():
        values.update(
            _extract_scope_values(
                view,
                score_duration=duration,
                logical_lookup=logical_lookup,
                written_lookup=written_lookup,
                metrics=metrics,
            )
        )

    values.update(_extract_global_values(score))

    ordered_values: list[Yan2023FeatureValue] = []
    for slot in WORKING_FEATURE_SLOTS:
        value = values.get(slot.slot_id)
        if value is not None:
            ordered_values.append(value)
    return ordered_values


def extract_first_pass_from_path(
    path: str | Path,
) -> tuple[ScoreIR, list[Yan2023FeatureValue]]:
    """Load one MusicXML-family file and run the first-pass Yan extractor."""

    document = load_musicxml_document(path)
    score = build_score_ir(document)
    return score, extract_first_pass(score)


def _build_scope_views(score: ScoreIR) -> dict[str, _ScopeView]:
    scope_views: dict[str, _ScopeView] = {
        "es": _ScopeView(
            code="es",
            logical_notes=tuple(score.logical_notes),
            written_notes=tuple(score.written_notes),
            chord_events=tuple(
                onset_group for onset_group in score.onset_groups if onset_group.hand is None
            ),
        )
    }
    for scope_code, staff in _SCOPE_TO_STAFF.items():
        hand = "left" if scope_code == "bs" else "right"
        scope_views[scope_code] = _ScopeView(
            code=scope_code,
            logical_notes=tuple(note for note in score.logical_notes if note.staff == staff),
            written_notes=tuple(note for note in score.written_notes if note.staff == staff),
            chord_events=tuple(
                onset_group
                for onset_group in score.onset_groups
                if onset_group.hand == hand
            ),
        )
    return scope_views


def _extract_scope_values(
    view: _ScopeView,
    *,
    score_duration: Fraction,
    logical_lookup: dict[str, LogicalNoteIR],
    written_lookup: dict[str, WrittenNoteIR],
    metrics: object,
) -> dict[str, Yan2023FeatureValue]:
    values: dict[str, Yan2023FeatureValue] = {}
    logical_notes = list(view.logical_notes)
    written_notes = list(view.written_notes)
    pitch_values = [note.pitch_midi for note in logical_notes]
    duration_values = [float(note.duration) for note in logical_notes if note.duration > 0]

    values[f"pitch_mean_{view.code}"] = _value(
        f"pitch_mean_{view.code}",
        _mean(pitch_values),
        "midi",
        status="implemented",
    )
    values[f"deviation_of_pitch_{view.code}"] = _value(
        f"deviation_of_pitch_{view.code}",
        _population_stddev(pitch_values),
        "midi",
        status="implemented",
    )
    values[f"pitch_range_{view.code}"] = _value(
        f"pitch_range_{view.code}",
        (max(pitch_values) - min(pitch_values)) if pitch_values else 0.0,
        "semitones",
        status="implemented",
    )
    values[f"pitch_entropy_{view.code}"] = _value(
        f"pitch_entropy_{view.code}",
        _entropy(pitch_values),
        "bits",
        status="implemented",
    )
    values[f"deviation_of_pitch_from_C4_{view.code}"] = _value(
        f"deviation_of_pitch_from_C4_{view.code}",
        _mean(abs(pitch - 60) for pitch in pitch_values),
        "semitones",
        status="implemented",
    )
    values[f"black_key_rate_{view.code}"] = _value(
        f"black_key_rate_{view.code}",
        _ratio(
            sum(1 for pitch in pitch_values if pitch % 12 in _BLACK_KEY_CLASSES),
            len(pitch_values),
        ),
        "ratio",
        status="implemented",
    )
    values[f"mean_of_note_duration_{view.code}"] = _value(
        f"mean_of_note_duration_{view.code}",
        _mean(duration_values),
        "quarter_notes",
        status="implemented",
    )
    values[f"deviation_of_note_duration_{view.code}"] = _value(
        f"deviation_of_note_duration_{view.code}",
        _population_stddev(duration_values),
        "quarter_notes",
        status="implemented",
    )
    values[f"note_density_{view.code}"] = _value(
        f"note_density_{view.code}",
        _ratio(len(logical_notes), float(score_duration)),
        "notes_per_quarter",
        status="implemented",
    )
    values[f"pitch_variability_{view.code}"] = _value(
        f"pitch_variability_{view.code}",
        _adjacent_normalized_variability(
            [note.pitch_midi for note in _ordered_written_notes(written_notes)]
        ),
        "ratio",
        status="implemented",
    )
    values[f"note_duration_variability_{view.code}"] = _value(
        f"note_duration_variability_{view.code}",
        _adjacent_normalized_variability(
            [float(note.duration) for note in _ordered_written_notes(written_notes)]
        ),
        "ratio",
        status="implemented",
    )
    values[f"staccato_rate_{view.code}"] = _value(
        f"staccato_rate_{view.code}",
        _ratio(
            sum(1 for note in written_notes if "staccato" in note.articulations),
            len(written_notes),
        ),
        "ratio",
        status="implemented",
    )

    dotted_count, dotted_diagnostics = _dotted_note_count(written_notes)
    values[f"dotted_note_rate_{view.code}"] = Yan2023FeatureValue(
        slot_id=f"dotted_note_rate_{view.code}",
        value=_ratio(dotted_count, len(written_notes)),
        units="ratio",
        status="proxyable",
        reliability="proxy",
        diagnostics=tuple(dotted_diagnostics),
    )

    chord_type_counts = _chord_type_counts(view.chord_events, logical_lookup, written_lookup)
    values[f"triad_{view.code}"] = _value(
        f"triad_{view.code}",
        chord_type_counts["triad"],
        "chords",
        status="implemented",
    )
    values[f"seventh_chord_{view.code}"] = _value(
        f"seventh_chord_{view.code}",
        chord_type_counts["seventh"],
        "chords",
        status="implemented",
    )
    values[f"ninth_chord_{view.code}"] = _value(
        f"ninth_chord_{view.code}",
        chord_type_counts["ninth_or_larger"],
        "chords",
        status="implemented",
    )

    onset_groups = _scope_onset_groups(logical_notes)
    attack_count = len(onset_groups)
    polyphonic_onsets = sum(1 for pitches in onset_groups.values() if len(pitches) > 1)
    values[f"polyphony_rate_{view.code}"] = _value(
        f"polyphony_rate_{view.code}",
        _ratio(polyphonic_onsets, attack_count),
        "ratio",
        status="implemented",
    )
    values[f"playing_speed_{view.code}"] = Yan2023FeatureValue(
        slot_id=f"playing_speed_{view.code}",
        value=_ratio(attack_count, float(score_duration)),
        units="attacks_per_quarter",
        status="proxyable",
        reliability="proxy",
        diagnostics=(
            "Proxy uses attack density because the paper does not fully publish the playing-speed formula.",
        ),
    )
    values[f"distinct_stroke_rate_{view.code}"] = Yan2023FeatureValue(
        slot_id=f"distinct_stroke_rate_{view.code}",
        value=_ratio(attack_count, len(logical_notes)),
        units="ratio",
        status="proxyable",
        reliability="proxy",
        diagnostics=(
            "Proxy uses unique attack count over note count because the exact stroke-identity rule is unpublished.",
        ),
    )
    values[f"irregular_rhythm_{view.code}"] = Yan2023FeatureValue(
        slot_id=f"irregular_rhythm_{view.code}",
        value=_distinct_duration_ratio(written_notes),
        units="ratio",
        status="proxyable",
        reliability="proxy",
        diagnostics=(
            "Proxy uses distinct written-duration ratio because the paper does not fully publish the irregular-rhythm formula.",
        ),
    )

    if view.code in {"bs", "ts"}:
        hand = "left" if view.code == "bs" else "right"
        hand_metrics = metrics.hand_metrics[hand]
        values[f"hand_displacement_rate_{view.code}"] = Yan2023FeatureValue(
            slot_id=f"hand_displacement_rate_{view.code}",
            value=hand_metrics.timed_difficult_displacement_ratio,
            units="ratio",
            status="proxyable",
            reliability="proxy",
            diagnostics=(
                "Proxy uses repo timed-difficult-displacement ratio, not the unpublished Yan hand-displacement contract.",
            ),
        )
        values[f"hand_stretch_{view.code}"] = Yan2023FeatureValue(
            slot_id=f"hand_stretch_{view.code}",
            value=_max_vertical_span(logical_notes, onset_groups),
            units="semitones",
            status="proxyable",
            reliability="proxy",
            diagnostics=(
                "Proxy uses maximum same-onset vertical span because the paper does not publish a full hand-stretch model.",
            ),
        )

    return values


def _extract_global_values(score: ScoreIR) -> dict[str, Yan2023FeatureValue]:
    duration = _score_duration_quarters(score)
    measures = score.measures

    values: dict[str, Yan2023FeatureValue] = {
        "length": _value(
            "length",
            float(duration),
            "quarter_notes",
            status="implemented",
        ),
        "tempo": _value(
            "tempo",
            _initial_tempo(score.directions, measures),
            "bpm",
            status="implemented",
        ),
        "key_signature": _value(
            "key_signature",
            _initial_key_fifths(measures),
            "fifths",
            status="implemented",
        ),
        "playing_speed_variation": _value(
            "playing_speed_variation",
            _tempo_variation_ratio(score.directions, measures),
            "ratio",
            status="implemented",
        ),
    }
    return values


def _value(
    slot_id: str,
    value: float | int | str | None,
    units: str | None,
    *,
    status: FeatureStatus,
) -> Yan2023FeatureValue:
    return Yan2023FeatureValue(
        slot_id=slot_id,
        value=value,
        units=units,
        status=status,
        reliability="direct" if status == "implemented" else "proxy",
    )


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _score_duration_quarters(score: ScoreIR) -> Fraction:
    if score.measures:
        start = min(measure.start for measure in score.measures)
        end = max(measure.end for measure in score.measures)
        return max(Fraction(0), end - start)

    note_ends = [note.onset + note.duration for note in score.logical_notes]
    return max(note_ends, default=Fraction(0))


def _mean(values) -> float:
    values_list = list(values)
    if not values_list:
        return 0.0
    return float(sum(values_list)) / len(values_list)


def _population_stddev(values) -> float:
    values_list = list(values)
    if not values_list:
        return 0.0
    average = _mean(values_list)
    return sqrt(sum((float(value) - average) ** 2 for value in values_list) / len(values_list))


def _entropy(values: list[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum(
        (count / total) * log2(count / total)
        for count in counts.values()
        if count > 0
    )


def _ordered_written_notes(written_notes: list[WrittenNoteIR]) -> list[WrittenNoteIR]:
    return sorted(
        written_notes,
        key=lambda note: (
            note.onset,
            note.measure_index or 0,
            note.measure_staff_order or 0,
            note.xml_order or 0,
            note.note_id,
        ),
    )


def _adjacent_normalized_variability(values: list[float | int]) -> float:
    if len(values) < 2:
        return 0.0
    terms: list[float] = []
    for left, right in zip(values, values[1:]):
        denominator = (abs(float(left)) + abs(float(right))) / 2
        if denominator == 0:
            continue
        terms.append(abs(float(left) - float(right)) / denominator)
    return _mean(terms)


def _dotted_note_count(written_notes: list[WrittenNoteIR]) -> tuple[int, list[str]]:
    dotted_count = 0
    diagnostics: list[str] = []
    for note in written_notes:
        if note.tuplet_actual is not None:
            diagnostics.append(
                "Ignored tuplet note while heuristically recovering dotted-note rate."
            )
            continue
        base_duration = _DURATION_TYPE_QUARTERS.get(note.duration_type or "")
        if base_duration is None or base_duration <= 0:
            diagnostics.append(
                "Skipped note without recoverable duration type while estimating dotted-note rate."
            )
            continue
        ratio = float(note.duration / base_duration)
        if abs(ratio - 1.5) < 1e-6 or abs(ratio - 1.75) < 1e-6:
            dotted_count += 1
    return dotted_count, sorted(set(diagnostics))


def _chord_type_counts(
    chord_events: tuple[OnsetGroupIR, ...],
    logical_lookup: dict[str, LogicalNoteIR],
    written_lookup: dict[str, WrittenNoteIR],
) -> dict[str, int]:
    counts = {"triad": 0, "seventh": 0, "ninth_or_larger": 0}
    for chord_event in chord_events:
        pitch_classes = {
            _pitch_class_for_id(note_id, logical_lookup, written_lookup)
            for note_id in chord_event.note_ids
        }
        pitch_classes.discard(None)
        size = len(pitch_classes)
        if size == 3:
            counts["triad"] += 1
        elif size == 4:
            counts["seventh"] += 1
        elif size >= 5:
            counts["ninth_or_larger"] += 1
    return counts


def _pitch_class_for_id(
    note_id: str,
    logical_lookup: dict[str, LogicalNoteIR],
    written_lookup: dict[str, WrittenNoteIR],
) -> int | None:
    logical_note = logical_lookup.get(note_id)
    if logical_note is not None:
        return logical_note.pitch_midi % 12
    written_note = written_lookup.get(note_id)
    if written_note is not None:
        return written_note.pitch_midi % 12
    return None


def _scope_onset_groups(logical_notes: list[LogicalNoteIR]) -> dict[Fraction, list[int]]:
    grouped: dict[Fraction, list[int]] = defaultdict(list)
    for note in logical_notes:
        grouped[note.onset].append(note.pitch_midi)
    return grouped


def _max_vertical_span(
    logical_notes: list[LogicalNoteIR],
    onset_groups: dict[Fraction, list[int]],
) -> int:
    if not logical_notes:
        return 0
    spans = [
        max(pitches) - min(pitches)
        for pitches in onset_groups.values()
        if len(pitches) > 1
    ]
    return max(spans, default=0)


def _distinct_duration_ratio(written_notes: list[WrittenNoteIR]) -> float:
    if not written_notes:
        return 0.0
    duration_values = {float(note.duration) for note in written_notes if note.duration > 0}
    return _ratio(len(duration_values), len(written_notes))


def _initial_tempo(
    directions: list[DirectionIR],
    measures: list[MeasureIR],
) -> float | None:
    tempo_directions = sorted(
        (direction for direction in directions if direction.kind == "tempo"),
        key=lambda direction: (direction.start, direction.direction_id),
    )
    if tempo_directions:
        return _parse_float(tempo_directions[0].value)
    for measure in measures:
        if measure.tempo_bpm is not None:
            return measure.tempo_bpm
    return None


def _initial_key_fifths(measures: list[MeasureIR]) -> int | None:
    for measure in measures:
        if measure.key_fifths is not None:
            return measure.key_fifths
    return None


def _tempo_variation_ratio(
    directions: list[DirectionIR],
    measures: list[MeasureIR],
) -> float:
    tempo_values = [
        _parse_float(direction.value)
        for direction in sorted(
            (direction for direction in directions if direction.kind == "tempo"),
            key=lambda direction: (direction.start, direction.direction_id),
        )
    ]
    known_values = [value for value in tempo_values if value is not None]
    if not known_values:
        known_values = [measure.tempo_bpm for measure in measures if measure.tempo_bpm is not None]
    if not known_values:
        return 0.0
    if len(known_values) == 1:
        return 0.0

    changes = 0
    previous = known_values[0]
    for value in known_values[1:]:
        if value != previous:
            changes += 1
            previous = value
    return _ratio(changes, len(known_values))


def _parse_float(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


__all__ = [
    "Yan2023FeatureValue",
    "extract_first_pass",
    "extract_first_pass_from_path",
]
