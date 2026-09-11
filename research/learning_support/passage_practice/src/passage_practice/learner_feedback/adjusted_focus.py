"""S5.5 LearnerAdjustedFocus contract.

Preserves base semantic bundle identity while producing a learner-adjusted
ranking of pedagogical hypotheses. Deterministic, immutable, and does not
mutate the original semantic bundle or pedagogical report.

Design refs:
- docs/learner_feedback_policy.md (D-019)
- learner_feedback/contracts.py, learner_feedback/mapping.py, learner_feedback/prompts.py
- pedagogy/contracts.py, pedagogy/integration.py
- semantics/contracts.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from passage_practice.learner_feedback.contracts import LearnerFeedbackSignal
from passage_practice.learner_feedback.mapping import map_feedback
from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.pedagogy.contracts import PedagogicalHypothesis
from passage_practice.semantics.contracts import SemanticBundle

LEARNER_ADJUSTED_FOCUS_SCHEMA_VERSION = "learner_adjusted_focus.v1"
SUPPORTED_VERSIONS = {LEARNER_ADJUSTED_FOCUS_SCHEMA_VERSION}
METHOD_ID = "learner_adjusted_focus.v1"
METHOD_VERSION = "v1"


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
        _check_id(v, f"{field} entry")
    return values


@dataclass(frozen=True, slots=True)
class LearnerAdjustedFocus:
    """Learner-adjusted ranking over pedagogical hypotheses.

    - adjusted_focus_id: stable ID (e.g., ``<passage>:adjusted_focus:v1``)
    - source_passage_id: passage under analysis
    - base_semantic_bundle_id: ID of the original SemanticBundle (preserved)
    - base_pedagogical_report_id: optional ID of the base pedagogical report
    - feedback_ids: feedback signals that influenced this adjustment
    - ranked_hypothesis_ids: hypothesis types/IDs in new rank order (deterministic)
    - ranked_hypotheses: full hypothesis objects in rank order (copies, not mutated)
    - primary_focus: hypothesis_type of top-ranked hypothesis, or None if empty
    - secondary_focuses: hypothesis_types of remaining ranked hypotheses
    - deprioritized_ids: hypothesis IDs that were demoted/rejected by feedback
    - rationale: human-readable explanation of how feedback changed ranking
    - diagnostics: e.g., preserved, boosted, request_more_evidence
    - method_id/method_version: provenance
    """

    adjusted_focus_id: str
    source_passage_id: str
    base_semantic_bundle_id: str
    feedback_ids: tuple[str, ...]
    ranked_hypothesis_ids: tuple[str, ...]
    ranked_hypotheses: tuple[PedagogicalHypothesis, ...]
    primary_focus: str | None
    secondary_focuses: tuple[str, ...]
    deprioritized_ids: tuple[str, ...]
    rationale: str
    method_id: str = METHOD_ID
    method_version: str = METHOD_VERSION
    diagnostics: tuple[Diagnostic, ...] = ()
    schema_version: str = LEARNER_ADJUSTED_FOCUS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _check_id(self.adjusted_focus_id, "adjusted_focus_id")
        _check_id(self.source_passage_id, "source_passage_id")
        _check_id(self.base_semantic_bundle_id, "base_semantic_bundle_id")
        _check_id_tuple(self.feedback_ids, "feedback_ids")
        _check_id_tuple(self.ranked_hypothesis_ids, "ranked_hypothesis_ids")
        if not isinstance(self.ranked_hypotheses, tuple):
            raise TypeError("ranked_hypotheses must be tuple")
        for h in self.ranked_hypotheses:
            if not isinstance(h, PedagogicalHypothesis):
                raise TypeError(f"ranked_hypotheses must contain PedagogicalHypothesis, got {type(h).__name__}")
            if h.source_passage_id != self.source_passage_id:
                raise ValueError(f"hypothesis {h.hypothesis_id!r} passage mismatch")
        if self.primary_focus is not None:
            _check_id(self.primary_focus, "primary_focus")
        _check_id_tuple(self.secondary_focuses, "secondary_focuses")
        _check_id_tuple(self.deprioritized_ids, "deprioritized_ids")
        if not isinstance(self.rationale, str) or not self.rationale:
            raise ValueError(f"rationale must be non-empty str, got {self.rationale!r}")
        _check_id(self.method_id, "method_id")
        _check_id(self.method_version, "method_version")
        if not isinstance(self.diagnostics, tuple):
            raise TypeError("diagnostics must be tuple")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "adjusted_focus_id": self.adjusted_focus_id,
            "source_passage_id": self.source_passage_id,
            "base_semantic_bundle_id": self.base_semantic_bundle_id,
            "feedback_ids": list(self.feedback_ids),
            "ranked_hypothesis_ids": list(self.ranked_hypothesis_ids),
            "ranked_hypotheses": [h.to_dict() for h in self.ranked_hypotheses],
            "primary_focus": self.primary_focus,
            "secondary_focuses": list(self.secondary_focuses),
            "deprioritized_ids": list(self.deprioritized_ids),
            "rationale": self.rationale,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnerAdjustedFocus":
        if not isinstance(data, dict):
            raise TypeError(f"LearnerAdjustedFocus requires dict, got {type(data).__name__}")
        version = data.get("schema_version")
        if version not in SUPPORTED_VERSIONS:
            raise ValueError(f"unsupported schema_version {version!r}")
        return cls(
            adjusted_focus_id=data["adjusted_focus_id"],
            source_passage_id=data["source_passage_id"],
            base_semantic_bundle_id=data["base_semantic_bundle_id"],
            feedback_ids=tuple(data.get("feedback_ids", [])),
            ranked_hypothesis_ids=tuple(data.get("ranked_hypothesis_ids", [])),
            ranked_hypotheses=tuple(PedagogicalHypothesis.from_dict(h) for h in data.get("ranked_hypotheses", [])),
            primary_focus=data.get("primary_focus"),
            secondary_focuses=tuple(data.get("secondary_focuses", [])),
            deprioritized_ids=tuple(data.get("deprioritized_ids", [])),
            rationale=data["rationale"],
            method_id=data.get("method_id", METHOD_ID),
            method_version=data.get("method_version", METHOD_VERSION),
            diagnostics=tuple(Diagnostic.from_dict(d) for d in data.get("diagnostics", [])),
        )


def build_learner_adjusted_focus(
    bundle: SemanticBundle,
    pedagogical_hypotheses: tuple[PedagogicalHypothesis, ...],
    feedback_signals: tuple[LearnerFeedbackSignal, ...],
    *,
    base_bundle_id: str | None = None,
) -> LearnerAdjustedFocus:
    """Build a learner-adjusted focus from base hypotheses and feedback.

    - ``bundle`` is the original semantic bundle (preserved verbatim; this
      function must not mutate it). ``bundle.bundle_id`` is recorded as
      ``base_semantic_bundle_id``.
    - ``pedagogical_hypotheses`` are the base pedagogical hypotheses (e.g., from
      ``build_pedagogical_report``). They are treated as the input ranking.
    - ``feedback_signals`` are applied deterministically in order of
      ``feedback_id``. Each signal's mapping (via ``map_feedback``) may boost,
      demote, or preserve hypotheses.
    - Determinism: feedback sorted by ID, hypothesis ranking is stable sort by
      boosted status then original confidence then hypothesis_type.
    - Rationale is a concise, deterministic string describing which feedback
      caused which adjustment; it is not free-text advice.

    Tests required:
    - original bundle unchanged (assert bundle == copy after call)
    - deterministic output (two calls with same inputs produce equal dicts)
    """
    if not isinstance(bundle, SemanticBundle):
        raise TypeError(f"bundle must be SemanticBundle, got {type(bundle).__name__}")
    if not isinstance(pedagogical_hypotheses, tuple):
        raise TypeError("pedagogical_hypotheses must be tuple")
    if not isinstance(feedback_signals, tuple):
        raise TypeError("feedback_signals must be tuple")
    for h in pedagogical_hypotheses:
        if not isinstance(h, PedagogicalHypothesis):
            raise TypeError(f"pedagogical_hypotheses must contain PedagogicalHypothesis, got {type(h).__name__}")
        if h.source_passage_id != bundle.source_passage_id:
            raise ValueError(f"hypothesis {h.hypothesis_id!r} passage mismatch with bundle {bundle.source_passage_id!r}")
    for sig in feedback_signals:
        if not isinstance(sig, LearnerFeedbackSignal):
            raise TypeError(f"feedback_signals must contain LearnerFeedbackSignal, got {type(sig).__name__}")
        if sig.source_passage_id != bundle.source_passage_id:
            raise ValueError(f"feedback {sig.feedback_id!r} passage mismatch")

    base_id = base_bundle_id if base_bundle_id is not None else bundle.bundle_id

    # Verify bundle unchanged by keeping a dict snapshot (immutable, so just check later)
    original_bundle_dict = bundle.to_dict()

    # Sort feedback deterministically
    sorted_feedback = tuple(sorted(feedback_signals, key=lambda s: s.feedback_id))

    # Map each feedback to boosted/demoted sets
    boosted_types: set[str] = set()
    demoted_types: set[str] = set()
    diagnostics: list[Diagnostic] = []
    for sig in sorted_feedback:
        adj = map_feedback(sig, pedagogical_hypotheses)
        boosted_types.update(adj.boosted_ids)
        demoted_types.update(adj.demoted_ids)
        diagnostics.extend(adj.diagnostics)
        if adj.preserved:
            diagnostics.append(Diagnostic(code="feedback_preserved_in_focus", severity=Severity.INFO, message=f"feedback {sig.feedback_id!r} preserved"))
        if adj.request_more_evidence:
            diagnostics.append(Diagnostic(code="request_more_evidence", severity=Severity.INFO, message=f"feedback {sig.feedback_id!r} requests more evidence"))

    # Build adjusted ranking: boosted hypotheses first (sorted by original confidence desc),
    # then remaining hypotheses in original confidence order, then demoted last
    hyp_by_type: dict[str, list[PedagogicalHypothesis]] = {}
    for h in pedagogical_hypotheses:
        hyp_by_type.setdefault(h.hypothesis_type, []).append(h)

    boosted_hyps: list[PedagogicalHypothesis] = []
    remaining_hyps: list[PedagogicalHypothesis] = []
    demoted_hyps: list[PedagogicalHypothesis] = []

    for h in pedagogical_hypotheses:
        if h.hypothesis_type in demoted_types:
            demoted_hyps.append(h)
        elif h.hypothesis_type in boosted_types:
            boosted_hyps.append(h)
        else:
            remaining_hyps.append(h)

    # Deduplicate while preserving order: boosted first, then remaining, then demoted
    # Within each group, sort by confidence desc then hypothesis_type for determinism
    def _sort_group(group: list[PedagogicalHypothesis]) -> list[PedagogicalHypothesis]:
        return sorted(group, key=lambda h: (-h.confidence, h.hypothesis_type, h.hypothesis_id))

    boosted_sorted = _sort_group(boosted_hyps)
    remaining_sorted = _sort_group(remaining_hyps)
    demoted_sorted = _sort_group(demoted_hyps)

    ranked = tuple(boosted_sorted + remaining_sorted + demoted_sorted)
    ranked_ids = tuple(h.hypothesis_type for h in ranked)
    deprioritized_ids = tuple(h.hypothesis_type for h in demoted_sorted)

    primary = ranked[0].hypothesis_type if ranked else None
    secondary = tuple(h.hypothesis_type for h in ranked[1:]) if len(ranked) > 1 else ()

    # Build deterministic rationale
    if not sorted_feedback:
        rationale = "no feedback; base ranking preserved"
    elif boosted_types and not demoted_types:
        rationale = f"boosted {sorted(boosted_types)!r} from feedback {[s.feedback_id for s in sorted_feedback]!r}; base bundle {base_id!r} unchanged"
    elif demoted_types:
        rationale = f"demoted {sorted(demoted_types)!r}, boosted {sorted(boosted_types)!r} from feedback {[s.feedback_id for s in sorted_feedback]!r}; base bundle {base_id!r} unchanged"
    elif any(adj.preserved for adj in [map_feedback(s, pedagogical_hypotheses) for s in sorted_feedback]):
        rationale = f"feedback preserved original ranking; base bundle {base_id!r} unchanged"
    else:
        rationale = f"feedback processed {[s.feedback_id for s in sorted_feedback]!r}; base bundle {base_id!r} unchanged"

    # Verify original bundle unchanged
    assert bundle.to_dict() == original_bundle_dict, "bundle mutated during adjusted focus construction"

    # Ensure diagnostics include synthetic preservation
    diagnostics.append(Diagnostic(code="base_bundle_preserved", severity=Severity.INFO, message=f"base bundle {base_id!r} preserved"))

    adjusted_id = f"{bundle.source_passage_id}:adjusted_focus:v1"
    feedback_ids = tuple(s.feedback_id for s in sorted_feedback)

    return LearnerAdjustedFocus(
        adjusted_focus_id=adjusted_id,
        source_passage_id=bundle.source_passage_id,
        base_semantic_bundle_id=base_id,
        feedback_ids=feedback_ids,
        ranked_hypothesis_ids=ranked_ids,
        ranked_hypotheses=ranked,
        primary_focus=primary,
        secondary_focuses=secondary,
        deprioritized_ids=deprioritized_ids,
        rationale=rationale,
        diagnostics=tuple(diagnostics),
    )


__all__ = ["LearnerAdjustedFocus", "LEARNER_ADJUSTED_FOCUS_SCHEMA_VERSION", "build_learner_adjusted_focus"]
