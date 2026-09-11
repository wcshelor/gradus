"""S4.5 rhythmic coordination pedagogical hypothesis.

Maps independent rhythm / hand-alignment evidence to a qualified coordination
focus. Heuristic: staggered onsets across hands indicates potential
coordination demand; aligned hands with common attacks indicates no focus.

Design refs:
- pedagogy/contracts.py, pedagogy/rules.py
- semantics/contracts.py, semantics/rhythm.py (rhythm_layer detector)
- observations/__init__.py (observe_hand_alignment_ratio, observe_subdivision_mismatch)
- docs/pedagogical_input_boundary.md
"""

from __future__ import annotations

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.pedagogy.contracts import PedagogicalHypothesis
from passage_practice.pedagogy.rules import PedagogicalRule, evaluate_rule
from passage_practice.semantics.contracts import SemanticBundle

RHYTHMIC_COORDINATION_RULE = PedagogicalRule(
    rule_id="rhythmic_coordination.v1",
    rule_version="v1",
    required_hypothesis_types=("rhythm.independent_hands",),
    optional_difficulty_dimensions=("hand_timing_mismatch",),
    learner_caveats=("ask_whether_hands_together_hard", "no_learner_data_coordination_unconfirmed"),
    candidate_objectives=("objective.hand_coordination", "objective.rhythmic_alignment"),
    candidate_strategies=("strategy.hands_separate_then_together", "strategy.common_attack_skeleton"),
    contraindications=("aligned_hands_no_independence",),
)

RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE = "pedagogy.rhythmic_coordination"
METHOD_ID = "rhythmic_coordination.v1"
METHOD_VERSION = "v1"


def build_rhythmic_coordination_hypothesis(
    bundle: SemanticBundle,
    *,
    hand_alignment_ratio: int | None = None,
    learner_feedback_present: bool = False,
) -> PedagogicalHypothesis | None:
    """Build rhythmic coordination hypothesis from bundle and optional alignment.

    - Requires at least one ``rhythm.independent_hands`` semantic hypothesis.
      Aligned hands (bundle lacks that hypothesis, but may contain
      ``rhythm.common_attack_skeleton``) yields ``None`` (negative).
    - ``hand_alignment_ratio`` is optional integer percent (0-100) from
      ``observe_hand_alignment_ratio``. When present and high (>=80), it
      contradicts independence and reduces confidence; when low (<40) it
      strengthens. This keeps observation evidence explicit without fabricating.
    - Low confidence when rhythm evidence incomplete: if supporting semantic
      confidence is <0.6 or if hand_alignment suggests strong alignment, the
      resulting pedagogical confidence is reduced (×0.85) but still produced if
      above 0.25. Caller can inspect low confidence as incomplete evidence signal.
    - Learner caveats retained when ``learner_feedback_present`` is False.
    """
    applies, diags = evaluate_rule(RHYTHMIC_COORDINATION_RULE, bundle)
    if not applies:
        return None

    rhythm_hyps = [h for h in bundle.hypotheses if h.hypothesis_type.startswith("rhythm.independent_hands")]
    if not rhythm_hyps:
        return None

    # Check for contradictory aligned evidence: if hand_alignment_ratio high, treat as aligned negative
    if hand_alignment_ratio is not None:
        if hand_alignment_ratio >= 80:
            # Strong alignment contradicts coordination focus
            return None

    supporting_ids = tuple(h.hypothesis_id for h in rhythm_hyps)
    base_conf = min(h.confidence for h in rhythm_hyps)

    # Evidence completeness: if base confidence low (<0.6) or hand_alignment missing mid-range
    incomplete = base_conf < 0.60
    if hand_alignment_ratio is None:
        incomplete = True  # missing alignment observation is incomplete evidence
        base_conf *= 0.85
    elif hand_alignment_ratio >= 60:
        # Moderate alignment suggests coordination less clear
        base_conf *= 0.85
        incomplete = True
    elif hand_alignment_ratio is not None and hand_alignment_ratio < 40:
        # Low alignment strengthens independence
        base_conf = min(1.0, base_conf + 0.05)

    if not learner_feedback_present:
        base_conf *= 0.9
    if base_conf < 0.25:
        base_conf = 0.25

    missing: tuple[str, ...] = ()
    for h in rhythm_hyps:
        if h.missing_evidence:
            missing = tuple(sorted(set(missing) | set(h.missing_evidence)))

    caveats: tuple[str, ...] = RHYTHMIC_COORDINATION_RULE.learner_caveats
    if learner_feedback_present:
        caveats = ()

    diagnostics: list[Diagnostic] = list(diags)
    if missing:
        diagnostics.append(
            Diagnostic(
                code="semantic_missing_evidence",
                severity=Severity.INFO,
                message=f"rhythmic coordination missing evidence: {missing!r}",
            )
        )
    if incomplete:
        diagnostics.append(
            Diagnostic(
                code="rhythm_evidence_incomplete",
                severity=Severity.INFO,
                message=f"rhythm evidence incomplete (hand_alignment_ratio={hand_alignment_ratio!r})",
            )
        )
    if hand_alignment_ratio is not None:
        diagnostics.append(
            Diagnostic(
                code="hand_alignment_ratio_present",
                severity=Severity.INFO,
                message=f"hand_alignment_ratio={hand_alignment_ratio} considered",
            )
        )

    return PedagogicalHypothesis(
        hypothesis_id=f"{bundle.source_passage_id}:rhythmic_coordination:000",
        hypothesis_type=RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE,
        source_passage_id=bundle.source_passage_id,
        supporting_semantic_ids=supporting_ids,
        confidence=round(base_conf, 4),
        confidence_method="heuristic",
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        candidate_objectives=RHYTHMIC_COORDINATION_RULE.candidate_objectives,
        candidate_strategies=RHYTHMIC_COORDINATION_RULE.candidate_strategies,
        learner_caveats=caveats,
        missing_evidence=missing,
        learner_question="question.hands_together" if not learner_feedback_present else None,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "RHYTHMIC_COORDINATION_RULE",
    "RHYTHMIC_COORDINATION_HYPOTHESIS_TYPE",
    "build_rhythmic_coordination_hypothesis",
]
