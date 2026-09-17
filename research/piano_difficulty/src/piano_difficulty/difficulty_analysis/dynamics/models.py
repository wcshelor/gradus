"""Typed data models for the Difficulty Dynamics lane."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from piano_difficulty.temporal.windows import HandMode, ScoreRegion
from piano_difficulty.temporal.transform import NormalizationConfig, SmoothingConfig

NormalizationMethod = Literal["none", "min_max", "z_score", "robust"]
SmoothingMethod = Literal["none", "moving_average", "trailing_moving_average"]
PeakDetectionMethod = Literal["top_n", "percentile", "local_maxima"]
SegmentationKind = Literal["measure", "beat"]
FinalWindowBehavior = Literal["include", "drop"]


@dataclass(frozen=True, slots=True)
class WindowStrategyConfig:
    kind: SegmentationKind = "measure"
    size: int = 4
    step: int = 1
    final_window_behavior: FinalWindowBehavior = "include"
    beat_size: float | None = None
    beat_step: float | None = None


@dataclass(frozen=True, slots=True)
class CompositeConfig:
    enabled: bool = True
    feature_ids: tuple[str, ...] = ()
    weights: dict[str, float] = field(default_factory=dict)
    minimum_valid_features: int = 1
    exclude_missing: bool = True
    output_feature_id: str = "composite.difficulty"


@dataclass(frozen=True, slots=True)
class PeakDetectionConfig:
    method: PeakDetectionMethod = "top_n"
    top_n: int = 3
    percentile: float = 0.9
    minimum_separation: int = 1


@dataclass(frozen=True, slots=True)
class ExportConfig:
    output_root: Path
    run_name: str | None = None
    json_filename: str = "difficulty_profile.json"
    csv_filename: str = "difficulty_profile.csv"
    peaks_filename: str = "difficulty_peaks.json"
    hotspots_filename: str = "difficulty_hotspots.csv"
    report_filename: str = "difficulty_summary.md"
    plot_filename: str = "difficulty_profile.png"
    write_plot: bool = True


@dataclass(frozen=True, slots=True)
class DifficultyDynamicsConfig:
    experiment_name: str
    score_path: Path
    feature_ids: tuple[str, ...]
    hand_mode: HandMode = "both"
    score_id: str | None = None
    window: WindowStrategyConfig = field(default_factory=WindowStrategyConfig)
    normalization: NormalizationConfig = field(default_factory=NormalizationConfig)
    smoothing: SmoothingConfig = field(default_factory=SmoothingConfig)
    composite: CompositeConfig = field(default_factory=CompositeConfig)
    peaks: PeakDetectionConfig = field(default_factory=PeakDetectionConfig)
    export: ExportConfig = field(default_factory=lambda: ExportConfig(output_root=Path("tests/artifacts/difficulty_dynamics")))
    config_path: Path | None = None
    overview_mode: bool = False


@dataclass(frozen=True, slots=True)
class TemporalFeatureSeries:
    feature_id: str
    feature_name: str | None
    provenance: str
    temporal_adaptation: str
    hand_mode: HandMode
    extractor_name: str
    extractor_config: dict[str, Any] = field(default_factory=dict)
    units: str | None = None
    source_scope: str | None = None
    source_scope_ref: str | None = None
    regions: tuple[ScoreRegion, ...] = ()
    raw_values: tuple[float | None, ...] = ()
    normalized_values: tuple[float | None, ...] = ()
    smoothed_values: tuple[float | None, ...] = ()
    missing_region_indices: tuple[int, ...] = ()
    transformation_metadata: dict[str, Any] = field(default_factory=dict)
    availability_notes: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "provenance": self.provenance,
            "temporal_adaptation": self.temporal_adaptation,
            "hand_mode": self.hand_mode,
            "extractor_name": self.extractor_name,
            "extractor_config": dict(self.extractor_config),
            "units": self.units,
            "source_scope": self.source_scope,
            "source_scope_ref": self.source_scope_ref,
            "regions": [region_to_payload(region) for region in self.regions],
            "raw_values": list(self.raw_values),
            "normalized_values": list(self.normalized_values),
            "smoothed_values": list(self.smoothed_values),
            "missing_region_indices": list(self.missing_region_indices),
            "transformation_metadata": dict(self.transformation_metadata),
            "availability_notes": list(self.availability_notes),
        }


@dataclass(frozen=True, slots=True)
class DifficultyPassage:
    passage_id: str
    region: ScoreRegion
    score_position: float | None
    value: float
    contributing_feature_id: str
    rank: int
    method: str
    threshold: float | None = None

    def to_payload(self) -> dict[str, object]:
        measure_numbers = list(self.region.measure_numbers)
        if len(measure_numbers) >= 2:
            measure_range = f"{measure_numbers[0]}-{measure_numbers[-1]}"
        elif measure_numbers:
            measure_range = measure_numbers[0]
        else:
            measure_range = ""
        if self.region.measure_start == self.region.measure_end:
            measure_index_range = str(self.region.measure_start)
        else:
            measure_index_range = f"{self.region.measure_start}-{self.region.measure_end}"
        return {
            "passage_id": self.passage_id,
            "region": region_to_payload(self.region),
            "score_position": self.score_position,
            "value": self.value,
            "contributing_feature_id": self.contributing_feature_id,
            "rank": self.rank,
            "method": self.method,
            "threshold": self.threshold,
            "window_index": self.region.window_index,
            "measure_start": self.region.measure_start,
            "measure_end": self.region.measure_end,
            "measure_index_start": self.region.measure_start,
            "measure_index_end": self.region.measure_end,
            "measure_index_range": measure_index_range,
            "measure_numbers": measure_numbers,
            "measure_range": measure_range,
            "label": self.region.label,
        }


@dataclass(frozen=True, slots=True)
class FeatureContribution:
    feature_id: str
    feature_name: str | None
    raw_value: float | None
    normalized_value: float | None
    smoothed_value: float | None
    attribution_value: float
    weight: float
    weighted_value: float
    contribution_share: float | None
    rank: int
    is_peak_support: bool = False

    def to_payload(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "feature_name": self.feature_name,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "smoothed_value": self.smoothed_value,
            "attribution_value": self.attribution_value,
            "weight": self.weight,
            "weighted_value": self.weighted_value,
            "contribution_share": self.contribution_share,
            "rank": self.rank,
            "is_peak_support": self.is_peak_support,
        }


@dataclass(frozen=True, slots=True)
class DifficultyHotspot:
    hotspot_id: str
    region: ScoreRegion
    score_position: float | None
    support_count: int
    supporting_feature_ids: tuple[str, ...]
    supporting_passages: tuple[DifficultyPassage, ...]
    best_value: float
    best_feature_id: str
    best_rank: int
    methods: tuple[str, ...]
    method: str
    feature_contributions: tuple[FeatureContribution, ...] = ()

    def to_payload(self) -> dict[str, object]:
        # Explicit diagnostic fields preserve both internal indices and printed numbers
        # to debug pickup/hidden-measure label drift without changing user-facing labels.
        measure_numbers = list(self.region.measure_numbers)
        if len(measure_numbers) >= 2:
            measure_range = f"{measure_numbers[0]}-{measure_numbers[-1]}"
        elif measure_numbers:
            measure_range = measure_numbers[0]
        else:
            measure_range = ""
        if self.region.measure_start == self.region.measure_end:
            measure_index_range = str(self.region.measure_start)
        else:
            measure_index_range = f"{self.region.measure_start}-{self.region.measure_end}"
        return {
            "hotspot_id": self.hotspot_id,
            "region": region_to_payload(self.region),
            "score_position": self.score_position,
            "support_count": self.support_count,
            "supporting_feature_ids": list(self.supporting_feature_ids),
            "supporting_passages": [passage.to_payload() for passage in self.supporting_passages],
            "best_value": self.best_value,
            "best_feature_id": self.best_feature_id,
            "best_rank": self.best_rank,
            "methods": list(self.methods),
            "method": self.method,
            "feature_contributions": [contribution.to_payload() for contribution in self.feature_contributions],
            "window_index": self.region.window_index,
            "measure_start": self.region.measure_start,
            "measure_end": self.region.measure_end,
            "measure_index_start": self.region.measure_start,
            "measure_index_end": self.region.measure_end,
            "measure_index_range": measure_index_range,
            "measure_numbers": measure_numbers,
            "measure_range": measure_range,
            "label": self.region.label,
        }


@dataclass(frozen=True, slots=True)
class DifficultyProfile:
    schema: str
    schema_version: str
    score_id: str | None
    score_title: str | None
    score_composer: str | None
    source_path: str | None
    regions: tuple[ScoreRegion, ...]
    series: dict[str, TemporalFeatureSeries]
    overall_series: TemporalFeatureSeries | None
    passages: tuple[DifficultyPassage, ...]
    hard_spots: tuple[DifficultyHotspot, ...] = ()
    warnings: tuple[str, ...] = ()
    feature_availability: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "score": {
                "score_id": self.score_id,
                "title": self.score_title,
                "composer": self.score_composer,
                "source_path": self.source_path,
            },
            "regions": [region_to_payload(region) for region in self.regions],
            "series": {feature_id: series.to_payload() for feature_id, series in self.series.items()},
            "overall_series": None if self.overall_series is None else self.overall_series.to_payload(),
            "passages": [passage.to_payload() for passage in self.passages],
            "hard_spots": [spot.to_payload() for spot in self.hard_spots],
            "warnings": list(self.warnings),
            "feature_availability": self.feature_availability,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class DifficultyDynamicsRunResult:
    run_dir: Path
    json_path: Path
    csv_path: Path
    peaks_path: Path
    hotspots_path: Path
    report_path: Path
    plot_path: Path | None
    profile: DifficultyProfile


def region_to_payload(region: ScoreRegion) -> dict[str, object]:
    return {
        "score_id": region.score_id,
        "window_index": region.window_index,
        "measure_start": region.measure_start,
        "measure_end": region.measure_end,
        "measure_numbers": list(region.measure_numbers),
        "start_offset": None if region.start_offset is None else str(region.start_offset),
        "end_offset": None if region.end_offset is None else str(region.end_offset),
        "start_beat": None if region.start_beat is None else str(region.start_beat),
        "end_beat": None if region.end_beat is None else str(region.end_beat),
        "position": region.position,
        "hand": region.hand,
        "label": region.label,
    }
