"""Texture and vertical-density descriptors.

This family should eventually summarize how many notes sound or attack together,
how dense vertical sonorities are, and how busy the local texture appears from
an onset-centric perspective.
"""

from __future__ import annotations

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import (
    feature_record,
    mean,
    score_duration_quarters,
)
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract direct texture statistics from onset groups."""

    metrics = compute_reference_metrics(score)
    global_groups = [group for group in score.onset_groups if group.hand is None]
    group_sizes = [len(group.note_ids) for group in global_groups]
    duration = score_duration_quarters(score)
    total_note_duration = sum((note.duration for note in score.logical_notes), start=0)
    simultaneity_ratio = (
        sum(1 for size in group_sizes if size > 1) / len(group_sizes)
        if group_sizes
        else 0.0
    )

    records = [
        feature_record(
            "texture.notes_per_onset",
            value=mean(group_sizes),
            units="notes_per_onset",
            events=score.logical_notes,
        ),
        feature_record(
            "texture.simultaneity_density",
            value=simultaneity_ratio,
            units="ratio",
            events=score.logical_notes,
        ),
        feature_record(
            "texture.vertical_density_proxy",
            value=(float(total_note_duration) / float(duration)) if duration > 0 else 0.0,
            units="average_sounding_notes",
            events=score.logical_notes,
        ),
    ]
    for hand, hand_metrics in metrics.hand_metrics.items():
        hand_notes = list(hand_metrics.notes)
        records.extend(
            [
                feature_record(
                    "texture.chord_count",
                    value=hand_metrics.chord_count,
                    units="onsets",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                ),
                feature_record(
                    "texture.chord_ratio",
                    value=hand_metrics.chord_ratio,
                    units="percent",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                ),
                feature_record(
                    "texture.octave_chord_ratio",
                    value=hand_metrics.octave_chord_ratio,
                    units="percent",
                    events=hand_notes,
                    scope="hand",
                    scope_ref=hand,
                ),
            ]
        )
        for measure_index, chord_count in hand_metrics.chord_measure_counts.items():
            records.append(
                feature_record(
                    "texture.chord_count",
                    value=chord_count,
                    units="onsets",
                    events=[
                        note
                        for note in hand_notes
                        if note.measure_index == measure_index
                    ],
                    scope="measure",
                    scope_ref=str(measure_index),
                )
            )
    return records
