"""Recommendation engine v0 — rank next actions with evidence provenance.

Evidence priority (highest first):
  0 today's input (user just marked hard)
  1 piece logs (low confidence / recent failures)
  2 routines/cards (existing cards with few attempts)
  3 learner patterns (factor-level dismissal/accept trends)
  4 cached analysis (hotspot confidence)
  5 fresh analysis (only if needed; lazily injected)
"""

from __future__ import annotations

from typing import Any

from piano_difficulty.pedagogy.models import (
    GradusRecommendationContext,
    HotspotStatus,
    PracticeCard,
    PracticeHotspot,
    PracticeLog,
)


def _today_input_recs(context: GradusRecommendationContext, hotspots: list[PracticeHotspot]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if not context.today_input:
        return recs
    span = context.today_input_span or {}
    ms = span.get("measure_start")
    me = span.get("measure_end")
    # find matching hotspot or create synthetic
    target = None
    if isinstance(ms, int) and isinstance(me, int):
        for hs in hotspots:
            if hs.measure_start == ms and hs.measure_end == me:
                target = hs
                break
    recs.append({
        "evidence_priority": 0,
        "evidence_source": "today_input",
        "target_id": target.hotspot_id if target else f"today:{ms}-{me}",
        "target_span": {"measure_start": ms, "measure_end": me} if isinstance(ms, int) else None,
        "reason": f"you marked this passage hard today: {context.today_input!r}" if context.today_input else "today’s input",
        "evidence_ids": [target.hotspot_id] if target else [],
        "provenance": {"evidence_priority": 0, "source": "today_input", "today_input": context.today_input},
        "priority": 0,
    })
    return recs


def _piece_log_recs(context: GradusRecommendationContext, hotspots: list[PracticeHotspot]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    # low confidence logs suggest revisiting that span
    for log in context.piece_logs:
        if log.confidence is not None and float(log.confidence) < 0.5:
            # find hotspot overlapping log span
            lms = log.measure_start
            lme = log.measure_end
            matched: PracticeHotspot | None = None
            if isinstance(lms, int) and isinstance(lme, int):
                for hs in hotspots:
                    if hs.status == HotspotStatus.dismissed:
                        continue
                    # overlap check
                    if not (hs.measure_end < lms or hs.measure_start > lme):
                        matched = hs
                        break
            recs.append({
                "evidence_priority": 1,
                "evidence_source": "piece_logs",
                "target_id": matched.hotspot_id if matched else (log.card_id or log.log_id),
                "target_span": {"measure_start": lms, "measure_end": lme} if isinstance(lms, int) else None,
                "reason": f"low confidence ({log.confidence:.1f}) in recent log — revisit with a slower tempo ladder",
                "evidence_ids": [log.log_id],
                "provenance": {"evidence_priority": 1, "source": "piece_logs", "log_id": log.log_id, "confidence": log.confidence},
                "priority": 1,
                "_confidence": float(log.confidence) if log.confidence is not None else 1.0,
            })
    # sort low confidence first
    recs.sort(key=lambda r: (r.get("_confidence", 1.0), r["target_id"]))
    for r in recs:
        r.pop("_confidence", None)
    return recs


def _routine_card_recs(context: GradusRecommendationContext, hotspots: list[PracticeHotspot]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for card in context.routines_cards:
        # cards with few attempts are next up; dismissed hotspots never produce cards? but guard
        if card.attempts < 3:
            # check card's hotspot not dismissed
            recs.append({
                "evidence_priority": 2,
                "evidence_source": "routines_cards",
                "target_id": card.card_id,
                "target_span": {"measure_start": card.measure_start, "measure_end": card.measure_end},
                "reason": f"practice card for m.{card.measure_start}–{card.measure_end} has {card.attempts} attempt(s) — 5-minute pitstop",
                "evidence_ids": [card.card_id],
                "provenance": {"evidence_priority": 2, "source": "routines_cards", "card_id": card.card_id, "attempts": card.attempts},
                "priority": 2,
                "_attempts": card.attempts,
            })
    recs.sort(key=lambda r: (r["_attempts"], r["target_id"]))
    for r in recs:
        r.pop("_attempts", None)
    return recs


def _learner_pattern_recs(context: GradusRecommendationContext, hotspots: list[PracticeHotspot]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if context.learner_patterns is None:
        return recs
    lp = context.learner_patterns
    # factor patterns: if learner often struggles with a factor, surface that hotspot
    # dismissed factors deprioritized: skip hotspots whose primary factor is heavily dismissed
    # For v0: simple — surface hotspots whose suggested factor is in top factor_pattern_counts
    if lp.factor_pattern_counts:
        top_factor = max(lp.factor_pattern_counts, key=lambda k: lp.factor_pattern_counts[k])
        for hs in hotspots:
            if hs.status == HotspotStatus.dismissed:
                continue
            for factor in hs.suggested_factors:
                if factor.factor_id == top_factor:
                    recs.append({
                        "evidence_priority": 3,
                        "evidence_source": "learner_patterns",
                        "target_id": hs.hotspot_id,
                        "target_span": {"measure_start": hs.measure_start, "measure_end": hs.measure_end},
                        "reason": f"you’ve often flagged ‘{factor.factor_id}’ — this passage has the same demand",
                        "evidence_ids": [hs.hotspot_id],
                        "provenance": {"evidence_priority": 3, "source": "learner_patterns", "factor_id": top_factor, "uncertainty": lp.uncertainty.to_payload()},
                        "priority": 3,
                    })
                    break
    # also surface that dismissed hotspot ids are NOT recommended
    # (handled by filtering hotspots upstream; no separate rec)
    return recs


def _cached_analysis_recs(hotspots: list[PracticeHotspot]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    # rank non-dismissed hotspots by confidence desc
    active = [hs for hs in hotspots if hs.status != HotspotStatus.dismissed]
    active_sorted = sorted(active, key=lambda hs: (-(hs.confidence or 0), hs.measure_start))
    for rank, hs in enumerate(active_sorted):
        recs.append({
            "evidence_priority": 4,
            "evidence_source": "cached_analysis",
            "target_id": hs.hotspot_id,
            "target_span": {"measure_start": hs.measure_start, "measure_end": hs.measure_end},
            "reason": f"score analysis flagged m.{hs.measure_start}–{hs.measure_end} (confidence {hs.confidence:.2f})" if hs.confidence is not None else f"score analysis flagged m.{hs.measure_start}–{hs.measure_end}",
            "evidence_ids": [e.evidence_id for e in hs.evidence[:3]] or [hs.hotspot_id],
            "provenance": {"evidence_priority": 4, "source": "cached_analysis", "hotspot_id": hs.hotspot_id, "confidence": hs.confidence},
            "priority": 4,
            "_conf": hs.confidence or 0,
            "_rank": rank,
        })
    recs.sort(key=lambda r: (-r["_conf"], r["_rank"]))
    for r in recs:
        r.pop("_conf", None)
        r.pop("_rank", None)
    return recs


def _fresh_analysis_recs(context: GradusRecommendationContext) -> list[dict[str, Any]]:
    # Only used when cached_analysis is None and fresh_analysis provided; not otherwise
    if context.cached_analysis is not None:
        return []
    if context.fresh_analysis is None:
        return []
    # Fresh analysis would be used to build hotspots elsewhere; here just note that we used it
    return [{
        "evidence_priority": 5,
        "evidence_source": "fresh_analysis",
        "target_id": "fresh_analysis",
        "target_span": None,
        "reason": "fresh score analysis was run because no cached analysis was available",
        "evidence_ids": ["fresh_analysis"],
        "provenance": {"evidence_priority": 5, "source": "fresh_analysis"},
        "priority": 5,
    }]


def rank_recommendations(
    context: GradusRecommendationContext,
    hotspots: list[PracticeHotspot],
) -> list[dict[str, Any]]:
    """Rank next-action recommendations using evidence priority.

    Hotspots must already be generated. Dismissed hotspots are deprioritized
    (they only appear if no active recommendations exist, and via cached analysis
    they are excluded). Returns ordered list of recommendation dicts with
    explicit provenance.
    """
    # Collect per evidence source.
    today_input = _today_input_recs(context, hotspots)
    piece_logs = _piece_log_recs(context, hotspots)
    routine_cards = _routine_card_recs(context, hotspots)
    learner_patterns = _learner_pattern_recs(context, hotspots)
    cached_analysis = _cached_analysis_recs(hotspots)
    fresh_analysis = _fresh_analysis_recs(context)

    # Concatenate in priority order; within each evidence source original order is already ranked.
    ordered = [*today_input, *piece_logs, *routine_cards, *learner_patterns, *cached_analysis, *fresh_analysis]

    # Attach overall rank
    for idx, rec in enumerate(ordered):
        rec["rank"] = idx + 1

    # If no recommendations at all, suggest first-read entry (easiest passage)
    if not ordered:
        # first-read: pick easiest active hotspot or smallest measure
        active = [hs for hs in hotspots if hs.status != HotspotStatus.dismissed]
        if active:
            easiest = min(active, key=lambda hs: (hs.confidence or 0, hs.measure_start))
            ordered.append({
                "evidence_priority": 4,
                "evidence_source": "cached_analysis",
                "target_id": easiest.hotspot_id,
                "target_span": {"measure_start": easiest.measure_start, "measure_end": easiest.measure_end},
                "reason": f"start here: m.{easiest.measure_start}–{easiest.measure_end} is the gentlest entry point",
                "evidence_ids": [easiest.hotspot_id],
                "provenance": {"evidence_priority": 4, "source": "cached_analysis_first_read", "hotspot_id": easiest.hotspot_id},
                "priority": 4,
                "rank": 1,
            })

    return ordered
