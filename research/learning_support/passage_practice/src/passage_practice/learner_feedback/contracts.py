"""S5.2 LearnerFeedbackSignal contract.

Design refs:
- docs/learner_feedback_policy.md (S-Q005 / D-019)
- docs/pedagogical_input_boundary.md (S4.1)
- semantics/contracts.py pattern (immutable, versioned, deterministic)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from passage_practice.models.diagnostics import Diagnostic

LEARNER_FEEDBACK_SIGNAL_SCHEMA_VERSION = "learner_feedback_signal.v1"
SUPPORTED_VERSIONS = {LEARNER_FEEDBACK_SIGNAL_SCHEMA_VERSION}


class AnswerKind(str, Enum):
    SELECTED_CHOICE = "selected_choice"
    FREE_TEXT = "free_text"
    SKIPPED = "skipped"
    SOMETHING_ELSE = "something_else"


class RetentionScope(str, Enum):
    SESSION = "session"
    EXPLICIT_SAVE = "explicit_save"


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


def _check_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    return value


def _check_id_tuple(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for v in values:
        _check_id(v, f"{field} entry")
    return values


@dataclass(frozen=True, slots=True)
class LearnerFeedbackSignal:
    """One constrained learner answer addressing a passage.

    - feedback_id: stable ID
    - source_passage_id: required passage under discussion (resolvable)
    - prompt_id: S5.3 prompt ID (e.g., hardest_aspect)
    - answer_kind: controlled enum
    - selected_value: choice ID when answer_kind==selected_choice
    - free_text: optional verbatim text (synthetic in tests, preserved verbatim)
    - mapped_hypothesis_ids / mapped_objective_ids: derived via S5.4 mapping,
      not invented from free text
    - retention_scope: session vs explicit_save (D-019)
    - method_id/method_version: provenance
    - diagnostics: e.g., synthetic_data marker
    """

    feedback_id: str
    source_passage_id: str
    prompt_id: str
    answer_kind: AnswerKind
    method_id: str
    method_version: str
    retention_scope: RetentionScope = RetentionScope.SESSION
    selected_value: str | None = None
    free_text: str | None = None
    mapped_hypothesis_ids: tuple[str, ...] = ()
    mapped_objective_ids: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.feedback_id, "feedback_id")
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.prompt_id, "prompt_id")
        if not isinstance(self.answer_kind, AnswerKind):
            raise TypeError(f"answer_kind must be AnswerKind, got {type(self.answer_kind).__name__}")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.retention_scope, RetentionScope):
            raise TypeError(f"retention_scope must be RetentionScope, got {type(self.retention_scope).__name__}")
        if self.answer_kind == AnswerKind.SELECTED_CHOICE:
            if self.selected_value is None:
                raise ValueError("selected_choice requires selected_value")
            _check_id(self.selected_value, "selected_value")
        else:
            if self.selected_value is not None and self.answer_kind != AnswerKind.SOMETHING_ELSE:
                # something_else may carry selected_value="something_else"
                # but generally non-choice kinds should not have selected_value
                # Allow None only for free_text/skipped/something_else with optional selected_value
                pass
            if self.selected_value is not None:
                _check_id(self.selected_value, "selected_value")
        if self.free_text is not None:
            _check_text(self.free_text, "free_text")
        _check_id_tuple(self.mapped_hypothesis_ids, "mapped_hypothesis_ids")
        _check_id_tuple(self.mapped_objective_ids, "mapped_objective_ids")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(f"diagnostics must contain Diagnostic, got {type(d).__name__}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": LEARNER_FEEDBACK_SIGNAL_SCHEMA_VERSION,
            "feedback_id": self.feedback_id,
            "source_passage_id": self.source_passage_id,
            "prompt_id": self.prompt_id,
            "answer_kind": self.answer_kind.value,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "retention_scope": self.retention_scope.value,
        }
        if self.selected_value is not None:
            payload["selected_value"] = self.selected_value
        if self.free_text is not None:
            payload["free_text"] = self.free_text
        if self.mapped_hypothesis_ids:
            payload["mapped_hypothesis_ids"] = list(self.mapped_hypothesis_ids)
        if self.mapped_objective_ids:
            payload["mapped_objective_ids"] = list(self.mapped_objective_ids)
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnerFeedbackSignal":
        if not isinstance(data, dict):
            raise TypeError(f"LearnerFeedbackSignal requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported schema_version {version!r}")
        try:
            feedback_id = data["feedback_id"]
            source_passage_id = data["source_passage_id"]
            prompt_id = data["prompt_id"]
            answer_kind_raw = data["answer_kind"]
            method_id = data["method_id"]
            method_version = data["method_version"]
        except KeyError as exc:
            raise ValueError(f"missing field {exc.args[0]!r}") from exc
        try:
            answer_kind = AnswerKind(answer_kind_raw)
        except ValueError as exc:
            raise ValueError(f"unsupported answer_kind {answer_kind_raw!r}") from exc
        retention_raw = data.get("retention_scope", RetentionScope.SESSION.value)
        try:
            retention = RetentionScope(retention_raw)
        except ValueError as exc:
            raise ValueError(f"unsupported retention_scope {retention_raw!r}") from exc
        mapped_hyps = tuple(data.get("mapped_hypothesis_ids", []))
        mapped_objs = tuple(data.get("mapped_objective_ids", []))
        raw_diags = data.get("diagnostics", [])
        return cls(
            feedback_id=feedback_id,
            source_passage_id=source_passage_id,
            prompt_id=prompt_id,
            answer_kind=answer_kind,
            method_id=method_id,
            method_version=method_version,
            retention_scope=retention,
            selected_value=data.get("selected_value"),
            free_text=data.get("free_text"),
            mapped_hypothesis_ids=mapped_hyps,
            mapped_objective_ids=mapped_objs,
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


__all__ = ["AnswerKind", "LearnerFeedbackSignal", "RetentionScope", "LEARNER_FEEDBACK_SIGNAL_SCHEMA_VERSION"]
