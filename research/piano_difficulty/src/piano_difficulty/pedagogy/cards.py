"""Practice cards and logs — creation + simple aggregation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from piano_difficulty.pedagogy.models import DrillType, PracticeCard, PracticeHotspot, PracticeLog, LogMode


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _card_id(piece_id: str | None, ms: int, me: int, extra: str = "") -> str:
    base = f"{piece_id or 'piece'}:card:{ms}-{me}:{extra}:{_now_iso()}"
    return f"card:{ms}-{me}:{hashlib.sha1(base.encode()).hexdigest()[:8]}"


def create_card(
    hotspot_or_span: PracticeHotspot | dict[str, Any],
    *,
    factor_tags: tuple[str, ...] | None = None,
    drill_type: DrillType | str | None = None,
    piece_id: str | None = None,
    target_tempo: float | None = None,
    estimated_minutes: int = 5,
) -> PracticeCard:
    """Create a PracticeCard attached to 1-2 measures or a selected span."""
    if isinstance(hotspot_or_span, PracticeHotspot):
        ms = hotspot_or_span.measure_start
        me = hotspot_or_span.measure_end
        # 1-2 measure default: if span larger, keep as is; card panel is 1-2 measures
        # for large hotspots, recommend first 2 measures
        if me - ms + 1 > 2:
            me = ms + 1
        tags = factor_tags if factor_tags is not None else tuple(f.factor_id for f in hotspot_or_span.suggested_factors)
        pid = piece_id or hotspot_or_span.piece_id
        extra = hotspot_or_span.hotspot_id
    elif isinstance(hotspot_or_span, dict):
        ms = hotspot_or_span.get("measure_start")
        me = hotspot_or_span.get("measure_end")
        if not isinstance(ms, int) or not isinstance(me, int):
            raise ValueError("span dict requires measure_start/end int")
        tags = factor_tags or tuple(hotspot_or_span.get("factor_tags", []))
        pid = piece_id or hotspot_or_span.get("piece_id")
        extra = str(hotspot_or_span.get("hotspot_id", ""))
    else:
        raise TypeError("hotspot_or_span must be PracticeHotspot or dict")

    if isinstance(drill_type, str):
        try:
            drill_type = DrillType(drill_type)
        except ValueError as exc:
            raise ValueError(f"unknown DrillType {drill_type!r}") from exc

    if factor_tags is not None:
        tags = tuple(str(t) for t in factor_tags)

    return PracticeCard(
        card_id=_card_id(pid, ms, me, extra),
        piece_id=pid,
        measure_start=ms,
        measure_end=me,
        factor_tags=tuple(str(t) for t in tags),
        drill_type=drill_type,  # type: ignore[arg-type]
        target_tempo=target_tempo,
        attempts=0,
        best_controlled_tempo=None,
        confidence=None,
        effort=None,
        accuracy=None,
        helpfulness={},
        confidence_trend=(),
        effort_trend=(),
        accuracy_trend=(),
        notes=None,
        estimated_minutes=estimated_minutes,
        created_at=_now_iso(),
        diagnostics=(),
    )


def apply_log(card: PracticeCard, log: PracticeLog) -> PracticeCard:
    """Return updated card with aggregated log signals."""
    if not isinstance(card, PracticeCard):
        raise TypeError("card must be PracticeCard")
    if not isinstance(log, PracticeLog):
        raise TypeError("log must be PracticeLog")

    # link check: warn via diagnostics if mismatched ids (non-fatal)
    diags = list(card.diagnostics)
    if log.card_id and log.card_id != card.card_id:
        diags.append(f"log card_id mismatch: {log.card_id} != {card.card_id}")

    new_attempts = card.attempts + 1
    new_best = card.best_controlled_tempo
    if log.controlled_tempo is not None:
        if new_best is None or float(log.controlled_tempo) > float(new_best):
            new_best = float(log.controlled_tempo)

    # trends
    new_conf_trend = tuple(list(card.confidence_trend) + ([float(log.confidence)] if log.confidence is not None else []))
    new_eff_trend = tuple(list(card.effort_trend) + ([float(log.effort)] if log.effort is not None else []))
    new_acc_trend = tuple(list(card.accuracy_trend) + ([float(log.accuracy)] if log.accuracy is not None else []))

    # latest values
    new_conf = float(log.confidence) if log.confidence is not None else card.confidence
    new_eff = float(log.effort) if log.effort is not None else card.effort
    new_acc = float(log.accuracy) if log.accuracy is not None else card.accuracy

    # helpfulness: merge latest (overwrite per facet with moving average-like keep last)
    new_help = dict(card.helpfulness)
    for k, v in log.helpfulness.items():
        new_help[k] = float(v)

    # optional: aggregate helpfulness facets as simple last-value

    return PracticeCard(
        card_id=card.card_id,
        piece_id=card.piece_id,
        measure_start=card.measure_start,
        measure_end=card.measure_end,
        factor_tags=card.factor_tags,
        drill_type=card.drill_type,
        target_tempo=card.target_tempo,
        attempts=new_attempts,
        best_controlled_tempo=new_best,
        confidence=new_conf,
        effort=new_eff,
        accuracy=new_acc,
        helpfulness=new_help,
        confidence_trend=new_conf_trend,
        effort_trend=new_eff_trend,
        accuracy_trend=new_acc_trend,
        notes=card.notes,
        estimated_minutes=card.estimated_minutes,
        created_at=card.created_at,
        diagnostics=tuple(diags),
    )


def aggregate_logs_for_piece(logs: list[PracticeLog], piece_id: str | None = None) -> dict[str, Any]:
    """Simple aggregation for piece-level trends."""
    relevant = [l for l in logs if piece_id is None or l.piece_id == piece_id]
    confidences = [float(l.confidence) for l in relevant if l.confidence is not None]
    efforts = [float(l.effort) for l in relevant if l.effort is not None]
    accuracies = [float(l.accuracy) for l in relevant if l.accuracy is not None]
    tempos = [float(l.controlled_tempo) for l in relevant if l.controlled_tempo is not None]

    def trend(values: list[float]) -> float | None:
        if not values:
            return None
        # simple delta first->last
        if len(values) == 1:
            return 0.0
        return values[-1] - values[0]

    return {
        "log_count": len(relevant),
        "confidence_trend": trend(confidences),
        "effort_trend": trend(efforts),
        "accuracy_trend": trend(accuracies),
        "best_controlled_tempo": max(tempos) if tempos else None,
        "avg_confidence": sum(confidences) / len(confidences) if confidences else None,
        "helpfulness_facets": _aggregate_helpfulness(relevant),
    }


def _aggregate_helpfulness(logs: list[PracticeLog]) -> dict[str, float]:
    acc: dict[str, list[float]] = {}
    for log in logs:
        for k, v in log.helpfulness.items():
            acc.setdefault(k, []).append(float(v))
    return {k: sum(vs) / len(vs) for k, vs in acc.items()}


def create_log(
    *,
    log_id: str,
    mode: LogMode | str,
    timestamp: str | None = None,
    passage_id: str | None = None,
    card_id: str | None = None,
    session_id: str | None = None,
    piece_id: str | None = None,
    measure_start: int | None = None,
    measure_end: int | None = None,
    confidence: float | None = None,
    effort: float | None = None,
    accuracy: float | None = None,
    helpfulness: dict[str, float] | None = None,
    free_notes: str | None = None,
    controlled_tempo: float | None = None,
) -> PracticeLog:
    if isinstance(mode, str):
        try:
            mode = LogMode(mode)
        except ValueError as exc:
            raise ValueError(f"unknown LogMode {mode!r}") from exc
    return PracticeLog(
        log_id=log_id,
        mode=mode,  # type: ignore[arg-type]
        timestamp=timestamp or _now_iso(),
        passage_id=passage_id,
        card_id=card_id,
        session_id=session_id,
        piece_id=piece_id,
        measure_start=measure_start,
        measure_end=measure_end,
        confidence=confidence,
        effort=effort,
        accuracy=accuracy,
        helpfulness=helpfulness or {},
        free_notes=free_notes,
        controlled_tempo=controlled_tempo,
        diagnostics=(),
    )
