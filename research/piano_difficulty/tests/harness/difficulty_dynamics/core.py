"""Core Difficulty Dynamics pipeline logic."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from piano_difficulty.analysis.grouping import group_onsets, group_onsets_by_hand
from piano_difficulty.features import extract_all
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir
from piano_difficulty.normalize.schema import ScoreIR
from piano_difficulty.temporal.transform import (
    NormalizationConfig,
    SmoothingConfig,
    normalize_series,
    smooth_series,
)
from piano_difficulty.temporal.windows import (
    BeatWindowSpec,
    MeasureWindowSpec,
    ScoreRegion,
    build_beat_regions,
    build_measure_regions,
)
from piano_difficulty.validation.sanity_checks import run_sanity_checks

from .models import (
    CompositeConfig,
    DifficultyDynamicsConfig,
    FeatureContribution,
    DifficultyHotspot,
    DifficultyPassage,
    DifficultyProfile,
    PeakDetectionConfig,
    TemporalFeatureSeries,
)

SCHEMA_NAME = "difficulty_dynamics.profile"
SCHEMA_VERSION = "difficulty_dynamics.v1"
YAN_DERIVED_FEATURE_IDS = {
    "rhythm.note_density",
}


def run_difficulty_dynamics(config: DifficultyDynamicsConfig) -> tuple[ScoreIR, DifficultyProfile]:
    document = load_musicxml_document(config.score_path)
    score = build_score_ir(document)
    score.diagnostics.extend(run_sanity_checks(score))
    profile = build_difficulty_profile(score, config)
    return score, profile


def build_difficulty_profile(score: ScoreIR, config: DifficultyDynamicsConfig) -> DifficultyProfile:
    regions = _build_regions(score, config)

    feature_series: dict[str, TemporalFeatureSeries] = {}
    feature_availability: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []

    for feature_id in config.feature_ids:
        series = _build_feature_series(score, regions, feature_id, config)
        feature_series[feature_id] = series
        feature_availability[feature_id] = {
            "available_regions": len(series.raw_values) - len(series.missing_region_indices),
            "missing_regions": list(series.missing_region_indices),
            "provenance": series.provenance,
        }
        warnings.extend(series.availability_notes)

    overall_series = None
    if config.composite.enabled:
        composite_feature_ids = config.composite.feature_ids or config.feature_ids
        overall_series = _build_composite_series(
            regions=regions,
            selected_series={feature_id: feature_series[feature_id] for feature_id in composite_feature_ids if feature_id in feature_series},
            config=config.composite,
        )

    passages = tuple(_collect_peak_passages(feature_series, overall_series, config.peaks))
    hard_spots = tuple(_build_hotspots(passages, feature_series, config.composite))

    return DifficultyProfile(
        schema=SCHEMA_NAME,
        schema_version=SCHEMA_VERSION,
        score_id=config.score_id or _score_identifier(score),
        score_title=score.title,
        score_composer=score.composer,
        source_path=str(score.source_path) if score.source_path is not None else None,
        regions=tuple(regions),
        series=feature_series,
        overall_series=overall_series,
        passages=passages,
        hard_spots=hard_spots,
        warnings=tuple(dict.fromkeys(warnings)),
        feature_availability=feature_availability,
        metadata={
            "experiment_name": config.experiment_name,
            "hand_mode": config.hand_mode,
            "window": {
                "kind": config.window.kind,
                "size": config.window.size,
                "step": config.window.step,
                "final_window_behavior": config.window.final_window_behavior,
                "beat_size": config.window.beat_size,
                "beat_step": config.window.beat_step,
            },
            "normalization": {"method": config.normalization.method},
            "smoothing": {
                "method": config.smoothing.method,
                "window_size": config.smoothing.window_size,
                "centered": config.smoothing.centered,
            },
            "composite": {
                "enabled": config.composite.enabled,
                "feature_ids": list(config.composite.feature_ids or config.feature_ids),
                "weights": dict(config.composite.weights),
                "minimum_valid_features": config.composite.minimum_valid_features,
                "exclude_missing": config.composite.exclude_missing,
                "output_feature_id": config.composite.output_feature_id,
            },
            "peaks": {
                "method": config.peaks.method,
                "top_n": config.peaks.top_n,
                "percentile": config.peaks.percentile,
                "minimum_separation": config.peaks.minimum_separation,
            },
        },
    )


def _build_feature_series(
    score: ScoreIR,
    regions: list[ScoreRegion],
    feature_id: str,
    config: DifficultyDynamicsConfig,
) -> TemporalFeatureSeries:
    raw_values: list[float | None] = []
    source_scope = None
    source_scope_ref = None
    units = None
    availability_notes: list[str] = []

    for region in regions:
        region_score = _slice_score_to_region(score, region)
        if not region_score.measures:
            raw_values.append(None)
            availability_notes.append(f"{feature_id}: region {region.window_index} has no measures")
            continue

        feature_records = extract_all(region_score)
        resolved_value, resolved_scope, resolved_scope_ref, resolved_units, note = _resolve_feature_record(
            feature_records,
            feature_id,
            config.hand_mode,
        )
        if note is not None:
            availability_notes.append(f"{feature_id}: {note}")

        if resolved_value is None:
            raw_values.append(None)
            continue

        source_scope = resolved_scope
        source_scope_ref = resolved_scope_ref
        units = resolved_units
        raw_values.append(resolved_value)

    normalized_values, normalization_metadata = normalize_series(raw_values, config.normalization)
    smoothed_values, smoothing_metadata = smooth_series(normalized_values, config.smoothing)

    missing_region_indices = tuple(
        region.window_index for region, value in zip(regions, raw_values) if value is None
    )
    return TemporalFeatureSeries(
        feature_id=feature_id,
        feature_name=_human_feature_name(feature_id),
        provenance=_feature_provenance(feature_id),
        temporal_adaptation="measure_window",
        hand_mode=config.hand_mode,
        extractor_name="piano_difficulty.features.extract_all",
        extractor_config={"feature_id": feature_id, "hand_mode": config.hand_mode},
        units=units,
        source_scope=source_scope,
        source_scope_ref=source_scope_ref,
        regions=tuple(regions),
        raw_values=tuple(raw_values),
        normalized_values=tuple(normalized_values),
        smoothed_values=tuple(smoothed_values),
        missing_region_indices=missing_region_indices,
        transformation_metadata={
            "normalization": normalization_metadata,
            "smoothing": smoothing_metadata,
        },
        availability_notes=tuple(dict.fromkeys(availability_notes)),
    )


def _build_composite_series(
    regions: list[ScoreRegion],
    selected_series: dict[str, TemporalFeatureSeries],
    config: CompositeConfig,
) -> TemporalFeatureSeries:
    values: list[float | None] = []
    contributing_feature_ids = tuple(config.feature_ids or tuple(selected_series))
    for region_index, _region in enumerate(regions):
        terms: list[float] = []
        valid_feature_count = 0
        for feature_id in contributing_feature_ids:
            series = selected_series.get(feature_id)
            if series is None:
                continue
            value = series.normalized_values[region_index] if region_index < len(series.normalized_values) else None
            if value is None:
                if config.exclude_missing:
                    continue
                terms = []
                valid_feature_count = 0
                break
            valid_feature_count += 1
            terms.append(value * config.weights.get(feature_id, 1.0))
        if valid_feature_count < config.minimum_valid_features:
            values.append(None)
            continue
        if not terms:
            values.append(None)
            continue
        weight_total = sum(config.weights.get(feature_id, 1.0) for feature_id in contributing_feature_ids if selected_series.get(feature_id) is not None and (
            selected_series[feature_id].normalized_values[region_index] is not None if region_index < len(selected_series[feature_id].normalized_values) else False
        ))
        if weight_total == 0:
            values.append(None)
            continue
        values.append(sum(terms) / weight_total)

    normalized_values, normalization_metadata = normalize_series(values, NormalizationConfig(method="none"))
    smoothed_values, smoothing_metadata = smooth_series(normalized_values, SmoothingConfig(method="none"))
    return TemporalFeatureSeries(
        feature_id=config.output_feature_id,
        feature_name="Composite Difficulty",
        provenance="repo_native",
        temporal_adaptation="normalized_feature_aggregation",
        hand_mode="both",
        extractor_name="composite",
        extractor_config={
            "feature_ids": list(contributing_feature_ids),
            "weights": dict(config.weights),
            "minimum_valid_features": config.minimum_valid_features,
            "exclude_missing": config.exclude_missing,
        },
        units="normalized_score",
        regions=tuple(regions),
        raw_values=tuple(values),
        normalized_values=tuple(normalized_values),
        smoothed_values=tuple(smoothed_values),
        missing_region_indices=tuple(
            region.window_index for region, value in zip(regions, values) if value is None
        ),
        transformation_metadata={
            "normalization": normalization_metadata,
            "smoothing": smoothing_metadata,
            "contributing_feature_ids": list(contributing_feature_ids),
            "weights": {feature_id: config.weights.get(feature_id, 1.0) for feature_id in contributing_feature_ids},
            "minimum_valid_features": config.minimum_valid_features,
            "exclude_missing": config.exclude_missing,
        },
        availability_notes=("composite difficulty is descriptive, not a validated ground truth",),
    )


def detect_peaks(
    series: TemporalFeatureSeries | None,
    config: PeakDetectionConfig,
) -> list[DifficultyPassage]:
    if series is None:
        return []
    values = series.smoothed_values if any(value is not None for value in series.smoothed_values) else series.normalized_values
    indexed_values = [(index, value) for index, value in enumerate(values) if value is not None]
    if not indexed_values:
        return []

    if config.method == "top_n":
        selected = sorted(indexed_values, key=lambda item: item[1], reverse=True)[: max(config.top_n, 0)]
        threshold = selected[-1][1] if selected else None
        return [
            _build_peak_passage(series, index, value, rank=index_rank + 1, method="top_n", threshold=threshold)
            for index_rank, (index, value) in enumerate(selected)
        ]

    if config.method == "percentile":
        threshold = _percentile_threshold([value for _, value in indexed_values], config.percentile)
        selected = [(index, value) for index, value in indexed_values if value >= threshold]
        selected.sort(key=lambda item: item[1], reverse=True)
        return [
            _build_peak_passage(series, index, value, rank=index_rank + 1, method="percentile", threshold=threshold)
            for index_rank, (index, value) in enumerate(selected)
        ]

    if config.method == "local_maxima":
        candidates = [
            (index, value)
            for index, value in indexed_values
            if _is_local_maximum(values, index)
        ]
        candidates.sort(key=lambda item: item[1], reverse=True)
        selected: list[tuple[int, float]] = []
        for index, value in candidates:
            if all(abs(index - chosen_index) >= config.minimum_separation for chosen_index, _chosen_value in selected):
                selected.append((index, value))
        return [
            _build_peak_passage(series, index, value, rank=index_rank + 1, method="local_maxima", threshold=None)
            for index_rank, (index, value) in enumerate(selected)
        ]

    raise ValueError(f"Unsupported peak detection method {config.method!r}.")


def _collect_peak_passages(
    feature_series: dict[str, TemporalFeatureSeries],
    overall_series: TemporalFeatureSeries | None,
    config: PeakDetectionConfig,
) -> list[DifficultyPassage]:
    passages: list[DifficultyPassage] = []
    for feature_id, series in feature_series.items():
        passages.extend(detect_peaks(series, config))
    if overall_series is not None:
        passages.extend(detect_peaks(overall_series, config))
    passages.sort(key=lambda passage: (passage.region.window_index, passage.contributing_feature_id, passage.rank, -passage.value))
    return passages


def rank_feature_contributions_for_region(
    feature_series: dict[str, TemporalFeatureSeries],
    region_index: int,
    composite_config: CompositeConfig,
    *,
    peak_support_feature_ids: tuple[str, ...] = (),
) -> list[FeatureContribution]:
    contribution_feature_ids = composite_config.feature_ids or tuple(feature_series)
    peak_support = set(peak_support_feature_ids)
    candidates: list[tuple[TemporalFeatureSeries, float | None, float | None, float | None, float, float, bool]] = []

    for feature_id in contribution_feature_ids:
        series = feature_series.get(feature_id)
        if series is None:
            continue
        raw_value = _series_value_at(series.raw_values, region_index)
        normalized_value = _series_value_at(series.normalized_values, region_index)
        smoothed_value = _series_value_at(series.smoothed_values, region_index)
        attribution_value = _attribution_value(normalized_value, smoothed_value)
        if attribution_value is None:
            continue
        weight = composite_config.weights.get(feature_id, 1.0)
        weighted_value = attribution_value * weight
        candidates.append(
            (
                series,
                raw_value,
                normalized_value,
                smoothed_value,
                float(weight),
                float(weighted_value),
                feature_id in peak_support,
            )
        )

    positive_total = sum(max(weighted_value, 0.0) for *_values, weighted_value, _is_peak_support in candidates)
    ranked = sorted(
        candidates,
        key=lambda item: (
            -max(item[5], 0.0),
            -item[5],
            item[0].feature_id,
        ),
    )

    contributions: list[FeatureContribution] = []
    for rank, (series, raw_value, normalized_value, smoothed_value, weight, weighted_value, is_peak_support) in enumerate(ranked, start=1):
        positive_value = max(weighted_value, 0.0)
        contributions.append(
            FeatureContribution(
                feature_id=series.feature_id,
                feature_name=series.feature_name,
                raw_value=raw_value,
                normalized_value=normalized_value,
                smoothed_value=smoothed_value,
                attribution_value=smoothed_value if smoothed_value is not None else normalized_value if normalized_value is not None else 0.0,
                weight=weight,
                weighted_value=weighted_value,
                contribution_share=None if positive_total == 0 else positive_value / positive_total,
                rank=rank,
                is_peak_support=is_peak_support,
            )
        )
    return contributions


def _build_hotspots(
    passages: tuple[DifficultyPassage, ...],
    feature_series: dict[str, TemporalFeatureSeries] | None = None,
    composite_config: CompositeConfig | None = None,
) -> list[DifficultyHotspot]:
    grouped_by_region: dict[int, list[DifficultyPassage]] = {}
    for passage in passages:
        grouped_by_region.setdefault(passage.region.window_index, []).append(passage)

    hotspots: list[DifficultyHotspot] = []
    for region_index, region_passages in grouped_by_region.items():
        ordered_support = sorted(
            region_passages,
            key=lambda passage: (passage.rank, -passage.value, passage.contributing_feature_id),
        )
        best_passage = max(
            ordered_support,
            key=lambda passage: (passage.value, -passage.rank, passage.contributing_feature_id),
        )
        region = ordered_support[0].region
        peak_support_feature_ids = tuple(
            passage.contributing_feature_id
            for passage in ordered_support
            if passage.contributing_feature_id != (composite_config.output_feature_id if composite_config is not None else None)
        )
        feature_contributions = (
            tuple(
                rank_feature_contributions_for_region(
                    feature_series,
                    region_index,
                    composite_config,
                    peak_support_feature_ids=peak_support_feature_ids,
                )
            )
            if feature_series is not None and composite_config is not None
            else ()
        )
        hotspots.append(
            DifficultyHotspot(
                hotspot_id=f"{region.score_id or 'score'}:{region_index}",
                region=region,
                score_position=region.position,
                support_count=len(ordered_support),
                supporting_feature_ids=tuple(dict.fromkeys(passage.contributing_feature_id for passage in ordered_support)),
                supporting_passages=tuple(ordered_support),
                best_value=best_passage.value,
                best_feature_id=best_passage.contributing_feature_id,
                best_rank=best_passage.rank,
                methods=tuple(dict.fromkeys(passage.method for passage in ordered_support)),
                method="consensus_peak_support",
                feature_contributions=feature_contributions,
            )
        )

    hotspots.sort(
        key=lambda hotspot: (
            -hotspot.support_count,
            -hotspot.best_value,
            hotspot.best_rank,
            hotspot.region.window_index,
        )
    )
    return hotspots


def _series_value_at(values: tuple[float | None, ...], index: int) -> float | None:
    if index < 0 or index >= len(values):
        return None
    return values[index]


def _attribution_value(normalized_value: float | None, smoothed_value: float | None) -> float | None:
    return smoothed_value if smoothed_value is not None else normalized_value


def export_profile_rows(profile: DifficultyProfile) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for feature_series in [*profile.series.values(), *( [profile.overall_series] if profile.overall_series is not None else [] )]:
        if feature_series is None:
            continue
        for region, raw_value, normalized_value, smoothed_value in zip(
            feature_series.regions,
            feature_series.raw_values,
            feature_series.normalized_values,
            feature_series.smoothed_values,
        ):
            rows.append(
                {
                    "score_id": profile.score_id,
                    "window_index": region.window_index,
                    "start_measure": region.measure_start,
                    "end_measure": region.measure_end,
                    "position": region.position,
                    "hand": feature_series.hand_mode,
                    "feature_id": feature_series.feature_id,
                    "feature_name": feature_series.feature_name,
                    "provenance": feature_series.provenance,
                    "temporal_adaptation": feature_series.temporal_adaptation,
                    "raw_value": raw_value,
                    "normalized_value": normalized_value,
                    "smoothed_value": smoothed_value,
                    "units": feature_series.units,
                    "source_scope": feature_series.source_scope,
                    "source_scope_ref": feature_series.source_scope_ref,
                }
            )
    return rows


def _build_peak_passage(
    series: TemporalFeatureSeries,
    region_index: int,
    value: float,
    *,
    rank: int,
    method: str,
    threshold: float | None,
) -> DifficultyPassage:
    region = series.regions[region_index]
    return DifficultyPassage(
        passage_id=f"{series.feature_id}:{region.window_index}:{rank}",
        region=region,
        score_position=region.position,
        value=float(value),
        contributing_feature_id=series.feature_id,
        rank=rank,
        method=method,
        threshold=threshold,
    )


def _resolve_feature_record(
    records: list[FeatureRecord],
    feature_id: str,
    hand_mode: str,
) -> tuple[float | None, str | None, str | None, str | None, str | None]:
    matching_records = [record for record in records if record.feature_id == feature_id]
    numeric_records = [
        record
        for record in matching_records
        if isinstance(record.value, (int, float)) and isfinite(float(record.value))
    ]
    if not numeric_records:
        return None, None, None, None, f"feature {feature_id} unavailable in region"

    if hand_mode in {"left", "right"}:
        exact_hand_records = [
            record
            for record in numeric_records
            if record.scope == "hand" and record.scope_ref == hand_mode
        ]
        if exact_hand_records:
            chosen = exact_hand_records[0]
            return float(chosen.value), chosen.scope, chosen.scope_ref, chosen.units, None
        piece_records = [record for record in numeric_records if record.scope == "piece"]
        if piece_records:
            chosen = piece_records[0]
            return float(chosen.value), chosen.scope, chosen.scope_ref, chosen.units, (
                f"used piece-level value for {feature_id} because hand-specific record was absent"
            )
        return None, None, None, None, f"hand-specific value for {feature_id} unavailable"

    piece_records = [record for record in numeric_records if record.scope == "piece"]
    if piece_records:
        chosen = piece_records[0]
        return float(chosen.value), chosen.scope, chosen.scope_ref, chosen.units, None

    hand_records = [record for record in numeric_records if record.scope == "hand"]
    if hand_records:
        values = [float(record.value) for record in hand_records]
        chosen = hand_records[0]
        return (
            sum(values) / len(values),
            chosen.scope,
            "hand_mean",
            chosen.units,
            f"averaged {len(values)} hand-specific values for {feature_id}",
        )

    chosen = numeric_records[0]
    return float(chosen.value), chosen.scope, chosen.scope_ref, chosen.units, None


def _slice_score_to_region(score: ScoreIR, region: ScoreRegion) -> ScoreIR:
    measures = [
        measure
        for measure in score.measures
        if region.measure_start <= measure.measure_index <= region.measure_end
    ]
    measure_indices = {measure.measure_index for measure in measures}

    written_notes = [note for note in score.written_notes if note.measure_index in measure_indices]
    rests = [rest for rest in score.rests if rest.measure_index in measure_indices]
    logical_notes = [note for note in score.logical_notes if note.measure_index in measure_indices]
    directions = [direction for direction in score.directions if direction.measure_index in measure_indices]
    clefs = [clef for clef in score.clefs if clef.measure_index in measure_indices]

    region_score = ScoreIR(
        source_path=score.source_path,
        title=score.title,
        composer=score.composer,
        measures=measures,
        written_notes=written_notes,
        rests=rests,
        logical_notes=logical_notes,
        directions=directions,
        clefs=clefs,
        onset_groups=[*group_onsets(logical_notes), *group_onsets_by_hand(logical_notes)],
        diagnostics=list(score.diagnostics),
    )
    return region_score


def _feature_provenance(feature_id: str) -> str:
    return "yan2023" if feature_id in YAN_DERIVED_FEATURE_IDS else "repo_native"


def _human_feature_name(feature_id: str) -> str | None:
    return feature_id.replace(".", " ").replace("_", " ").title()


def _score_identifier(score: ScoreIR) -> str | None:
    if score.source_path is not None:
        return str(score.source_path)
    return score.title


def _percentile_threshold(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if percentile <= 0:
        return min(values)
    if percentile >= 1:
        return max(values)
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return ordered[index]


def _is_local_maximum(values: list[float | None], index: int) -> bool:
    current = values[index]
    if current is None:
        return False
    left = values[index - 1] if index > 0 else None
    right = values[index + 1] if index + 1 < len(values) else None
    return (left is None or current >= left) and (right is None or current >= right)


def _build_regions(score: ScoreIR, config: DifficultyDynamicsConfig) -> list[ScoreRegion]:
    if config.window.kind == "beat":
        return build_beat_regions(
            score,
            BeatWindowSpec(
                size=config.window.beat_size if config.window.beat_size is not None else config.window.size,
                step=config.window.beat_step if config.window.beat_step is not None else config.window.step,
                final_window_behavior=config.window.final_window_behavior,
                hand=config.hand_mode,
            ),
        )
    return build_measure_regions(
        score,
        MeasureWindowSpec(
            size=config.window.size,
            step=config.window.step,
            final_window_behavior=config.window.final_window_behavior,
            hand=config.hand_mode,
        ),
    )
