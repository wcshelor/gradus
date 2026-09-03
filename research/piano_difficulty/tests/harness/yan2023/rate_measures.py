"""Shared rate formula banks for Yan 2023 score-native feature experiments."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from fractions import Fraction
from typing import Literal

from piano_difficulty.normalize.schema import LogicalNoteIR, WrittenNoteIR

_BLACK_KEY_CLASSES = {1, 3, 6, 8, 10}

BlackKeyRateFormulaName = Literal[
    "written_note_ratio",
    "logical_note_ratio",
    "onset_ratio",
    "duration_weighted_ratio",
]
PolyphonyRateFormulaName = Literal[
    "polyphonic_onset_ratio",
    "polyphonic_note_ratio",
    "polyphonic_extra_note_ratio",
    "polyphonic_duration_ratio",
]
StaccatoRateFormulaName = Literal[
    "written_note_ratio",
    "logical_note_ratio",
    "onset_ratio",
    "duration_weighted_ratio",
]
DottedNoteRateFormulaName = Literal[
    "heuristic_any_note_ratio",
    "heuristic_1_5_note_ratio",
    "heuristic_1_75_note_ratio",
    "heuristic_any_duration_ratio",
]

DEFAULT_BLACK_KEY_RATE_FORMULA: BlackKeyRateFormulaName = "written_note_ratio"
DEFAULT_POLYPHONY_RATE_FORMULA: PolyphonyRateFormulaName = "polyphonic_onset_ratio"
DEFAULT_STACCATO_RATE_FORMULA: StaccatoRateFormulaName = "written_note_ratio"
DEFAULT_DOTTED_NOTE_RATE_FORMULA: DottedNoteRateFormulaName = "heuristic_any_note_ratio"

BLACK_KEY_RATE_FORMULA_NAMES: tuple[BlackKeyRateFormulaName, ...] = (
    "written_note_ratio",
    "logical_note_ratio",
    "onset_ratio",
    "duration_weighted_ratio",
)
POLYPHONY_RATE_FORMULA_NAMES: tuple[PolyphonyRateFormulaName, ...] = (
    "polyphonic_onset_ratio",
    "polyphonic_note_ratio",
    "polyphonic_extra_note_ratio",
    "polyphonic_duration_ratio",
)
STACCATO_RATE_FORMULA_NAMES: tuple[StaccatoRateFormulaName, ...] = (
    "written_note_ratio",
    "logical_note_ratio",
    "onset_ratio",
    "duration_weighted_ratio",
)
DOTTED_NOTE_RATE_FORMULA_NAMES: tuple[DottedNoteRateFormulaName, ...] = (
    "heuristic_any_note_ratio",
    "heuristic_1_5_note_ratio",
    "heuristic_1_75_note_ratio",
    "heuristic_any_duration_ratio",
)


def compute_black_key_rate(
    written_notes: Sequence[WrittenNoteIR],
    logical_notes: Sequence[LogicalNoteIR],
    formula: BlackKeyRateFormulaName,
) -> tuple[float, tuple[str, ...]]:
    written_notes_list = list(written_notes)
    logical_notes_list = list(logical_notes)
    if formula == "written_note_ratio":
        numerator = sum(1 for note in written_notes_list if _is_black_key(note.pitch_midi))
        denominator = len(written_notes_list)
    elif formula == "logical_note_ratio":
        numerator = sum(1 for note in logical_notes_list if _is_black_key(note.pitch_midi))
        denominator = len(logical_notes_list)
    elif formula == "onset_ratio":
        numerator = sum(
            1 for pitches in _group_pitches_by_onset(logical_notes_list).values() if any(
                _is_black_key(pitch) for pitch in pitches
            )
        )
        denominator = len(_group_pitches_by_onset(logical_notes_list))
    elif formula == "duration_weighted_ratio":
        numerator = sum(
            float(note.duration)
            for note in written_notes_list
            if _is_black_key(note.pitch_midi)
        )
        denominator = sum(float(note.duration) for note in written_notes_list)
    else:
        raise ValueError(f"Unsupported black-key rate formula {formula!r}.")
    return _ratio(numerator, denominator), (
        f"black_key_rate_formula={formula}",
        f"black_key_rate_bank={','.join(BLACK_KEY_RATE_FORMULA_NAMES)}",
    )


def compute_polyphony_rate(
    logical_notes: Sequence[LogicalNoteIR],
    formula: PolyphonyRateFormulaName,
) -> tuple[float, tuple[str, ...]]:
    logical_notes_list = list(logical_notes)
    onset_map = _group_pitches_by_onset(logical_notes_list)
    onset_count = len(onset_map)
    polyphonic_group_sizes = [len(pitches) for pitches in onset_map.values() if len(pitches) > 1]
    polyphonic_note_count = sum(polyphonic_group_sizes)
    extra_note_count = sum(size - 1 for size in polyphonic_group_sizes)
    duration_by_onset = _group_duration_by_onset(logical_notes_list)
    polyphonic_duration = sum(
        duration
        for onset, duration in duration_by_onset.items()
        if len(onset_map.get(onset, ())) > 1
    )
    total_duration = sum(duration_by_onset.values())
    if formula == "polyphonic_onset_ratio":
        numerator = len(polyphonic_group_sizes)
        denominator = onset_count
    elif formula == "polyphonic_note_ratio":
        numerator = polyphonic_note_count
        denominator = len(logical_notes_list)
    elif formula == "polyphonic_extra_note_ratio":
        numerator = extra_note_count
        denominator = len(logical_notes_list)
    elif formula == "polyphonic_duration_ratio":
        numerator = polyphonic_duration
        denominator = total_duration
    else:
        raise ValueError(f"Unsupported polyphony rate formula {formula!r}.")
    return _ratio(numerator, denominator), (
        f"polyphony_rate_formula={formula}",
        f"polyphony_rate_bank={','.join(POLYPHONY_RATE_FORMULA_NAMES)}",
    )


def compute_staccato_rate(
    written_notes: Sequence[WrittenNoteIR],
    logical_notes: Sequence[LogicalNoteIR],
    formula: StaccatoRateFormulaName,
) -> tuple[float, tuple[str, ...]]:
    written_notes_list = list(written_notes)
    logical_notes_list = list(logical_notes)
    logical_staccato_sources = _logical_notes_with_articulation(logical_notes_list, written_notes_list, "staccato")
    onset_map = _group_note_ids_by_onset(logical_notes_list)
    duration_by_note_id = {note.note_id: float(note.duration) for note in written_notes_list}
    if formula == "written_note_ratio":
        numerator = sum(1 for note in written_notes_list if "staccato" in note.articulations)
        denominator = len(written_notes_list)
    elif formula == "logical_note_ratio":
        numerator = len(logical_staccato_sources)
        denominator = len(logical_notes_list)
    elif formula == "onset_ratio":
        numerator = sum(
            1
            for onset_note_ids in onset_map.values()
            if any(note_id in logical_staccato_sources for note_id in onset_note_ids)
        )
        denominator = len(onset_map)
    elif formula == "duration_weighted_ratio":
        numerator = sum(
            duration_by_note_id[note.note_id]
            for note in written_notes_list
            if "staccato" in note.articulations
        )
        denominator = sum(duration_by_note_id.values())
    else:
        raise ValueError(f"Unsupported staccato rate formula {formula!r}.")
    return _ratio(numerator, denominator), (
        f"staccato_rate_formula={formula}",
        f"staccato_rate_bank={','.join(STACCATO_RATE_FORMULA_NAMES)}",
    )


def compute_dotted_note_rate(
    written_notes: Sequence[WrittenNoteIR],
    logical_notes: Sequence[LogicalNoteIR],
    formula: DottedNoteRateFormulaName,
) -> tuple[float, tuple[str, ...]]:
    written_notes_list = list(written_notes)
    logical_notes_list = list(logical_notes)
    dotted_written_notes_15 = _dotted_written_notes(written_notes_list, 1.5)
    dotted_written_notes_175 = _dotted_written_notes(written_notes_list, 1.75)
    dotted_written_notes = {
        note.note_id
        for note in dotted_written_notes_15
    } | {
        note.note_id
        for note in dotted_written_notes_175
    }
    onset_map = _group_note_ids_by_onset(logical_notes_list)
    duration_by_note_id = {note.note_id: float(note.duration) for note in written_notes_list}
    logical_dotted_notes = _logical_notes_with_written_source_ids(
        logical_notes_list,
        dotted_written_notes,
    )
    if formula == "heuristic_any_note_ratio":
        numerator = len(dotted_written_notes)
        denominator = len(written_notes_list)
    elif formula == "heuristic_1_5_note_ratio":
        numerator = len(dotted_written_notes_15)
        denominator = len(written_notes_list)
    elif formula == "heuristic_1_75_note_ratio":
        numerator = len(dotted_written_notes_175)
        denominator = len(written_notes_list)
    elif formula == "heuristic_any_duration_ratio":
        numerator = sum(
            duration_by_note_id[note_id]
            for note_id in dotted_written_notes
            if note_id in duration_by_note_id
        )
        denominator = sum(duration_by_note_id.values())
    else:
        raise ValueError(f"Unsupported dotted-note rate formula {formula!r}.")
    diagnostics = (
        f"dotted_note_rate_formula={formula}",
        f"dotted_note_rate_bank={','.join(DOTTED_NOTE_RATE_FORMULA_NAMES)}",
        f"dotted_note_ids={len(dotted_written_notes)}",
        f"dotted_note_onsets={sum(1 for onset_note_ids in onset_map.values() if any(note_id in logical_dotted_notes for note_id in onset_note_ids))}",
    )
    return _ratio(numerator, denominator), diagnostics


def _dotted_written_notes(
    written_notes: Sequence[WrittenNoteIR],
    ratio_target: float,
) -> list[WrittenNoteIR]:
    dotted_notes: list[WrittenNoteIR] = []
    for note in written_notes:
        if note.tuplet_actual is not None:
            continue
        base_duration = _duration_type_quarters(note.duration_type or "")
        if base_duration is None or base_duration <= 0:
            continue
        ratio = float(note.duration / base_duration)
        if abs(ratio - ratio_target) < 1e-6:
            dotted_notes.append(note)
    return dotted_notes


def _group_pitches_by_onset(notes: Sequence[LogicalNoteIR]) -> dict[Fraction, list[int]]:
    grouped: dict[Fraction, list[int]] = defaultdict(list)
    for note in notes:
        grouped[note.onset].append(note.pitch_midi)
    return grouped


def _group_duration_by_onset(notes: Sequence[LogicalNoteIR]) -> dict[Fraction, float]:
    grouped: dict[Fraction, float] = defaultdict(float)
    for note in notes:
        grouped[note.onset] += float(note.duration)
    return grouped


def _group_note_ids_by_onset(notes: Sequence[LogicalNoteIR]) -> dict[Fraction, list[str]]:
    grouped: dict[Fraction, list[str]] = defaultdict(list)
    for note in notes:
        grouped[note.onset].append(note.note_id)
    return grouped


def _logical_notes_with_articulation(
    logical_notes: Sequence[LogicalNoteIR],
    written_notes: Sequence[WrittenNoteIR],
    articulation: str,
) -> set[str]:
    written_lookup = {note.note_id: note for note in written_notes}
    logical_note_ids: set[str] = set()
    for logical_note in logical_notes:
        for source_note_id in logical_note.source_note_ids:
            source_note = written_lookup.get(source_note_id)
            if source_note is not None and articulation in source_note.articulations:
                logical_note_ids.add(logical_note.note_id)
                break
    return logical_note_ids


def _logical_notes_with_written_source_ids(
    logical_notes: Sequence[LogicalNoteIR],
    written_note_ids: set[str],
) -> set[str]:
    logical_note_ids: set[str] = set()
    for logical_note in logical_notes:
        if any(source_note_id in written_note_ids for source_note_id in logical_note.source_note_ids):
            logical_note_ids.add(logical_note.note_id)
    return logical_note_ids


def _is_black_key(pitch_midi: int) -> bool:
    return pitch_midi % 12 in _BLACK_KEY_CLASSES


def _duration_type_quarters(duration_type: str) -> Fraction | None:
    match duration_type:
        case "whole":
            return Fraction(4, 1)
        case "half":
            return Fraction(2, 1)
        case "quarter":
            return Fraction(1, 1)
        case "eighth":
            return Fraction(1, 2)
        case "16th":
            return Fraction(1, 4)
        case "32nd":
            return Fraction(1, 8)
        case "64th":
            return Fraction(1, 16)
        case "128th":
            return Fraction(1, 32)
        case "256th":
            return Fraction(1, 64)
        case _:
            return None


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)
