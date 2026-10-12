"""Thin normalized representation for notation markings.

Covers dynamics, hairpins, octave shifts, phrase/slur, arpeggiation (rolled chord)
where accessible from ScoreIR. If full MusicXML extraction is unavailable, reports
unsupported status rather than silently ignoring.

This layer is intentionally thin — it exposes what is already parsed, documents gaps,
and propagates markings as chunk evidence (traits, boundary priors, context, payload).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from piano_difficulty.normalize.schema import ScoreIR
from .models import ScoreEvent

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ScoreMarking:
    marking_id: str
    kind: str  # dynamics, wedge_start, wedge_stop, wedge_span, octave_shift, slur, phrase, arpeggiate
    value: str  # e.g., "p", "crescendo", "8va_up", "slur_start"
    start_onset: Fraction
    end_onset: Fraction | None
    staff: int | None
    measure_index: int | None
    confidence: float
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "marking_id": self.marking_id,
            "kind": self.kind,
            "value": self.value,
            "start_onset": str(self.start_onset),
            "end_onset": str(self.end_onset) if self.end_onset is not None else None,
            "staff": self.staff,
            "measure_index": self.measure_index,
            "confidence": self.confidence,
            "payload": dict(self.payload),
        }

MARKING_KINDS = (
    "dynamics",
    "wedge_span",  # hairpin with start..end
    "wedge_start",
    "wedge_stop",
    "octave_shift_span",
    "octave_shift_start",
    "octave_shift_stop",
    "slur",
    "phrase",
    "arpeggiate",
)

# Which kinds are supported vs thin/not yet fully spanned
SUPPORTED_STATUS: dict[str, str] = {
    "dynamics": "supported (DirectionIR.kind dynamics from <dynamics>)",
    "wedge_span": "thin — span reconstructed via wedge number linking; cross-part breaks may truncate",
    "wedge_start": "supported (wedge type crescendo/diminuendo)",
    "wedge_stop": "supported (wedge type stop)",
    "octave_shift_span": "thin — reconstructed via octave-shift number; sounding-vs-written caveat",
    "octave_shift_start": "supported (direction-type octave-shift up/down)",
    "octave_shift_stop": "supported (octave-shift type stop)",
    "slur": "thin — note-level <slur> start/stop captured; phrase vs slur distinction depends on exporter",
    "phrase": "unsupported if exporter conflates phrase and slur; documented as thin",
    "arpeggiate": "supported (notations/arpeggiate on WrittenNoteIR)",
}

def marking_support_status() -> dict[str, str]:
    return dict(SUPPORTED_STATUS)

# ---------------------------------------------------------------------------
# Extraction from ScoreIR
# ---------------------------------------------------------------------------

def extract_markings_from_score(score: ScoreIR) -> list[ScoreMarking]:
    out: list[ScoreMarking] = []
    # Dynamics
    for idx, d in enumerate(score.directions):
        if d.kind == "dynamics":
            out.append(ScoreMarking(
                marking_id=f"mk_dyn_{idx}:{d.direction_id}",
                kind="dynamics",
                value=str(d.value),
                start_onset=d.start,
                end_onset=d.end,
                staff=d.staff,
                measure_index=d.measure_index,
                confidence=0.95,
                payload={"source": "DirectionIR", "direction_id": d.direction_id},
            ))
        elif d.kind == "wedge":
            # value like crescendo, diminuendo, stop
            val = str(d.value).lower()
            if val in ("crescendo", "diminuendo", "crescendo_stop", "diminuendo_stop", "stop"):
                kind = "wedge_start" if val in ("crescendo", "diminuendo") else "wedge_stop"
                # stop may still carry type via extra
                extra_type = ""
                if d.extra and "wedge_type" in d.extra:
                    extra_type = d.extra.get("wedge_type", "")
                    if extra_type:
                        val = extra_type.lower()
                        kind = "wedge_start" if val in ("crescendo", "diminuendo") else "wedge_stop"
                out.append(ScoreMarking(
                    marking_id=f"mk_wedge_{idx}:{d.direction_id}",
                    kind=kind,
                    value=val,
                    start_onset=d.start,
                    end_onset=d.end,
                    staff=d.staff,
                    measure_index=d.measure_index,
                    confidence=0.9,
                    payload={"source": "DirectionIR", "number": d.number, "extra": dict(d.extra or {})},
                ))
        elif d.kind == "octave_shift":
            val = str(d.value)
            # val like "up:8" etc
            kind = "octave_shift_stop" if "stop" in val.lower() else "octave_shift_start"
            out.append(ScoreMarking(
                marking_id=f"mk_oct_{idx}:{d.direction_id}",
                kind=kind,
                value=val,
                start_onset=d.start,
                end_onset=d.end,
                staff=d.staff,
                measure_index=d.measure_index,
                confidence=0.9,
                payload={"source": "DirectionIR", "number": d.number, "extra": dict(d.extra or {})},
            ))
    # Arpeggiate and slur from written_notes / logical_notes
    for idx, n in enumerate(score.written_notes):
        if getattr(n, "arpeggiate", False):
            out.append(ScoreMarking(
                marking_id=f"mk_arp_w_{idx}:{n.note_id}",
                kind="arpeggiate",
                value="rolled_chord",
                start_onset=n.onset,
                end_onset=n.onset + n.duration,
                staff=n.staff,
                measure_index=n.measure_index,
                confidence=0.95,
                payload={"source": "WrittenNoteIR", "note_id": n.note_id},
            ))
        if getattr(n, "has_slur_start", False) or getattr(n, "has_slur_stop", False):
            v = "slur_start" if n.has_slur_start and not n.has_slur_stop else "slur_stop" if n.has_slur_stop and not n.has_slur_start else "slur_mid"
            out.append(ScoreMarking(
                marking_id=f"mk_slur_w_{idx}:{n.note_id}",
                kind="slur",
                value=v,
                start_onset=n.onset,
                end_onset=n.onset + n.duration,
                staff=n.staff,
                measure_index=n.measure_index,
                confidence=0.85,
                payload={"source": "WrittenNoteIR", "has_start": bool(n.has_slur_start), "has_stop": bool(n.has_slur_stop)},
            ))
        # phrase distinct if exporter uses phrase element captured separately
        if getattr(n, "phrase_start", False) or getattr(n, "phrase_stop", False):
            v = "phrase_start" if n.phrase_start else "phrase_stop" if n.phrase_stop else "phrase"
            out.append(ScoreMarking(
                marking_id=f"mk_phrase_w_{idx}:{n.note_id}",
                kind="phrase",
                value=v,
                start_onset=n.onset,
                end_onset=n.onset + n.duration,
                staff=n.staff,
                measure_index=n.measure_index,
                confidence=0.80,
                payload={"source": "WrittenNoteIR"},
            ))
    # Also capture from logical_notes to avoid missing after tie collapse (arpeggiate already propagated)
    for idx, n in enumerate(score.logical_notes):
        # avoid duplicate if already added via written: check if arpeggiate on logical but not already as written marking with same onset/staff
        if getattr(n, "arpeggiate", False):
            # if not already emitted for that onset/staff, add
            exists = any(m.kind == "arpeggiate" and m.start_onset == n.onset and m.staff == n.staff for m in out)
            if not exists:
                out.append(ScoreMarking(
                    marking_id=f"mk_arp_l_{idx}:{n.note_id}",
                    kind="arpeggiate",
                    value="rolled_chord",
                    start_onset=n.onset,
                    end_onset=n.onset + n.duration,
                    staff=n.staff,
                    measure_index=n.measure_index,
                    confidence=0.85,
                    payload={"source": "LogicalNoteIR", "note_id": n.note_id},
                ))
    # Reconstruct wedge spans by number linking (thin)
    spans = _spans_from_wedge_markings(out)
    out.extend(spans)
    oct_spans = _spans_from_octave_markings(out)
    out.extend(oct_spans)
    # sort stable
    out.sort(key=lambda m: (m.start_onset, m.kind, m.value))
    return out

def _spans_from_wedge_markings(marks: list[ScoreMarking]) -> list[ScoreMarking]:
    """Pair wedge_start and wedge_stop by number to create wedge_span."""
    by_number: dict[int | None, list[ScoreMarking]] = {}
    for m in marks:
        if m.kind in ("wedge_start", "wedge_stop"):
            num = m.payload.get("number") if m.payload.get("number") is not None else None
            # need int or None; try to coerce
            try:
                key = int(num) if num is not None else None
            except Exception:
                key = None
            by_number.setdefault(key, []).append(m)
    spans: list[ScoreMarking] = []
    for key, lst in by_number.items():
        # sort by onset
        lst_sorted = sorted(lst, key=lambda x: x.start_onset)
        # pair start->stop
        opens: list[ScoreMarking] = []
        for cur in lst_sorted:
            if cur.kind == "wedge_start":
                opens.append(cur)
            elif cur.kind == "wedge_stop" and opens:
                start = opens.pop(0)
                # Determine type from start value
                v = start.value
                if "crescendo" in v.lower():
                    span_val = "crescendo"
                elif "diminuendo" in v.lower() or "decrescendo" in v.lower():
                    span_val = "decrescendo"
                else:
                    span_val = v
                spans.append(ScoreMarking(
                    marking_id=f"mk_wedge_span_{key or 0}:{start.marking_id}->{cur.marking_id}",
                    kind="wedge_span",
                    value=span_val,
                    start_onset=start.start_onset,
                    end_onset=cur.start_onset,
                    staff=start.staff,
                    measure_index=start.measure_index,
                    confidence=0.88,
                    payload={"wedge_number": key, "start_id": start.marking_id, "stop_id": cur.marking_id, "type": span_val},
                ))
        # remaining opens become unbounded spans with caveat
        for start in opens:
            v = start.value
            spans.append(ScoreMarking(
                marking_id=f"mk_wedge_span_open_{key or 0}:{start.marking_id}",
                kind="wedge_span",
                value=v,
                start_onset=start.start_onset,
                end_onset=None,
                staff=start.staff,
                measure_index=start.measure_index,
                confidence=0.65,
                payload={"wedge_number": key, "start_id": start.marking_id, "open": True, "caveat": "no_stop_found"},
            ))
    return spans

def _spans_from_octave_markings(marks: list[ScoreMarking]) -> list[ScoreMarking]:
    by_number: dict[int | None, list[ScoreMarking]] = {}
    for m in marks:
        if m.kind in ("octave_shift_start", "octave_shift_stop"):
            num = m.payload.get("number")
            try:
                key = int(num) if num is not None else None
            except Exception:
                key = None
            by_number.setdefault(key, []).append(m)
    spans: list[ScoreMarking] = []
    for key, lst in by_number.items():
        lst_sorted = sorted(lst, key=lambda x: x.start_onset)
        opens: list[ScoreMarking] = []
        for cur in lst_sorted:
            if cur.kind == "octave_shift_start":
                opens.append(cur)
            elif cur.kind == "octave_shift_stop" and opens:
                start = opens.pop(0)
                spans.append(ScoreMarking(
                    marking_id=f"mk_oct_span_{key or 0}:{start.marking_id}->{cur.marking_id}",
                    kind="octave_shift_span",
                    value=start.value,
                    start_onset=start.start_onset,
                    end_onset=cur.start_onset,
                    staff=start.staff,
                    measure_index=start.measure_index,
                    confidence=0.88,
                    payload={"octave_number": key, "start_id": start.marking_id, "stop_id": cur.marking_id, "caveat": "sounding_vs_written_pitch"},
                ))
        for start in opens:
            spans.append(ScoreMarking(
                marking_id=f"mk_oct_span_open_{key or 0}:{start.marking_id}",
                kind="octave_shift_span",
                value=start.value,
                start_onset=start.start_onset,
                end_onset=None,
                staff=start.staff,
                measure_index=start.measure_index,
                confidence=0.65,
                payload={"octave_number": key, "start_id": start.marking_id, "open": True, "caveat": "no_stop_found sounding_vs_written"},
            ))
    return spans

# ---------------------------------------------------------------------------
# Helpers to query markings relative to events / chunks
# ---------------------------------------------------------------------------

def extract_markings_from_events(events: list[ScoreEvent]) -> list[ScoreMarking]:
    """Build marking-like objects purely from ScoreEvent flags (thin fallback for synthetic bundles)."""
    out: list[ScoreMarking] = []
    for ev in events:
        if getattr(ev, "is_arpeggiated", False):
            out.append(ScoreMarking(
                marking_id=f"mk_evt_arp:{ev.event_id}",
                kind="arpeggiate",
                value="rolled_chord",
                start_onset=ev.onset,
                end_onset=ev.end,
                staff=ev.staff,
                measure_index=ev.measure_index,
                confidence=0.9,
                payload={"source": "ScoreEvent", "event_id": ev.event_id},
            ))
        if getattr(ev, "has_slur_start", False) or getattr(ev, "has_slur_stop", False):
            v = "slur_start" if ev.has_slur_start and not ev.has_slur_stop else "slur_stop" if ev.has_slur_stop else "slur_mid"
            out.append(ScoreMarking(
                marking_id=f"mk_evt_slur:{ev.event_id}",
                kind="slur",
                value=v,
                start_onset=ev.onset,
                end_onset=ev.end,
                staff=ev.staff,
                measure_index=ev.measure_index,
                confidence=0.85,
                payload={"source": "ScoreEvent"},
            ))
        if getattr(ev, "phrase_start", False) or getattr(ev, "phrase_stop", False):
            v = "phrase_start" if ev.phrase_start else "phrase_stop"
            out.append(ScoreMarking(
                marking_id=f"mk_evt_phrase:{ev.event_id}",
                kind="phrase",
                value=v,
                start_onset=ev.onset,
                end_onset=ev.end,
                staff=ev.staff,
                measure_index=ev.measure_index,
                confidence=0.80,
                payload={"source": "ScoreEvent"},
            ))
        if ev.dynamics:
            # dynamics per event is already captured but treat as marking as well
            out.append(ScoreMarking(
                marking_id=f"mk_evt_dyn:{ev.event_id}",
                kind="dynamics",
                value=str(ev.dynamics),
                start_onset=ev.onset,
                end_onset=ev.end,
                staff=ev.staff,
                measure_index=ev.measure_index,
                confidence=0.75,
                payload={"source": "ScoreEvent.dynamics"},
            ))
    out.sort(key=lambda m: (m.start_onset, m.kind))
    return out

def markings_in_span(markings: list[ScoreMarking], start: Fraction, end: Fraction) -> list[ScoreMarking]:
    return [m for m in markings if m.start_onset >= start and (m.end_onset is None or m.start_onset < end) or (m.start_onset < end and (m.end_onset is None or m.end_onset > start))]

def wedge_span_overlaps(markings: list[ScoreMarking], start: Fraction, end: Fraction) -> list[ScoreMarking]:
    return [m for m in markings if m.kind == "wedge_span" and not (m.end_onset is not None and m.end_onset <= start) and not (m.start_onset >= end)]

def octave_markings_overlaps(markings: list[ScoreMarking], start: Fraction, end: Fraction) -> list[ScoreMarking]:
    return [m for m in markings if m.kind in ("octave_shift_span", "octave_shift_start") and not (m.end_onset is not None and m.end_onset <= start) and not (m.start_onset >= end)]
