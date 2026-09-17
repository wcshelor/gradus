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


def contains_mosso_text(value: str | None) -> bool:
    """Direct check for mosso-style tempo text (case-insensitive substring)."""
    if not value:
        return False
    return "mosso" in value.lower()


def has_mosso_in_region(score: ScoreIR, start, end, *, measure_start: int | None = None, measure_end: int | None = None) -> bool:
    """Return True if any mosso tempo text is active in the region.

    Checks ScoreIR directions with kind words and MeasureIR tempo_text, without
    interpreting performance tempo. Exact half-open interval for directions,
    inclusive measure indices for tempo_text.
    """
    for direction in score.directions:
        if direction.kind != "words":
            continue
        if not contains_mosso_text(direction.value):
            continue
        if start is not None and end is not None and direction.start is not None:
            if not (start <= direction.start < end):
                # For words that start exactly at region boundary, include; otherwise require overlap.
                # Also include directions in neighboring measures that are part of same window's measure range.
                if measure_start is not None and measure_end is not None and direction.measure_index is not None:
                    if not (measure_start <= direction.measure_index <= measure_end):
                        continue
                    # allow directions that are within the region's measure span even if offset slightly outside due to clipping
                else:
                    continue
        return True
    if measure_start is not None and measure_end is not None:
        for measure in score.measures:
            if measure_start <= measure.measure_index <= measure_end and contains_mosso_text(measure.tempo_text):
                return True
    else:
        for measure in score.measures:
            if start is not None and end is not None and not (measure.start < end and measure.end > start):
                continue
            if contains_mosso_text(measure.tempo_text):
                return True
    return False


def collect_mosso_texts_for_region(score: ScoreIR, start, end, *, measure_start: int | None = None, measure_end: int | None = None) -> list[str]:
    """Collect distinct mosso-related tempo texts intersecting the region."""
    texts: list[str] = []
    seen: set[str] = set()
    for direction in score.directions:
        if direction.kind == "words" and contains_mosso_text(direction.value):
            in_region = False
            if start is not None and end is not None and direction.start is not None:
                if start <= direction.start < end:
                    in_region = True
                elif measure_start is not None and measure_end is not None and direction.measure_index is not None and measure_start <= direction.measure_index <= measure_end:
                    in_region = True
            elif measure_start is not None and direction.measure_index is not None and measure_start <= direction.measure_index <= measure_end:
                in_region = True
            if in_region and direction.value not in seen:
                seen.add(direction.value)
                texts.append(direction.value)
    if measure_start is not None and measure_end is not None:
        for measure in score.measures:
            if measure_start <= measure.measure_index <= measure_end and measure.tempo_text and contains_mosso_text(measure.tempo_text) and measure.tempo_text not in seen:
                seen.add(measure.tempo_text)
                texts.append(measure.tempo_text)
    return texts


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
