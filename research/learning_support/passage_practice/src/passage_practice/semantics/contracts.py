"""Minimal semantic-hypothesis contracts — S1.2/S1.3 (D-015).

`SemanticHypothesis` is independent from `PatternMatch` (D-015, S-Q001):
pattern matches are cited as evidence through `supporting_pattern_ids`
(opaque ID strings), never subclassed or embedded. `SemanticBundle` groups
the complete semantic analysis for one passage and preserves contradictory
hypotheses; consumers rank and filter, producers never hide uncertainty by
returning only one winner.

Design refs:
- docs/practice_chunk_objects.md: semantic hypotheses attach richer
  interpretations to bounded chunks when evidence supports them
- docs/decisions.md: D-015 (S-Q001 independence decision)
- docs/contracts.md: versioning and contract-test policy
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from passage_practice.models.diagnostics import Diagnostic
from passage_practice.models.source import SourceRef
from passage_practice.models.time import ScoreInterval

from .confidence import check_confidence, parse_method_status

SEMANTIC_HYPOTHESIS_SCHEMA_VERSION = "semantic_hypothesis.v1"
SEMANTIC_BUNDLE_SCHEMA_VERSION = "semantic_bundle.v1"

SUPPORTED_SEMANTIC_HYPOTHESIS_VERSIONS = {SEMANTIC_HYPOTHESIS_SCHEMA_VERSION}
SUPPORTED_SEMANTIC_BUNDLE_VERSIONS = {SEMANTIC_BUNDLE_SCHEMA_VERSION}

# Conventional hypothesis-type families (plan vocabulary). The contract does
# not enforce them: a detector for a new family must not break this schema.
# `confidence_method` vocabulary is the S-Q003 set enforced by
# `semantics.confidence.parse_method_status`; bands derive from `confidence`
# via `semantics.confidence.band_for`.
HYPOTHESIS_TYPE_FAMILIES = (
    "role.",
    "texture.",
    "rhythm.",
    "phrase.",
    "harmony.",
    "motor_proxy.",
)


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_id_list(values: tuple[str, ...], field: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple")
    for value in values:
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"{field} must contain non-empty str, got {value!r}"
            )


def _check_confidence(value: float) -> float:
    """Bounded-score validation with a single source of truth (S1.5)."""
    return check_confidence(value)


@dataclass(frozen=True, slots=True)
class SemanticHypothesis:
    """One evidence-backed musical interpretation over a passage.

    - source_passage_id: required passage under analysis (resolvable context).
    - covered_region: exact half-open interval the claim spans.
    - covered_event_ids: non-empty source events behind the claim. An
      inference about no events carries no source provenance, so emptiness
      is rejected; region-level claims cite the events in the region.
    - confidence: bounded [0, 1] ranking score, not a calibrated probability
      (calibration status declared in `confidence_method`, whose vocabulary
      is the S-Q003 set enforced via `semantics.confidence`).
    - supporting_observation_ids / supporting_pattern_ids: opaque ID strings
      into view/observation/bundle or pattern-registry payloads. Pattern IDs
      stay unvalidated until the pattern registry publishes resolvable IDs
      (D-015); missing evidence is recorded, never fabricated.
    - Staff, encoded voice, inferred hand, and inferred musical role stay
      separate: role claims live in `hypothesis_type` (e.g. `role.melody`)
      and must not smuggle hand/voice identity.
    """

    hypothesis_id: str
    hypothesis_type: str
    source_passage_id: str
    covered_region: ScoreInterval
    covered_event_ids: tuple[SourceRef, ...]
    confidence: float
    confidence_method: str
    method_id: str
    method_version: str
    supporting_observation_ids: tuple[str, ...] = ()
    supporting_pattern_ids: tuple[str, ...] = ()
    satisfied_criteria: tuple[str, ...] = ()
    contradictory_criteria: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.hypothesis_id, "hypothesis_id")
        _check_id(self.hypothesis_type, "hypothesis_type")
        _check_id(self.source_passage_id, "source_passage_id")
        if not isinstance(self.covered_region, ScoreInterval):
            raise TypeError("covered_region must be ScoreInterval")
        if not isinstance(self.covered_event_ids, tuple) or not self.covered_event_ids:
            raise ValueError("covered_event_ids must be a non-empty tuple")
        for r in self.covered_event_ids:
            if not isinstance(r, SourceRef):
                raise TypeError(
                    f"covered_event_ids must contain SourceRef, got {type(r).__name__}"
                )
        object.__setattr__(self, "confidence", _check_confidence(self.confidence))
        object.__setattr__(
            self,
            "confidence_method",
            parse_method_status(self.confidence_method).value,
        )
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        _check_id_list(self.supporting_observation_ids, "supporting_observation_ids")
        _check_id_list(self.supporting_pattern_ids, "supporting_pattern_ids")
        _check_id_list(self.satisfied_criteria, "satisfied_criteria")
        _check_id_list(self.contradictory_criteria, "contradictory_criteria")
        _check_id_list(self.missing_evidence, "missing_evidence")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SEMANTIC_HYPOTHESIS_SCHEMA_VERSION,
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_type": self.hypothesis_type,
            "source_passage_id": self.source_passage_id,
            "covered_region": self.covered_region.to_dict(),
            "covered_event_ids": [r.to_dict() for r in self.covered_event_ids],
            "confidence": self.confidence,
            "confidence_method": self.confidence_method,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "supporting_observation_ids": list(self.supporting_observation_ids),
            "supporting_pattern_ids": list(self.supporting_pattern_ids),
            "satisfied_criteria": list(self.satisfied_criteria),
            "contradictory_criteria": list(self.contradictory_criteria),
            "missing_evidence": list(self.missing_evidence),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticHypothesis":
        if not isinstance(data, dict):
            raise TypeError(
                f"SemanticHypothesis requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_SEMANTIC_HYPOTHESIS_VERSIONS:
            raise ValueError(
                f"unsupported SemanticHypothesis schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SEMANTIC_HYPOTHESIS_VERSIONS)}"
            )
        try:
            hypothesis_id = data["hypothesis_id"]
            hypothesis_type = data["hypothesis_type"]
            source_passage_id = data["source_passage_id"]
            covered_region_data = data["covered_region"]
            covered_event_data = data["covered_event_ids"]
            confidence = data["confidence"]
            confidence_method = data["confidence_method"]
            method_id = data["method_id"]
            method_version = data["method_version"]
        except KeyError as exc:
            raise ValueError(
                f"missing SemanticHypothesis field {exc.args[0]!r}"
            ) from exc
        if not isinstance(covered_event_data, list):
            raise ValueError("SemanticHypothesis covered_event_ids must be list")
        id_list = data.get("supporting_observation_ids", [])
        pattern_list = data.get("supporting_pattern_ids", [])
        satisfied = data.get("satisfied_criteria", [])
        contradictory = data.get("contradictory_criteria", [])
        missing = data.get("missing_evidence", [])
        for field, raw in (
            ("supporting_observation_ids", id_list),
            ("supporting_pattern_ids", pattern_list),
            ("satisfied_criteria", satisfied),
            ("contradictory_criteria", contradictory),
            ("missing_evidence", missing),
        ):
            if not isinstance(raw, list):
                raise ValueError(f"SemanticHypothesis {field} must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("SemanticHypothesis diagnostics must be list")
        return cls(
            hypothesis_id=hypothesis_id,
            hypothesis_type=hypothesis_type,
            source_passage_id=source_passage_id,
            covered_region=ScoreInterval.from_dict(covered_region_data),
            covered_event_ids=tuple(SourceRef.from_dict(r) for r in covered_event_data),
            confidence=confidence,
            confidence_method=confidence_method,
            method_id=method_id,
            method_version=method_version,
            supporting_observation_ids=tuple(str(v) for v in id_list),
            supporting_pattern_ids=tuple(str(v) for v in pattern_list),
            satisfied_criteria=tuple(str(v) for v in satisfied),
            contradictory_criteria=tuple(str(v) for v in contradictory),
            missing_evidence=tuple(str(v) for v in missing),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )


@dataclass(frozen=True, slots=True)
class SemanticBundle:
    """The complete semantic analysis for one passage.

    - hypotheses: every hypothesis for `source_passage_id`, including
      contradictory ones. The bundle never dedupes or re-ranks; ranking is
      carried separately in `ranked_hypothesis_ids` and filtering is the
      consumer's job.
    - ranked_hypothesis_ids: ordered refs into `hypotheses` (subset allowed,
      duplicates rejected). Empty means unranked, not unsupported — the
      no-supported-hypothesis payload (S1.6) is an empty `hypotheses` tuple
      with a diagnostic, not a missing bundle.
    - view_refs / observation_refs / method_versions: opaque producer
      records of which views were read, which observations were consumed,
      and which detector versions ran ( runnable-again provenance even when
      nothing was found).
    """

    bundle_id: str
    source_passage_id: str
    hypotheses: tuple[SemanticHypothesis, ...] = ()
    ranked_hypothesis_ids: tuple[str, ...] = ()
    view_refs: tuple[str, ...] = ()
    observation_refs: tuple[str, ...] = ()
    method_versions: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.bundle_id, "bundle_id")
        _check_id(self.source_passage_id, "source_passage_id")
        if not isinstance(self.hypotheses, tuple):
            raise TypeError("hypotheses must be tuple")
        seen: set[str] = set()
        for h in self.hypotheses:
            if not isinstance(h, SemanticHypothesis):
                raise TypeError(
                    f"hypotheses must contain SemanticHypothesis, got {type(h).__name__}"
                )
            if h.source_passage_id != self.source_passage_id:
                raise ValueError(
                    "hypothesis "
                    f"{h.hypothesis_id!r} belongs to passage "
                    f"{h.source_passage_id!r}, not bundle passage "
                    f"{self.source_passage_id!r}"
                )
            if h.hypothesis_id in seen:
                raise ValueError(
                    f"duplicate hypothesis_id {h.hypothesis_id!r} in bundle"
                )
            seen.add(h.hypothesis_id)
        _check_id_list(self.ranked_hypothesis_ids, "ranked_hypothesis_ids")
        if len(set(self.ranked_hypothesis_ids)) != len(self.ranked_hypothesis_ids):
            raise ValueError("ranked_hypothesis_ids must not contain duplicates")
        for ref in self.ranked_hypothesis_ids:
            if ref not in seen:
                raise ValueError(
                    f"ranked_hypothesis_id {ref!r} matches no bundle hypothesis"
                )
        _check_id_list(self.view_refs, "view_refs")
        _check_id_list(self.observation_refs, "observation_refs")
        _check_id_list(self.method_versions, "method_versions")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")
        for d in self.diagnostics:
            if not isinstance(d, Diagnostic):
                raise TypeError(
                    f"diagnostics must contain Diagnostic, got {type(d).__name__}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SEMANTIC_BUNDLE_SCHEMA_VERSION,
            "bundle_id": self.bundle_id,
            "source_passage_id": self.source_passage_id,
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "ranked_hypothesis_ids": list(self.ranked_hypothesis_ids),
            "view_refs": list(self.view_refs),
            "observation_refs": list(self.observation_refs),
            "method_versions": list(self.method_versions),
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticBundle":
        if not isinstance(data, dict):
            raise TypeError(
                f"SemanticBundle requires dict, got {type(data).__name__}"
            )
        version = data.get("schema_version")
        if version not in SUPPORTED_SEMANTIC_BUNDLE_VERSIONS:
            raise ValueError(
                f"unsupported SemanticBundle schema_version {version!r}; "
                f"supported: {sorted(SUPPORTED_SEMANTIC_BUNDLE_VERSIONS)}"
            )
        try:
            bundle_id = data["bundle_id"]
            source_passage_id = data["source_passage_id"]
        except KeyError as exc:
            raise ValueError(
                f"missing SemanticBundle field {exc.args[0]!r}"
            ) from exc
        raw_hyps = data.get("hypotheses", [])
        if not isinstance(raw_hyps, list):
            raise ValueError("SemanticBundle hypotheses must be list")
        raw_ranked = data.get("ranked_hypothesis_ids", [])
        if not isinstance(raw_ranked, list):
            raise ValueError("SemanticBundle ranked_hypothesis_ids must be list")
        raw_views = data.get("view_refs", [])
        raw_obs = data.get("observation_refs", [])
        raw_methods = data.get("method_versions", [])
        for field, raw in (
            ("view_refs", raw_views),
            ("observation_refs", raw_obs),
            ("method_versions", raw_methods),
        ):
            if not isinstance(raw, list):
                raise ValueError(f"SemanticBundle {field} must be list")
        raw_diags = data.get("diagnostics", [])
        if not isinstance(raw_diags, list):
            raise ValueError("SemanticBundle diagnostics must be list")
        return cls(
            bundle_id=bundle_id,
            source_passage_id=source_passage_id,
            hypotheses=tuple(SemanticHypothesis.from_dict(h) for h in raw_hyps),
            ranked_hypothesis_ids=tuple(str(v) for v in raw_ranked),
            view_refs=tuple(str(v) for v in raw_views),
            observation_refs=tuple(str(v) for v in raw_obs),
            method_versions=tuple(str(v) for v in raw_methods),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in raw_diags),
        )
