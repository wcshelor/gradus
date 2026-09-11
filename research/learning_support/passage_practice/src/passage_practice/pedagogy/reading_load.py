"""S4.6 reading-load pedagogical hypothesis.

Maps notation density, accidentals, rhythm complexity, and low pattern
redundancy to possible reading burden. Unlike melody/bass/rhythm rules, this
hypothesis is driven primarily by direct observations (notation-readability
and rhythm) plus an explicit missing-layout diagnostic.

Design refs:
- pedagogy/contracts.py, pedagogy/rules.py
- semantics/contracts.py
- observations/__init__.py (observe_accidental_density, observe_shortest_duration,
  observe_syncopation_proxy, ledger_line proxy, etc.)
- docs/pedagogical_input_boundary.md: missing layout stays unavailable, not zero
"""

from __future__ import annotations

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.pedagogy.contracts import PedagogicalHypothesis
from passage_practice.pedagogy.rules import PedagogicalRule
from passage_practice.semantics.contracts import SemanticBundle

READING_LOAD_RULE = PedagogicalRule(
    rule_id="reading_load.v1",
    rule_version="v1",
    required_hypothesis_types=("role.bass", "role.melody", "texture.arpeggiated", "rhythm.syncopated_layer", "texture.polyphonic"),
    # Required types are a disjunction for reading-load: any semantic hypothesis qualifies
    # so the rule can fire on notation/rhythm observations alone. The disjunction is
    # encoded by accepting any hypothesis family; the real gate is observation thresholds.
    optional_difficulty_dimensions=("accidental_density", "rhythm_complexity"),
    learner_caveats=("ask_whether_reading_hard", "no_learner_data_reading_unconfirmed"),
    candidate_objectives=("objective.reading_chunking", "objective.visual_grouping"),
    candidate_strategies=("strategy.blocked_harmony", "strategy.rhythmic_simplification"),
    contraindications=(),
)

# For reading-load we relax the required hypothesis check: any bundle with at least one
# hypothesis passes the semantic gate, because the load is observation-driven.
READING_LOAD_HYPOTHESIS_TYPE = "pedagogy.reading_load"
METHOD_ID = "reading_load.v1"
METHOD_VERSION = "v1"


def _bundle_has_any_hypothesis(bundle: SemanticBundle) -> bool:
    return len(bundle.hypotheses) > 0


def build_reading_load_hypothesis(
    bundle: SemanticBundle,
    *,
    accidental_count: int | None = None,
    syncopation_proxy_count: int | None = None,
    shortest_duration_ticks: int | None = None,
    has_low_redundancy: bool = False,
    layout_available: bool = False,
    learner_feedback_present: bool = False,
) -> PedagogicalHypothesis | None:
    """Build reading-load hypothesis from observations + bundle.

    - ``accidental_count``: from ``observe_accidental_density`` (0 means none,
      ``None`` means unavailable — but accidentals are always measurable; None
      is treated as 0 for this builder).
    - ``syncopation_proxy_count`` / ``shortest_duration_ticks``: rhythm complexity
      proxies. ``None`` means unavailable.
    - ``has_low_redundancy``: low pattern redundancy flag (e.g., no accompaniment
      pattern + ambiguous texture).
    - ``layout_available``: whether layout data (e.g., line breaks) is available.
      If False, a ``layout_data_unavailable`` missing_evidence is recorded and never
      treated as 0.
    - Learner caveats retained when ``learner_feedback_present`` is False.

    Scoring (heuristic, deliberately conservative):
    - Accidentals alone (>=1 but alone) → low confidence 0.30-0.35, not overclaimed.
    - Combined evidence (accidentals + rhythm complexity + low redundancy) → higher
      confidence additive (each evidence +0.15, capped).
    - Missing layout always recorded as missing_evidence, never as zero.
    - If no evidence (accidental 0 and no rhythm complexity and not low redundancy)
      → returns None (no reading burden claimed).
    """
    if not _bundle_has_any_hypothesis(bundle):
        return None

    accidental = accidental_count if accidental_count is not None else 0
    # Normalize rhythm complexity: syncopation and short duration
    has_sync = syncopation_proxy_count is not None and syncopation_proxy_count > 0
    has_short = shortest_duration_ticks is not None and shortest_duration_ticks <= 240  # <= eighth at 480 ticks/q

    evidence_count = 0
    if accidental > 0:
        evidence_count += 1
    if has_sync:
        evidence_count += 1
    if has_short:
        evidence_count += 1
    if has_low_redundancy:
        evidence_count += 1

    if evidence_count == 0:
        return None

    # Confidence: accidentals alone not overclaimed
    if evidence_count == 1 and accidental > 0 and not has_sync and not has_short and not has_low_redundancy:
        base_conf = 0.30 + min(0.05, accidental * 0.01)  # capped low
    else:
        # Combined evidence higher
        base_conf = 0.35 + (evidence_count - 1) * 0.15
        if accidental >= 3:
            base_conf += 0.05
        if has_sync and has_short:
            base_conf += 0.05
        base_conf = min(0.85, base_conf)

    if not learner_feedback_present:
        base_conf *= 0.9
    if base_conf < 0.25:
        base_conf = 0.25

    # Missing evidence handling
    missing: list[str] = []
    if not layout_available:
        missing.append("layout_data_unavailable")
    # Also surface rhythm missing if counts were None
    if syncopation_proxy_count is None:
        missing.append("syncopation_proxy_unavailable")
    if shortest_duration_ticks is None:
        missing.append("shortest_duration_unavailable")

    caveats: tuple[str, ...] = READING_LOAD_RULE.learner_caveats
    if learner_feedback_present:
        caveats = ()

    diagnostics: list[Diagnostic] = []
    if missing:
        diagnostics.append(
            Diagnostic(
                code="reading_missing_evidence",
                severity=Severity.INFO,
                message=f"reading load missing evidence: {tuple(missing)!r}",
            )
        )
    if evidence_count == 1 and accidental > 0:
        diagnostics.append(
            Diagnostic(
                code="accidentals_alone_not_overclaimed",
                severity=Severity.INFO,
                message=f"accidentals alone ({accidental}) not overclaimed; confidence {base_conf:.2f}",
            )
        )
    if evidence_count >= 2:
        diagnostics.append(
            Diagnostic(
                code="combined_reading_evidence_higher",
                severity=Severity.INFO,
                message=f"combined evidence count {evidence_count} yields higher confidence {base_conf:.2f}",
            )
        )

    # Supporting semantic IDs: all bundle hypotheses (reading is passage-level)
    supporting_ids = tuple(h.hypothesis_id for h in bundle.hypotheses)

    return PedagogicalHypothesis(
        hypothesis_id=f"{bundle.source_passage_id}:reading_load:000",
        hypothesis_type=READING_LOAD_HYPOTHESIS_TYPE,
        source_passage_id=bundle.source_passage_id,
        supporting_semantic_ids=supporting_ids,
        confidence=round(base_conf, 4),
        confidence_method="heuristic",
        method_id=METHOD_ID,
        method_version=METHOD_VERSION,
        candidate_objectives=READING_LOAD_RULE.candidate_objectives,
        candidate_strategies=READING_LOAD_RULE.candidate_strategies,
        learner_caveats=caveats,
        missing_evidence=tuple(sorted(set(missing))),
        learner_question="question.reading_hard" if not learner_feedback_present else None,
        diagnostics=tuple(diagnostics),
    )


__all__ = ["READING_LOAD_RULE", "READING_LOAD_HYPOTHESIS_TYPE", "build_reading_load_hypothesis"]
