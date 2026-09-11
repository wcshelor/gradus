"""S7.2 annotation record contract.

Design refs:
- docs/annotation_schema.md (S-Q006 / D-020)
- semantics/contracts.py pattern (immutable, versioned, deterministic)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from passage_practice.models.diagnostics import Diagnostic
from passage_practice.models.source import SourceRef

ANNOTATION_SCHEMA_VERSION = "annotation.v1"
SUPPORTED_VERSIONS = {ANNOTATION_SCHEMA_VERSION}

# Controlled vocabularies per label family (from docs/annotation_schema.md)
FAMILY_VOCABULARIES: dict[str, set[str]] = {
    "melody": {"top_voice", "left_hand", "inner_voice", "hidden", "none"},
    "bass": {"anchor", "walking", "pedal", "melodic", "none"},
    "accompaniment": {"broken_chord", "alberti", "block", "arpeggiated", "ostinato", "none"},
    "texture": {"monophonic", "homophonic_block", "melody_plus_accompaniment", "arpeggiated", "polyphonic"},
    "phrase": {"boundary", "continuation", "ambiguous"},
    "harmony": {"local_key_C", "local_key_G", "cadence", "no_cadence", "ambiguous"},
    "difficulty_reason": {"leap", "rhythm", "reading", "coordination", "harmony", "none"},
    "learner_issue": {"melody_hidden", "jumps_hard", "hands_together", "reading_hard", "none"},
    "advice": {"simplify_accompaniment", "blocked_bass", "hands_separate", "harder_chunking"},
}


class LabelFamily(str, Enum):
    MELODY = "melody"
    BASS = "bass"
    ACCOMPANIMENT = "accompaniment"
    TEXTURE = "texture"
    PHRASE = "phrase"
    HARMONY = "harmony"
    DIFFICULTY_REASON = "difficulty_reason"
    LEARNER_ISSUE = "learner_issue"
    ADVICE = "advice"


class AnnotatorRole(str, Enum):
    TEACHER = "teacher"
    RESEARCHER = "researcher"
    SYNTHETIC = "synthetic"


class ReviewState(str, Enum):
    UNREVIEWED = "unreviewed"
    REVIEWED = "reviewed"
    DISPUTED = "disputed"


class PrivacyStatus(str, Enum):
    SYNTHETIC = "synthetic"
    ANONYMIZED = "anonymized"


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_confidence(value: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"confidence must be float, got {value!r}")
    fv = float(value)
    if not 0.0 <= fv <= 1.0:
        raise ValueError(f"confidence must be in [0,1], got {fv}")
    return fv


@dataclass(frozen=True, slots=True)
class AnnotationRecord:
    """One human (or synthetic) label for a passage.

    - annotation_id: stable ID
    - source_passage_id: Passage.passage_id
    - label_family: controlled enum
    - label_value: must be in family's vocabulary
    - annotator_role: teacher/researcher/synthetic
    - confidence: bounded [0,1]
    - provenance: synthetic/human
    - review_state: unreviewed/reviewed/disputed
    - privacy_status: synthetic/anonymized (real data blocked)
    - source_refs: optional resolvable refs
    - diagnostics: e.g., synthetic_data
    """

    annotation_id: str
    source_passage_id: str
    label_family: LabelFamily
    label_value: str
    annotator_role: AnnotatorRole
    confidence: float
    provenance: str
    review_state: ReviewState
    privacy_status: PrivacyStatus
    source_refs: tuple[SourceRef, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = ANNOTATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_id(self.annotation_id, "annotation_id")
        _check_id(self.source_passage_id, "source_passage_id")
        if not isinstance(self.label_family, LabelFamily):
            raise TypeError(f"label_family must be LabelFamily, got {type(self.label_family).__name__}")
        vocab = FAMILY_VOCABULARIES.get(self.label_family.value)
        if vocab is None:
            raise ValueError(f"unknown label_family {self.label_family.value!r}")
        if self.label_value not in vocab:
            raise ValueError(f"label_value {self.label_value!r} not in vocabulary for {self.label_family.value!r}: {sorted(vocab)}")
        if not isinstance(self.annotator_role, AnnotatorRole):
            raise TypeError(f"annotator_role must be AnnotatorRole, got {type(self.annotator_role).__name__}")
        object.__setattr__(self, "confidence", _check_confidence(self.confidence))
        if self.provenance not in ("synthetic", "human"):
            raise ValueError(f"provenance must be 'synthetic' or 'human', got {self.provenance!r}")
        if not isinstance(self.review_state, ReviewState):
            raise TypeError(f"review_state must be ReviewState, got {type(self.review_state).__name__}")
        if not isinstance(self.privacy_status, PrivacyStatus):
            raise TypeError(f"privacy_status must be PrivacyStatus, got {type(self.privacy_status).__name__}")
        # Synthetic-only policy: committed synthetic fixtures must be synthetic
        # This is enforced at test level, not as hard contract, to allow human role for future real workflow
        if not isinstance(self.source_refs, tuple):
            raise TypeError("source_refs must be tuple")
        for r in self.source_refs:
            if not isinstance(r, SourceRef):
                raise TypeError(f"source_refs must contain SourceRef, got {type(r).__name__}")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(f"diagnostics must contain Diagnostic, got {type(d).__name__}")
        if self.schema_version != ANNOTATION_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {ANNOTATION_SCHEMA_VERSION!r}, got {self.schema_version!r}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "annotation_id": self.annotation_id,
            "source_passage_id": self.source_passage_id,
            "label_family": self.label_family.value,
            "label_value": self.label_value,
            "annotator_role": self.annotator_role.value,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "review_state": self.review_state.value,
            "privacy_status": self.privacy_status.value,
        }
        if self.source_refs:
            payload["source_refs"] = [r.to_dict() for r in self.source_refs]
        if self.diagnostics:
            payload["diagnostics"] = [d.to_dict() for d in self.diagnostics]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnnotationRecord":
        if not isinstance(data, dict):
            raise TypeError(f"AnnotationRecord requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported schema_version {version!r}")
        try:
            annotation_id = data["annotation_id"]
            source_passage_id = data["source_passage_id"]
            label_family_raw = data["label_family"]
            label_value = data["label_value"]
            annotator_role_raw = data["annotator_role"]
            confidence = data["confidence"]
            provenance = data["provenance"]
            review_state_raw = data["review_state"]
            privacy_status_raw = data["privacy_status"]
        except KeyError as exc:
            raise ValueError(f"missing AnnotationRecord field {exc.args[0]!r}") from exc
        try:
            label_family = LabelFamily(label_family_raw)
        except ValueError as exc:
            raise ValueError(f"unknown label_family {label_family_raw!r}") from exc
        try:
            annotator_role = AnnotatorRole(annotator_role_raw)
        except ValueError as exc:
            raise ValueError(f"unknown annotator_role {annotator_role_raw!r}") from exc
        try:
            review_state = ReviewState(review_state_raw)
        except ValueError as exc:
            raise ValueError(f"unknown review_state {review_state_raw!r}") from exc
        try:
            privacy_status = PrivacyStatus(privacy_status_raw)
        except ValueError as exc:
            raise ValueError(f"unknown privacy_status {privacy_status_raw!r}") from exc
        raw_refs = data.get("source_refs", [])
        if not isinstance(raw_refs, list):
            raise ValueError("source_refs must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("diagnostics must be list")
        return cls(
            annotation_id=annotation_id,
            source_passage_id=source_passage_id,
            label_family=label_family,
            label_value=label_value,
            annotator_role=annotator_role,
            confidence=confidence,
            provenance=provenance,
            review_state=review_state,
            privacy_status=privacy_status,
            source_refs=tuple(SourceRef.from_dict(r) for r in raw_refs),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


__all__ = ["AnnotationRecord", "ANNOTATION_SCHEMA_VERSION", "AnnotatorRole", "LabelFamily", "PrivacyStatus", "ReviewState", "FAMILY_VOCABULARIES"]
