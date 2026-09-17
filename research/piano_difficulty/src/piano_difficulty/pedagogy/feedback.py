"""Feedback ingestion — accept/dismiss/adjust hotspot events and hard-section labels.

Append-only, non-destructive: dismissed hotspots are preserved and deprioritized,
not deleted.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from piano_difficulty.pedagogy.factors import guess_factors_for_features
from piano_difficulty.pedagogy.models import (
    DifficultyFactor,
    EvidenceRef,
    FeedbackEvent,
    FeedbackKind,
    HotspotOrigin,
    HotspotStatus,
    PracticeHotspot,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ingest_feedback(
    hotspots: list[PracticeHotspot],
    event: FeedbackEvent,
) -> tuple[list[PracticeHotspot], FeedbackEvent]:
    """Apply one feedback event to hotspot list. Returns (updated_hotspots, event).

    Non-mutating: returns new list. Dismissals are preserved. Adjust creates a
    new hotspot with adjusted span.
    """
    if not isinstance(event, FeedbackEvent):
        raise TypeError("event must be FeedbackEvent")
    updated: list[PracticeHotspot] = list(hotspots)

    if event.kind == FeedbackKind.accept:
        # mark matching hotspot accepted
        new_list: list[PracticeHotspot] = []
        matched = False
        for hs in updated:
            if event.hotspot_id and hs.hotspot_id == event.hotspot_id:
                matched = True
                new_list.append(PracticeHotspot(
                    hotspot_id=hs.hotspot_id,
                    piece_id=hs.piece_id,
                    source_path=hs.source_path,
                    measure_start=hs.measure_start,
                    measure_end=hs.measure_end,
                    measure_numbers=hs.measure_numbers,
                    window_index=hs.window_index,
                    score_position=hs.score_position,
                    confidence=hs.confidence,
                    evidence=hs.evidence,
                    suggested_factors=hs.suggested_factors,
                    status=HotspotStatus.accepted,
                    origin=hs.origin,
                    created_at=hs.created_at,
                    diagnostics=hs.diagnostics,
                ))
            else:
                new_list.append(hs)
        if not matched and event.hotspot_id:
            # unknown id — no mutation, just record event
            pass
        return new_list, event

    if event.kind == FeedbackKind.dismiss:
        new_list = []
        for hs in updated:
            if event.hotspot_id and hs.hotspot_id == event.hotspot_id:
                new_list.append(PracticeHotspot(
                    hotspot_id=hs.hotspot_id,
                    piece_id=hs.piece_id,
                    source_path=hs.source_path,
                    measure_start=hs.measure_start,
                    measure_end=hs.measure_end,
                    measure_numbers=hs.measure_numbers,
                    window_index=hs.window_index,
                    score_position=hs.score_position,
                    confidence=hs.confidence,
                    evidence=hs.evidence,
                    suggested_factors=hs.suggested_factors,
                    status=HotspotStatus.dismissed,
                    origin=hs.origin,
                    created_at=hs.created_at,
                    diagnostics=hs.diagnostics,
                ))
            else:
                new_list.append(hs)
        return new_list, event

    if event.kind == FeedbackKind.adjust:
        new_list = []
        adjusted_added: PracticeHotspot | None = None
        for hs in updated:
            if event.hotspot_id and hs.hotspot_id == event.hotspot_id:
                # preserve original as dismissed/adjusted? spec says preserved; mark original dismissed
                new_list.append(PracticeHotspot(
                    hotspot_id=hs.hotspot_id,
                    piece_id=hs.piece_id,
                    source_path=hs.source_path,
                    measure_start=hs.measure_start,
                    measure_end=hs.measure_end,
                    measure_numbers=hs.measure_numbers,
                    window_index=hs.window_index,
                    score_position=hs.score_position,
                    confidence=hs.confidence,
                    evidence=hs.evidence,
                    suggested_factors=hs.suggested_factors,
                    status=HotspotStatus.dismissed,
                    origin=hs.origin,
                    created_at=hs.created_at,
                    diagnostics=(*hs.diagnostics, "superseded by adjust"),
                ))
                # create adjusted copy
                new_ms = event.adjusted_measure_start if event.adjusted_measure_start is not None else hs.measure_start
                new_me = event.adjusted_measure_end if event.adjusted_measure_end is not None else hs.measure_end
                # build new measure_numbers
                new_numbers = tuple(str(i) for i in range(new_ms, new_me + 1))
                # relabel factors if provided
                new_factors: tuple[DifficultyFactor, ...] = hs.suggested_factors
                if event.selected_factors:
                    new_factors = tuple(
                        DifficultyFactor(factor_id=fid, confidence=0.9, evidence_ids=(), source_feature_ids=())
                        for fid in event.selected_factors
                    )
                adjusted_id = f"{hs.hotspot_id}:adj:{new_ms}-{new_me}"
                adjusted_added = PracticeHotspot(
                    hotspot_id=adjusted_id,
                    piece_id=hs.piece_id,
                    source_path=hs.source_path,
                    measure_start=new_ms,
                    measure_end=new_me,
                    measure_numbers=new_numbers,
                    window_index=hs.window_index,
                    score_position=hs.score_position,
                    confidence=hs.confidence,
                    evidence=hs.evidence,
                    suggested_factors=new_factors,
                    status=HotspotStatus.adjusted,
                    origin=HotspotOrigin.manual,
                    created_at=_now_iso(),
                    diagnostics=("adjusted from " + hs.hotspot_id,),
                )
            else:
                new_list.append(hs)
        if adjusted_added is not None:
            new_list.append(adjusted_added)
        return new_list, event

    if event.kind == FeedbackKind.hard_section_label:
        # Create a manual hotspot from the labelled passage
        ms = event.measure_start
        me = event.measure_end
        if ms is None or me is None:
            raise ValueError("hard_section_label requires measure_start/end")
        if not isinstance(ms, int) or not isinstance(me, int):
            raise ValueError("measure_start/end must be int")
        # piece_id from existing hotspots or event hotspot_id prefix
        piece_id = None
        source_path = None
        for hs in updated:
            piece_id = hs.piece_id
            source_path = hs.source_path
            break
        # guess 3 factors from selected_factors if provided, else generic
        suggested: tuple[DifficultyFactor, ...]
        if event.selected_factors:
            suggested = tuple(
                DifficultyFactor(factor_id=fid, confidence=0.85, evidence_ids=(), source_feature_ids=())
                for fid in event.selected_factors[:3]
            )
        else:
            # fallback guesses
            guessed = guess_factors_for_features([])
            suggested = tuple(guessed[:3])
        # evidence for manual label
        evidence = (EvidenceRef(evidence_id=f"manual:{ms}-{me}", kind="manual_label", window_index=None),)
        hid = f"hs:manual:{ms}-{me}:{event.event_id[:8]}"
        new_hs = PracticeHotspot(
            hotspot_id=hid,
            piece_id=piece_id,
            source_path=source_path,
            measure_start=ms,
            measure_end=me,
            measure_numbers=tuple(str(i) for i in range(ms, me + 1)),
            window_index=None,
            score_position=None,
            confidence=0.7,
            evidence=evidence,
            suggested_factors=suggested,
            status=HotspotStatus.accepted,
            origin=HotspotOrigin.manual,
            created_at=_now_iso(),
            diagnostics=("hard_section_label",),
        )
        return [*updated, new_hs], event

    return updated, event


def apply_feedback_log(
    hotspots: list[PracticeHotspot],
    events: list[FeedbackEvent],
) -> tuple[list[PracticeHotspot], list[FeedbackEvent]]:
    """Apply a sequence of feedback events (append-only log)."""
    current = list(hotspots)
    log: list[FeedbackEvent] = []
    for ev in events:
        current, applied = ingest_feedback(current, ev)
        log.append(applied)
    return current, log


def filter_active(hotspots: list[PracticeHotspot], *, include_dismissed: bool = False) -> list[PracticeHotspot]:
    """Return hotspots filtered by status. By default excludes dismissed."""
    if include_dismissed:
        return list(hotspots)
    return [hs for hs in hotspots if hs.status != HotspotStatus.dismissed]


def normalize_event_payload(data: dict[str, Any]) -> FeedbackEvent:
    """Parse and validate a raw event dict from Oktav persistence."""
    return FeedbackEvent.from_payload(data)
