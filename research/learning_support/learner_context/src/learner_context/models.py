"""Minimal learner request, journal, and context contracts — LS-03b.

Implements the section-4 records of the three-area plan for LS-01 scenarios
S3–S5. Contracts only: no storage, retrieval, UI, or external processing.

Design refs:
- docs/Task_list_2026-09-05_flexible_piano_learning_support.md, section 4
- research/learning_support/first_slice.md (S3–S5, section 5 outputs)
- research/learning_support/learner_context/README.md (boundary choice)

Key invariants:
- Request intent is separate from persisted history. An unresolved request
  (no region, no investigation reference) is valid, never an invalid Passage.
- Journal text is verbatim and immutable; corrections are new revisions
  linked by `supersedes`. Reports never share a container with score facts.
- Permissions: session-only entries cannot inform future requests; exclusion
  wins over any use flag. Deletion is removal (LS-04 storage behavior).
- Summaries reference source-entry IDs so LS-04 can invalidate them after
  corrections/deletions; interpretation stays tentative until confirmed.
- Every assistance result states its rationale and at least one limitation;
  score evidence (`passage_refs`) and self-reports (`report_refs`) are
  referenced separately. No measured-outcome claims.

Reuses `ScoreInterval` and `Diagnostic` from passage_practice; passage
subjects are referenced by stable ID string only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from passage_practice.models.diagnostics import Diagnostic
from passage_practice.models.time import ScoreInterval

ASSISTANCE_REQUEST_SCHEMA_VERSION = "assistance_request.v1"
JOURNAL_ENTRY_SCHEMA_VERSION = "journal_entry.v1"
CONTEXT_PERMISSION_SCHEMA_VERSION = "context_permission.v1"
CONTEXT_SUMMARY_SCHEMA_VERSION = "context_summary.v1"
ASSISTANCE_RESULT_SCHEMA_VERSION = "assistance_result.v1"

SUPPORTED_REQUEST_VERSIONS = {ASSISTANCE_REQUEST_SCHEMA_VERSION}
SUPPORTED_JOURNAL_VERSIONS = {JOURNAL_ENTRY_SCHEMA_VERSION}
SUPPORTED_PERMISSION_VERSIONS = {CONTEXT_PERMISSION_SCHEMA_VERSION}
SUPPORTED_SUMMARY_VERSIONS = {CONTEXT_SUMMARY_SCHEMA_VERSION}
SUPPORTED_RESULT_VERSIONS = {ASSISTANCE_RESULT_SCHEMA_VERSION}


class RequestIntent(str, Enum):
    UNDERSTAND = "understand"
    PRACTICE_AID = "practice_aid"
    JOURNAL_ONLY = "journal_only"
    UNSPECIFIED = "unspecified"


class ContextScope(str, Enum):
    NONE = "none"
    REFERENCED = "referenced"
    PERMITTED = "permitted"


class EntryScope(str, Enum):
    GENERAL = "general"
    PIECE = "piece"
    REGION = "region"


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_opt_id(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    return _check_id(value, field)


def _check_opt_text(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str or None, got {value!r}")
    return value


def _check_text(value: str, field: str) -> str:
    """Prose fields (reports, rationale, needs): non-empty, no ID length cap."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    return value


def _check_time(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601, got {value!r}") from exc
    return value


def _check_flag(value: bool, field: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field} must be bool, got {value!r}")
    return value


def _check_id_tuple(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for v in values:
        _check_id(v, f"{field} entry")
    return values


def _check_text_tuple(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    """Prose tuples (e.g. limitations): non-empty strings, no ID length cap."""
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for v in values:
        _check_text(v, f"{field} entry")
    return values


def _check_diagnostics(values: tuple[Diagnostic, ...]) -> tuple[Diagnostic, ...]:
    if not isinstance(values, tuple):
        raise TypeError("diagnostics must be tuple")
    for d in values:
        if not isinstance(d, Diagnostic):
            raise TypeError(
                f"diagnostics must contain Diagnostic, got {type(d).__name__}"
            )
    return values


@dataclass(frozen=True, slots=True)
class AssistanceRequest:
    """Current learner intent; distinct from any persisted history."""

    request_id: str
    intent: RequestIntent
    context_scope: ContextScope = ContextScope.NONE
    question: str | None = None
    piece_id: str | None = None
    score_version: str | None = None
    region: ScoreInterval | None = None
    investigation_ref: str | None = None
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.request_id, "request_id")
        if not isinstance(self.intent, RequestIntent):
            raise TypeError(
                f"intent must be RequestIntent, got {type(self.intent).__name__}"
            )
        if not isinstance(self.context_scope, ContextScope):
            raise TypeError(
                "context_scope must be ContextScope, "
                f"got {type(self.context_scope).__name__}"
            )
        _check_opt_text(self.question, "question")
        _check_opt_id(self.piece_id, "piece_id")
        _check_opt_id(self.score_version, "score_version")
        if self.region is not None and not isinstance(self.region, ScoreInterval):
            raise TypeError("region must be ScoreInterval or None")
        _check_opt_id(self.investigation_ref, "investigation_ref")
        _check_diagnostics(self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": ASSISTANCE_REQUEST_SCHEMA_VERSION,
            "request_id": self.request_id,
            "intent": self.intent.value,
            "context_scope": self.context_scope.value,
        }
        if self.question is not None:
            payload["question"] = self.question
        if self.piece_id is not None:
            payload["piece_id"] = self.piece_id
        if self.score_version is not None:
            payload["score_version"] = self.score_version
        if self.region is not None:
            payload["region"] = self.region.to_dict()
        if self.investigation_ref is not None:
            payload["investigation_ref"] = self.investigation_ref
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssistanceRequest":
        if not isinstance(data, dict):
            raise TypeError(
                f"AssistanceRequest requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_REQUEST_VERSIONS:
            raise ValueError(
                f"unsupported AssistanceRequest schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_REQUEST_VERSIONS)}"
            )
        try:
            request_id = data["request_id"]
            intent_raw = data["intent"]
            scope_raw = data.get("context_scope", ContextScope.NONE.value)
        except KeyError as exc:
            raise ValueError(
                f"missing AssistanceRequest field {exc.args[0]!r}"
            ) from exc
        try:
            intent = RequestIntent(intent_raw)
        except ValueError as exc:
            raise ValueError(f"unknown intent {intent_raw!r}") from exc
        try:
            scope = ContextScope(scope_raw)
        except ValueError as exc:
            raise ValueError(f"unknown context_scope {scope_raw!r}") from exc
        region_data = data.get("region")
        region = ScoreInterval.from_dict(region_data) if region_data is not None else None
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("AssistanceRequest diagnostics must be list")
        diagnostics = tuple(Diagnostic.from_dict(d) for d in raw_diags)
        return cls(
            request_id=request_id,
            intent=intent,
            context_scope=scope,
            question=data.get("question"),
            piece_id=data.get("piece_id"),
            score_version=data.get("score_version"),
            region=region,
            investigation_ref=data.get("investigation_ref"),
            diagnostics=diagnostics,
        )


@dataclass(frozen=True, slots=True)
class JournalEntry:
    """One verbatim learner report. Text is immutable; corrections supersede."""

    entry_id: str
    text: str
    author: str
    recorded_at: str
    scope: EntryScope = EntryScope.GENERAL
    piece_id: str | None = None
    region: ScoreInterval | None = None
    practice_note: str | None = None
    tags: tuple[str, ...] = ()
    fields: dict[str, str] | None = None
    revision: int = 1
    supersedes: str | None = None

    def __post_init__(self) -> None:
        _check_id(self.entry_id, "entry_id")
        _check_text(self.text, "text")
        _check_id(self.author, "author")
        object.__setattr__(self, "recorded_at", _check_time(self.recorded_at, "recorded_at"))
        if not isinstance(self.scope, EntryScope):
            raise TypeError(f"scope must be EntryScope, got {type(self.scope).__name__}")
        _check_opt_id(self.piece_id, "piece_id")
        if self.region is not None and not isinstance(self.region, ScoreInterval):
            raise TypeError("region must be ScoreInterval or None")
        if self.scope == EntryScope.REGION and self.region is None:
            raise ValueError("REGION scope requires a region")
        if self.scope != EntryScope.REGION and self.region is not None:
            raise ValueError(f"{self.scope.value} scope must not carry a region")
        _check_opt_text(self.practice_note, "practice_note")
        _check_id_tuple(self.tags, "tags")
        if self.fields is not None:
            if not isinstance(self.fields, dict):
                raise TypeError("fields must be dict[str, str] or None")
            for k, v in self.fields.items():
                _check_id(k, "fields key")
                if not isinstance(v, str):
                    raise TypeError(f"fields[{k!r}] must be str")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int):
            raise TypeError(f"revision must be int, got {self.revision!r}")
        if self.revision < 1:
            raise ValueError(f"revision must be >= 1, got {self.revision}")
        _check_opt_id(self.supersedes, "supersedes")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": JOURNAL_ENTRY_SCHEMA_VERSION,
            "entry_id": self.entry_id,
            "text": self.text,
            "author": self.author,
            "recorded_at": self.recorded_at,
            "scope": self.scope.value,
            "revision": self.revision,
        }
        if self.piece_id is not None:
            payload["piece_id"] = self.piece_id
        if self.region is not None:
            payload["region"] = self.region.to_dict()
        if self.practice_note is not None:
            payload["practice_note"] = self.practice_note
        if self.tags:
            payload["tags"] = list(self.tags)
        if self.fields:
            payload["fields"] = {k: self.fields[k] for k in sorted(self.fields)}
        if self.supersedes is not None:
            payload["supersedes"] = self.supersedes
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JournalEntry":
        if not isinstance(data, dict):
            raise TypeError(f"JournalEntry requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_JOURNAL_VERSIONS:
            raise ValueError(
                f"unsupported JournalEntry schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_JOURNAL_VERSIONS)}"
            )
        try:
            entry_id = data["entry_id"]
            text = data["text"]
            author = data["author"]
            recorded_at = data["recorded_at"]
            scope_raw = data.get("scope", EntryScope.GENERAL.value)
        except KeyError as exc:
            raise ValueError(f"missing JournalEntry field {exc.args[0]!r}") from exc
        try:
            scope = EntryScope(scope_raw)
        except ValueError as exc:
            raise ValueError(f"unknown scope {scope_raw!r}") from exc
        region_data = data.get("region")
        region = ScoreInterval.from_dict(region_data) if region_data is not None else None
        raw_tags = data.get("tags", [])
        if not isinstance(raw_tags, list):
            raise ValueError("JournalEntry tags must be list")
        fields = data.get("fields")
        return cls(
            entry_id=entry_id,
            text=text,
            author=author,
            recorded_at=recorded_at,
            scope=scope,
            piece_id=data.get("piece_id"),
            region=region,
            practice_note=data.get("practice_note"),
            tags=tuple(raw_tags),
            fields=fields,
            revision=data.get("revision", 1),
            supersedes=data.get("supersedes"),
        )


@dataclass(frozen=True, slots=True)
class ContextPermission:
    """How one entry may be used. Exclusion wins; session-only cannot persist."""

    entry_id: str
    saved: bool = False
    use_current: bool = True
    use_future: bool = False
    excluded: bool = False

    def __post_init__(self) -> None:
        _check_id(self.entry_id, "entry_id")
        _check_flag(self.saved, "saved")
        _check_flag(self.use_current, "use_current")
        _check_flag(self.use_future, "use_future")
        _check_flag(self.excluded, "excluded")
        if self.excluded and (self.use_current or self.use_future):
            raise ValueError("excluded entries must not allow current or future use")
        if self.use_future and not self.saved:
            raise ValueError("session-only entries cannot inform future requests")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTEXT_PERMISSION_SCHEMA_VERSION,
            "entry_id": self.entry_id,
            "saved": self.saved,
            "use_current": self.use_current,
            "use_future": self.use_future,
            "excluded": self.excluded,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextPermission":
        if not isinstance(data, dict):
            raise TypeError(
                f"ContextPermission requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_PERMISSION_VERSIONS:
            raise ValueError(
                f"unsupported ContextPermission schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_PERMISSION_VERSIONS)}"
            )
        try:
            entry_id = data["entry_id"]
        except KeyError as exc:
            raise ValueError(
                f"missing ContextPermission field {exc.args[0]!r}"
            ) from exc
        return cls(
            entry_id=entry_id,
            saved=data.get("saved", False),
            use_current=data.get("use_current", True),
            use_future=data.get("use_future", False),
            excluded=data.get("excluded", False),
        )


@dataclass(frozen=True, slots=True)
class ContextSummary:
    """Tentative interpretation over named source entries. Confirm to trust."""

    summary_id: str
    source_entry_ids: tuple[str, ...]
    method_id: str
    method_version: str
    created_at: str
    interpretation: str
    confirmed: bool = False

    def __post_init__(self) -> None:
        _check_id(self.summary_id, "summary_id")
        if not isinstance(self.source_entry_ids, tuple) or not self.source_entry_ids:
            raise ValueError("source_entry_ids must be a non-empty tuple")
        _check_id_tuple(self.source_entry_ids, "source_entry_ids")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        object.__setattr__(self, "created_at", _check_time(self.created_at, "created_at"))
        _check_text(self.interpretation, "interpretation")
        _check_flag(self.confirmed, "confirmed")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTEXT_SUMMARY_SCHEMA_VERSION,
            "summary_id": self.summary_id,
            "source_entry_ids": list(self.source_entry_ids),
            "method_id": self.method_id,
            "method_version": self.method_version,
            "created_at": self.created_at,
            "interpretation": self.interpretation,
            "confirmed": self.confirmed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextSummary":
        if not isinstance(data, dict):
            raise TypeError(f"ContextSummary requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_SUMMARY_VERSIONS:
            raise ValueError(
                f"unsupported ContextSummary schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SUMMARY_VERSIONS)}"
            )
        try:
            summary_id = data["summary_id"]
            source_entry_ids = data["source_entry_ids"]
            method_id = data["method_id"]
            method_version = data["method_version"]
            created_at = data["created_at"]
            interpretation = data["interpretation"]
        except KeyError as exc:
            raise ValueError(
                f"missing ContextSummary field {exc.args[0]!r}"
            ) from exc
        if not isinstance(source_entry_ids, list):
            raise ValueError("ContextSummary source_entry_ids must be list")
        return cls(
            summary_id=summary_id,
            source_entry_ids=tuple(source_entry_ids),
            method_id=method_id,
            method_version=method_version,
            created_at=created_at,
            interpretation=interpretation,
            confirmed=data.get("confirmed", False),
        )


@dataclass(frozen=True, slots=True)
class AssistanceResult:
    """Traceable outcome of one request. Evidence and reports stay separate."""

    result_id: str
    request_ref: str
    need: str
    rationale: str
    limitations: tuple[str, ...]
    method_id: str
    method_version: str
    passage_refs: tuple[str, ...] = ()
    report_refs: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    suggestion: str | None = None
    objective: str | None = None
    learner_response: str | None = None
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.result_id, "result_id")
        _check_id(self.request_ref, "request_ref")
        _check_text(self.need, "need")
        _check_text(self.rationale, "rationale")
        if not isinstance(self.limitations, tuple) or not self.limitations:
            raise ValueError("limitations must be a non-empty tuple")
        _check_text_tuple(self.limitations, "limitations")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        _check_id_tuple(self.passage_refs, "passage_refs")
        _check_id_tuple(self.report_refs, "report_refs")
        _check_id_tuple(self.observation_refs, "observation_refs")
        _check_opt_text(self.suggestion, "suggestion")
        _check_opt_text(self.objective, "objective")
        _check_opt_text(self.learner_response, "learner_response")
        _check_diagnostics(self.diagnostics)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": ASSISTANCE_RESULT_SCHEMA_VERSION,
            "result_id": self.result_id,
            "request_ref": self.request_ref,
            "need": self.need,
            "rationale": self.rationale,
            "limitations": list(self.limitations),
            "method_id": self.method_id,
            "method_version": self.method_version,
        }
        if self.passage_refs:
            payload["passage_refs"] = list(self.passage_refs)
        if self.report_refs:
            payload["report_refs"] = list(self.report_refs)
        if self.observation_refs:
            payload["observation_refs"] = list(self.observation_refs)
        if self.suggestion is not None:
            payload["suggestion"] = self.suggestion
        if self.objective is not None:
            payload["objective"] = self.objective
        if self.learner_response is not None:
            payload["learner_response"] = self.learner_response
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssistanceResult":
        if not isinstance(data, dict):
            raise TypeError(
                f"AssistanceResult requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_RESULT_VERSIONS:
            raise ValueError(
                f"unsupported AssistanceResult schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_RESULT_VERSIONS)}"
            )
        try:
            result_id = data["result_id"]
            request_ref = data["request_ref"]
            need = data["need"]
            rationale = data["rationale"]
            limitations = data["limitations"]
            method_id = data["method_id"]
            method_version = data["method_version"]
        except KeyError as exc:
            raise ValueError(
                f"missing AssistanceResult field {exc.args[0]!r}"
            ) from exc
        if not isinstance(limitations, list):
            raise ValueError("AssistanceResult limitations must be list")

        def _ids(key: str) -> tuple[str, ...]:
            raw = data.get(key, [])
            if not isinstance(raw, list):
                raise ValueError(f"AssistanceResult {key} must be list")
            return tuple(raw)

        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("AssistanceResult diagnostics must be list")
        diagnostics = tuple(Diagnostic.from_dict(d) for d in raw_diags)
        return cls(
            result_id=result_id,
            request_ref=request_ref,
            need=need,
            rationale=rationale,
            limitations=tuple(limitations),
            method_id=method_id,
            method_version=method_version,
            passage_refs=_ids("passage_refs"),
            report_refs=_ids("report_refs"),
            observation_refs=_ids("observation_refs"),
            suggestion=data.get("suggestion"),
            objective=data.get("objective"),
            learner_response=data.get("learner_response"),
            diagnostics=diagnostics,
        )
