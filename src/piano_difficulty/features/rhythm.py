"""Direct rhythm descriptors.

The initial scope should stay close to observable score facts:

- note density,
- attack density,
- shortest written duration,
- tuplet counts.
"""

from __future__ import annotations

from piano_difficulty.analysis.compatibility import build_php_compatibility_view
from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import (
    feature_record,
    rate_per_quarter,
    score_duration_quarters,
)
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract rhythm descriptors from normalized notes and measures."""

    metrics = compute_reference_metrics(score)
    duration = score_duration_quarters(score)
    global_onsets = {note.onset for note in score.logical_notes}
    positive_written_durations = [
        note.duration for note in score.written_notes if note.duration > 0
    ]
    compatibility_view = build_php_compatibility_view(score)
    tuplet_notes = [
        note
        for notes in compatibility_view.tuplets_by_measure.values()
        for note in notes
    ]

    records = [
        feature_record(
            "rhythm.note_density",
            value=rate_per_quarter(len(score.logical_notes), duration),
            units="notes_per_quarter",
            events=score.logical_notes,
        ),
        feature_record(
            "rhythm.attack_density",
            value=rate_per_quarter(len(global_onsets), duration),
            units="attacks_per_quarter",
            events=score.logical_notes,
        ),
        feature_record(
            "rhythm.shortest_written_duration",
            value=float(min(positive_written_durations, default=0)),
            units="quarter_notes",
            events=score.written_notes,
        ),
        feature_record(
            "rhythm.tuplet_count",
            value=len(tuplet_notes),
            units="notes",
            events=score.written_notes,
        ),
    ]
    for stat in metrics.duration_distribution:
        records.append(
            feature_record(
                "rhythm.duration_value_ratio",
                value=stat.ratio,
                units="ratio",
                events=list(stat.notes),
                scope="duration_value",
                scope_ref=stat.scope_ref,
            )
        )
    records.append(
        feature_record(
            "rhythm.significant_shortest_value",
            value=float(metrics.significant_shortest_value),
            units="whole_note_denominator",
            events=score.written_notes,
        )
    )
    records.append(
        feature_record(
            "rhythm.asymmetric_tuplet_measure_ratio",
            value=(
                len(metrics.asymmetric_tuplet_measures) / len(score.measures)
                if score.measures
                else 0.0
            ),
            units="ratio",
            events=[
                measure
                for measure in score.measures
                if measure.measure_index in metrics.asymmetric_tuplet_measures
            ],
        )
    )
    records.append(
        feature_record(
            "rhythm.polyrhythm_measure_ratio",
            value=(
                len(metrics.polyrhythm_measures) / len(score.measures)
                if score.measures
                else 0.0
            ),
            units="ratio",
            events=[
                measure
                for measure in score.measures
                if measure.measure_index in metrics.polyrhythm_measures
            ],
        )
    )
    for measure_index in metrics.polyrhythm_measures:
        records.append(
            feature_record(
                "rhythm.polyrhythm_flag",
                value=1,
                units="flag",
                events=[
                    measure
                    for measure in score.measures
                    if measure.measure_index == measure_index
                ],
                scope="measure",
                scope_ref=str(measure_index),
            )
        )
    return records
