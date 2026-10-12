"""Pipeline adapter for difficulty events.

Post-processing layer: metrics first, notes second.  Does not mutate scores.
Opt-in flag keeps existing payloads unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from piano_difficulty.difficulty_analysis.dynamics.core import build_difficulty_profile
from piano_difficulty.difficulty_analysis.dynamics.models import (
    CompositeConfig,
    DifficultyDynamicsConfig,
    NormalizationConfig,
    PeakDetectionConfig,
    WindowStrategyConfig,
)
from piano_difficulty.difficulty_analysis.overview import OverviewOptions
from piano_difficulty.features.registry import resolve_factors
from piano_difficulty.normalize.schema import ScoreIR
from piano_difficulty.temporal.windows import ScoreRegion

from .labeling import explain_flagged_span


def _reconstruct_profile(extraction: Any, options: OverviewOptions | None) -> Any:
    """Rebuild DifficultyProfile used for segmentation.

    Uses same construction as overview._build_view but returns raw profile
    instead of serialized payload.  This avoids coupling to private view state.
    """
    opts = options or OverviewOptions()
    factors = resolve_factors(opts.feature_ids)
    composite = CompositeConfig(weights={f.feature_id: f.weight for f in factors})
    config = DifficultyDynamicsConfig(
        experiment_name="difficulty_events",
        score_path=extraction.score.source_path or Path("score.musicxml"),
        feature_ids=tuple(f.feature_id for f in factors),
        hand_mode=opts.hand,  # type: ignore[arg-type]
        window=WindowStrategyConfig(
            kind=opts.window,  # type: ignore[arg-type]
            size=int(opts.window_size),
            step=int(opts.stride),
            beat_size=opts.window_size,
            beat_step=opts.stride,
        ),
        normalization=NormalizationConfig(method="min_max"),
        composite=composite,
        peaks=PeakDetectionConfig(top_n=opts.top_sections),
        overview_mode=True,
    )
    return build_difficulty_profile(extraction.score, config)


def _payload_region_to_score_region(d: dict[str, Any], score_id: str | None) -> ScoreRegion | None:
    from fractions import Fraction

    def _frac(v: Any) -> Fraction | None:
        if v is None:
            return None
        try:
            return Fraction(str(v))
        except Exception:
            return None

    try:
        return ScoreRegion(
            score_id=d.get("score_id") or score_id,
            window_index=int(d.get("window_index", 0)),
            measure_start=int(d.get("measure_start", 0)),
            measure_end=int(d.get("measure_end", 0)),
            measure_numbers=tuple(str(x) for x in d.get("measure_numbers", [])),
            start_offset=_frac(d.get("start_offset")),
            end_offset=_frac(d.get("end_offset")),
            start_beat=_frac(d.get("start_beat")),
            end_beat=_frac(d.get("end_beat")),
            position=d.get("position"),
            hand=d.get("hand"),
            label=d.get("label"),
        )
    except Exception:
        return None


def explain_events_for_extraction(
    extraction: Any,
    overview_payload: dict[str, Any] | None,
    *,
    options: OverviewOptions | None = None,
    max_sections: int | None = None,
    use_note_inspection: bool = True,
) -> dict[str, Any]:
    """Generate difficulty events for flagged candidate sections.

    Returns dict with `events_by_section` and flat `events` list, both
    serializable via to_payload().  Does not mutate extraction.
    """
    score: ScoreIR = extraction.score
    if overview_payload is None:
        return {"schema": "difficulty_events", "schema_version": "difficulty_events.v1", "events_by_section": [], "events": [], "diagnostics": ["no overview payload — events unavailable"]}

    candidate_sections = overview_payload.get("candidate_sections") or []
    if not candidate_sections:
        return {"schema": "difficulty_events", "schema_version": "difficulty_events.v1", "events_by_section": [], "events": [], "diagnostics": ["no candidate_sections — nothing flagged"]}

    profile = _reconstruct_profile(extraction, options)
    limit = max_sections or len(candidate_sections)
    events_by_section: list[dict[str, Any]] = []
    flat_events: list[dict[str, Any]] = []
    diagnostics: list[str] = []

    for sec in candidate_sections[:limit]:
        region_dict = sec.get("region") if isinstance(sec.get("region"), dict) else {}
        if not region_dict:
            continue
        flagged = _payload_region_to_score_region(region_dict, profile.score_id)
        if flagged is None:
            diagnostics.append(f"skip section {sec.get('section_id')}: could not reconstruct region")
            continue
        try:
            events = explain_flagged_span(score, profile, flagged, use_note_inspection=use_note_inspection)
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(f"section {sec.get('section_id')}: explain failed: {exc}")
            continue
        payloads = [e.to_payload() for e in events]
        flat_events.extend(payloads)
        events_by_section.append(
            {
                "section_id": sec.get("section_id"),
                "region": region_dict,
                "event_count": len(payloads),
                "events": payloads,
            }
        )

    return {
        "schema": "difficulty_events",
        "schema_version": "difficulty_events.v1",
        "interpretation": "Post-processing subdivision of already-flagged difficult passages into playable events; metric-driven first, note inspection second; does not change difficulty scores.",
        "events_by_section": events_by_section,
        "events": flat_events,
        "event_count": len(flat_events),
        "diagnostics": diagnostics,
        "methods": {
            "segmentation": "metric_delta_boundaries.v1",
            "labeling": "metric_plus_selective_note_inspection.v1",
            "overlap": "allowed",
            "confidence": "weighted metric support + note corroboration; uncertain when below threshold",
        },
    }
