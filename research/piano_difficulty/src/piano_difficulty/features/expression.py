"""Articulation and written-dynamics descriptors.

This family stays score-native and direct. It does not attempt to infer
performed velocity or phrasing beyond what is explicitly encoded in the score.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.features._common import (
    feature_record,
    rate_per_quarter,
    score_duration_quarters,
)
from piano_difficulty.normalize.schema import DirectionIR, ScoreIR, WrittenNoteIR

_ARTICULATION_IDS: tuple[str, ...] = (
    "staccato",
    "accent",
    "strong-accent",
    "tenuto",
)

_DYNAMIC_LEVEL_ORDER: dict[str, int] = {
    "pppp": -4,
    "ppp": -3,
    "pp": -2,
    "p": -1,
    "mp": 0,
    "mf": 1,
    "f": 2,
    "ff": 3,
    "fff": 4,
    "ffff": 5,
    "fp": 1,
    "sf": 2,
    "sfp": 2,
    "sfz": 3,
    "sffz": 4,
    "fz": 3,
    "rf": 2,
    "rfz": 3,
}


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract direct articulation and dynamics descriptors."""

    records: list[FeatureRecord] = []
    written_notes = list(score.written_notes)
    duration = score_duration_quarters(score)

    articulated_notes = [note for note in written_notes if note.articulations]
    records.extend(
        [
            feature_record(
                "expression.articulated_note_ratio",
                value=_note_ratio(articulated_notes, written_notes),
                units="ratio",
                events=written_notes,
            ),
            feature_record(
                "expression.articulation_density",
                value=rate_per_quarter(len(articulated_notes), duration),
                units="articulated_notes_per_quarter",
                events=articulated_notes or written_notes,
            ),
        ]
    )

    for articulation in _ARTICULATION_IDS:
        matching_notes = [note for note in written_notes if articulation in note.articulations]
        records.append(
            feature_record(
                f"expression.{articulation.replace('-', '_')}_note_ratio",
                value=_note_ratio(matching_notes, written_notes),
                units="ratio",
                events=matching_notes or written_notes,
            )
        )

    for hand in ("right", "left"):
        hand_notes = [note for note in written_notes if note.hand == hand]
        hand_articulated_notes = [note for note in hand_notes if note.articulations]
        records.append(
            feature_record(
                "expression.articulated_note_ratio",
                value=_note_ratio(hand_articulated_notes, hand_notes),
                units="ratio",
                events=hand_notes,
                scope="hand",
                scope_ref=hand,
            )
        )
        for articulation in _ARTICULATION_IDS:
            matching_notes = [note for note in hand_notes if articulation in note.articulations]
            records.append(
                feature_record(
                    f"expression.{articulation.replace('-', '_')}_note_ratio",
                    value=_note_ratio(matching_notes, hand_notes),
                    units="ratio",
                    events=matching_notes or hand_notes,
                    scope="hand",
                    scope_ref=hand,
                )
            )

    dynamic_marks = [direction for direction in score.directions if direction.kind == "dynamics"]
    wedge_starts = [
        direction
        for direction in score.directions
        if direction.kind == "wedge" and direction.value in {"crescendo", "diminuendo"}
    ]
    dynamic_levels = [level for level in (_primary_dynamic_level(direction) for direction in dynamic_marks) if level is not None]
    dynamic_ordinals = [value for value in (_DYNAMIC_LEVEL_ORDER.get(level) for level in dynamic_levels) if value is not None]

    records.extend(
        [
            feature_record(
                "expression.dynamic_marking_count",
                value=len(dynamic_marks),
                units="markings",
                events=dynamic_marks or score.directions,
            ),
            feature_record(
                "expression.dynamic_marking_rate",
                value=rate_per_quarter(len(dynamic_marks), duration),
                units="markings_per_quarter",
                events=dynamic_marks or score.directions,
            ),
            feature_record(
                "expression.dynamic_change_count",
                value=_change_count(dynamic_levels),
                units="changes",
                events=dynamic_marks or score.directions,
            ),
            feature_record(
                "expression.dynamic_range_span",
                value=(max(dynamic_ordinals) - min(dynamic_ordinals)) if dynamic_ordinals else 0,
                units="ordinal_steps",
                events=dynamic_marks or score.directions,
            ),
            feature_record(
                "expression.wedge_start_count",
                value=len(wedge_starts),
                units="wedges",
                events=wedge_starts or score.directions,
            ),
            feature_record(
                "expression.crescendo_start_count",
                value=sum(1 for direction in wedge_starts if direction.value == "crescendo"),
                units="wedges",
                events=[direction for direction in wedge_starts if direction.value == "crescendo"] or wedge_starts,
            ),
            feature_record(
                "expression.diminuendo_start_count",
                value=sum(1 for direction in wedge_starts if direction.value == "diminuendo"),
                units="wedges",
                events=[direction for direction in wedge_starts if direction.value == "diminuendo"] or wedge_starts,
            ),
            feature_record(
                "expression.staff_specific_dynamic_ratio",
                value=(
                    sum(1 for direction in [*dynamic_marks, *wedge_starts] if direction.staff is not None)
                    / len([*dynamic_marks, *wedge_starts])
                    if dynamic_marks or wedge_starts
                    else 0.0
                ),
                units="ratio",
                events=[*dynamic_marks, *wedge_starts] or score.directions,
            ),
        ]
    )

    return records


def _note_ratio(
    matching_notes: list[WrittenNoteIR],
    notes: list[WrittenNoteIR],
) -> float:
    if not notes:
        return 0.0
    return len(matching_notes) / len(notes)


def _primary_dynamic_level(direction: DirectionIR) -> str | None:
    tokens = [token.strip().lower() for token in direction.value.split(",") if token.strip()]
    for token in tokens:
        if token in _DYNAMIC_LEVEL_ORDER:
            return token
    return None


def _change_count(values: list[str]) -> int:
    if not values:
        return 0

    changes = 0
    previous = values[0]
    for value in values[1:]:
        if value != previous:
            changes += 1
            previous = value
    return changes
