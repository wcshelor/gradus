"""Pedagogical hypothesis contracts — S4.2/S4.3.

Design refs:
- docs/pedagogical_input_boundary.md (S4.1)
- docs/practice_chunk_objects.md: learner-facing claims attach to bounded
  chunks without rewriting score-derived evidence
- semantics/contracts.py (SemanticHypothesis pattern)
- pedagogy/rules.py (PedagogicalRule)

A pedagogical hypothesis is a qualified learner-facing interpretation of
semantic evidence plus optional difficulty context. It never contains
free-text advice (S4.1 rejection) — it contains a hypothesis_type, supporting
semantic IDs, confidence with heuristic method, learner caveats, and candidate
objectives/strategies as controlled IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from passage_practice.models.diagnostics import Diagnostic

from passage_practice.semantics.confidence import check_confidence, parse_method_status

PEDAGOGICAL_HYPOTHESIS_SCHEMA_VERSION = "pedagogical_hypothesis.v1"

SUPPORTED_PEDAGOGICAL_HYPOTHESIS_VERSIONS = {PEDAGOGICAL_HYPOTHESIS_SCHEMA_VERSION}


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_id_list(values: tuple[str, ...], field: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for v in values:
        if not isinstance(v, str) or not v:
            raise ValueError(f"{field} must contain non-empty str, got {v!r}")


@dataclass(frozen=True, slots=True)
class PedagogicalHypothesis:
    """One qualified pedagogical interpretation over a passage.

    - hypothesis_id: stable id (e.g. ``melody_projection.v1:<passage>:000``)
    - hypothesis_type: pedagogical family (e.g. ``pedagogy.melody_projection``)
    - source_passage_id: required passage under analysis
    - supporting_semantic_ids: semantic hypothesis IDs this derives from
    - confidence / confidence_method: bounded score, heuristic only in v1
    - learner_caveats: controlled caveats when learner data absent
    - candidate_objectives / candidate_strategies: controlled IDs
    - missing_evidence: unavailable evidence codes
    - learner_question: controlled question ID that could confirm/reject (optional)
    """

    hypothesis_id: str
    hypothesis_type: str
    source_passage_id: str
    supporting_semantic_ids: tuple[str, ...]
    confidence: float
    confidence_method: str
    method_id: str
    method_version: str
    supporting_observation_ids: tuple[str, ...] = ()
    candidate_objectives: tuple[str, ...] = ()
    candidate_strategies: tuple[str, ...] = ()
    learner_caveats: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    learner_question: str | None = None
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.hypothesis_id, "hypothesis_id")
        _check_id(self.hypothesis_type, "hypothesis_type")
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id_list(self.supporting_semantic_ids, "supporting_semantic_ids")
        if not self.supporting_semantic_ids:
            raise ValueError("supporting_semantic_ids must be non-empty tuple")
        object.__setattr__(self, "confidence", check_confidence(self.confidence))
        object.__setattr__(self, "confidence_method", parse_method_status(self.confidence_method).value)
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        _check_id_list(self.supporting_observation_ids, "supporting_observation_ids")
        _check_id_list(self.candidate_objectives, "candidate_objectives")
        _check_id_list(self.candidate_strategies, "candidate_strategies")
        _check_id_list(self.learner_caveats, "learner_caveats")
        _check_id_list(self.missing_evidence, "missing_evidence")
        if self.learner_question is not None:
            _check_id(self.learner_question, "learner_question")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(f"diagnostics must contain Diagnostic, got {type(d).__name__}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": PEDAGOGICAL_HYPOTHESIS_SCHEMA_VERSION,
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type,
            "source_passage_id": self.source_passage_id,
            "supporting_semantic_ids": list(self.supporting_semantic_ids),
            "confidence": self.confidence,
            "confidence_method": self.confidence_method,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "candidate_objectives": list(self.candidate_objectives),
            "candidate_strategies": list(self.candidate_strategies),
            "learner_caveats": list(self.learner_caveats),
            "missing_evidence": list(self.missing_evidence),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }
        if self.supporting_observation_ids:
            payload["supporting_observation_ids"] = list(self.supporting_observation_ids)
        if self.learner_question is not None:
            payload["learner_question"] = self.learner_question
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PedagogicalHypothesis":
        if not isinstance(data, dict):
            raise TypeError(f"PedagogicalHypothesis requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_PEDAGOGICAL_HYPOTHESIS_VERSIONS:
            raise ValueError(f"unsupported schema_version {version!r}")
        try:
            hypothesis_id = data["hypothesis_id"]
            hypothesis_type = data["hypothesis_type"]
            source_passage_id = data["source_passage_id"]
            supporting_semantic_ids = tuple(data["supporting_semantic_ids"])
            confidence = data["confidence"]
            confidence_method = data["confidence_method"]
            method_id = data["method_id"]
            method_version = data["method_version"]
        except KeyError as exc:
            raise ValueError(f"missing field {exc.args[0]!r}") from exc
        supporting_obs = tuple(data.get("supporting_observation_ids", []))
        objectives = tuple(data.get("candidate_objectives", []))
        strategies = tuple(data.get("candidate_strategies", []))
        caveats = tuple(data.get("learner_caveats", []))
        missing = tuple(data.get("missing_evidence", []))
        learner_question = data.get("learner_question")
        raw_diags = data.get("diagnostics", [])
        return cls(
            hypothesis_id=hypothesis_id,
            hypothesis_type=hypothesis_type,
            source_passage_id=source_passage_id,
            supporting_semantic_ids=supporting_semantic_ids,
            confidence=confidence,
            confidence_method=confidence_method,
            method_id=method_id,
            method_version=method_version,
            supporting_observation_ids=supporting_obs,
            candidate_objectives=objectives,
            candidate_strategies=strategies,
            learner_caveats=caveats,
            missing_evidence=missing,
            learner_question=learner_question,
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


__all__ = ["PEDAGOGICAL_HYPOTHESIS_SCHEMA_VERSION", "PedagogicalHypothesis"]
