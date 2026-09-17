"""Metadata and score-context descriptors.

This family should eventually cover stable score-level facts such as measure
count, note count, pitch range, and the number of key, meter, or tempo changes.
These are low-risk features to implement early because they are direct and easy
to validate against tiny fixtures.
"""

from __future__ import annotations

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import (
    feature_record,
    score_duration_quarters,
    score_events,
)
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract score-level metadata and context descriptors."""

    events = score_events(score)
    pitches = [note.pitch_midi for note in score.logical_notes]
    metrics = compute_reference_metrics(score)

    records: list[FeatureRecord] = [
        feature_record(
            "metadata.page_count",
            value=metrics.page_count,
            units="pages",
            events=events,
        ),
        feature_record(
            "metadata.measure_count",
            value=len(score.measures),
            units="measures",
            events=events,
        ),
        feature_record(
            "metadata.note_count",
            value=len(score.logical_notes),
            units="notes",
            events=score.logical_notes,
        ),
        feature_record(
            "metadata.pitch_range",
            value=(max(pitches) - min(pitches)) if pitches else 0,
            units="semitones",
            events=score.logical_notes,
        ),
        feature_record(
            "metadata.tempo_change_count",
            value=_tempo_change_count(score),
            units="changes",
            events=score.directions or score.measures,
        ),
        feature_record(
            "metadata.key_change_count",
            value=_change_count([measure.key_signature for measure in score.measures]),
            units="changes",
            events=score.measures,
        ),
        feature_record(
            "metadata.meter_change_count",
            value=_change_count(
                [measure.time_signature for measure in score.measures]
            ),
            units="changes",
            events=score.measures,
        ),
    ]

    # Compact score-native predictors promoted from Yan harness (direct, low-risk).
    length_quarters = float(score_duration_quarters(score))
    records.append(
        feature_record(
            "metadata.length_quarters",
            value=length_quarters,
            units="quarter_notes",
            events=events,
            diagnostics=["Yan-harness derived: score duration (max measure end - min start)"],
        )
    )

    primary_tempo = _initial_tempo(score)
    if primary_tempo is not None:
        records.append(
            feature_record(
                "metadata.primary_tempo",
                value=float(primary_tempo),
                units="bpm",
                events=score.directions or score.measures,
                diagnostics=["Yan-harness derived: first tempo direction or first measure tempo_bpm"],
            )
        )
    else:
        records.append(
            feature_record(
                "metadata.primary_tempo",
                value=0.0,
                units="bpm",
                events=score.directions or score.measures,
                diagnostics=["Yan-harness derived: no tempo found, fallback 0"],
            )
        )

    key_signature = _initial_key_fifths(score)
    if key_signature is not None:
        records.append(
            feature_record(
                "metadata.key_signature",
                value=int(key_signature),
                units="fifths",
                events=score.measures,
                diagnostics=["Yan-harness derived: first available measure key_fifths"],
            )
        )
    else:
        records.append(
            feature_record(
                "metadata.key_signature",
                value=0,
                units="fifths",
                events=score.measures,
                diagnostics=["Yan-harness derived: no key signature found, fallback 0"],
            )
        )

    return records


def _tempo_change_count(score: ScoreIR) -> int:
    tempo_values = [
        direction.value
        for direction in sorted(score.directions, key=lambda d: (d.start, d.direction_id))
        if direction.kind == "tempo"
    ]
    if tempo_values:
        return _change_count(tempo_values)

    return _change_count([measure.tempo_bpm for measure in score.measures])


def _change_count(values: list[object | None]) -> int:
    known_values = [value for value in values if value is not None]
    if not known_values:
        return 0

    changes = 0
    previous = known_values[0]
    for value in known_values[1:]:
        if value != previous:
            changes += 1
            previous = value
    return changes


def _initial_tempo(score: ScoreIR) -> float | None:
    tempo_directions = sorted(
        (d for d in score.directions if d.kind == "tempo"),
        key=lambda d: (d.start, d.direction_id),
    )
    if tempo_directions:
        parsed = _parse_float(tempo_directions[0].value)
        if parsed is not None:
            return parsed
    for measure in score.measures:
        if measure.tempo_bpm is not None:
            return float(measure.tempo_bpm)
    return None


def _initial_key_fifths(score: ScoreIR) -> int | None:
    for measure in score.measures:
        if measure.key_fifths is not None:
            return int(measure.key_fifths)
    return None


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
