"""Data models for difficulty events.

Each event is a musically meaningful sub-span inside an already-flagged
difficult passage.  Events may overlap.  Confidence is explicit; the layer
may declare uncertainty rather than invent a clean label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from piano_difficulty.difficulty_analysis.dynamics.models import region_to_payload
from piano_difficulty.temporal.windows import ScoreRegion

DIFFICULTY_EVENTS_SCHEMA = "difficulty_events"
DIFFICULTY_EVENTS_SCHEMA_VERSION = "difficulty_events.v1"

# Canonical event type ids — extensible, not exhaustive.
# Labels map to brief examples and to pedagogy taxonomy where possible.
EVENT_TYPE_LABELS: dict[str, str] = {
    "repeated_ascending_pattern": "Repeated ascending right-hand pattern",
    "two_voice_texture": "Two-voice right-hand texture",
    "arpeggiated_arrival": "Large arpeggiated arrival",
    "hand_relocation": "Left-hand octave relocation",
    "dense_two_hand_coordination": "Dense two-hand coordination",
    "wide_span": "Wide simultaneous span",
    "rapid_leaps": "Rapid large leaps",
    "high_density": "High onset density",
    "polyphonic_texture": "Polyphonic / chordal texture",
    "subdivision_mismatch": "Hand timing mismatch",
    "uncertain": "Uncertain — manual review suggested",
}

# Valid difficulty_type ids reuse pedagogy factor_ids + above event types.
# Validation is soft: unknown ids are allowed with diagnostics.


@dataclass(frozen=True, slots=True)
class MetricEvidence:
    """One metric that supports an event."""

    feature_id: str
    window_index: int
    raw_value: float | None = None
    normalized_value: float | None = None
    smoothed_value: float | None = None
    delta_normalized: float | None = None
    contribution_share: float | None = None
    is_peak_support: bool = False
    note: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "feature_id": self.feature_id,
            "window_index": self.window_index,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "smoothed_value": self.smoothed_value,
            "delta_normalized": self.delta_normalized,
            "contribution_share": self.contribution_share,
            "is_peak_support": self.is_peak_support,
            "note": self.note,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> MetricEvidence:
        return cls(
            feature_id=str(data["feature_id"]),
            window_index=int(data["window_index"]),
            raw_value=data.get("raw_value"),
            normalized_value=data.get("normalized_value"),
            smoothed_value=data.get("smoothed_value"),
            delta_normalized=data.get("delta_normalized"),
            contribution_share=data.get("contribution_share"),
            is_peak_support=bool(data.get("is_peak_support", False)),
            note=data.get("note"),
        )


@dataclass(frozen=True, slots=True)
class NoteSummary:
    """Lightweight per-hand summary for a span — used as note_evidence."""

    hand: str | None
    note_count: int
    onset_count: int
    voice_count: int
    pitch_min: int | None
    pitch_max: int | None
    span_semitones: int | None
    mean_leap: float | None = None
    max_leap: int | None = None

    def to_payload(self) -> dict[str, object]:
        return {
            "hand": self.hand,
            "note_count": self.note_count,
            "onset_count": self.onset_count,
            "voice_count": self.voice_count,
            "pitch_min": self.pitch_min,
            "pitch_max": self.pitch_max,
            "span_semitones": self.span_semitones,
            "mean_leap": self.mean_leap,
            "max_leap": self.max_leap,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> NoteSummary:
        return cls(
            hand=data.get("hand"),
            note_count=int(data["note_count"]),
            onset_count=int(data["onset_count"]),
            voice_count=int(data["voice_count"]),
            pitch_min=data.get("pitch_min"),
            pitch_max=data.get("pitch_max"),
            span_semitones=data.get("span_semitones"),
            mean_leap=data.get("mean_leap"),
            max_leap=data.get("max_leap"),
        )


@dataclass(frozen=True, slots=True)
class NoteEvidence:
    """Selective note-level context for a span."""

    start_offset: Fraction | str | None
    end_offset: Fraction | str | None
    measure_start: int | None
    measure_end: int | None
    measure_numbers: tuple[str, ...] = ()
    logical_note_ids: tuple[str, ...] = ()
    written_note_ids: tuple[str, ...] = ()
    hand_summaries: tuple[NoteSummary, ...] = ()
    diagnostics: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        return {
            "start_offset": None if self.start_offset is None else str(self.start_offset),
            "end_offset": None if self.end_offset is None else str(self.end_offset),
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "measure_numbers": list(self.measure_numbers),
            "logical_note_ids": list(self.logical_note_ids),
            "written_note_ids": list(self.written_note_ids),
            "hand_summaries": [s.to_payload() for s in self.hand_summaries],
            "diagnostics": list(self.diagnostics),
            "extra": dict(self.extra),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> NoteEvidence:
        from fractions import Fraction as _F

        def _frac(v: Any) -> Fraction | str | None:
            if v is None:
                return None
            try:
                return _F(str(v))
            except Exception:
                return str(v)

        return cls(
            start_offset=_frac(data.get("start_offset")),
            end_offset=_frac(data.get("end_offset")),
            measure_start=data.get("measure_start"),
            measure_end=data.get("measure_end"),
            measure_numbers=tuple(str(x) for x in data.get("measure_numbers", [])),
            logical_note_ids=tuple(str(x) for x in data.get("logical_note_ids", [])),
            written_note_ids=tuple(str(x) for x in data.get("written_note_ids", [])),
            hand_summaries=tuple(NoteSummary.from_payload(s) for s in data.get("hand_summaries", [])),
            diagnostics=tuple(str(x) for x in data.get("diagnostics", [])),
            extra=dict(data.get("extra", {})),
        )


@dataclass(frozen=True, slots=True)
class DifficultyEvent:
    """One playable challenge inside a flagged passage. May overlap others."""

    event_id: str
    span: ScoreRegion
    difficulty_type: str
    label: str
    confidence: float
    supporting_metric_evidence: tuple[MetricEvidence, ...] = ()
    note_evidence: NoteEvidence | None = None
    uncertainty: bool = False
    uncertainty_reason: str | None = None
    diagnostics: tuple[str, ...] = ()
    window_indices: tuple[int, ...] = ()
    measure_start: int | None = None
    measure_end: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, str) or not self.event_id:
            raise ValueError("event_id must be non-empty str")
        if not isinstance(self.difficulty_type, str) or not self.difficulty_type:
            raise ValueError("difficulty_type must be non-empty str")
        if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be in [0,1]")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema": DIFFICULTY_EVENTS_SCHEMA,
            "schema_version": DIFFICULTY_EVENTS_SCHEMA_VERSION,
            "event_id": self.event_id,
            "span": region_to_payload(self.span),
            "window_indices": list(self.window_indices),
            "measure_start": self.measure_start if self.measure_start is not None else self.span.measure_start,
            "measure_end": self.measure_end if self.measure_end is not None else self.span.measure_end,
            "measure_numbers": list(self.span.measure_numbers),
            "measure_range": (
                f"{self.span.measure_numbers[0]}-{self.span.measure_numbers[-1]}"
                if len(self.span.measure_numbers) >= 2
                else (self.span.measure_numbers[0] if self.span.measure_numbers else "")
            ),
            "label": self.span.label,
            "difficulty_type": self.difficulty_type,
            "difficulty_label": self.label,
            "confidence": float(self.confidence),
            "uncertainty": bool(self.uncertainty),
            "uncertainty_reason": self.uncertainty_reason,
            "supporting_metric_evidence": [e.to_payload() for e in self.supporting_metric_evidence],
            "note_evidence": None if self.note_evidence is None else self.note_evidence.to_payload(),
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> DifficultyEvent:
        # Minimal reconstruction: span from payload
        from piano_difficulty.temporal.windows import ScoreRegion as _SR

        span_data = data.get("span", {})
        # Rebuild ScoreRegion from payload — tolerant to missing fields
        def _frac_or_none(v: Any) -> Fraction | None:
            if v is None:
                return None
            try:
                return Fraction(str(v))
            except Exception:
                return None

        span = _SR(
            score_id=span_data.get("score_id"),
            window_index=int(span_data.get("window_index", data.get("window_indices", [0])[0] if data.get("window_indices") else 0)),
            measure_start=int(span_data.get("measure_start", data.get("measure_start", 0))),
            measure_end=int(span_data.get("measure_end", data.get("measure_end", 0))),
            measure_numbers=tuple(str(x) for x in span_data.get("measure_numbers", [])),
            start_offset=_frac_or_none(span_data.get("start_offset")),
            end_offset=_frac_or_none(span_data.get("end_offset")),
            start_beat=_frac_or_none(span_data.get("start_beat")),
            end_beat=_frac_or_none(span_data.get("end_beat")),
            position=span_data.get("position"),
            hand=span_data.get("hand"),
            label=span_data.get("label"),
        )
        note_ev = data.get("note_evidence")
        return cls(
            event_id=str(data["event_id"]),
            span=span,
            difficulty_type=str(data.get("difficulty_type", "uncertain")),
            label=str(data.get("difficulty_label") or data.get("label") or span.label or ""),
            confidence=float(data.get("confidence", 0.0)),
            supporting_metric_evidence=tuple(MetricEvidence.from_payload(e) for e in data.get("supporting_metric_evidence", [])),
            note_evidence=NoteEvidence.from_payload(note_ev) if isinstance(note_ev, dict) else None,
            uncertainty=bool(data.get("uncertainty", False)),
            uncertainty_reason=data.get("uncertainty_reason"),
            diagnostics=tuple(str(x) for x in data.get("diagnostics", [])),
            window_indices=tuple(int(x) for x in data.get("window_indices", [])),
            measure_start=data.get("measure_start"),
            measure_end=data.get("measure_end"),
        )
