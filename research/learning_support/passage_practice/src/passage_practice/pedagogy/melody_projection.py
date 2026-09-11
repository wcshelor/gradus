"""S4.3 melody-projection pedagogical hypothesis.

Maps melody-hidden or melody-plus-accompaniment semantic evidence to a
qualified learner challenge + learner question.

Design refs:
- docs/pedagogical_input_boundary.md (S4.1)
- pedagogy/contracts.py (PedagogicalHypothesis)
- pedagogy/rules.py (rule metadata, evaluation)
- semantics/contracts.py (SemanticBundle/Hypothesis)
"""

from __future__ import annotations

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.pedagogy.contracts import PedagogicalHypothesis
from passage_practice.pedagogy.rules import PedagogicalRule, evaluate_rule
from passage_practice.semantics.contracts import SemanticBundle

MELODY_PROJECTION_RULE = PedagogicalRule(
    rule_id="melody_projection.v1",
    rule_version="v1",
    required_hypothesis_types=("role.melody",),
    optional_difficulty_dimensions=(),
    learner_caveats=("ask_whether_melody_hidden", "no_learner_data_projection_unconfirmed"),
    candidate_objectives=("objective.project_melody", "objective.balance_melody_accompaniment"),
    candidate_strategies=("strategy.melody_accent", "strategy.simplify_accompaniment"),
    contraindications=("monophonic_texture",),
)

MELODY_PROJECTION_HYPOTHESIS_TYPE = "pedagogy.melody_projection"
METHOD_ID = "melody_projection.v1"
METHOD_VERSION = "v1"


def build_melody_projection_hypothesis(
    bundle: SemanticBundle,
    *,
    learner_feedback_present: bool = False,
) -> PedagogicalHypothesis | None:
    """Build a melody-projection hypothesis from ``bundle``.

    - Requires at least one ``role.melody`` hypothesis. Optional strengthening:
      ``texture.melody_plus_accompaniment`` or ``texture.arpeggiated`` or
      ``texture.polyphonic`` in the same bundle.
    - If contradictory evidence is present (see rule evaluation), returns None
      with no hypothesis (caller can inspect diagnostics via evaluate_rule).
    - Confidence is min of supporting semantic confidences, reduced when learner
      data is absent (×0.9) and when no accompaniment texture supports it (×0.85,
      but not below 0.25). Contradiction handling is delegated to rule evaluation
      (returns None instead of low confidence, to keep abstention explicit).
    - Learner caveats are always included when learner_feedback_present is False;
      a learner question ``question.melody_hidden`` is included.
    """
    applies, diags = evaluate_rule(MELODY_PROJECTION_RULE, bundle)
    if not applies:
        return None

    # Find supporting semantic hypotheses
    melody_hyps = [h for h in bundle.hypotheses if h.hypothesis_type.startswith("role.melody")]
    texture_support = [
        h for h in bundle.hypotheses
        if h.hypothesis_type in ("texture.melody_plus_accompaniment", "texture.arpeggiated", "texture.polyphonic")
        or h.hypothesis_type.startswith("texture.melody")
    ]

    if not melody_hyps:
        return None

    supporting_ids = tuple(h.hypothesis_id for h in melody_hyps)
    # Include texture support if present
    if texture_support:
        supporting_ids = supporting_ids + tuple(h.hypothesis_id for h in texture_support)

    base_conf = min(h.confidence for h in melody_hyps)
    # Reduce if no texture support (less evidence that melody is hidden in accompaniment)
    if not texture_support:
        base_conf *= 0.85
    # Reduce if learner data absent (unconfirmed)
    if not learner_feedback_present:
        base_conf *= 0.9

    # Clamp to valid range and keep above unsupported threshold if we decided to produce
    if base_conf < 0.25:
        base_conf = 0.25

    missing: tuple[str, ...] = ()
    for h in melody_hyps:
        if h.missing_evidence:
            missing = tuple(sorted(set(missing) | set(h.missing_evidence)))

    caveats: tuple[str, ...] = MELODY_PROJECTION_RULE.learner_caveats
    if learner_feedback_present:
        caveats = ()

    diagnostics: list[Diagnostic] = list(diags)
    # Surface missing evidence from semantics
    if missing:
        diagnostics.append(
            Diagnostic(
                code="semantic_missing_evidence",
                severity=Severity.INFO,
                message=f"melody projection missing evidence from semantics: {missing!r}",
            )
        )

    return PedagogicalHypothesis(
        hypothesis_id=f"{bundle.source_passage_id}:melody_projection:000",
        hypothesis_type=MELODY_PROJECTION_HYPOTHESIS_TYPE,
        source_passage_id=bundle.source_passage_id,
        supporting_semantic_ids=supporting_ids,
        confidence=round(base_conf, 4),
        confidence_method="heuristic",
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        candidate_objectives=MELODY_PROJECTION_RULE.candidate_objectives,
        candidate_strategies=MELODY_PROJECTION_RULE.candidate_strategies,
        learner_caveats=caveats,
        missing_evidence=missing,
        learner_question="question.melody_hidden" if not learner_feedback_present else None,
        diagnostics=tuple(diagnostics),
    )


__all__ = ["MELODY_PROJECTION_RULE", "MELODY_PROJECTION_HYPOTHESIS_TYPE", "build_melody_projection_hypothesis"]
