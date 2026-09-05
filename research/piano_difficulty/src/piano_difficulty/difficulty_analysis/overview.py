"""Public overview assembled from promoted Difficulty Dynamics components."""

from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path

from piano_difficulty.features.registry import DEFAULT_FACTOR_IDS, REGISTRY_VERSION, resolve_factors
from piano_difficulty.features import extract_all
from piano_difficulty.temporal.selection import select_region
from .dynamics.core import build_difficulty_profile, _resolve_feature_record
from .dynamics.models import (
    CompositeConfig, DifficultyDynamicsConfig, NormalizationConfig,
    PeakDetectionConfig, WindowStrategyConfig,
)
from .sections import consolidate_sections


@dataclass(frozen=True)
class OverviewOptions:
    window: str = "measure"
    window_size: float = 2
    stride: float = 1
    hand: str = "both"
    top_sections: int = 5
    feature_ids: tuple[str, ...] = DEFAULT_FACTOR_IDS

    def __post_init__(self):
        if self.window not in {"measure", "beat"} or self.hand not in {"both", "left", "right"}:
            raise ValueError("Unsupported window or hand selection.")
        if any(not isfinite(v) or v <= 0 for v in (self.window_size, self.stride)):
            raise ValueError("Window size and stride must be finite and positive.")
        if self.window == "measure" and any(int(v) != v for v in (self.window_size, self.stride)):
            raise ValueError("Measure windows require integer sizes and strides.")
        if not isinstance(self.top_sections, int) or self.top_sections < 1:
            raise ValueError("top_sections must be a positive integer.")
        if not self.feature_ids or len(set(self.feature_ids)) != len(self.feature_ids):
            raise ValueError("Select at least one factor, without duplicates.")
        resolve_factors(self.feature_ids)


@dataclass
class DifficultyAnalysisResult:
    payload: dict

    def to_payload(self):
        return self.payload


class DifficultyOverviewProfile:
    profile_id = "difficulty_overview"
    profile_version = "1"

    def analyze(self, extraction, options=None):
        options = options or OverviewOptions()
        hands = (options.hand,) if options.hand != "both" else ("both", "right", "left")
        views = {}
        for hand in hands:
            if hand != "both" and not any(f.scope != "coordination" for f in resolve_factors(options.feature_ids)):
                continue
            if hand != "both" and not any(n.hand == hand for n in extraction.score.logical_notes):
                continue
            views[hand] = _build_view(extraction, replace(options, hand=hand))
        # Preserve a meaningful empty result when the requested hand is absent.
        if options.hand not in views:
            views[options.hand] = _build_view(extraction, options)
        main = views[options.hand]
        return DifficultyAnalysisResult({
            "schema_version": "difficulty_overview.v1",
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "factor_registry_version": REGISTRY_VERSION,
            "interpretation": "Relative score demands within this piece; no calibrated difficulty grade.",
            "factor_ranking_method": "mean within-piece normalized value across analysis windows",
            "hand_mode": options.hand,
            **main,
            "hand_views": {hand: view for hand, view in views.items() if hand != options.hand},
            "diagnostics": [
                "Factor ranks describe contributions to this chosen profile, not measured learner difficulty.",
                "Constant factors have no local peak; raw values remain visible.",
                "Attack selection omits sustains entering a window; original written durations are retained.",
                "Evidence IDs identify region inputs, not a causal or event-level difficulty attribution.",
                "Hand labels use the parser's conservative staff-based inference.",
                "Transitions crossing a window start are omitted; overlapping windows reduce this boundary effect.",
                *main["warnings"],
            ],
        })


def _build_view(extraction, options):
    factors = [f for f in resolve_factors(options.feature_ids)
               if options.hand == "both" or f.scope != "coordination"]
    if not factors:
        raise ValueError("No selected factors support the requested hand.")
    composite = CompositeConfig(weights={f.feature_id: f.weight for f in factors})
    config = DifficultyDynamicsConfig(
        experiment_name="difficulty_overview",
        score_path=extraction.score.source_path or Path("score.musicxml"),
        feature_ids=tuple(f.feature_id for f in factors),
        hand_mode=options.hand,
        window=WindowStrategyConfig(
            kind=options.window, size=int(options.window_size), step=int(options.stride),
            beat_size=options.window_size, beat_step=options.stride),
        normalization=NormalizationConfig(method="min_max"),
        composite=composite, peaks=PeakDetectionConfig(top_n=options.top_sections),
        overview_mode=True,
    )
    profile = build_difficulty_profile(extraction.score, config)
    # Flat tracks have no relative local peak, even if the raw demand is large.
    profile = replace(profile, passages=tuple(p for p in profile.passages if p.value > 0))
    piece_records = extraction.features
    if options.hand != "both" and profile.regions:
        whole_region = replace(
            profile.regions[0], end_offset=max(m.end for m in extraction.score.measures))
        piece_records = extract_all(select_region(extraction.score, whole_region))
    summaries = []
    for factor in factors:
        series = profile.series[factor.feature_id]
        valid = [v for v in series.normalized_values if v is not None]
        raw = [v for v in series.raw_values if v is not None]
        piece_value = _resolve_feature_record(
            piece_records, factor.feature_id, options.hand, hand_aggregation="max")[0]
        if not raw:
            piece_value = None
        summaries.append({
            **factor.to_payload(), "units": series.units or factor.units,
            "piece_value": piece_value,
            "local_min": min(raw) if raw else None, "local_max": max(raw) if raw else None,
            "profile_contribution": sum(valid) / len(valid) * factor.weight if valid else None,
            "availability": "available" if raw else "unavailable",
            "peak_ids": [p.passage_id for p in profile.passages if p.contributing_feature_id == factor.feature_id],
        })
    summaries.sort(key=lambda f: (-(f["profile_contribution"] or 0), f["feature_id"]))
    for rank, summary in enumerate(summaries, start=1):
        summary["rank"] = rank
    evidence = []
    for region in profile.regions:
        selection = select_region(extraction.score, region)
        evidence.append({
            "window_index": region.window_index,
            "written_note_ids": [n.note_id for n in selection.written_notes],
            "logical_note_ids": [n.note_id for n in selection.logical_notes],
            "source_note_ids": sorted({i for n in selection.logical_notes for i in n.source_note_ids}),
            "scope": "region_input_events",
        })
    temporal = profile.to_payload()
    warnings = list(profile.warnings)
    if not extraction.score.logical_notes:
        warnings.append("No logical note attacks were found in this score.")
    if any(n.hand is None for n in extraction.score.logical_notes):
        warnings.append("Some attacks have no inferred hand and are omitted from hand-specific profiles.")
    return {
        "factors": summaries, "regions": temporal["regions"], "series": temporal["series"],
        "composite": temporal["overall_series"],
        "factor_peaks": [p for p in temporal["passages"] if p["contributing_feature_id"] in profile.series],
        "composite_peaks": [p for p in temporal["passages"] if p["contributing_feature_id"] not in profile.series],
        "candidate_sections": consolidate_sections(profile, composite, limit=options.top_sections),
        "region_evidence": evidence, "warnings": warnings,
        "methods": profile.metadata,
    }
