"""S8.1 passage-level pedagogical corpus schema.

Separates score facts, difficulty context, semantic hypotheses, learner
feedback, human explanation, generated explanation, exercise candidate, and
review status. Synthetic-only for thesis phase.

Design refs:
- docs/practice_chunk_objects.md (chunk-centered evidence and explanations)
- semantic_music_extraction_tasks.md S8.1 (round-trip with synthetic data)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from passage_practice.models.diagnostics import Diagnostic

CORPUS_SCHEMA_VERSION = "pedagogical_corpus_record.v1"
SUPPORTED_VERSIONS = {CORPUS_SCHEMA_VERSION}


class CorpusReviewState(str, Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    APPROVED = "approved"


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_id_tuple(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for v in values:
        if not isinstance(v, str) or not v:
            raise ValueError(f"{field} must contain non-empty str, got {v!r}")
        if len(v) > 128:
            raise ValueError(f"{field} too long (>128): {v!r}")
    return values


@dataclass(frozen=True, slots=True)
class PedagogicalCorpusRecord:
    """One passage-level record for pedagogical corpus work.

    Fields are separated to keep score facts, system hypotheses, human
    comments, learner comments, and generated text distinct:

    - ``record_id``: stable synthetic ID
    - ``source_passage_id``: ``Passage.passage_id``
    - ``score_facts_ref``: score identity (e.g., fixture name or score_id)
    - ``difficulty_context_id``: optional difficulty context reference (may be None)
    - ``semantic_bundle_id``: ``SemanticBundle.bundle_id``
    - ``annotation_ids``: human label IDs (AnnotationRecord.annotation_id)
    - ``learner_feedback_ids``: learner signal IDs
    - ``human_explanation``: teacher-authored text (synthetic for tests)
    - ``generated_explanation``: system-generated text derived from hypotheses
    - ``exercise_candidate_ids``: exercise or transformation IDs
    - ``review_state``: draft/reviewed/approved
    - ``provenance``: synthetic/human
    - ``privacy_status``: synthetic/anonymized (real data blocked)
    - ``diagnostics``: e.g., synthetic_data
    """

    record_id: str
    source_passage_id: str
    score_facts_ref: str
    semantic_bundle_id: str
    annotation_ids: tuple[str, ...] = ()
    learner_feedback_ids: tuple[str, ...] = ()
    difficulty_context_id: str | None = None
    human_explanation: str | None = None
    generated_explanation: str | None = None
    exercise_candidate_ids: tuple[str, ...] = ()
    review_state: CorpusReviewState = CorpusReviewState.DRAFT
    provenance: str = "synthetic"
    privacy_status: str = "synthetic"
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = CORPUS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_id(self.record_id, "record_id")
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.score_facts_ref, "score_facts_ref")
        _check_id(self.semantic_bundle_id, "semantic_bundle_id")
        _check_id_tuple(self.annotation_ids, "annotation_ids")
        _check_id_tuple(self.learner_feedback_ids, "learner_feedback_ids")
        _check_id_tuple(self.exercise_candidate_ids, "exercise_candidate_ids")
        if self.difficulty_context_id is not None:
            _check_id(self.difficulty_context_id, "difficulty_context_id")
        if self.human_explanation is not None and not isinstance(self.human_explanation, str):
            raise TypeError("human_explanation must be str or None")
        if self.generated_explanation is not None and not isinstance(self.generated_explanation, str):
            raise TypeError("generated_explanation must be str or None")
        if not isinstance(self.review_state, CorpusReviewState):
            raise TypeError(f"review_state must be CorpusReviewState, got {type(self.review_state).__name__}")
        if self.provenance not in ("synthetic", "human"):
            raise ValueError(f"provenance must be synthetic/human, got {self.provenance!r}")
        if self.privacy_status not in ("synthetic", "anonymized"):
            raise ValueError(f"privacy_status must be synthetic/anonymized, got {self.privacy_status!r}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(f"diagnostics must contain Diagnostic, got {type(d).__name__}")
        if self.schema_version != CORPUS_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {CORPUS_SCHEMA_VERSION!r}, got {self.schema_version!r}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "source_passage_id": self.source_passage_id,
            "score_facts_ref": self.score_facts_ref,
            "semantic_bundle_id": self.semantic_bundle_id,
            "review_state": self.review_state.value,
            "provenance": self.provenance,
            "privacy_status": self.privacy_status,
        }
        if self.annotation_ids:
            payload["annotation_ids"] = list(self.annotation_ids)
        if self.learner_feedback_ids:
            payload["learner_feedback_ids"] = list(self.learner_feedback_ids)
        if self.difficulty_context_id is not None:
            payload["difficulty_context_id"] = self.difficulty_context_id
        if self.human_explanation is not None:
            payload["human_explanation"] = self.human_explanation
        if self.generated_explanation is not None:
            payload["generated_explanation"] = self.generated_explanation
        if self.exercise_candidate_ids:
            payload["exercise_candidate_ids"] = list(self.exercise_candidate_ids)
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PedagogicalCorpusRecord":
        if not isinstance(data, dict):
            raise TypeError(f"PedagogicalCorpusRecord requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported schema_version {version!r}")
        try:
            record_id = data["record_id"]
            source_passage_id = data["source_passage_id"]
            score_facts_ref = data["score_facts_ref"]
            semantic_bundle_id = data["semantic_bundle_id"]
            review_state_raw = data["review_state"]
            provenance = data["provenance"]
            privacy_status = data["privacy_status"]
        except KeyError as exc:
            raise ValueError(f"missing PedagogicalCorpusRecord field {exc.args[0]!r}") from exc
        try:
            review_state = CorpusReviewState(review_state_raw)
        except ValueError as exc:
            raise ValueError(f"unknown review_state {review_state_raw!r}") from exc
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("diagnostics must be list")
        return cls(
            record_id=str(record_id),
            source_passage_id=str(source_passage_id),
            score_facts_ref=str(score_facts_ref),
            semantic_bundle_id=str(semantic_bundle_id),
            annotation_ids=tuple(str(v) for v in data.get("annotation_ids", [])),
            learner_feedback_ids=tuple(str(v) for v in data.get("learner_feedback_ids", [])),
            difficulty_context_id=str(data["difficulty_context_id"]) if "difficulty_context_id" in data else None,
            human_explanation=str(data["human_explanation"]) if "human_explanation" in data else None,
            generated_explanation=str(data["generated_explanation"]) if "generated_explanation" in data else None,
            exercise_candidate_ids=tuple(str(v) for v in data.get("exercise_candidate_ids", [])),
            review_state=review_state,
            provenance=str(provenance),
            privacy_status=str(privacy_status),
            diagnostics=tuple(__import__("passage_practice.models.diagnostics", fromlist=["Diagnostic"]).Diagnostic.from_dict(d) for d in raw_diags),
        )


__all__ = ["PedagogicalCorpusRecord", "CorpusReviewState", "CORPUS_SCHEMA_VERSION"]
