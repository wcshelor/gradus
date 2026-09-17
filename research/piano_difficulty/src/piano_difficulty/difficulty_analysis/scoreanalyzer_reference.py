"""PHP-compatible reference difficulty profile."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import TYPE_CHECKING

from piano_difficulty.analysis.reference_metrics import ReferenceMetrics, compute_reference_metrics
from piano_difficulty.difficulty_analysis.models import (
    AnalysisDimensionResult,
    AnalysisProfileResult,
    DifficultyProfile,
)
if TYPE_CHECKING:
    from piano_difficulty.pipeline import ExtractionResult


def mark_speed(value: float | None) -> int | None:
    if value is None:
        return None
    if value <= 20:
        return 1
    if value <= 50:
        return 2
    if value <= 80:
        return 3
    return 4


def mark_displacement(value_rh: float | None, value_lh: float | None) -> int | None:
    result = _threshold_mark(value_rh, (5, 10, 20))
    result_lh = _threshold_mark(value_lh, (10, 20, 55))
    if result is None or result_lh is None:
        return None
    if result == 2 and result_lh == 2:
        return 3
    if result == 3 and result_lh == 3:
        return 4
    return max(result, result_lh)


def mark_chords(value_rh: float | None, value_lh: float | None) -> int | None:
    result = _threshold_mark(value_rh, (10, 30, 60))
    result_lh = _threshold_mark(value_lh, (10, 30, 60))
    if result is None or result_lh is None:
        return None
    if result == 2 and result_lh == 2:
        return 3
    if result == 3 and result_lh == 3:
        return 4
    return max(result, result_lh)


def mark_harmony(value_rh: float | None, value_lh: float | None) -> int | None:
    result = _threshold_mark(value_rh, (5, 20, 30))
    result_lh = _threshold_mark(value_lh, (5, 20, 30))
    if result is None or result_lh is None:
        return None
    if result == 3 and result_lh == 3:
        return 4
    return max(result, result_lh)


def mark_rhythm(value: float | None) -> int | None:
    if value is None:
        return None
    if value == 0:
        return 1
    if value <= 20:
        return 2
    if value <= 60:
        return 3
    return 4


def mark_length(value: int | None) -> int | None:
    if value is None or value <= 0:
        return None
    if value <= 2:
        return 1
    if value <= 4:
        return 2
    if value <= 6:
        return 3
    return 4


def mark_tonality(value: int | None) -> int | None:
    if value is None:
        return None
    if value <= 1:
        return 1
    if value <= 3:
        return 2
    if value <= 5:
        return 3
    return 4


def scoreanalyzer_legacy_label(mark: float | int | None) -> str | None:
    """Legacy ScoreAnalyzer compatibility labels for the reference profile only."""
    if mark is None:
        return None
    if mark < 1.5:
        return "beginner"
    if mark < 2.5:
        return "intermediate"
    if mark < 3.5:
        return "advanced"
    return "virtuoso"


def speed_ratio(metrics: ReferenceMetrics) -> float | None:
    if metrics.initial_tempo_bpm is None:
        return None
    return float(metrics.initial_tempo_bpm * float(metrics.significant_shortest_value) * 100 / 2816)


def _threshold_mark(value: float | None, thresholds: tuple[float, float, float]) -> int | None:
    if value is None:
        return None
    if value <= thresholds[0]:
        return 1
    if value <= thresholds[1]:
        return 2
    if value <= thresholds[2]:
        return 3
    return 4


@dataclass(slots=True)
class ScoreAnalyzerReferenceProfile(DifficultyProfile):
    profile_id: str = "scoreanalyzer_reference"
    profile_version: str = "1.0"

    def analyze(self, extraction: "ExtractionResult") -> AnalysisProfileResult:
        metrics = compute_reference_metrics(extraction.score)
        dimensions = [
            self._speed_dimension(metrics),
            self._displacement_dimension(metrics),
            self._chords_dimension(metrics),
            self._harmony_dimension(metrics),
            self._rhythm_dimension(metrics, measure_count=len(extraction.score.measures)),
            self._length_dimension(metrics),
            self._tonality_dimension(metrics),
        ]
        for dimension in dimensions:
            dimension.legacy_label = scoreanalyzer_legacy_label(dimension.mark)
        marks = [dimension.mark for dimension in dimensions]
        diagnostics: list[str] = []
        if any(mark is None for mark in marks):
            diagnostics.append("Overall score is unavailable because one or more dimensions are missing.")
            overall_score = None
            scoreanalyzer_legacy_grade = None
        else:
            overall_score = round(sum(marks) / len(marks), 1)
            scoreanalyzer_legacy_grade = scoreanalyzer_legacy_label(overall_score)

        notable_measures = sorted(
            {
                measure_index
                for dimension in dimensions
                for measure_index in dimension.notable_measures
            }
        )
        return AnalysisProfileResult(
            profile_id=self.profile_id,
            profile_version=self.profile_version,
            overall_score=overall_score,
            dimensions=dimensions,
            scoreanalyzer_legacy_grade=scoreanalyzer_legacy_grade,
            diagnostics=diagnostics,
            notable_measures=notable_measures,
        )

    def _speed_dimension(self, metrics: ReferenceMetrics) -> AnalysisDimensionResult:
        ratio = speed_ratio(metrics)
        mark = mark_speed(ratio)
        shortest = _fraction_text(metrics.significant_shortest_value)
        tempo = metrics.initial_tempo_bpm
        summary = (
            f"Estimated speed ratio {ratio:.1f}% from tempo {tempo:.0f} and significant shortest value {shortest}."
            if ratio is not None and tempo is not None
            else "Tempo context is missing."
        )
        return AnalysisDimensionResult(
            dimension_id="speed",
            mark=mark,
            raw_value=round(ratio, 3) if ratio is not None else None,
            raw_units="percent",
            summary=summary,
            source_span={"measure_start": 1 if tempo is not None else None, "measure_end": 1 if tempo is not None else None},
            diagnostics=[] if ratio is not None else ["No tempo value was available."],
            notable_measures=[],
        )

    def _displacement_dimension(self, metrics: ReferenceMetrics) -> AnalysisDimensionResult:
        right = metrics.hand_metrics["right"]
        left = metrics.hand_metrics["left"]
        mark = mark_displacement(
            right.timed_difficult_displacement_ratio,
            left.timed_difficult_displacement_ratio,
        )
        notable_measures = sorted(
            set(right.displacement_measure_counts) | set(left.displacement_measure_counts)
        )
        return AnalysisDimensionResult(
            dimension_id="displacement",
            mark=mark,
            raw_value=round(
                max(
                    right.timed_difficult_displacement_ratio,
                    left.timed_difficult_displacement_ratio,
                ),
                3,
            ),
            raw_units="percent",
            summary=(
                "Timed >12-semitone displacement ratio: "
                f"RH {right.timed_difficult_displacement_ratio:.1f}%, "
                f"LH {left.timed_difficult_displacement_ratio:.1f}%."
            ),
            source_span=_span_from_measures(notable_measures),
            notable_measures=notable_measures,
        )

    def _chords_dimension(self, metrics: ReferenceMetrics) -> AnalysisDimensionResult:
        right = metrics.hand_metrics["right"]
        left = metrics.hand_metrics["left"]
        notable_measures = sorted(set(right.chord_measure_counts) | set(left.chord_measure_counts))
        return AnalysisDimensionResult(
            dimension_id="chords",
            mark=mark_chords(right.chord_ratio, left.chord_ratio),
            raw_value=round(max(right.chord_ratio, left.chord_ratio), 3),
            raw_units="percent",
            summary=(
                f"Chord ratio RH {right.chord_ratio:.1f}% ({right.octave_chord_ratio:.1f}% octaves), "
                f"LH {left.chord_ratio:.1f}% ({left.octave_chord_ratio:.1f}% octaves)."
            ),
            source_span=_span_from_measures(notable_measures),
            notable_measures=notable_measures,
        )

    def _harmony_dimension(self, metrics: ReferenceMetrics) -> AnalysisDimensionResult:
        right = metrics.hand_metrics["right"]
        left = metrics.hand_metrics["left"]
        notable_measures = sorted(
            set(right.accidental_measure_counts) | set(left.accidental_measure_counts)
        )
        return AnalysisDimensionResult(
            dimension_id="harmony",
            mark=mark_harmony(right.accidental_ratio, left.accidental_ratio),
            raw_value=round(max(right.accidental_ratio, left.accidental_ratio), 3),
            raw_units="percent",
            summary=(
                f"Accidental ratio RH {right.accidental_ratio:.1f}%, "
                f"LH {left.accidental_ratio:.1f}%."
            ),
            source_span=_span_from_measures(notable_measures),
            notable_measures=notable_measures,
        )

    def _rhythm_dimension(
        self,
        metrics: ReferenceMetrics,
        *,
        measure_count: int,
    ) -> AnalysisDimensionResult:
        ratio = (
            len(metrics.polyrhythm_measures) / measure_count * 100.0
            if measure_count
            else None
        )
        notable_measures = list(metrics.polyrhythm_measures)
        return AnalysisDimensionResult(
            dimension_id="rhythm",
            mark=mark_rhythm(ratio),
            raw_value=round(ratio, 3) if ratio is not None else None,
            raw_units="percent",
            summary=(
                f"Polyrhythm measure ratio {ratio:.1f}% across {measure_count} measures."
                if ratio is not None
                else "Measure count is unavailable."
            ),
            source_span=_span_from_measures(notable_measures),
            diagnostics=[] if ratio is not None else ["No measures were available."],
            notable_measures=notable_measures,
        )

    def _length_dimension(self, metrics: ReferenceMetrics) -> AnalysisDimensionResult:
        mark = mark_length(metrics.page_count)
        return AnalysisDimensionResult(
            dimension_id="length",
            mark=mark,
            raw_value=metrics.page_count,
            raw_units="pages",
            summary=f"Declared page count {metrics.page_count}.",
            source_span={"measure_start": 1 if metrics.page_count else None, "measure_end": 1 if metrics.page_count else None},
            notable_measures=[],
        )

    def _tonality_dimension(self, metrics: ReferenceMetrics) -> AnalysisDimensionResult:
        fifths = abs(metrics.initial_key_fifths) if metrics.initial_key_fifths is not None else None
        mark = mark_tonality(fifths)
        return AnalysisDimensionResult(
            dimension_id="tonality",
            mark=mark,
            raw_value=fifths,
            raw_units="fifths",
            summary=(
                f"Initial key signature distance {fifths} fifths."
                if fifths is not None
                else "Key signature context is missing."
            ),
            source_span={"measure_start": 1 if fifths is not None else None, "measure_end": 1 if fifths is not None else None},
            diagnostics=[] if fifths is not None else ["No key signature value was available."],
            notable_measures=[],
        )


def _span_from_measures(measures: list[int]) -> dict[str, int | None]:
    if not measures:
        return {"measure_start": None, "measure_end": None}
    return {
        "measure_start": min(measures),
        "measure_end": max(measures),
    }


def _fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"
