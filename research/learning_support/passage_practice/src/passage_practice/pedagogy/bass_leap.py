"""S4.4 bass/leap targeting pedagogical hypothesis.

Maps bass-anchor plus leap/motor-proxy observations to a qualified
relocation / landing-target focus.

Design refs:
- docs/pedagogical_input_boundary.md (S4.1)
- pedagogy/contracts.py, pedagogy/rules.py
- semantics/contracts.py
- observations/__init__.py (observe_leap_frequency, observe_pitch_range)
"""

from __future__ import annotations

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.pedagogy.contracts import PedagogicalHypothesis
from passage_practice.pedagogy.rules import PedagogicalRule, evaluate_rule
from passage_practice.semantics.contracts import SemanticBundle

BASS_LEAP_RULE = PedagogicalRule(
    rule_id="bass_leap.v1",
    rule_version="v1",
    required_hypothesis_types=("role.bass",),
    optional_difficulty_dimensions=("largest_pitch_transition", "leap_count"),
    learner_caveats=("ask_whether_leaps_hard", "no_learner_data_leap_unconfirmed"),
    candidate_objectives=("objective.landing_target", "objective.relocation_preparation"),
    candidate_strategies=("strategy.blocked_bass", "strategy.isolated_leaps"),
    contraindications=("smooth_bass_no_leap", "no_anchor_evidence_longest_or_recurrence"),
)

BASS_LEAP_HYPOTHESIS_TYPE = "pedagogy.bass_leap"
METHOD_ID = "bass_leap.v1"
METHOD_VERSION = "v1"


def build_bass_leap_hypothesis(
    bundle: SemanticBundle,
    *,
    leap_count: int | None = None,
    has_leap_observation: bool | None = None,
    learner_feedback_present: bool = False,
) -> PedagogicalHypothesis | None:
    """Build a bass/leap targeting hypothesis from ``bundle`` and leap evidence.

    - Requires at least one ``role.bass`` hypothesis in the bundle. The leap
      evidence is provided via ``leap_count`` (from ``observe_leap_frequency``)
      or ``has_leap_observation`` (derived from pitch_transition observations).
      If neither is provided, the function inspects the bundle's bass hypotheses
      for leap-related criteria as fallback: presence of ``large_leap`` or
      ``leap`` in satisfied_criteria is treated as leap evidence.
    - Smooth bass (leap_count == 0 or no leap observation and no leap criteria)
      yields ``None`` (negative case: no relocation focus justified).
    - Contradictory evidence from rule evaluation blocks the hypothesis.
    - Learner caveats added when ``learner_feedback_present`` is False.
    """
    applies, diags = evaluate_rule(BASS_LEAP_RULE, bundle)
    if not applies:
        return None

    bass_hyps = [h for h in bundle.hypotheses if h.hypothesis_type.startswith("role.bass")]
    if not bass_hyps:
        return None

    # Determine leap presence
    leap_present: bool
    if has_leap_observation is not None:
        leap_present = bool(has_leap_observation)
    elif leap_count is not None:
        leap_present = leap_count > 0
    else:
        # Fallback: inspect semantic criteria for leap hints
        leap_present = any(
            any("leap" in crit.lower() for crit in h.satisfied_criteria)
            for h in bass_hyps
        )
        # Also check if bundle has any semantic hypothesis mentioning leap motor proxy
        if not leap_present:
            leap_present = any(
                "leap" in h.hypothesis_type.lower() or any("leap" in c.lower() for c in h.satisfied_criteria)
                for h in bundle.hypotheses
            )

    if not leap_present:
        # Smooth bass negative: do not propose relocation focus
        return None

    # Check for smooth_bass contraindication in bundle (explicit smooth)
    for h in bass_hyps:
        if "smooth_bass_no_leap" in h.contradictory_criteria or "smooth_bass_no_leap" in h.satisfied_criteria:
            # If rule says smooth, it would have been caught as contraindication already,
            # but also treat as negative
            pass

    supporting_ids = tuple(h.hypothesis_id for h in bass_hyps)
    base_conf = min(h.confidence for h in bass_hyps)
    # Strengthen if leap evidence strong (leap_count large)
    if leap_count is not None and leap_count >= 3:
        base_conf = min(1.0, base_conf + 0.05)
    if not learner_feedback_present:
        base_conf *= 0.9
    if base_conf < 0.25:
        base_conf = 0.25

    missing: tuple[str, ...] = ()
    for h in bass_hyps:
        if h.missing_evidence:
            missing = tuple(sorted(set(missing) | set(h.missing_evidence)))

    caveats: tuple[str, ...] = BASS_LEAP_RULE.learner_caveats
    if learner_feedback_present:
        caveats = ()

    diagnostics: list[Diagnostic] = list(diags)
    if missing:
        diagnostics.append(
            Diagnostic(
                code="semantic_missing_evidence",
                severity=Severity.INFO,
                message=f"bass leap missing evidence from semantics: {missing!r}",
            )
        )
    if leap_count is not None:
        diagnostics.append(
            Diagnostic(
                code="leap_count_present",
                severity=Severity.INFO,
                message=f"leap_count={leap_count} considered for bass relocation",
            )
        )

    return PedagogicalHypothesis(
        hypothesis_id=f"{bundle.source_passage_id}:bass_leap:000",
        hypothesis_type=BASS_LEAP_HYPOTHESIS_TYPE,
        source_passage_id=bundle.source_passage_id,
        supporting_semantic_ids=supporting_ids,
        confidence=round(base_conf, 4),
        confidence_method="heuristic",
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        candidate_objectives=BASS_LEAP_RULE.candidate_objectives,
        candidate_strategies=BASS_LEAP_RULE.candidate_strategies,
        learner_caveats=caveats,
        missing_evidence=missing,
        learner_question="question.bass_leaps" if not learner_feedback_present else None,
        diagnostics=tuple(diagnostics),
    )


__all__ = ["BASS_LEAP_RULE", "BASS_LEAP_HYPOTHESIS_TYPE", "build_bass_leap_hypothesis"]
