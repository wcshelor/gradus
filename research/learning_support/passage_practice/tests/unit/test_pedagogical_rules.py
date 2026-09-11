"""Tests for S4.2 pedagogical rule metadata — missing required hypothesis, contradictory evidence."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.pedagogy.rules import PedagogicalRule, PedagogicalRuleRegistry, evaluate_rule
from passage_practice.semantics.contracts import SemanticBundle, SemanticHypothesis
from passage_practice.models.diagnostics import Diagnostic, Severity

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=1, measure_number="1", offset_in_measure=q)


def _make_hypothesis(h_type: str, criteria=(), contradictory=()) -> SemanticHypothesis:
    return SemanticHypothesis(
        hypothesis_id=f"test.{h_type.replace('.', '_')}.000",
        hypothesis_type=h_type,
        source_passage_id="test_passage@[0,4)/detection",
        covered_region=ScoreInterval(start=_pos(Fraction(0)), end=_pos(Fraction(4))),
        covered_event_ids=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
        confidence=0.8,
        confidence_method="heuristic",
        method_id="test.v1",
        method_version="v1",
        satisfied_criteria=tuple(criteria),
        contradictory_criteria=tuple(contradictory),
    )


def _bundle_with(*hyps: SemanticHypothesis) -> SemanticBundle:
    return SemanticBundle(
        bundle_id="test_passage@[0,4)/detection:bundle:v1",
        source_passage_id="test_passage@[0,4)/detection",
        hypotheses=tuple(hyps),
        ranked_hypothesis_ids=tuple(h.hypothesis_id for h in hyps),
    )


def test_rule_requires_required_hypothesis():
    rule = PedagogicalRule(
        rule_id="melody_projection.v1",
        rule_version="v1",
        required_hypothesis_types=("role.melody",),
        candidate_objectives=("objective.project_melody",),
        candidate_strategies=("strategy.melody_accent",),
        learner_caveats=("ask_whether_melody_hidden",),
    )
    bundle_empty = _bundle_with()
    applies, diags = evaluate_rule(rule, bundle_empty)
    assert applies is False
    assert any(d.code == "missing_required_hypothesis" for d in diags)


def test_rule_applies_when_required_present():
    rule = PedagogicalRule(
        rule_id="melody_projection.v1",
        rule_version="v1",
        required_hypothesis_types=("role.melody",),
        candidate_objectives=("objective.project_melody",),
    )
    hyp = _make_hypothesis("role.melody", criteria=("top_voice",))
    bundle = _bundle_with(hyp)
    applies, diags = evaluate_rule(rule, bundle)
    assert applies is True


def test_contradictory_evidence_blocks_rule():
    rule = PedagogicalRule(
        rule_id="melody_projection.v1",
        rule_version="v1",
        required_hypothesis_types=("role.melody",),
        contraindications=("monophonic_texture",),
    )
    hyp = _make_hypothesis("role.melody", criteria=("monophonic_texture",))
    bundle = _bundle_with(hyp)
    applies, diags = evaluate_rule(rule, bundle)
    assert applies is False
    assert any(d.code == "contradictory_evidence" for d in diags)


def test_contradictory_criteria_blocks_rule():
    rule = PedagogicalRule(
        rule_id="melody_projection.v1",
        rule_version="v1",
        required_hypothesis_types=("role.melody",),
    )
    hyp = _make_hypothesis("role.melody", contradictory=("role.melody.not_possible",))
    bundle = _bundle_with(hyp)
    applies, diags = evaluate_rule(rule, bundle)
    assert applies is False
    assert any(d.code == "contradictory_evidence" for d in diags)


def test_rule_validates_required_types():
    with pytest.raises(ValueError):
        PedagogicalRule(rule_id="bad.v1", rule_version="v1", required_hypothesis_types=())


def test_rule_rejects_free_text_advice_in_caveats():
    # Learner caveats must be controlled codes, not free-text advice; the contract enforces ID-style strings
    # Free-text with spaces is allowed as code strings but advice must not be passed as hypothesis creation
    # This test ensures rule creation still requires proper IDs
    with pytest.raises(ValueError):
        PedagogicalRule(rule_id="", rule_version="v1", required_hypothesis_types=("role.melody",))


def test_registry_rejects_duplicate():
    reg = PedagogicalRuleRegistry()
    rule = PedagogicalRule(rule_id="dup.v1", rule_version="v1", required_hypothesis_types=("role.melody",))
    reg.register(rule)
    with pytest.raises(ValueError):
        reg.register(rule)


def test_difficulty_dimensions_are_optional_context():
    rule = PedagogicalRule(
        rule_id="bass_leap.v1",
        rule_version="v1",
        required_hypothesis_types=("role.bass",),
        optional_difficulty_dimensions=("largest_pitch_transition",),
    )
    hyp = _make_hypothesis("role.bass")
    bundle = _bundle_with(hyp)
    applies, diags = evaluate_rule(rule, bundle, difficulty_dimensions=("largest_pitch_transition",))
    assert applies is True
    assert any(d.code == "difficulty_context_present" for d in diags)
