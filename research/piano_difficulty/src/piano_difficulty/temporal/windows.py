"""Window and score-region helpers for temporal analysis."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal, Protocol

from piano_difficulty.normalize.schema import MeasureIR, ScoreIR

FinalWindowBehavior = Literal["include", "drop"]
HandMode = Literal["both", "left", "right"]
WindowKind = Literal["measure", "beat"]


@dataclass(frozen=True, slots=True)
class ScoreRegion:
    """A bounded score region suitable for plotting or regional extraction."""

    score_id: str | None
    window_index: int
    measure_start: int
    measure_end: int
    measure_numbers: tuple[str, ...] = ()
    start_offset: Fraction | None = None
    end_offset: Fraction | None = None
    start_beat: Fraction | None = None
    end_beat: Fraction | None = None
    position: float | None = None
    hand: HandMode | None = None
    label: str | None = None


@dataclass(frozen=True, slots=True)
class MeasureWindowSpec:
    """Fixed-measure window configuration."""

    size: int
    step: int = 1
    final_window_behavior: FinalWindowBehavior = "include"
    hand: HandMode | None = None


@dataclass(frozen=True, slots=True)
class BeatWindowSpec:
    """Beat-based window configuration."""

    size: Fraction | int | float
    step: Fraction | int | float | None = None
    final_window_behavior: FinalWindowBehavior = "include"
    hand: HandMode | None = None


class WindowStrategy(Protocol):
    """Protocol for future regional segmentation strategies."""

    def build(self, score: ScoreIR) -> list[ScoreRegion]:
        """Return ordered regions for the supplied score."""


def build_measure_windows(
    measures: Sequence[MeasureIR],
    size: int,
    step: int = 1,
    *,
    include_partial_final: bool = True,
) -> list[tuple[MeasureIR, ...]]:
    """Construct fixed-size measure windows for later local analysis."""

    if size <= 0:
        raise ValueError("Window size must be positive.")
    if step <= 0:
        raise ValueError("Window step must be positive.")

    ordered_measures = sorted(measures, key=lambda measure: measure.measure_index)
    if not ordered_measures:
        return []

    windows: list[tuple[MeasureIR, ...]] = []
    for start_index in range(0, len(ordered_measures), step):
        window = tuple(ordered_measures[start_index : start_index + size])
        if not window:
            continue
        if len(window) < size and not include_partial_final:
            continue
        windows.append(window)
    return windows


def build_measure_regions(
    score: ScoreIR,
    spec: MeasureWindowSpec,
) -> list[ScoreRegion]:
    """Return ordered score regions for a measure-based segmentation."""

    windows = build_measure_windows(
        score.measures,
        spec.size,
        spec.step,
        include_partial_final=spec.final_window_behavior == "include",
    )
    regions: list[ScoreRegion] = []
    score_id = _score_identifier(score)
    for window_index, window in enumerate(windows):
        if not window:
            continue
        start_measure = window[0]
        end_measure = window[-1]
        regions.append(
            ScoreRegion(
                score_id=score_id,
                window_index=window_index,
                measure_start=start_measure.measure_index,
                measure_end=end_measure.measure_index,
                measure_numbers=tuple(measure.measure_number for measure in window),
                start_offset=start_measure.start,
                end_offset=end_measure.end,
                start_beat=start_measure.start,
                end_beat=end_measure.end,
                position=_region_position(window),
                hand=spec.hand,
                label=_region_label(window_index, start_measure, end_measure, spec.hand),
            )
        )
    return regions


def build_beat_regions(
    score: ScoreIR,
    spec: BeatWindowSpec,
) -> list[ScoreRegion]:
    """Return ordered score regions using a beat-sized sliding window."""

    measures = sorted(score.measures, key=lambda measure: measure.measure_index)
    if not measures:
        return []

    window_size = _to_fraction(spec.size)
    if window_size <= 0:
        raise ValueError("Beat window size must be positive.")
    window_step = _to_fraction(spec.step if spec.step is not None else spec.size)
    if window_step <= 0:
        raise ValueError("Beat window step must be positive.")

    score_start = min(measure.start for measure in measures)
    score_end = max(measure.end for measure in measures)

    regions: list[ScoreRegion] = []
    window_index = 0
    window_start = score_start
    while window_start < score_end:
        window_end = min(window_start + window_size, score_end)
        overlapping = [
            measure
            for measure in measures
            if measure.start < window_end and measure.end > window_start
        ]
        if overlapping:
            if window_end - window_start < window_size and spec.final_window_behavior == "drop":
                break
            start_measure = overlapping[0]
            end_measure = overlapping[-1]
            regions.append(
                ScoreRegion(
                    score_id=_score_identifier(score),
                    window_index=window_index,
                    measure_start=start_measure.measure_index,
                    measure_end=end_measure.measure_index,
                    measure_numbers=tuple(measure.measure_number for measure in overlapping),
                    start_offset=window_start,
                    end_offset=window_end,
                    start_beat=window_start,
                    end_beat=window_end,
                    position=float((window_start + window_end) / 2),
                    hand=spec.hand,
                    label=_beat_region_label(window_index, window_start, window_end, spec.hand),
                )
            )
            window_index += 1

        if window_end >= score_end:
            break
        window_start += window_step

    return regions


def _score_identifier(score: ScoreIR) -> str | None:
    if score.source_path is not None:
        return str(score.source_path)
    return score.title


def _region_position(window: Sequence[MeasureIR]) -> float | None:
    if not window:
        return None
    start = window[0].start
    end = window[-1].end
    return float((start + end) / 2)


def _region_label(
    window_index: int,
    start_measure: MeasureIR,
    end_measure: MeasureIR,
    hand: HandMode | None,
) -> str:
    hand_suffix = "" if hand is None else f" [{hand}]"
    if start_measure.measure_index == end_measure.measure_index:
        return f"window {window_index + 1}: measure {start_measure.measure_number}{hand_suffix}"
    return (
        f"window {window_index + 1}: measures {start_measure.measure_number}"
        f"-{end_measure.measure_number}{hand_suffix}"
    )


def _beat_region_label(
    window_index: int,
    start_beat: Fraction,
    end_beat: Fraction,
    hand: HandMode | None,
) -> str:
    hand_suffix = "" if hand is None else f" [{hand}]"
    return f"beat window {window_index + 1}: {start_beat}..{end_beat}{hand_suffix}"


def _to_fraction(value: Fraction | int | float | None) -> Fraction:
    if value is None:
        return Fraction(0, 1)
    if isinstance(value, Fraction):
        return value
    return Fraction(str(value))
