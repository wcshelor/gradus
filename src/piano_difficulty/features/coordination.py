"""Inter-hand coordination descriptors.

The scaffold reserves this family for direct coordination facts that do not yet
depend on pedagogy-sensitive weighting:

- aligned versus asynchronous hand attacks,
- simple subdivision mismatch counts,
- overlap patterns that reflect independent activity.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import feature_record, measures_by_index
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract direct inter-hand coordination descriptors."""

    right_notes = [note for note in score.logical_notes if note.hand == "right"]
    left_notes = [note for note in score.logical_notes if note.hand == "left"]
    hand_notes = [*right_notes, *left_notes]

    right_onsets = {note.onset for note in right_notes}
    left_onsets = {note.onset for note in left_notes}
    union_onsets = right_onsets | left_onsets
    aligned_onsets = right_onsets & left_onsets
    asynchronous_onsets = union_onsets - aligned_onsets
    aligned_ratio = len(aligned_onsets) / len(union_onsets) if union_onsets else 0.0

    mismatch_ratio = _subdivision_mismatch_ratio(score)

    return [
        feature_record(
            "coordination.aligned_hand_onset_count",
            value=len(aligned_onsets),
            units="onsets",
            events=hand_notes,
        ),
        feature_record(
            "coordination.asynchronous_hand_onset_count",
            value=len(asynchronous_onsets),
            units="onsets",
            events=hand_notes,
        ),
        feature_record(
            "coordination.aligned_hand_onset_ratio",
            value=aligned_ratio,
            units="ratio",
            events=hand_notes,
        ),
        feature_record(
            "coordination.subdivision_mismatch_proxy",
            value=mismatch_ratio,
            units="ratio",
            events=hand_notes,
        ),
    ]


def _subdivision_mismatch_ratio(score: ScoreIR) -> float:
    measures = measures_by_index(score)
    offsets_by_measure: dict[int, dict[str, set[Fraction]]] = defaultdict(
        lambda: {"right": set(), "left": set()}
    )

    for note in score.logical_notes:
        if note.hand not in {"right", "left"} or note.measure_index is None:
            continue

        measure = measures.get(note.measure_index)
        offset = note.onset - measure.start if measure is not None else note.onset
        offsets_by_measure[note.measure_index][note.hand].add(offset)

    mismatch_count = 0
    union_count = 0
    for hand_offsets in offsets_by_measure.values():
        right_offsets = hand_offsets["right"]
        left_offsets = hand_offsets["left"]
        if not right_offsets or not left_offsets:
            continue

        union_offsets = right_offsets | left_offsets
        mismatch_count += len(union_offsets - (right_offsets & left_offsets))
        union_count += len(union_offsets)

    return mismatch_count / union_count if union_count else 0.0
