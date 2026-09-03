"""Melodic and relocation-oriented descriptors.

The first pass should focus on simple direct quantities such as mean leap size,
maximum leap size, and threshold exceedance counts by hand.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import feature_record, mean
from piano_difficulty.normalize.schema import LogicalNoteIR, ScoreIR

_LEAP_THRESHOLDS = (5, 8, 12)


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract direct leap statistics from hand-specific logical note streams."""

    records: list[FeatureRecord] = []
    metrics = compute_reference_metrics(score)

    for hand in ("right", "left"):
        notes = [note for note in score.logical_notes if note.hand == hand]
        leaps = _inter_onset_leaps(notes)
        records.extend(
            [
                feature_record(
                    "leaps.mean_melodic_leap",
                    value=mean(leaps),
                    units="semitones",
                    events=notes,
                    scope="hand",
                    scope_ref=hand,
                ),
                feature_record(
                    "leaps.max_melodic_leap",
                    value=max(leaps, default=0),
                    units="semitones",
                    events=notes,
                    scope="hand",
                    scope_ref=hand,
                ),
            ]
        )

        for threshold in _LEAP_THRESHOLDS:
            records.append(
                feature_record(
                    f"leaps.count_ge_{threshold}",
                    value=sum(1 for leap in leaps if leap >= threshold),
                    units="leaps",
                    events=notes,
                    scope="hand",
                    scope_ref=hand,
                )
            )
        hand_metrics = metrics.hand_metrics[hand]
        records.extend(
            [
                feature_record(
                    "leaps.timed_difficult_displacement_ratio",
                    value=hand_metrics.timed_difficult_displacement_ratio,
                    units="percent",
                    events=list(hand_metrics.notes),
                    scope="hand",
                    scope_ref=hand,
                ),
                feature_record(
                    "leaps.max_timed_difficult_displacement",
                    value=hand_metrics.max_timed_difficult_displacement,
                    units="semitones",
                    events=list(hand_metrics.notes),
                    scope="hand",
                    scope_ref=hand,
                ),
            ]
        )
        for measure_index, count in hand_metrics.displacement_measure_counts.items():
            records.append(
                feature_record(
                    "leaps.timed_difficult_displacement_count",
                    value=count,
                    units="events",
                    events=[
                        note
                        for note in hand_metrics.notes
                        if note.measure_index == measure_index
                    ],
                    scope="measure",
                    scope_ref=str(measure_index),
                )
            )

    return records


def _inter_onset_leaps(notes: list[LogicalNoteIR]) -> list[int]:
    """Compute closest pitch-set distance between consecutive hand onsets."""

    if not notes:
        return []

    grouped: dict[Fraction, list[int]] = defaultdict(list)
    for note in notes:
        grouped[note.onset].append(note.pitch_midi)

    pitch_sets = [
        sorted(pitches) for _onset, pitches in sorted(grouped.items(), key=lambda item: item[0])
    ]
    leaps: list[int] = []
    for previous, current in zip(pitch_sets, pitch_sets[1:]):
        leaps.append(min(abs(a - b) for a in previous for b in current))
    return leaps
