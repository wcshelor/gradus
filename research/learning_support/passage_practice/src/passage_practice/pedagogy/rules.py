"""Semantic-to-diagnosis rule metadata — S4.2.

Design refs:
- docs/pedagogical_input_boundary.md (S4.1 boundary)
- docs/practice_chunk_objects.md (learner-facing claims attach to chunks
  without rewriting score-derived evidence)
- semantics/contracts.py (SemanticHypothesis/Bundles)
- passage_practice/models/source.py (SourceRef)

Each rule declares which semantic hypotheses it needs, which difficulty
dimensions are optional context, which learner caveats apply, and which
pedagogical objectives/strategies it can propose. Rules do not contain
free-text advice; they produce structured hypothesis IDs via evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.semantics.contracts import SemanticBundle, SemanticHypothesis


def _check_id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be non-empty str, got {value!r}")
    if len(value) > 128:
        raise ValueError(f"{field} too long (>128): {value!r}")
    return value


def _check_id_tuple(values: tuple[str, ...], field: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise TypeError(f"{field} must be tuple, got {type(values).__name__}")
    for v in values:
        if not isinstance(v, str) or not v:
            raise ValueError(f"{field} must contain non-empty str, got {v!r}")
        if len(v) > 128:
            raise ValueError(f"{field} too long (>128): {v!r}")
    if not allow_empty and not values:
        raise ValueError(f"{field} must be non-empty tuple")
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not contain duplicates, got {values!r}")
    return values


@dataclass(frozen=True, slots=True)
class PedagogicalRule:
    """Immutable metadata for one semantic-to-pedagogical mapping.

    - rule_id / rule_version: stable identity (e.g. ``melody_projection.v1``).
    - required_hypothesis_types: at least one hypothesis_type prefix or exact
      type that must be present in the bundle (e.g. ``"role.melody"``). Matching
      is prefix-aware: ``"role.melody"`` matches ``"role.melody"`` and any
      future ``"role.melody.*"`` if dot logic is used, but contract keeps
      simple startswith.
    - optional_difficulty_dimensions: feature/dimension IDs that strengthen the
      rule when present (e.g. ``"largest_pitch_transition"``) but are never
      required.
    - learner_caveats: explicit caveats when learner data is absent (e.g.
      ``"ask learner whether melody is hidden"``). Never free-text advice; each
      caveat is a controlled code/label.
    - candidate_objectives: objective IDs the rule can propose (e.g.
      ``"objective.project_melody"``).
    - candidate_strategies: strategy IDs the rule can propose (e.g.
      ``"strategy.melody_accent"``).
    - contraindications: conditions when the rule must not propose (e.g.
      ``"monophonic_texture"``).
    """

    rule_id: str
    rule_version: str
    required_hypothesis_types: tuple[str, ...]
    optional_difficulty_dimensions: tuple[str, ...] = ()
    learner_caveats: tuple[str, ...] = ()
    candidate_objectives: tuple[str, ...] = ()
    candidate_strategies: tuple[str, ...] = ()
    contraindications: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _check_id(self.rule_id, "rule_id")
        _check_id(self.rule_version, "rule_version")
        _check_id_tuple(self.required_hypothesis_types, "required_hypothesis_types", allow_empty=False)
        _check_id_tuple(self.optional_difficulty_dimensions, "optional_difficulty_dimensions", allow_empty=True)
        _check_id_tuple(self.learner_caveats, "learner_caveats", allow_empty=True)
        _check_id_tuple(self.candidate_objectives, "candidate_objectives", allow_empty=True)
        _check_id_tuple(self.candidate_strategies, "candidate_strategies", allow_empty=True)
        _check_id_tuple(self.contraindications, "contraindications", allow_empty=True)
        for ht in self.required_hypothesis_types:
            if "." not in ht:
                raise ValueError(f"required_hypothesis_type must contain '.', got {ht!r}")


def _hypothesis_matches_required(
    hypothesis: SemanticHypothesis, required: tuple[str, ...]
) -> bool:
    for req in required:
        if hypothesis.hypothesis_type == req or hypothesis.hypothesis_type.startswith(req):
            return True
    return False


def evaluate_rule(
    rule: PedagogicalRule,
    bundle: SemanticBundle,
    *,
    difficulty_dimensions: tuple[str, ...] = (),
) -> tuple[bool, tuple[Diagnostic, ...]]:
    """Evaluate whether ``rule`` applies to ``bundle``.

    Returns (applies, diagnostics). Diagnostics are always returned even when
    not applying, so callers can inspect why a rule did not fire.

    - Missing required hypothesis → does not apply, diagnostic
      ``missing_required_hypothesis``.
    - Contradictory criteria from the matching hypothesis that intersect the
      rule's contraindications → does not apply, diagnostic
      ``contradictory_evidence``.
    - Otherwise → applies (even if learner caveats exist; those are informational).
    Optional difficulty_dimensions are not gating; they are informational context
    (when present, a diagnostic notes they were available).
    """
    if not isinstance(rule, PedagogicalRule):
        raise TypeError(f"rule must be PedagogicalRule, got {type(rule).__name__}")
    if not isinstance(bundle, SemanticBundle):
        raise TypeError(f"bundle must be SemanticBundle, got {type(bundle).__name__}")

    diagnostics: list[Diagnostic] = []

    matching = [h for h in bundle.hypotheses if _hypothesis_matches_required(h, rule.required_hypothesis_types)]

    if not matching:
        diagnostics.append(
            Diagnostic(
                code="missing_required_hypothesis",
                severity=Severity.INFO,
                message=f"rule {rule.rule_id!r} requires hypothesis types {rule.required_hypothesis_types!r}; none present",
            )
        )
        return False, tuple(diagnostics)

    # Check contraindications against satisfied/contradictory criteria of matching hyps
    for h in matching:
        for contra in rule.contraindications:
            if contra in h.satisfied_criteria or contra in h.contradictory_criteria:
                diagnostics.append(
                    Diagnostic(
                        code="contradictory_evidence",
                        severity=Severity.INFO,
                        message=f"rule {rule.rule_id!r} contraindicated by {contra!r} in hypothesis {h.hypothesis_id!r}",
                    )
                )
                return False, tuple(diagnostics)
        # Also check if contradictory_criteria of hypothesis directly contradicts rule expectation
        # For generic contradictory evidence: if hypothesis has contradictory_criteria that include
        # any required hypothesis type family, treat as contradictory
        if h.contradictory_criteria:
            # If any contradictory criterion mentions the required family, flag
            for crit in h.contradictory_criteria:
                if any(req in crit for req in rule.required_hypothesis_types):
                    diagnostics.append(
                        Diagnostic(
                            code="contradictory_evidence",
                            severity=Severity.INFO,
                            message=f"rule {rule.rule_id!r} has contradictory evidence {crit!r} in hypothesis {h.hypothesis_id!r}",
                        )
                    )
                    return False, tuple(diagnostics)

    if difficulty_dimensions:
        diagnostics.append(
            Diagnostic(
                code="difficulty_context_present",
                severity=Severity.INFO,
                message=f"difficulty dimensions {difficulty_dimensions!r} available as optional context for {rule.rule_id!r}",
            )
        )

    if rule.learner_caveats:
        diagnostics.append(
            Diagnostic(
                code="learner_caveat",
                severity=Severity.INFO,
                message=f"rule {rule.rule_id!r} learner caveats: {rule.learner_caveats!r}",
            )
        )

    return True, tuple(diagnostics)


class PedagogicalRuleRegistry:
    """Deterministic registry for pedagogical rules."""

    def __init__(self) -> None:
        self._by_id: dict[str, PedagogicalRule] = {}

    def register(self, rule: PedagogicalRule) -> None:
        if not isinstance(rule, PedagogicalRule):
            raise TypeError(f"rule must be PedagogicalRule, got {type(rule).__name__}")
        if rule.rule_id in self._by_id:
            raise ValueError(f"duplicate rule_id {rule.rule_id!r}")
        self._by_id[rule.rule_id] = rule

    def get(self, rule_id: str) -> PedagogicalRule:
        _check_id(rule_id, "rule_id")
        try:
            return self._by_id[rule_id]
        except KeyError as exc:
            raise KeyError(f"unknown rule_id {rule_id!r}") from exc

    def list_all(self) -> list[PedagogicalRule]:
        return [self._by_id[k] for k in sorted(self._by_id)]

    def __len__(self) -> int:
        return len(self._by_id)


__all__ = ["PedagogicalRule", "PedagogicalRuleRegistry", "evaluate_rule"]
