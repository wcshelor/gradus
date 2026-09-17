"""Drill request specs — short drill plans without score generation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from piano_difficulty.pedagogy.models import DrillSpec, DrillType, PracticeCard, PracticeHotspot


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _drill_id(piece_id: str | None, ms: int, me: int, kind: DrillType) -> str:
    base = f"{piece_id or 'piece'}:drill:{kind.value}:{ms}-{me}:{_now_iso()}"
    return f"drill:{kind.value}:{ms}-{me}:{hashlib.sha1(base.encode()).hexdigest()[:8]}"


# Default params per drill kind (UI can override)
_DEFAULT_PARAMS: dict[DrillType, dict[str, Any]] = {
    DrillType.isolate_notes: {"focus": "single_voice", "hands": "both"},
    DrillType.simplify_texture: {"reduce": "inner_voices", "keep": "outer_voices"},
    DrillType.hands_separate: {"hands": "right", "then": "left"},
    DrillType.tempo_ladder: {"start_bpm": 60, "steps": [60, 80, 100], "target_bpm": 100},
    DrillType.transition_loop: {"loop_bars": 1, "overlap": "one_beat"},
    DrillType.voicing_focus: {"voicing": "top_voice", "balance": "melody_over_accompaniment"},
}


def spec_for(
    card_or_hotspot: PracticeCard | PracticeHotspot | dict[str, Any],
    kind: DrillType | str,
    *,
    params: dict[str, Any] | None = None,
    provenance: tuple[str, ...] | None = None,
) -> DrillSpec:
    """Emit a DrillSpec for a given card/hotspot and drill kind."""
    if isinstance(kind, str):
        try:
            kind = DrillType(kind)
        except ValueError as exc:
            raise ValueError(f"unknown DrillType {kind!r}") from exc

    if isinstance(card_or_hotspot, PracticeCard):
        ms = card_or_hotspot.measure_start
        me = card_or_hotspot.measure_end
        piece_id = card_or_hotspot.piece_id
        prov = provenance if provenance is not None else tuple(card_or_hotspot.factor_tags)
    elif isinstance(card_or_hotspot, PracticeHotspot):
        ms = card_or_hotspot.measure_start
        me = card_or_hotspot.measure_end
        piece_id = card_or_hotspot.piece_id
        prov = provenance if provenance is not None else tuple(f.factor_id for f in card_or_hotspot.suggested_factors)
    elif isinstance(card_or_hotspot, dict):
        ms = card_or_hotspot.get("measure_start")
        me = card_or_hotspot.get("measure_end")
        if not isinstance(ms, int) or not isinstance(me, int):
            raise ValueError("dict span requires measure_start/end int")
        piece_id = card_or_hotspot.get("piece_id")
        prov = provenance or ()
    else:
        raise TypeError("card_or_hotspot must be PracticeCard, PracticeHotspot, or dict")

    merged_params = dict(_DEFAULT_PARAMS.get(kind, {}))
    if params:
        merged_params.update(params)

    return DrillSpec(
        drill_id=_drill_id(piece_id, ms, me, kind),  # type: ignore[arg-type]
        kind=kind,  # type: ignore[arg-type]
        measure_start=ms,
        measure_end=me,
        params=merged_params,
        provenance=tuple(str(p) for p in prov),
        piece_id=piece_id,
        created_at=_now_iso(),
    )


def available_drills() -> list[str]:
    return [dt.value for dt in DrillType]


def drill_payload_for_card(card: PracticeCard) -> dict[str, Any]:
    """Convenience: build drill payload for card's current drill_type if set."""
    if card.drill_type is None:
        return {"available": available_drills(), "current": None}
    spec = spec_for(card, card.drill_type)
    return {"available": available_drills(), "current": spec.to_payload()}
