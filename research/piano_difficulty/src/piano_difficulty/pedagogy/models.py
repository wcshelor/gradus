"""Gradus domain models — contracts for UI-neutral practice payloads.

All dataclasses are frozen + slots, JSON round-trippable via to_payload/from_payload
with schema version checks. Preserves the directive that FeatureRecords remain
observable facts; these models interpret them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from piano_difficulty.pedagogy.taxonomy import TAXONOMY_VERSION, TAXONOMY, get_factor


GRADUS_SCHEMA = "gradus.practice_payload"
GRADUS_SCHEMA_VERSION = "gradus.practice_payload.v1"

PRACTICE_HOTSPOT_SCHEMA_VERSION = "gradus.practice_hotspot.v1"
DIFFICULTY_FACTOR_SCHEMA_VERSION = "gradus.difficulty_factor.v1"
PRACTICE_CARD_SCHEMA_VERSION = "gradus.practice_card.v1"
PRACTICE_LOG_SCHEMA_VERSION = "gradus.practice_log.v1"
LEARNER_PROFILE_SCHEMA_VERSION = "gradus.learner_profile.v1"
GRADUS_RECOMMENDATION_CONTEXT_SCHEMA_VERSION = "gradus.recommendation_context.v1"
FEEDBACK_EVENT_SCHEMA_VERSION = "gradus.feedback_event.v1"
DRILL_SPEC_SCHEMA_VERSION = "gradus.drill_spec.v1"
EVIDENCE_REF_SCHEMA_VERSION = "gradus.evidence_ref.v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be non-empty str, got {value!r}")
    if len(value) > 256:
        raise ValueError(f"{field_name} too long (>256): {value!r}")
    return value


def _check_opt_id(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _check_id(value, field_name)


def _check_opt_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be non-empty str or None, got {value!r}")
    return value


def _check_iso_time(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be non-empty str")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be ISO-8601, got {value!r}") from exc
    return value


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class HotspotStatus(str, Enum):
    candidate = "candidate"
    accepted = "accepted"
    dismissed = "dismissed"
    adjusted = "adjusted"


class HotspotOrigin(str, Enum):
    auto = "auto"
    manual = "manual"


class LogMode(str, Enum):
    quick = "quick"
    full = "full"


class FeedbackKind(str, Enum):
    accept = "accept"
    dismiss = "dismiss"
    adjust = "adjust"
    hard_section_label = "hard_section_label"


class DrillType(str, Enum):
    isolate_notes = "isolate_notes"
    simplify_texture = "simplify_texture"
    hands_separate = "hands_separate"
    tempo_ladder = "tempo_ladder"
    transition_loop = "transition_loop"
    voicing_focus = "voicing_focus"


# ---------------------------------------------------------------------------
# Small shared types
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Provenance pointer to a feature record or region."""

    evidence_id: str
    kind: str  # e.g. "feature_record", "region", "measure_summary"
    feature_id: str | None = None
    window_index: int | None = None
    note_ids: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": EVIDENCE_REF_SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "kind": self.kind,
            "feature_id": self.feature_id,
            "window_index": self.window_index,
            "note_ids": list(self.note_ids),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> EvidenceRef:
        if not isinstance(data, dict):
            raise TypeError("EvidenceRef requires dict")
        ev_id = data.get("evidence_id")
        kind = data.get("kind")
        if not isinstance(ev_id, str) or not ev_id:
            raise ValueError("EvidenceRef evidence_id must be non-empty str")
        if not isinstance(kind, str) or not kind:
            raise ValueError("EvidenceRef kind must be non-empty str")
        raw_notes = data.get("note_ids", [])
        if not isinstance(raw_notes, list):
            raise ValueError("EvidenceRef note_ids must be list")
        return cls(
            evidence_id=ev_id,
            kind=kind,
            feature_id=data.get("feature_id"),
            window_index=data.get("window_index"),
            note_ids=tuple(str(x) for x in raw_notes),
        )


@dataclass(frozen=True, slots=True)
class DifficultyFactor:
    """One learner-visible musical demand with confidence and evidence links."""

    factor_id: str
    label: str | None = None
    confidence: float | None = None
    evidence_ids: tuple[str, ...] = ()
    source_feature_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.factor_id, "factor_id")
        if self.factor_id not in TAXONOMY:
            # allow extensibility but warn via validation — accept any non-empty id
            # to keep payload extensible; taxonomy lookup is optional
            pass
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)):
                raise TypeError("confidence must be float or None")
            if not 0 <= float(self.confidence) <= 1:
                raise ValueError("confidence must be in [0,1]")
        if not isinstance(self.evidence_ids, tuple):
            raise TypeError("evidence_ids must be tuple")
        if not isinstance(self.source_feature_ids, tuple):
            raise TypeError("source_feature_ids must be tuple")

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": DIFFICULTY_FACTOR_SCHEMA_VERSION,
            "factor_id": self.factor_id,
            "evidence_ids": list(self.evidence_ids),
            "source_feature_ids": list(self.source_feature_ids),
        }
        # resolve label from taxonomy if not provided
        label = self.label
        if label is None and self.factor_id in TAXONOMY:
            label = TAXONOMY[self.factor_id].label
        if label is not None:
            payload["label"] = label
        if self.confidence is not None:
            payload["confidence"] = float(self.confidence)
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> DifficultyFactor:
        if not isinstance(data, dict):
            raise TypeError("DifficultyFactor requires dict")
        fid = data.get("factor_id")
        _check_id(str(fid) if fid is not None else "", "factor_id")  # validate
        raw_ev = data.get("evidence_ids", [])
        raw_src = data.get("source_feature_ids", [])
        if not isinstance(raw_ev, list) or not isinstance(raw_src, list):
            raise ValueError("evidence_ids/source_feature_ids must be list")
        conf = data.get("confidence")
        if conf is not None and not isinstance(conf, (int, float)):
            raise ValueError("confidence must be number or None")
        return cls(
            factor_id=str(fid),
            label=data.get("label"),
            confidence=float(conf) if conf is not None else None,
            evidence_ids=tuple(str(x) for x in raw_ev),
            source_feature_ids=tuple(str(x) for x in raw_src),
        )


# ---------------------------------------------------------------------------
# PracticeHotspot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PracticeHotspot:
    hotspot_id: str
    measure_start: int
    measure_end: int
    status: HotspotStatus = HotspotStatus.candidate
    origin: HotspotOrigin = HotspotOrigin.auto
    piece_id: str | None = None
    source_path: str | None = None
    measure_numbers: tuple[str, ...] = ()
    window_index: int | None = None
    score_position: float | None = None
    confidence: float | None = None
    evidence: tuple[EvidenceRef, ...] = ()
    suggested_factors: tuple[DifficultyFactor, ...] = ()
    created_at: str | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.hotspot_id, "hotspot_id")
        if not isinstance(self.measure_start, int) or not isinstance(self.measure_end, int):
            raise TypeError("measure_start/end must be int")
        if self.measure_start > self.measure_end:
            raise ValueError("measure_start must be <= measure_end")
        if not isinstance(self.status, HotspotStatus):
            raise TypeError("status must be HotspotStatus")
        if not isinstance(self.origin, HotspotOrigin):
            raise TypeError("origin must be HotspotOrigin")
        _check_opt_id(self.piece_id, "piece_id")
        _check_opt_text(self.source_path, "source_path")
        if not isinstance(self.measure_numbers, tuple):
            raise TypeError("measure_numbers must be tuple")
        if self.window_index is not None and not isinstance(self.window_index, int):
            raise TypeError("window_index must be int or None")
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)) or not 0 <= float(self.confidence) <= 1:
                raise ValueError("confidence must be in [0,1] or None")
        if not isinstance(self.evidence, tuple):
            raise TypeError("evidence must be tuple")
        if not isinstance(self.suggested_factors, tuple):
            raise TypeError("suggested_factors must be tuple")
        if self.created_at is not None:
            _check_iso_time(self.created_at, "created_at")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": PRACTICE_HOTSPOT_SCHEMA_VERSION,
            "hotspot_id": self.hotspot_id,
            "piece_id": self.piece_id,
            "source_path": self.source_path,
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "measure_numbers": list(self.measure_numbers),
            "window_index": self.window_index,
            "score_position": self.score_position,
            "confidence": self.confidence,
            "evidence": [e.to_payload() for e in self.evidence],
            "suggested_factors": [f.to_payload() for f in self.suggested_factors],
            "status": self.status.value,
            "origin": self.origin.value,
            "created_at": self.created_at,
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> PracticeHotspot:
        if not isinstance(data, dict):
            raise TypeError("PracticeHotspot requires dict")
        hid = data.get("hotspot_id")
        _check_id(str(hid) if hid else "", "hotspot_id")
        ms = data.get("measure_start")
        me = data.get("measure_end")
        if not isinstance(ms, int) or not isinstance(me, int):
            raise ValueError("measure_start/end must be int")
        status_raw = data.get("status", HotspotStatus.candidate.value)
        origin_raw = data.get("origin", HotspotOrigin.auto.value)
        try:
            status = HotspotStatus(status_raw)
        except ValueError as exc:
            raise ValueError(f"unknown HotspotStatus {status_raw!r}") from exc
        try:
            origin = HotspotOrigin(origin_raw)
        except ValueError as exc:
            raise ValueError(f"unknown HotspotOrigin {origin_raw!r}") from exc
        raw_ev = data.get("evidence", [])
        raw_factors = data.get("suggested_factors", [])
        raw_numbers = data.get("measure_numbers", [])
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_ev, list) or not isinstance(raw_factors, list):
            raise ValueError("evidence/suggested_factors must be list")
        if not isinstance(raw_numbers, list) or not isinstance(raw_diags, list):
            raise ValueError("measure_numbers/diagnostics must be list")
        return cls(
            hotspot_id=str(hid),
            measure_start=ms,
            measure_end=me,
            status=status,
            origin=origin,
            piece_id=data.get("piece_id"),
            source_path=data.get("source_path"),
            measure_numbers=tuple(str(x) for x in raw_numbers),
            window_index=data.get("window_index"),
            score_position=data.get("score_position"),
            confidence=data.get("confidence"),
            evidence=tuple(EvidenceRef.from_payload(e) for e in raw_ev),
            suggested_factors=tuple(DifficultyFactor.from_payload(f) for f in raw_factors),
            created_at=data.get("created_at"),
            diagnostics=tuple(str(x) for x in raw_diags),
        )


# ---------------------------------------------------------------------------
# PracticeCard
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PracticeCard:
    card_id: str
    measure_start: int
    measure_end: int
    factor_tags: tuple[str, ...] = ()
    drill_type: DrillType | None = None
    piece_id: str | None = None
    target_tempo: float | None = None
    attempts: int = 0
    best_controlled_tempo: float | None = None
    confidence: float | None = None
    effort: float | None = None
    accuracy: float | None = None
    helpfulness: dict[str, float] = field(default_factory=dict)
    confidence_trend: tuple[float, ...] = ()
    effort_trend: tuple[float, ...] = ()
    accuracy_trend: tuple[float, ...] = ()
    notes: str | None = None
    estimated_minutes: int = 5
    created_at: str | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.card_id, "card_id")
        if not isinstance(self.measure_start, int) or not isinstance(self.measure_end, int):
            raise TypeError("measure_start/end must be int")
        if self.measure_start > self.measure_end:
            raise ValueError("measure_start must be <= measure_end")
        if not isinstance(self.factor_tags, tuple):
            raise TypeError("factor_tags must be tuple")
        for t in self.factor_tags:
            _check_id(t, "factor_tag")
        if self.drill_type is not None and not isinstance(self.drill_type, DrillType):
            raise TypeError("drill_type must be DrillType or None")
        _check_opt_id(self.piece_id, "piece_id")
        if self.target_tempo is not None and not isinstance(self.target_tempo, (int, float)):
            raise TypeError("target_tempo must be number or None")
        if not isinstance(self.attempts, int) or self.attempts < 0:
            raise ValueError("attempts must be non-negative int")
        if self.best_controlled_tempo is not None and not isinstance(self.best_controlled_tempo, (int, float)):
            raise TypeError("best_controlled_tempo must be number or None")
        for name in ("confidence", "effort", "accuracy"):
            val = getattr(self, name)
            if val is not None and not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be number or None")
            if val is not None and not 0 <= float(val) <= 1:
                raise ValueError(f"{name} must be in [0,1] or None")
        if not isinstance(self.helpfulness, dict):
            raise TypeError("helpfulness must be dict")
        for k, v in self.helpfulness.items():
            if not isinstance(k, str) or not isinstance(v, (int, float)):
                raise ValueError("helpfulness entries must be str->number")
        if not isinstance(self.confidence_trend, tuple) or not isinstance(self.effort_trend, tuple) or not isinstance(self.accuracy_trend, tuple):
            raise TypeError("trends must be tuple")
        _check_opt_text(self.notes, "notes")
        if not isinstance(self.estimated_minutes, int) or not 1 <= self.estimated_minutes <= 30:
            raise ValueError("estimated_minutes must be int in [1,30]")
        if self.created_at is not None:
            _check_iso_time(self.created_at, "created_at")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": PRACTICE_CARD_SCHEMA_VERSION,
            "card_id": self.card_id,
            "piece_id": self.piece_id,
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "factor_tags": list(self.factor_tags),
            "drill_type": self.drill_type.value if self.drill_type else None,
            "target_tempo": self.target_tempo,
            "attempts": self.attempts,
            "best_controlled_tempo": self.best_controlled_tempo,
            "confidence": self.confidence,
            "effort": self.effort,
            "accuracy": self.accuracy,
            "helpfulness": dict(self.helpfulness),
            "confidence_trend": list(self.confidence_trend),
            "effort_trend": list(self.effort_trend),
            "accuracy_trend": list(self.accuracy_trend),
            "notes": self.notes,
            "estimated_minutes": self.estimated_minutes,
            "created_at": self.created_at,
            "diagnostics": list(self.diagnostics),
        }
        return payload

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> PracticeCard:
        if not isinstance(data, dict):
            raise TypeError("PracticeCard requires dict")
        cid = data.get("card_id")
        _check_id(str(cid) if cid else "", "card_id")
        ms = data.get("measure_start")
        me = data.get("measure_end")
        if not isinstance(ms, int) or not isinstance(me, int):
            raise ValueError("measure_start/end must be int")
        raw_tags = data.get("factor_tags", [])
        raw_help = data.get("helpfulness", {})
        raw_ct = data.get("confidence_trend", [])
        raw_et = data.get("effort_trend", [])
        raw_at = data.get("accuracy_trend", [])
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_tags, list) or not isinstance(raw_help, dict):
            raise ValueError("factor_tags must be list and helpfulness dict")
        if not isinstance(raw_ct, list) or not isinstance(raw_et, list) or not isinstance(raw_at, list):
            raise ValueError("trends must be list")
        if not isinstance(raw_diags, list):
            raise ValueError("diagnostics must be list")
        drill_raw = data.get("drill_type")
        drill = None
        if drill_raw is not None:
            try:
                drill = DrillType(drill_raw)
            except ValueError as exc:
                raise ValueError(f"unknown DrillType {drill_raw!r}") from exc
        return cls(
            card_id=str(cid),
            measure_start=ms,
            measure_end=me,
            factor_tags=tuple(str(x) for x in raw_tags),
            drill_type=drill,
            piece_id=data.get("piece_id"),
            target_tempo=data.get("target_tempo"),
            attempts=int(data.get("attempts", 0)),
            best_controlled_tempo=data.get("best_controlled_tempo"),
            confidence=data.get("confidence"),
            effort=data.get("effort"),
            accuracy=data.get("accuracy"),
            helpfulness={str(k): float(v) for k, v in raw_help.items()},
            confidence_trend=tuple(float(x) for x in raw_ct),
            effort_trend=tuple(float(x) for x in raw_et),
            accuracy_trend=tuple(float(x) for x in raw_at),
            notes=data.get("notes"),
            estimated_minutes=int(data.get("estimated_minutes", 5)),
            created_at=data.get("created_at"),
            diagnostics=tuple(str(x) for x in raw_diags),
        )


# ---------------------------------------------------------------------------
# PracticeLog
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PracticeLog:
    log_id: str
    mode: LogMode
    timestamp: str
    passage_id: str | None = None
    card_id: str | None = None
    session_id: str | None = None
    piece_id: str | None = None
    measure_start: int | None = None
    measure_end: int | None = None
    confidence: float | None = None
    effort: float | None = None
    accuracy: float | None = None
    helpfulness: dict[str, float] = field(default_factory=dict)
    free_notes: str | None = None
    controlled_tempo: float | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.log_id, "log_id")
        if not isinstance(self.mode, LogMode):
            raise TypeError("mode must be LogMode")
        _check_iso_time(self.timestamp, "timestamp")
        _check_opt_id(self.passage_id, "passage_id")
        _check_opt_id(self.card_id, "card_id")
        _check_opt_id(self.session_id, "session_id")
        _check_opt_id(self.piece_id, "piece_id")
        if self.measure_start is not None and not isinstance(self.measure_start, int):
            raise TypeError("measure_start must be int or None")
        if self.measure_end is not None and not isinstance(self.measure_end, int):
            raise TypeError("measure_end must be int or None")
        if self.measure_start is not None and self.measure_end is not None and self.measure_start > self.measure_end:
            raise ValueError("measure_start must be <= measure_end")
        for name in ("confidence", "effort", "accuracy"):
            val = getattr(self, name)
            if val is not None and not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be number or None")
            if val is not None and not 0 <= float(val) <= 1:
                raise ValueError(f"{name} must be in [0,1] or None")
        if not isinstance(self.helpfulness, dict):
            raise TypeError("helpfulness must be dict")
        for k, v in self.helpfulness.items():
            if not isinstance(k, str) or not isinstance(v, (int, float)):
                raise ValueError("helpfulness entries must be str->number")
            if not 0 <= float(v) <= 1:
                raise ValueError("helpfulness values must be in [0,1]")
        _check_opt_text(self.free_notes, "free_notes")
        if self.controlled_tempo is not None and not isinstance(self.controlled_tempo, (int, float)):
            raise TypeError("controlled_tempo must be number or None")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        # Quick mode must have at least one signal; full can have more but same minimum
        if self.mode == LogMode.quick:
            if self.confidence is None and self.effort is None and self.accuracy is None and not self.free_notes:
                raise ValueError("quick log requires at least one of confidence/effort/accuracy/free_notes")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": PRACTICE_LOG_SCHEMA_VERSION,
            "log_id": self.log_id,
            "mode": self.mode.value,
            "timestamp": self.timestamp,
            "passage_id": self.passage_id,
            "card_id": self.card_id,
            "session_id": self.session_id,
            "piece_id": self.piece_id,
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "confidence": self.confidence,
            "effort": self.effort,
            "accuracy": self.accuracy,
            "helpfulness": dict(self.helpfulness),
            "free_notes": self.free_notes,
            "controlled_tempo": self.controlled_tempo,
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> PracticeLog:
        if not isinstance(data, dict):
            raise TypeError("PracticeLog requires dict")
        lid = data.get("log_id")
        _check_id(str(lid) if lid else "", "log_id")
        mode_raw = data.get("mode")
        try:
            mode = LogMode(mode_raw)
        except ValueError as exc:
            raise ValueError(f"unknown LogMode {mode_raw!r}") from exc
        ts = data.get("timestamp")
        if not isinstance(ts, str):
            raise ValueError("timestamp must be str")
        raw_help = data.get("helpfulness", {})
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_help, dict) or not isinstance(raw_diags, list):
            raise ValueError("helpfulness must be dict, diagnostics list")
        return cls(
            log_id=str(lid),
            mode=mode,
            timestamp=ts,
            passage_id=data.get("passage_id"),
            card_id=data.get("card_id"),
            session_id=data.get("session_id"),
            piece_id=data.get("piece_id"),
            measure_start=data.get("measure_start"),
            measure_end=data.get("measure_end"),
            confidence=data.get("confidence"),
            effort=data.get("effort"),
            accuracy=data.get("accuracy"),
            helpfulness={str(k): float(v) for k, v in raw_help.items()},
            free_notes=data.get("free_notes"),
            controlled_tempo=data.get("controlled_tempo"),
            diagnostics=tuple(str(x) for x in raw_diags),
        )


# ---------------------------------------------------------------------------
# LearnerProfileSnapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class UncertaintyMeta:
    sample_count: int = 0
    confidence_level: str = "low"  # low|medium|high
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.sample_count, int) or self.sample_count < 0:
            raise ValueError("sample_count must be non-negative int")
        if self.confidence_level not in {"low", "medium", "high"}:
            raise ValueError("confidence_level must be low|medium|high")
        if not isinstance(self.limitations, tuple):
            raise TypeError("limitations must be tuple")

    def to_payload(self) -> dict[str, object]:
        return {
            "sample_count": self.sample_count,
            "confidence_level": self.confidence_level,
            "limitations": list(self.limitations),
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> UncertaintyMeta:
        if not isinstance(data, dict):
            raise TypeError("UncertaintyMeta requires dict")
        return cls(
            sample_count=int(data.get("sample_count", 0)),
            confidence_level=str(data.get("confidence_level", "low")),
            limitations=tuple(str(x) for x in data.get("limitations", [])),
        )


@dataclass(frozen=True, slots=True)
class LearnerProfileSnapshot:
    learner_id: str | None = None
    repertoire_piece_ids: tuple[str, ...] = ()
    accepted_hotspot_ids: tuple[str, ...] = ()
    dismissed_hotspot_ids: tuple[str, ...] = ()
    hard_spot_count: int = 0
    factor_pattern_counts: dict[str, int] = field(default_factory=dict)
    intervention_effectiveness: dict[str, float] = field(default_factory=dict)
    uncertainty: UncertaintyMeta = field(default_factory=UncertaintyMeta)
    created_at: str | None = None

    def __post_init__(self) -> None:
        _check_opt_id(self.learner_id, "learner_id")
        if not isinstance(self.repertoire_piece_ids, tuple):
            raise TypeError("repertoire_piece_ids must be tuple")
        if not isinstance(self.accepted_hotspot_ids, tuple) or not isinstance(self.dismissed_hotspot_ids, tuple):
            raise TypeError("hotspot id tuples must be tuple")
        if not isinstance(self.hard_spot_count, int) or self.hard_spot_count < 0:
            raise ValueError("hard_spot_count must be non-negative int")
        if not isinstance(self.factor_pattern_counts, dict) or not isinstance(self.intervention_effectiveness, dict):
            raise TypeError("pattern/effectiveness must be dict")
        if not isinstance(self.uncertainty, UncertaintyMeta):
            raise TypeError("uncertainty must be UncertaintyMeta")
        if self.created_at is not None:
            _check_iso_time(self.created_at, "created_at")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": LEARNER_PROFILE_SCHEMA_VERSION,
            "learner_id": self.learner_id,
            "repertoire_piece_ids": list(self.repertoire_piece_ids),
            "accepted_hotspot_ids": list(self.accepted_hotspot_ids),
            "dismissed_hotspot_ids": list(self.dismissed_hotspot_ids),
            "hard_spot_count": self.hard_spot_count,
            "factor_pattern_counts": dict(self.factor_pattern_counts),
            "intervention_effectiveness": dict(self.intervention_effectiveness),
            "uncertainty": self.uncertainty.to_payload(),
            "created_at": self.created_at,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> LearnerProfileSnapshot:
        if not isinstance(data, dict):
            raise TypeError("LearnerProfileSnapshot requires dict")
        raw_unc = data.get("uncertainty", {})
        if not isinstance(raw_unc, dict):
            raise ValueError("uncertainty must be dict")
        raw_rep = data.get("repertoire_piece_ids", [])
        raw_acc = data.get("accepted_hotspot_ids", [])
        raw_dis = data.get("dismissed_hotspot_ids", [])
        raw_factors = data.get("factor_pattern_counts", {})
        raw_eff = data.get("intervention_effectiveness", {})
        if not isinstance(raw_rep, list) or not isinstance(raw_acc, list) or not isinstance(raw_dis, list):
            raise ValueError("repertoire/accepted/dismissed must be list")
        if not isinstance(raw_factors, dict) or not isinstance(raw_eff, dict):
            raise ValueError("factor_pattern_counts / intervention_effectiveness must be dict")
        return cls(
            learner_id=data.get("learner_id"),
            repertoire_piece_ids=tuple(str(x) for x in raw_rep),
            accepted_hotspot_ids=tuple(str(x) for x in raw_acc),
            dismissed_hotspot_ids=tuple(str(x) for x in raw_dis),
            hard_spot_count=int(data.get("hard_spot_count", 0)),
            factor_pattern_counts={str(k): int(v) for k, v in raw_factors.items()},
            intervention_effectiveness={str(k): float(v) for k, v in raw_eff.items()},
            uncertainty=UncertaintyMeta.from_payload(raw_unc) if raw_unc else UncertaintyMeta(),
            created_at=data.get("created_at"),
        )


# ---------------------------------------------------------------------------
# GradusRecommendationContext
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GradusRecommendationContext:
    today_input: str | None = None
    today_input_span: dict[str, int | None] | None = None
    piece_logs: tuple[PracticeLog, ...] = ()
    routines_cards: tuple[PracticeCard, ...] = ()
    learner_patterns: LearnerProfileSnapshot | None = None
    cached_analysis: dict[str, Any] | None = None
    fresh_analysis: Any | None = None
    piece_id: str | None = None

    def __post_init__(self) -> None:
        _check_opt_text(self.today_input, "today_input")
        if self.today_input_span is not None and not isinstance(self.today_input_span, dict):
            raise TypeError("today_input_span must be dict or None")
        if not isinstance(self.piece_logs, tuple):
            raise TypeError("piece_logs must be tuple")
        if not isinstance(self.routines_cards, tuple):
            raise TypeError("routines_cards must be tuple")
        if self.learner_patterns is not None and not isinstance(self.learner_patterns, LearnerProfileSnapshot):
            raise TypeError("learner_patterns must be LearnerProfileSnapshot or None")
        if self.cached_analysis is not None and not isinstance(self.cached_analysis, dict):
            raise TypeError("cached_analysis must be dict or None")
        _check_opt_id(self.piece_id, "piece_id")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": GRADUS_RECOMMENDATION_CONTEXT_SCHEMA_VERSION,
            "today_input": self.today_input,
            "today_input_span": self.today_input_span,
            "piece_logs": [log.to_payload() for log in self.piece_logs],
            "routines_cards": [card.to_payload() for card in self.routines_cards],
            "learner_patterns": self.learner_patterns.to_payload() if self.learner_patterns else None,
            "cached_analysis": self.cached_analysis,
            "fresh_analysis": None,  # never serialize live AnalysisResult directly; use payload
            "piece_id": self.piece_id,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> GradusRecommendationContext:
        if not isinstance(data, dict):
            raise TypeError("GradusRecommendationContext requires dict")
        raw_logs = data.get("piece_logs", [])
        raw_cards = data.get("routines_cards", [])
        if not isinstance(raw_logs, list) or not isinstance(raw_cards, list):
            raise ValueError("piece_logs/routines_cards must be list")
        raw_patterns = data.get("learner_patterns")
        return cls(
            today_input=data.get("today_input"),
            today_input_span=data.get("today_input_span"),
            piece_logs=tuple(PracticeLog.from_payload(x) for x in raw_logs),
            routines_cards=tuple(PracticeCard.from_payload(x) for x in raw_cards),
            learner_patterns=LearnerProfileSnapshot.from_payload(raw_patterns) if isinstance(raw_patterns, dict) else None,
            cached_analysis=data.get("cached_analysis"),
            fresh_analysis=None,
            piece_id=data.get("piece_id"),
        )


# ---------------------------------------------------------------------------
# FeedbackEvent
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    event_id: str
    kind: FeedbackKind
    timestamp: str
    hotspot_id: str | None = None
    measure_start: int | None = None
    measure_end: int | None = None
    adjusted_measure_start: int | None = None
    adjusted_measure_end: int | None = None
    selected_factors: tuple[str, ...] = ()
    free_text: str | None = None
    actor: str = "learner"

    def __post_init__(self) -> None:
        _check_id(self.event_id, "event_id")
        if not isinstance(self.kind, FeedbackKind):
            raise TypeError("kind must be FeedbackKind")
        _check_iso_time(self.timestamp, "timestamp")
        _check_opt_id(self.hotspot_id, "hotspot_id")
        if self.measure_start is not None and not isinstance(self.measure_start, int):
            raise TypeError("measure_start must be int or None")
        if self.measure_end is not None and not isinstance(self.measure_end, int):
            raise TypeError("measure_end must be int or None")
        if self.adjusted_measure_start is not None and not isinstance(self.adjusted_measure_start, int):
            raise TypeError("adjusted_measure_start must be int or None")
        if self.adjusted_measure_end is not None and not isinstance(self.adjusted_measure_end, int):
            raise TypeError("adjusted_measure_end must be int or None")
        if not isinstance(self.selected_factors, tuple):
            raise TypeError("selected_factors must be tuple")
        for f in self.selected_factors:
            _check_id(f, "selected_factor")
        _check_opt_text(self.free_text, "free_text")
        if not isinstance(self.actor, str) or not self.actor:
            raise ValueError("actor must be non-empty str")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": FEEDBACK_EVENT_SCHEMA_VERSION,
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "hotspot_id": self.hotspot_id,
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "adjusted_measure_start": self.adjusted_measure_start,
            "adjusted_measure_end": self.adjusted_measure_end,
            "selected_factors": list(self.selected_factors),
            "free_text": self.free_text,
            "actor": self.actor,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> FeedbackEvent:
        if not isinstance(data, dict):
            raise TypeError("FeedbackEvent requires dict")
        eid = data.get("event_id")
        _check_id(str(eid) if eid else "", "event_id")
        kind_raw = data.get("kind")
        try:
            kind = FeedbackKind(kind_raw)
        except ValueError as exc:
            raise ValueError(f"unknown FeedbackKind {kind_raw!r}") from exc
        ts = data.get("timestamp")
        if not isinstance(ts, str):
            raise ValueError("timestamp must be str")
        raw_factors = data.get("selected_factors", [])
        if not isinstance(raw_factors, list):
            raise ValueError("selected_factors must be list")
        return cls(
            event_id=str(eid),
            kind=kind,
            timestamp=ts,
            hotspot_id=data.get("hotspot_id"),
            measure_start=data.get("measure_start"),
            measure_end=data.get("measure_end"),
            adjusted_measure_start=data.get("adjusted_measure_start"),
            adjusted_measure_end=data.get("adjusted_measure_end"),
            selected_factors=tuple(str(x) for x in raw_factors),
            free_text=data.get("free_text"),
            actor=str(data.get("actor", "learner")),
        )


# ---------------------------------------------------------------------------
# DrillSpec
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DrillSpec:
    drill_id: str
    kind: DrillType
    measure_start: int
    measure_end: int
    params: dict[str, object] = field(default_factory=dict)
    provenance: tuple[str, ...] = ()
    piece_id: str | None = None
    created_at: str | None = None

    def __post_init__(self) -> None:
        _check_id(self.drill_id, "drill_id")
        if not isinstance(self.kind, DrillType):
            raise TypeError("kind must be DrillType")
        if not isinstance(self.measure_start, int) or not isinstance(self.measure_end, int):
            raise TypeError("measure_start/end must be int")
        if self.measure_start > self.measure_end:
            raise ValueError("measure_start must be <= measure_end")
        if not isinstance(self.params, dict):
            raise TypeError("params must be dict")
        if not isinstance(self.provenance, tuple):
            raise TypeError("provenance must be tuple")
        _check_opt_id(self.piece_id, "piece_id")
        if self.created_at is not None:
            _check_iso_time(self.created_at, "created_at")

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": DRILL_SPEC_SCHEMA_VERSION,
            "drill_id": self.drill_id,
            "kind": self.kind.value,
            "measure_start": self.measure_start,
            "measure_end": self.measure_end,
            "params": dict(self.params),
            "provenance": list(self.provenance),
            "piece_id": self.piece_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> DrillSpec:
        if not isinstance(data, dict):
            raise TypeError("DrillSpec requires dict")
        did = data.get("drill_id")
        _check_id(str(did) if did else "", "drill_id")
        kind_raw = data.get("kind")
        try:
            kind = DrillType(kind_raw)
        except ValueError as exc:
            raise ValueError(f"unknown DrillType {kind_raw!r}") from exc
        ms = data.get("measure_start")
        me = data.get("measure_end")
        if not isinstance(ms, int) or not isinstance(me, int):
            raise ValueError("measure_start/end must be int")
        raw_params = data.get("params", {})
        raw_prov = data.get("provenance", [])
        if not isinstance(raw_params, dict) or not isinstance(raw_prov, list):
            raise ValueError("params must be dict, provenance list")
        return cls(
            drill_id=str(did),
            kind=kind,
            measure_start=ms,
            measure_end=me,
            params=dict(raw_params),
            provenance=tuple(str(x) for x in raw_prov),
            piece_id=data.get("piece_id"),
            created_at=data.get("created_at"),
        )
