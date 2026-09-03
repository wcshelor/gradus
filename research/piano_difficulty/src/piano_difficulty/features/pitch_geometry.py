"""Pitch geometry and hand-span descriptors.

This family should eventually report measurable properties such as:

- maximum simultaneity span by hand,
- mean simultaneity span,
- register range,
- local expansion or contraction behavior.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import feature_record, mean, notes_by_id
from piano_difficulty.normalize.schema import LogicalNoteIR, OnsetGroupIR
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract pitch-geometry descriptors from onset groups and note streams."""

    note_lookup = notes_by_id(score)
    hand_groups = [group for group in score.onset_groups if group.hand is not None]
    records: list[FeatureRecord] = []

    all_hand_spans = [_group_span(group, note_lookup) for group in hand_groups]
    records.append(
        feature_record(
            "pitch_geometry.mean_simultaneity_span",
            value=mean(all_hand_spans),
            units="semitones",
            events=_notes_for_groups(hand_groups, note_lookup),
        )
    )

    for hand in ("right", "left"):
        notes = [note for note in score.logical_notes if note.hand == hand]
        groups = [group for group in hand_groups if group.hand == hand]
        spans = [_group_span(group, note_lookup) for group in groups]
        pitches = [note.pitch_midi for note in notes]

        records.extend(
            [
                feature_record(
                    "pitch_geometry.max_simultaneity_span",
                    value=max(spans, default=0),
                    units="semitones",
                    events=_notes_for_groups(groups, note_lookup),
                    scope="hand",
                    scope_ref=hand,
                ),
                feature_record(
                    "pitch_geometry.register_range",
                    value=(max(pitches) - min(pitches)) if pitches else 0,
                    units="semitones",
                    events=notes,
                    scope="hand",
                    scope_ref=hand,
                ),
            ]
        )

    return records


def _group_span(
    group: OnsetGroupIR,
    note_lookup: dict[str, LogicalNoteIR],
) -> int:
    pitches = [
        note_lookup[note_id].pitch_midi
        for note_id in group.note_ids
        if note_id in note_lookup
    ]
    if len(pitches) < 2:
        return 0
    return max(pitches) - min(pitches)


def _notes_for_groups(
    groups: list[OnsetGroupIR],
    note_lookup: dict[str, LogicalNoteIR],
) -> list[LogicalNoteIR]:
    note_ids = {note_id for group in groups for note_id in group.note_ids}
    return [note for note_id, note in note_lookup.items() if note_id in note_ids]
