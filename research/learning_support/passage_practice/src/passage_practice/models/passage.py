"""Minimal versioned passage/view containers — T01.4.

Only fields required by WP-02 (exact selection) and WP-03 (derived views) are
included: passage ID, purpose, parent, event references, method metadata, and
omissions. No diagnosis/strategy/transformation speculatively added.

PassagePurpose and ViewType are distinct enums; Passage and View are frozen
and deterministically serializable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .diagnostics import Diagnostic
from .source import SourceRef
from .time import ScorePosition

PASSAGE_SCHEMA_VERSION = "passage.v1"
VIEW_SCHEMA_VERSION = "view.v1"
SUPPORTED_PASSAGE_VERSIONS = {PASSAGE_SCHEMA_VERSION}
SUPPORTED_VIEW_VERSIONS = {VIEW_SCHEMA_VERSION}


class PassagePurpose(str, Enum):
    DETECTION = "detection"
    EVIDENCE = "evidence"
    PATTERN = "pattern"
    PRACTICE = "practice"


class ViewType(str, Enum):
    WRITTEN_EVENT_STREAM = "written_event_stream"
    LOGICAL_ATTACK_STREAM = "logical_attack_stream"
    HAND_STREAM = "hand_stream"
    VOICE_STREAM = "voice_stream"
    ONSET_SLICES = "onset_slices"
    INTERVAL_TRANSITIONS = "interval_transitions"
    HAND_SHAPES = "hand_shapes"
    RHYTHMIC_CELLS = "rhythmic_cells"
    RHYTHM_GRID = "rhythm_grid"
    TEXTURE_GRID = "texture_grid"
    SALIENCE_VIEW = "salience_view"
    HARMONY_VIEW = "harmony_view"


def _validate_id(value: str, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    # keep simple: no whitespace, not too long
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")


@dataclass(frozen=True, slots=True)
class Passage:
    """Minimal passage container for WP-02 selection.

    - passage_id: stable unique ID (e.g., deterministic hash or client-provided)
    - score_id: source score identity (path or hash) — kept as str for now
    - start/end: exact half-open interval via ScorePosition (start < end enforced)
    - purpose: detection/evidence/pattern/practice
    - parent_id: optional parent passage_id for refinement lineage
    - event_refs: selected canonical event IDs (ordered, deterministic)
    - method_id/method_version: producer identity
    - omissions: tuple of strings declaring intentionally omitted info (e.g., "non-target-hand")
    - diagnostics: tuple of Diagnostic
    """

    passage_id: str
    score_id: str
    start: ScorePosition
    end: ScorePosition
    purpose: PassagePurpose
    method_id: str
    method_version: str
    parent_id: str | None = None
    event_refs: tuple[SourceRef, ...] = ()
    omissions: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _validate_id(self.passage_id, "passage_id")
        _validate_id(self.score_id, "score_id")
        if not isinstance(self.start, ScorePosition):
            raise TypeError("Passage start must be ScorePosition")
        if not isinstance(self.end, ScorePosition):
            raise TypeError("Passage end must be ScorePosition")
        if not self.start.quarters < self.end.quarters:
            raise ValueError(f"Passage interval must have start < end, got {self.start.quarters} >= {self.end.quarters}")
        if not isinstance(self.purpose, PassagePurpose):
            raise TypeError(f"Passage purpose must be PassagePurpose, got {type(self.purpose).__name__}")
        _validate_id(self.method_id, "method_id")
        _validate_id(self.method_version, "method_version")
        if self.parent_id is not None:
            _validate_id(self.parent_id, "parent_id")
        if not isinstance(self.event_refs, tuple):
            raise TypeError("Passage event_refs must be tuple")
        for r in self.event_refs:
            if not isinstance(r, SourceRef):
                raise TypeError(f"Passage event_refs must contain SourceRef, got {type(r).__name__}")
        if not isinstance(self.omissions, tuple):
            raise TypeError("Passage omissions must be tuple")
        for o in self.omissions:
            if not isinstance(o, str) or not o:
                raise ValueError(f"Passage omission must be non-empty str, got {o!r}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("Passage diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(f"Passage diagnostics must contain Diagnostic, got {type(d).__name__}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": PASSAGE_SCHEMA_VERSION,
            "passage_id": self.passage_id,
            "score_id": self.score_id,
            "start": self.start.to_dict(),
            "end": self.end.to_dict(),
            "purpose": self.purpose.value,
            "method_id": self.method_id,
            "method_version": self.method_version,
        }
        if self.parent_id is not None:
            payload["parent_id"] = self.parent_id
        if self.event_refs:
            payload["event_refs"] = [r.to_dict() for r in self.event_refs]
        if self.omissions:
            payload["omissions"] = list(self.omissions)
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Passage":
        if not isinstance(data, dict):
            raise TypeError(f"Passage requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_PASSAGE_VERSIONS:
            raise ValueError(f"unsupported Passage schema_version {version!r}; supported: {sorted(SUPPORTED_PASSAGE_VERSIONS)}")
        try:
            passage_id = data["passage_id"]
            score_id = data["score_id"]
            start_data = data["start"]
            end_data = data["end"]
            purpose_raw = data["purpose"]
            method_id = data["method_id"]
            method_version = data["method_version"]
        except KeyError as exc:
            raise ValueError(f"missing Passage field {exc.args[0]!r}") from exc
        try:
            purpose = PassagePurpose(purpose_raw)
        except ValueError as exc:
            raise ValueError(f"unknown PassagePurpose {purpose_raw!r}") from exc
        start = ScorePosition.from_dict(start_data)
        end = ScorePosition.from_dict(end_data)
        parent_id = data.get("parent_id")
        raw_refs = data.get("event_refs", [])
        if not isinstance(raw_refs, list):
            raise ValueError("Passage event_refs must be list")
        event_refs = tuple(SourceRef.from_dict(r) for r in raw_refs)
        raw_omissions = data.get("omissions", [])
        if not isinstance(raw_omissions, list):
            raise ValueError("Passage omissions must be list")
        omissions = tuple(str(o) for o in raw_omissions)
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("Passage diagnostics must be list")
        diagnostics = tuple(Diagnostic.from_dict(d) for d in raw_diags)
        return cls(
            passage_id=str(passage_id),
            score_id=str(score_id),
            start=start,
            end=end,
            purpose=purpose,
            method_id=str(method_id),
            method_version=str(method_version),
            parent_id=str(parent_id) if parent_id is not None else None,
            event_refs=event_refs,
            omissions=omissions,
            diagnostics=diagnostics,
        )


@dataclass(frozen=True, slots=True)
class View:
    """Minimal derived view container for WP-03.

    Mirrors the contract's required fields: view_type, source passage,
    method, included event IDs, ordering/grouping/omissions/diagnostics.
    Confidence is optional and only when inference is involved.
    """

    view_type: ViewType
    source_passage_id: str
    method_id: str
    method_version: str
    included_refs: tuple[SourceRef, ...] = ()
    ordering: str = "onset"
    grouping: str | None = None
    omissions: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.view_type, ViewType):
            raise TypeError(f"View view_type must be ViewType, got {type(self.view_type).__name__}")
        _validate_id(self.source_passage_id, "source_passage_id")
        _validate_id(self.method_id, "method_id")
        _validate_id(self.method_version, "method_version")
        if not isinstance(self.included_refs, tuple):
            raise TypeError("View included_refs must be tuple")
        for r in self.included_refs:
            if not isinstance(r, SourceRef):
                raise TypeError(f"View included_refs must contain SourceRef, got {type(r).__name__}")
        if not isinstance(self.ordering, str) or not self.ordering:
            raise ValueError(f"View ordering must be non-empty str, got {self.ordering!r}")
        if self.grouping is not None and not isinstance(self.grouping, str):
            raise TypeError("View grouping must be str or None")
        if not isinstance(self.omissions, tuple):
            raise TypeError("View omissions must be tuple")
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)):
                raise TypeError("View confidence must be float or None")
            if not 0.0 <= float(self.confidence) <= 1.0:
                raise ValueError(f"View confidence must be in [0,1], got {self.confidence}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": VIEW_SCHEMA_VERSION,
            "view_type": self.view_type.value,
            "source_passage_id": self.source_passage_id,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "ordering": self.ordering,
        }
        if self.included_refs:
            payload["included_refs"] = [r.to_dict() for r in self.included_refs]
        if self.grouping is not None:
            payload["grouping"] = self.grouping
        if self.omissions:
            payload["omissions"] = list(self.omissions)
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        if self.confidence is not None:
            payload["confidence"] = float(self.confidence)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "View":
        if not isinstance(data, dict):
            raise TypeError(f"View requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_VIEW_VERSIONS:
            raise ValueError(f"unsupported View schema_version {version!r}; supported: {sorted(SUPPORTED_VIEW_VERSIONS)}")
        try:
            view_type_raw = data["view_type"]
            source_passage_id = data["source_passage_id"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            ordering = data["ordering"]
        except KeyError as exc:
            raise ValueError(f"missing View field {exc.args[0]!r}") from exc
        try:
            view_type = ViewType(view_type_raw)
        except ValueError as exc:
            raise ValueError(f"unknown ViewType {view_type_raw!r}") from exc
        raw_refs = data.get("included_refs", [])
        included_refs = tuple(SourceRef.from_dict(r) for r in raw_refs)
        grouping = data.get("grouping")
        raw_omissions = data.get("omissions", [])
        omissions = tuple(str(o) for o in raw_omissions)
        raw_diags = data.get("diagnostics", [])
        diagnostics = tuple(Diagnostic.from_dict(d) for d in raw_diags)
        confidence = data.get("confidence")
        return cls(
            view_type=view_type,
            source_passage_id=str(source_passage_id),
            method_id=str(method_id),
            method_version=str(method_version),
            included_refs=included_refs,
            ordering=str(ordering),
            grouping=str(grouping) if grouping is not None else None,
            omissions=omissions,
            diagnostics=diagnostics,
            confidence=float(confidence) if confidence is not None else None,
        )
