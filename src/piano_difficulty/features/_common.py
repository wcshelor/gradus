"""Shared helpers for direct feature extractors."""

from __future__ import annotations

from collections.abc import Iterable
from fractions import Fraction

from piano_difficulty.analysis.source_map import HasMeasureIndex, build_source_span
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import LogicalNoteIR, MeasureIR, ScoreIR


def feature_record(
    feature_id: str,
    *,
    value: float | int | str,
    units: str | None,
    events: list[HasMeasureIndex] | None,
    scope: str = "piece",
    scope_ref: str = "all",
    reliability: str = "direct",
    diagnostics: list[str] | None = None,
) -> FeatureRecord:
    """Create a feature record with a consistent source-span shape."""

    return FeatureRecord(
        feature_id=feature_id,
        scope=scope,
        scope_ref=scope_ref,
        value=value,
        units=units,
        reliability=reliability,
        source_span=build_source_span(events or []),
        diagnostics=diagnostics or [],
    )


def score_events(score: ScoreIR) -> list[HasMeasureIndex]:
    """Return the broadest available event list for piece-level traceability."""

    if score.measures:
        return list(score.measures)
    if score.logical_notes:
        return list(score.logical_notes)
    return list(score.written_notes)


def score_duration_quarters(score: ScoreIR) -> Fraction:
    """Return the known score duration in quarter-note units."""

    if score.measures:
        start = min(measure.start for measure in score.measures)
        end = max(measure.end for measure in score.measures)
        return max(Fraction(0), end - start)

    note_ends = [note.onset + note.duration for note in score.logical_notes]
    return max(note_ends, default=Fraction(0))


def rate_per_quarter(count: int | float, duration: Fraction) -> float:
    """Return a per-quarter-note rate, guarding empty scores."""

    if duration <= 0:
        return 0.0
    return float(count) / float(duration)


def mean(values: Iterable[int | float]) -> float:
    """Return a float mean with an empty-input zero default."""

    values_list = list(values)
    if not values_list:
        return 0.0
    return float(sum(values_list)) / len(values_list)


def notes_by_id(score: ScoreIR) -> dict[str, LogicalNoteIR]:
    """Map logical note identifiers to notes."""

    return {note.note_id: note for note in score.logical_notes}


def measures_by_index(score: ScoreIR) -> dict[int, MeasureIR]:
    """Map measure indices to measure objects."""

    return {measure.measure_index: measure for measure in score.measures}
