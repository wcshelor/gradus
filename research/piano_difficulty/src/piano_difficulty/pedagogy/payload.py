"""Gradus JSON payload assembly — UI-neutral pedagogical payloads.

Builds `gradus.practice_payload.v1` from an AnalysisResult and optional
learner context. Existing score payload remains untouched.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from piano_difficulty.pedagogy.cards import aggregate_logs_for_piece
from piano_difficulty.pedagogy.hotspots import generate_hotspots
from piano_difficulty.pedagogy.models import (
    GRADUS_SCHEMA,
    GRADUS_SCHEMA_VERSION,
    GradusRecommendationContext,
    PracticeCard,
    PracticeHotspot,
)
from piano_difficulty.pedagogy.recommendations import rank_recommendations
from piano_difficulty.pedagogy.taxonomy import TAXONOMY_VERSION, taxonomy_payload


def _piece_id_from_payload(score_payload: dict[str, Any]) -> str | None:
    src = score_payload.get("source", {})
    if isinstance(src, dict):
        path = src.get("path")
        if isinstance(path, str) and path:
            return path
    score = score_payload.get("score", {})
    if isinstance(score, dict):
        title = score.get("title")
        if isinstance(title, str) and title:
            return title
    return None


def _overall_difficulty_from_profiles(profiles: list[dict[str, Any]]) -> dict[str, Any] | None:
    for prof in profiles:
        if not isinstance(prof, dict):
            continue
        if prof.get("profile_id") == "difficulty_overview":
            sections = prof.get("candidate_sections", []) if isinstance(prof.get("candidate_sections"), list) else []
            top_score = sections[0].get("score") if sections and isinstance(sections[0], dict) else None
            return {
                "profile_id": prof.get("profile_id"),
                "profile_version": prof.get("profile_version"),
                "top_score": top_score,
                "score_interpretation": "relative within-piece demand; not a calibrated learner grade",
                "interpretation": prof.get("interpretation"),
            }
    return None


def _first_read_entry_points(hotspots: list[PracticeHotspot], score_payload: dict[str, Any]) -> list[dict[str, Any]]:
    # Easiest measures = inverse of hotspots; for v0 use lowest confidence hotspot(s)
    active = [hs for hs in hotspots if hs.confidence is not None]
    if not active:
        # fallback: smallest measure index
        measure_count = score_payload.get("score", {}).get("measure_count") if isinstance(score_payload.get("score"), dict) else None
        if isinstance(measure_count, int) and measure_count >= 1:
            return [{"measure_start": 1, "measure_end": 1, "reason": "first measure (no analysis hotspots)"}]
        return []
    # sort ascending confidence
    easiest = sorted(active, key=lambda hs: (hs.confidence or 0, hs.measure_start))
    # pick up to 2
    points: list[dict[str, Any]] = []
    for hs in easiest[:2]:
        points.append({
            "measure_start": hs.measure_start,
            "measure_end": hs.measure_end,
            "measure_numbers": list(hs.measure_numbers),
            "hotspot_id": hs.hotspot_id,
            "reason": f"low demand (confidence {hs.confidence:.2f}) — gentle entry point",
            "cta": "first_read",
        })
    return points


def build_gradus_payload(
    analysis_result: Any,
    *,
    recommendation_context: GradusRecommendationContext | None = None,
    cards: list[PracticeCard] | None = None,
    max_hotspots: int = 5,
) -> dict[str, Any]:
    """Build a Gradus practice payload from an AnalysisResult.

    Does not mutate or wrap the existing score payload; caller may embed as
    `score_payload["gradus"] = build_gradus_payload(result)`.

    Accepts AnalysisResult, ExtractionResult, or raw payload dict.
    """
    # obtain score payload
    if hasattr(analysis_result, "to_json_payload"):
        score_payload = analysis_result.to_json_payload()
    elif isinstance(analysis_result, dict) and "schema" in analysis_result and "score" in analysis_result:
        score_payload = analysis_result
    else:
        # try to treat as extraction result with score attr
        try:
            score_payload = analysis_result.to_json_payload()  # type: ignore[union-attr]
        except Exception:
            score_payload = {"source": {}, "score": {}, "analysis_profiles": [], "measure_summaries": []}

    profiles = score_payload.get("analysis_profiles", []) if isinstance(score_payload, dict) else []
    if not isinstance(profiles, list):
        profiles = []

    hotspots = generate_hotspots(analysis_result, max_hotspots=max_hotspots)

    # piece preview report
    piece_id = _piece_id_from_payload(score_payload) if isinstance(score_payload, dict) else None
    overall = _overall_difficulty_from_profiles(profiles) if isinstance(profiles, list) else None
    likely_demands: list[dict[str, Any]] = []
    # aggregate top guessed factors across hotspots
    from collections import Counter
    factor_counts: Counter[str] = Counter()
    factor_conf: dict[str, float] = {}
    for hs in hotspots:
        for factor in hs.suggested_factors:
            factor_counts[factor.factor_id] += 1
            if factor.confidence is not None:
                factor_conf[factor.factor_id] = max(factor_conf.get(factor.factor_id, 0), float(factor.confidence))
    # sort by count then confidence
    sorted_factors = sorted(factor_counts.items(), key=lambda kv: (-kv[1], -factor_conf.get(kv[0], 0), kv[0]))
    for fid, _count in sorted_factors[:4]:
        likely_demands.append({"factor_id": fid, "confidence": factor_conf.get(fid)})

    jump_targets = [{"hotspot_id": hs.hotspot_id, "measure_start": hs.measure_start, "measure_end": hs.measure_end, "measure_numbers": list(hs.measure_numbers)} for hs in hotspots]

    first_read = _first_read_entry_points(hotspots, score_payload if isinstance(score_payload, dict) else {})

    # recommendations
    ctx = recommendation_context
    if ctx is None:
        # build minimal context with cached analysis
        ctx = GradusRecommendationContext(cached_analysis=score_payload if isinstance(score_payload, dict) else None, piece_id=piece_id)
    recommendations = rank_recommendations(ctx, hotspots)

    # cards/lots
    cards = cards or []
    # routine/session suggestion
    routine = {
        "recommended_order": [r["target_id"] for r in recommendations[:3]],
        "estimated_minutes": len(recommendations[:3]) * 5,
    }

    # logs aggregation if context has logs
    logs_summary: dict[str, Any] | None = None
    if ctx and ctx.piece_logs:
        logs_summary = aggregate_logs_for_piece(list(ctx.piece_logs), piece_id=piece_id)

    return {
        "schema": GRADUS_SCHEMA,
        "schema_version": GRADUS_SCHEMA_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "taxonomy": taxonomy_payload(),
        "piece_id": piece_id,
        "source_path": piece_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": {
            "overall_difficulty": overall,
            "top_hotspots": [hs.to_payload() for hs in hotspots[:3]],
            "likely_demands": likely_demands,
            "first_read_entry_points": first_read,
            "jump_targets": jump_targets,
        },
        "hotspots": [hs.to_payload() for hs in hotspots],
        "cards": [c.to_payload() for c in cards],
        "recommendations": recommendations,
        "routine": routine,
        "logs_summary": logs_summary,
        "provenance": {
            "analysis_profiles_used": [p.get("profile_id") for p in profiles if isinstance(p, dict) and isinstance(p.get("profile_id"), str)],
            "hotspot_count": len(hotspots),
            "recommendation_evidence_tiers": ["today_input", "piece_logs", "routines_cards", "learner_patterns", "cached_analysis", "fresh_analysis"],
        },
    }


def build_gradus_payload_from_dict(
    score_payload: dict[str, Any],
    *,
    recommendation_context: GradusRecommendationContext | None = None,
    cards: list[PracticeCard] | None = None,
    max_hotspots: int = 5,
) -> dict[str, Any]:
    """Dict-only variant for callers that already have a payload dict."""
    return build_gradus_payload(score_payload, recommendation_context=recommendation_context, cards=cards, max_hotspots=max_hotspots)
