from __future__ import annotations

import argparse
import copy
import csv
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable
from xml.etree import ElementTree

from piano_difficulty.analysis.compatibility import build_php_compatibility_view
from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.comparison.scoreanalyzer_parity import (
    CANONICAL_METRICS,
    _default_pieces_root,
    _resolve_shim_path,
    compare_values,
    run_og_php_metrics,
    run_replica_metrics,
)
from piano_difficulty.difficulty_analysis.scoreanalyzer_reference import (
    mark_chords,
    mark_displacement,
    mark_harmony,
    mark_length,
    mark_rhythm,
    mark_speed,
    mark_tonality,
)
from piano_difficulty.io.musicxml import MusicXMLDocument, load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir
from piano_difficulty.normalize.schema import RestEventIR, ScoreIR, WrittenNoteIR

_PIANO_NAME_TOKENS = ("piano", "pno", "pf", "klavier")
_DEFAULT_PIECE_RELPATH = "AllaTurca_Mozart/Alla_Turca.xml"
_DEFAULT_BATTERY_ARTIFACTS_ROOT = Path("tests/artifacts/normalization_battery")
_EPSILON = 1e-9


@dataclass(slots=True)
class NormalizationVariant:
    variant_id: str
    description: str
    apply: Callable[["_BatteryContext", dict[str, Any]], None]


@dataclass(slots=True)
class VariantResult:
    variant_id: str
    description: str
    metrics: dict[str, Any]
    metric_comparison: tuple[dict[str, Any], ...]
    mismatch_count: int
    mismatched_metrics: tuple[str, ...]
    fixed_metrics: tuple[str, ...]
    regressed_metrics: tuple[str, ...]
    net_gain: int


@dataclass(slots=True)
class _BatteryContext:
    piece_relpath: str
    piece_path: Path
    document: MusicXMLDocument
    score: ScoreIR
    baseline_metrics: dict[str, Any]


@dataclass(slots=True)
class _StaffDisplacementMetrics:
    ratio: float
    max_semitones: int
    max_measure_index: int


DEFAULT_VARIANT_IDS: tuple[str, ...] = (
    "baseline_current",
    "norm_base_duration_raw_units",
    "norm_hand_counts_by_voice",
    "norm_chord_detection_sequential",
    "norm_previous_note_xml_walk",
    "norm_displacement_gap_og_threshold",
    "norm_chord_context_no_inheritance",
    "quirk_max_interval_measure_index",
    "combined_og_compat_core",
)


def build_default_variants() -> tuple[NormalizationVariant, ...]:
    return (
        NormalizationVariant(
            variant_id="baseline_current",
            description="Current replica metric behavior with no overrides.",
            apply=lambda _ctx, _metrics: None,
        ),
        NormalizationVariant(
            variant_id="norm_base_duration_raw_units",
            description="Use raw MusicXML duration units for baseDuration.",
            apply=_apply_norm_base_duration_raw_units,
        ),
        NormalizationVariant(
            variant_id="norm_hand_counts_by_voice",
            description="Use voice-based hand counts and harmony denominators.",
            apply=_apply_norm_hand_counts_by_voice,
        ),
        NormalizationVariant(
            variant_id="norm_chord_detection_sequential",
            description="Use OG-style sequential chord chain detection.",
            apply=_apply_norm_chord_detection_sequential,
        ),
        NormalizationVariant(
            variant_id="norm_previous_note_xml_walk",
            description="Use OG-style previous-note walk for displacement context.",
            apply=_apply_norm_previous_note_xml_walk,
        ),
        NormalizationVariant(
            variant_id="norm_displacement_gap_og_threshold",
            description="Use OG-style displacement gap threshold scaling.",
            apply=_apply_norm_displacement_gap_og_threshold,
        ),
        NormalizationVariant(
            variant_id="norm_chord_context_no_inheritance",
            description="Disable inferred staff/voice inheritance on chord continuations.",
            apply=_apply_norm_chord_context_no_inheritance,
        ),
        NormalizationVariant(
            variant_id="quirk_max_interval_measure_index",
            description="Apply OG payload quirk: maxInterval fields carry measure index.",
            apply=_apply_quirk_max_interval_measure_index,
        ),
        NormalizationVariant(
            variant_id="combined_og_compat_core",
            description="Combined OG-compat core overrides (excluding baseline).",
            apply=_apply_combined_og_compat_core,
        ),
    )


def _default_out_dir(piece_relpath: str) -> Path:
    slug = _safe_slug(piece_relpath)
    return _DEFAULT_BATTERY_ARTIFACTS_ROOT / slug


def _safe_slug(text: str) -> str:
    return (
        text.replace("\\", "__")
        .replace("/", "__")
        .replace(".", "_")
        .replace(" ", "_")
    )


def _build_metric_comparison(
    og_metrics: dict[str, Any],
    replica_metrics: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for metric in CANONICAL_METRICS:
        og_value = og_metrics.get(metric)
        replica_value = replica_metrics.get(metric)
        equal, delta = compare_values(metric, og_value, replica_value)
        rows.append(
            {
                "metric": metric,
                "og_value": og_value,
                "replica_value": replica_value,
                "delta": delta,
                "equal": equal,
            }
        )
    return tuple(rows)


def _mismatched_metrics(metric_comparison: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    return tuple(
        row["metric"]
        for row in metric_comparison
        if not row["equal"]
    )


def _split_fixed_and_regressed(
    baseline_mismatch_set: set[str],
    current_mismatch_set: set[str],
) -> tuple[tuple[str, ...], tuple[str, ...], int]:
    fixed = tuple(sorted(baseline_mismatch_set - current_mismatch_set))
    regressed = tuple(sorted(current_mismatch_set - baseline_mismatch_set))
    net_gain = len(fixed) - len(regressed)
    return fixed, regressed, net_gain


def _rank_results(results: list[VariantResult]) -> list[VariantResult]:
    return sorted(
        results,
        key=lambda row: (-row.net_gain, row.mismatch_count, row.variant_id),
    )


def _write_variant_metric_matrix_csv(path: Path, results: list[VariantResult]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "variant_id",
                "metric",
                "og_value",
                "replica_value",
                "delta",
                "equal",
            ],
        )
        writer.writeheader()
        for result in results:
            for row in result.metric_comparison:
                writer.writerow(
                    {
                        "variant_id": result.variant_id,
                        "metric": row["metric"],
                        "og_value": row["og_value"],
                        "replica_value": row["replica_value"],
                        "delta": row["delta"],
                        "equal": row["equal"],
                    }
                )


def _write_variant_ranking_csv(path: Path, ranking: list[VariantResult]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "variant_id",
                "description",
                "mismatch_count",
                "net_gain",
                "fixed_metrics",
                "regressed_metrics",
                "mismatched_metrics",
            ],
        )
        writer.writeheader()
        for row in ranking:
            writer.writerow(
                {
                    "variant_id": row.variant_id,
                    "description": row.description,
                    "mismatch_count": row.mismatch_count,
                    "net_gain": row.net_gain,
                    "fixed_metrics": ";".join(row.fixed_metrics),
                    "regressed_metrics": ";".join(row.regressed_metrics),
                    "mismatched_metrics": ";".join(row.mismatched_metrics),
                }
            )


def _write_battery_summary_json(
    path: Path,
    *,
    piece_relpath: str,
    piece_path: Path,
    og_metrics: dict[str, Any],
    selected_variant_ids: tuple[str, ...],
    results: list[VariantResult],
    ranking: list[VariantResult],
) -> None:
    baseline = next(result for result in results if result.variant_id == "baseline_current")
    payload = {
        "piece_relpath": piece_relpath,
        "piece_path": str(piece_path),
        "selected_variants": list(selected_variant_ids),
        "baseline_mismatch_count": baseline.mismatch_count,
        "baseline_mismatched_metrics": list(baseline.mismatched_metrics),
        "og_metrics": og_metrics,
        "variant_results": [
            {
                "variant_id": result.variant_id,
                "description": result.description,
                "mismatch_count": result.mismatch_count,
                "mismatched_metrics": list(result.mismatched_metrics),
                "fixed_metrics": list(result.fixed_metrics),
                "regressed_metrics": list(result.regressed_metrics),
                "net_gain": result.net_gain,
                "metrics": result.metrics,
            }
            for result in results
        ],
        "ranking": [
            {
                "variant_id": result.variant_id,
                "description": result.description,
                "mismatch_count": result.mismatch_count,
                "mismatched_metrics": list(result.mismatched_metrics),
                "fixed_metrics": list(result.fixed_metrics),
                "regressed_metrics": list(result.regressed_metrics),
                "net_gain": result.net_gain,
            }
            for result in ranking
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _list_variant_ids(variants: tuple[NormalizationVariant, ...]) -> tuple[str, ...]:
    return tuple(variant.variant_id for variant in variants)


def _variant_map(variants: tuple[NormalizationVariant, ...]) -> dict[str, NormalizationVariant]:
    return {variant.variant_id: variant for variant in variants}


def _validate_selected_variants(
    selected_ids: tuple[str, ...],
    variant_ids: tuple[str, ...],
) -> tuple[bool, str]:
    if not selected_ids:
        return False, "No variants were selected."
    missing = [variant_id for variant_id in selected_ids if variant_id not in variant_ids]
    if missing:
        return False, f"Unknown variant id(s): {', '.join(missing)}."
    if "baseline_current" not in selected_ids:
        return False, "Selected variants must include 'baseline_current'."
    return True, ""


def _compute_replica_metrics_from_score(score: ScoreIR) -> dict[str, Any]:
    metrics = compute_reference_metrics(score)
    right = metrics.hand_metrics["right"]
    left = metrics.hand_metrics["left"]

    quickest_value = float(metrics.significant_shortest_value)
    speed_value = (
        metrics.initial_tempo_bpm * quickest_value
        if metrics.initial_tempo_bpm is not None
        else None
    )
    rhythm_ratio = (
        len(metrics.polyrhythm_measures) / len(score.measures) * 100.0
        if score.measures
        else None
    )

    merged: dict[str, Any] = {
        "fifths": metrics.initial_key_fifths,
        "mode": score.measures[0].key_mode if score.measures and score.measures[0].key_mode else None,
        "nbmeasures": len(score.measures),
        "quantise": _quantise_value(score),
        "baseDuration": _base_duration_value(score),
        "tempo": metrics.initial_tempo_bpm,
        "beats": score.measures[0].time_beats if score.measures else None,
        "beatType": score.measures[0].time_beat_type if score.measures else None,
        "quickestValue": quickest_value,
        "maxIntervalRH": right.max_timed_difficult_displacement,
        "maxIntervalLH": left.max_timed_difficult_displacement,
        "octavesRatioRH": right.octave_chord_ratio,
        "octavesRatioLH": left.octave_chord_ratio,
        "noteCounterRH": right.note_count,
        "noteCounterLH": left.note_count,
        "nbPositionsRH": right.position_count,
        "nbPositionsLH": left.position_count,
        "speed": speed_value,
        "displacementsRH": right.timed_difficult_displacement_ratio,
        "chordsRH": right.chord_ratio,
        "harmonyRH": right.accidental_ratio,
        "displacementsLH": left.timed_difficult_displacement_ratio,
        "chordsLH": left.chord_ratio,
        "harmonyLH": left.accidental_ratio,
        "rhythm": rhythm_ratio,
        "length": metrics.page_count,
    }
    _recompute_derived_difficulty_metrics(merged)
    return {metric: merged.get(metric) for metric in CANONICAL_METRICS}


def _quantise_value(score: ScoreIR) -> float | None:
    values = [_note_value(note, include_tuplet=False) for note in score.written_notes]
    filtered = [value for value in values if value is not None]
    return max(filtered) if filtered else None


def _base_duration_value(score: ScoreIR) -> float | None:
    durations = [
        float(note.duration)
        for note in score.written_notes
        if not note.tuplet_actual and note.duration > 0
    ]
    return min(durations) if durations else None


def _note_value(note: WrittenNoteIR, *, include_tuplet: bool) -> float | None:
    mapping = {
        "whole": 1.0,
        "half": 2.0,
        "quarter": 4.0,
        "eighth": 8.0,
        "16th": 16.0,
        "32nd": 32.0,
        "64th": 64.0,
        "128th": 128.0,
        "256th": 256.0,
    }
    base = mapping.get(note.duration_type)
    if base is None:
        return None
    if include_tuplet and note.tuplet_actual and note.tuplet_normal:
        return base * (note.tuplet_actual / note.tuplet_normal)
    return base


def _recompute_derived_difficulty_metrics(metrics: dict[str, Any]) -> None:
    speed_value = _coerce_float(metrics.get("speed"))
    speed_ratio = (speed_value * 100.0 / 2816.0) if speed_value is not None else None
    displacements_rh = _coerce_float(metrics.get("displacementsRH"))
    displacements_lh = _coerce_float(metrics.get("displacementsLH"))
    chords_rh = _coerce_float(metrics.get("chordsRH"))
    chords_lh = _coerce_float(metrics.get("chordsLH"))
    harmony_rh = _coerce_float(metrics.get("harmonyRH"))
    harmony_lh = _coerce_float(metrics.get("harmonyLH"))
    rhythm = _coerce_float(metrics.get("rhythm"))
    length = _coerce_int(metrics.get("length"))
    fifths = _coerce_int(metrics.get("fifths"))
    tonality_source = abs(fifths) if fifths is not None else None

    metrics["speedDifficulty"] = mark_speed(speed_ratio)
    metrics["displacementsDifficulty"] = mark_displacement(displacements_rh, displacements_lh)
    metrics["chordsDifficulty"] = mark_chords(chords_rh, chords_lh)
    metrics["harmonyDifficulty"] = mark_harmony(harmony_rh, harmony_lh)
    metrics["rhythmDifficulty"] = mark_rhythm(rhythm)
    metrics["lengthDifficulty"] = mark_length(length)
    metrics["tonalityDifficulty"] = mark_tonality(tonality_source)

    marks = [
        metrics["speedDifficulty"],
        metrics["displacementsDifficulty"],
        metrics["chordsDifficulty"],
        metrics["harmonyDifficulty"],
        metrics["rhythmDifficulty"],
        metrics["lengthDifficulty"],
        metrics["tonalityDifficulty"],
    ]
    metrics["overallDifficulty"] = (
        round(sum(marks) / len(marks), 1)
        if all(mark is not None for mark in marks)
        else None
    )


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _apply_norm_base_duration_raw_units(context: _BatteryContext, metrics: dict[str, Any]) -> None:
    metrics["baseDuration"] = _base_duration_raw_units(context.score)


def _base_duration_raw_units(score: ScoreIR) -> float | None:
    measure_divisions = {
        measure.measure_index: measure.divisions
        for measure in score.measures
        if measure.divisions and measure.divisions > 0
    }
    candidates: list[float] = []
    for note in score.written_notes:
        if note.tuplet_actual:
            continue
        if note.duration <= 0:
            continue
        if note.measure_index is None:
            continue
        divisions = measure_divisions.get(note.measure_index)
        if divisions is None:
            continue
        candidates.append(float(note.duration * divisions))
    return min(candidates) if candidates else None


def _apply_norm_hand_counts_by_voice(context: _BatteryContext, metrics: dict[str, Any]) -> None:
    written_notes = context.score.written_notes
    right_voice_count = sum(1 for note in written_notes if note.voice == "1")
    left_voice_count = sum(1 for note in written_notes if note.voice != "1")
    accidental_rh = sum(
        1
        for note in written_notes
        if note.staff == 1 and note.accidental
    )
    accidental_lh = sum(
        1
        for note in written_notes
        if note.staff == 2 and note.accidental
    )

    metrics["noteCounterRH"] = right_voice_count
    metrics["noteCounterLH"] = left_voice_count
    metrics["harmonyRH"] = (
        accidental_rh / right_voice_count * 100.0
        if right_voice_count
        else 0.0
    )
    metrics["harmonyLH"] = (
        accidental_lh / left_voice_count * 100.0
        if left_voice_count
        else 0.0
    )


def _apply_norm_chord_detection_sequential(context: _BatteryContext, metrics: dict[str, Any]) -> None:
    right = _sequential_chord_metrics(context.score, staff=1)
    left = _sequential_chord_metrics(context.score, staff=2)
    metrics["chordsRH"] = right["chord_ratio"]
    metrics["chordsLH"] = left["chord_ratio"]
    metrics["octavesRatioRH"] = right["octave_ratio"]
    metrics["octavesRatioLH"] = left["octave_ratio"]


def _sequential_chord_metrics(score: ScoreIR, *, staff: int) -> dict[str, float]:
    view = build_php_compatibility_view(score)
    notes = list(view.notes_for_staff(staff))
    if len(notes) <= 1:
        return {"chord_ratio": 0.0, "octave_ratio": 0.0}

    position_count = sum(
        1
        for index in range(1, len(notes))
        if not notes[index].is_chord_continuation
    )
    chord_count = 0
    octave_count = 0
    chord_base: int | None = None

    for index in range(1, len(notes)):
        note = notes[index]
        next_is_chord = (
            index < len(notes) - 1
            and notes[index + 1].is_chord_continuation
        )
        in_chord_chain = note.is_chord_continuation or (
            (not note.is_chord_continuation) and next_is_chord
        )
        if not in_chord_chain:
            continue
        if not note.is_chord_continuation:
            chord_count += 1
            chord_base = note.pitch_midi
        if chord_base is not None and note.pitch_midi == chord_base + 12:
            octave_count += 1

    chord_ratio = chord_count / position_count * 100.0 if position_count else 0.0
    octave_ratio = octave_count / chord_count * 100.0 if chord_count else 0.0
    return {
        "chord_ratio": chord_ratio,
        "octave_ratio": octave_ratio,
    }


def _apply_norm_previous_note_xml_walk(context: _BatteryContext, metrics: dict[str, Any]) -> None:
    displacement = _compute_displacement_metrics_with_xml_walk(
        context.score,
        quickest_value=_coerce_float(metrics.get("quickestValue")),
        use_og_gap_threshold=False,
    )
    metrics["displacementsRH"] = displacement["right"].ratio
    metrics["displacementsLH"] = displacement["left"].ratio
    metrics["maxIntervalRH"] = displacement["right"].max_semitones
    metrics["maxIntervalLH"] = displacement["left"].max_semitones


def _apply_norm_displacement_gap_og_threshold(context: _BatteryContext, metrics: dict[str, Any]) -> None:
    displacement = _compute_displacement_metrics_with_xml_walk(
        context.score,
        quickest_value=_coerce_float(metrics.get("quickestValue")),
        use_og_gap_threshold=True,
    )
    metrics["displacementsRH"] = displacement["right"].ratio
    metrics["displacementsLH"] = displacement["left"].ratio
    metrics["maxIntervalRH"] = displacement["right"].max_semitones
    metrics["maxIntervalLH"] = displacement["left"].max_semitones


def _apply_norm_chord_context_no_inheritance(
    context: _BatteryContext,
    metrics: dict[str, Any],
) -> None:
    mutated_score = _score_without_chord_context_inheritance(context.score, context.document)
    metrics.update(_compute_replica_metrics_from_score(mutated_score))


def _apply_quirk_max_interval_measure_index(context: _BatteryContext, metrics: dict[str, Any]) -> None:
    right_measure = _max_interval_measure_index_from_reference(context.score, hand="right")
    left_measure = _max_interval_measure_index_from_reference(context.score, hand="left")
    metrics["maxIntervalRH"] = right_measure
    metrics["maxIntervalLH"] = left_measure


def _apply_combined_og_compat_core(context: _BatteryContext, metrics: dict[str, Any]) -> None:
    mutated_score = _score_without_chord_context_inheritance(context.score, context.document)
    metrics.update(_compute_replica_metrics_from_score(mutated_score))
    metrics["baseDuration"] = _base_duration_raw_units(mutated_score)

    mutated_context = _BatteryContext(
        piece_relpath=context.piece_relpath,
        piece_path=context.piece_path,
        document=context.document,
        score=mutated_score,
        baseline_metrics=context.baseline_metrics,
    )

    _apply_norm_hand_counts_by_voice(mutated_context, metrics)
    _apply_norm_chord_detection_sequential(mutated_context, metrics)
    displacement = _compute_displacement_metrics_with_xml_walk(
        mutated_score,
        quickest_value=_coerce_float(metrics.get("quickestValue")),
        use_og_gap_threshold=True,
    )
    metrics["displacementsRH"] = displacement["right"].ratio
    metrics["displacementsLH"] = displacement["left"].ratio
    metrics["maxIntervalRH"] = displacement["right"].max_measure_index
    metrics["maxIntervalLH"] = displacement["left"].max_measure_index


def _score_without_chord_context_inheritance(
    score: ScoreIR,
    document: MusicXMLDocument,
) -> ScoreIR:
    mutated = copy.deepcopy(score)
    context_map = _build_note_explicit_context_map(document)
    for note in mutated.written_notes:
        context = context_map.get(note.note_id)
        if context is None:
            continue
        is_chord, has_staff, has_voice = context
        if not is_chord:
            continue
        if not has_staff:
            note.staff = None
        if not has_voice:
            note.voice = None
    return mutated


def _build_note_explicit_context_map(
    document: MusicXMLDocument,
) -> dict[str, tuple[bool, bool, bool]]:
    root = document.root
    if _local_name(root.tag) != "score-partwise":
        return {}

    parts = _children(root, "part")
    if not parts:
        return {}

    part_names = _part_names(root)
    selected_part = _select_part(parts, part_names)
    if selected_part is None:
        return {}

    result: dict[str, tuple[bool, bool, bool]] = {}
    xml_order = 0
    for measure in _children(selected_part, "measure"):
        for child in list(measure):
            if _local_name(child.tag) != "note":
                continue
            xml_order += 1
            if _child(child, "rest") is not None:
                continue
            note_id = child.get("id") or f"n{xml_order}"
            is_chord = _child(child, "chord") is not None
            has_staff = _text(_child(child, "staff")) is not None
            has_voice = _text(_child(child, "voice")) is not None
            result[note_id] = (is_chord, has_staff, has_voice)
    return result


def _select_part(
    parts: list[ElementTree.Element],
    part_names: dict[str, str],
) -> ElementTree.Element | None:
    if len(parts) == 1:
        return parts[0]
    for part in parts:
        part_id = part.get("id") or ""
        name = part_names.get(part_id, "").lower()
        if any(token in name for token in _PIANO_NAME_TOKENS):
            return part
    return parts[0] if parts else None


def _part_names(root: ElementTree.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    part_list = _child(root, "part-list")
    if part_list is None:
        return result
    for score_part in _children(part_list, "score-part"):
        part_id = score_part.get("id")
        if part_id:
            result[part_id] = _text(_child(score_part, "part-name")) or ""
    return result


def _compute_displacement_metrics_with_xml_walk(
    score: ScoreIR,
    *,
    quickest_value: float | None,
    use_og_gap_threshold: bool,
) -> dict[str, _StaffDisplacementMetrics]:
    base_raw_units = _base_duration_raw_units(score)
    right = _compute_staff_displacements_with_xml_walk(
        score,
        staff=1,
        quickest_value=quickest_value,
        base_raw_units=base_raw_units,
        use_og_gap_threshold=use_og_gap_threshold,
    )
    left = _compute_staff_displacements_with_xml_walk(
        score,
        staff=2,
        quickest_value=quickest_value,
        base_raw_units=base_raw_units,
        use_og_gap_threshold=use_og_gap_threshold,
    )
    return {
        "right": right,
        "left": left,
    }


def _compute_staff_displacements_with_xml_walk(
    score: ScoreIR,
    *,
    staff: int,
    quickest_value: float | None,
    base_raw_units: float | None,
    use_og_gap_threshold: bool,
) -> _StaffDisplacementMetrics:
    view = build_php_compatibility_view(score)
    notes = list(view.notes_for_staff(staff))
    events = list(view.events_for_staff(staff))
    if len(notes) <= 1:
        return _StaffDisplacementMetrics(ratio=0.0, max_semitones=0, max_measure_index=0)

    measure_divisions = {
        measure.measure_index: measure.divisions or 1
        for measure in score.measures
    }
    beat_types = {
        measure.measure_index: measure.time_beat_type
        for measure in score.measures
    }
    event_positions = {
        id(event): index
        for index, event in enumerate(events)
    }

    difficult_count = 0
    position_count = 0
    max_semitones = 0
    max_measure_index = 0

    for note in notes[1:]:
        if note.is_chord_continuation:
            continue
        position_count += 1
        event_pos = event_positions.get(id(note))
        if event_pos is None or event_pos <= 0:
            continue

        previous_event = events[event_pos - 1]
        gap_quarter = previous_event.duration
        gap_units = previous_event.duration * measure_divisions.get(previous_event.measure_index or 0, 1)
        previous_pos = event_pos - 1

        while isinstance(previous_event, RestEventIR):
            previous_pos -= 1
            if previous_pos < 0:
                break
            previous_event = events[previous_pos]
            gap_quarter += previous_event.duration
            gap_units += previous_event.duration * measure_divisions.get(previous_event.measure_index or 0, 1)

        if previous_pos < 0:
            continue

        while isinstance(previous_event, WrittenNoteIR) and previous_event.is_chord_continuation:
            previous_pos -= 1
            if previous_pos < 0:
                break
            previous_event = events[previous_pos]

        if previous_pos < 0 or not isinstance(previous_event, WrittenNoteIR):
            continue

        semitones = abs(note.pitch_midi - previous_event.pitch_midi)
        if semitones <= 12:
            continue

        previous_beat_type = beat_types.get(previous_event.measure_index or 0)
        current_beat_type = beat_types.get(note.measure_index or 0)
        effective_beat_type = current_beat_type or previous_beat_type or 4

        if use_og_gap_threshold:
            if quickest_value is None or base_raw_units is None:
                is_short_gap = False
            else:
                threshold_units = base_raw_units * quickest_value / effective_beat_type * 2.0
                is_short_gap = float(gap_units) <= threshold_units + _EPSILON
        else:
            is_short_gap = gap_quarter <= Fraction(8, effective_beat_type)

        if not is_short_gap:
            continue

        difficult_count += 1
        if semitones > max_semitones:
            max_semitones = semitones
            max_measure_index = note.measure_index or previous_event.measure_index or 0

    ratio = difficult_count / position_count * 100.0 if position_count else 0.0
    return _StaffDisplacementMetrics(
        ratio=ratio,
        max_semitones=max_semitones,
        max_measure_index=max_measure_index,
    )


def _max_interval_measure_index_from_reference(score: ScoreIR, *, hand: str) -> int:
    metrics = compute_reference_metrics(score)
    events = list(metrics.hand_metrics[hand].displacement_events)
    if not events:
        return 0
    max_event = events[0]
    for event in events[1:]:
        if event.semitones > max_event.semitones:
            max_event = event
    return max_event.measure_index


def _children(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    return [child for child in list(element) if _local_name(child.tag) == name]


def _child(element: ElementTree.Element | None, name: str) -> ElementTree.Element | None:
    if element is None:
        return None
    for child in list(element):
        if _local_name(child.tag) == name:
            return child
    return None


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = element.text.strip()
    return text or None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def run_normalization_battery(
    *,
    piece_relpath: str = _DEFAULT_PIECE_RELPATH,
    php_bin: Path,
    pieces_root: Path = _default_pieces_root(),
    out_dir: Path | None = None,
    variants: tuple[str, ...] | None = None,
    max_suspects_per_metric: int = 20,
    og_runner: Callable[[Path, Path, str], dict[str, Any]] = run_og_php_metrics,
) -> int:
    if max_suspects_per_metric <= 0:
        print("Invalid argument: --max-suspects-per-metric must be > 0.")
        return 2

    piece_path = pieces_root / piece_relpath
    if not piece_path.exists():
        print(f"Piece path not found: {piece_path}")
        return 2
    if not piece_path.is_file():
        print(f"Piece path is not a file: {piece_path}")
        return 2

    variant_registry = build_default_variants()
    variant_ids = _list_variant_ids(variant_registry)
    selected_variant_ids = variants or variant_ids
    valid, message = _validate_selected_variants(selected_variant_ids, variant_ids)
    if not valid:
        print(message)
        return 2
    selected_variant_map = _variant_map(variant_registry)

    resolved_out_dir = out_dir or _default_out_dir(piece_relpath)
    resolved_out_dir.mkdir(parents=True, exist_ok=True)
    battery_summary_path = resolved_out_dir / "battery_summary.json"
    metric_matrix_csv_path = resolved_out_dir / "variant_metric_matrix.csv"
    ranking_csv_path = resolved_out_dir / "variant_ranking.csv"

    try:
        piece_dir = str(Path(piece_relpath).parent).replace("\\", "/")
        shim_path = _resolve_shim_path(pieces_root)
        og_metrics = og_runner(php_bin, shim_path, piece_dir)
        baseline_metrics = run_replica_metrics(piece_path)
        document = load_musicxml_document(piece_path)
        score = build_score_ir(document)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to run normalization battery: {exc}")
        return 2

    context = _BatteryContext(
        piece_relpath=piece_relpath,
        piece_path=piece_path,
        document=document,
        score=score,
        baseline_metrics=baseline_metrics,
    )

    results: list[VariantResult] = []
    baseline_mismatch_set: set[str] | None = None

    for variant_id in selected_variant_ids:
        variant = selected_variant_map[variant_id]
        variant_metrics = dict(baseline_metrics)
        variant.apply(context, variant_metrics)
        _recompute_derived_difficulty_metrics(variant_metrics)
        normalized_metrics = {
            metric: variant_metrics.get(metric)
            for metric in CANONICAL_METRICS
        }
        metric_comparison = _build_metric_comparison(og_metrics, normalized_metrics)
        mismatched = _mismatched_metrics(metric_comparison)
        mismatch_set = set(mismatched)

        if variant_id == "baseline_current":
            baseline_mismatch_set = mismatch_set
            fixed, regressed, net_gain = ((), (), 0)
        else:
            current_baseline = baseline_mismatch_set or set()
            fixed, regressed, net_gain = _split_fixed_and_regressed(current_baseline, mismatch_set)

        results.append(
            VariantResult(
                variant_id=variant.variant_id,
                description=variant.description,
                metrics=normalized_metrics,
                metric_comparison=metric_comparison,
                mismatch_count=len(mismatched),
                mismatched_metrics=mismatched,
                fixed_metrics=fixed,
                regressed_metrics=regressed,
                net_gain=net_gain,
            )
        )

    ranking = _rank_results(results)
    _write_battery_summary_json(
        battery_summary_path,
        piece_relpath=piece_relpath,
        piece_path=piece_path,
        og_metrics=og_metrics,
        selected_variant_ids=selected_variant_ids,
        results=results,
        ranking=ranking,
    )
    _write_variant_metric_matrix_csv(metric_matrix_csv_path, results)
    _write_variant_ranking_csv(ranking_csv_path, ranking)

    baseline_result = next(result for result in results if result.variant_id == "baseline_current")
    print(f"Piece: {piece_relpath}")
    print(f"Baseline mismatched metrics: {baseline_result.mismatch_count}")
    print(f"Selected variants: {', '.join(selected_variant_ids)}")
    print(f"Output summary JSON: {battery_summary_path}")
    print(f"Output metric matrix CSV: {metric_matrix_csv_path}")
    print(f"Output ranking CSV: {ranking_csv_path}")
    return 1 if baseline_result.mismatch_count else 0


def build_parser() -> argparse.ArgumentParser:
    variant_registry = build_default_variants()
    variant_ids = _list_variant_ids(variant_registry)

    parser = argparse.ArgumentParser(
        prog="run_scoreanalyzer_normalization_battery",
        description="Run normalization-sensitivity parity battery for one piece.",
    )
    parser.add_argument(
        "--piece-relpath",
        default=_DEFAULT_PIECE_RELPATH,
        help="Piece path relative to pieces root.",
    )
    parser.add_argument(
        "--php-bin",
        type=Path,
        default=None,
        help="Path to php executable.",
    )
    parser.add_argument(
        "--pieces-root",
        type=Path,
        default=_default_pieces_root(),
        help="Root folder containing score piece directories.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Optional output folder. Defaults to scoreanalyzer normalization battery path.",
    )
    parser.add_argument(
        "--variant",
        dest="variants",
        action="append",
        choices=list(variant_ids),
        default=None,
        help="Variant id to run. Repeatable. Defaults to all variants.",
    )
    parser.add_argument(
        "--list-variants",
        action="store_true",
        help="Print available variant ids and exit.",
    )
    parser.add_argument(
        "--max-suspects-per-metric",
        type=int,
        default=20,
        help="Reserved compatibility knob (must be > 0).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    variants = build_default_variants()
    if args.list_variants:
        for variant in variants:
            print(f"{variant.variant_id}: {variant.description}")
        return 0
    if args.php_bin is None:
        parser.error("the following arguments are required: --php-bin")

    selected_variants = tuple(dict.fromkeys(args.variants)) if args.variants else None
    return run_normalization_battery(
        piece_relpath=args.piece_relpath,
        php_bin=args.php_bin,
        pieces_root=args.pieces_root,
        out_dir=args.out_dir,
        variants=selected_variants,
        max_suspects_per_metric=args.max_suspects_per_metric,
    )
