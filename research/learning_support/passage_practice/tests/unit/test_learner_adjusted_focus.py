"""Tests for S5.5 LearnerAdjustedFocus contract."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.learner_feedback.adjusted_focus import build_learner_adjusted_focus
from passage_practice.learner_feedback.contracts import AnswerKind, LearnerFeedbackSignal
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.pedagogy.contracts import PedagogicalHypothesis

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=1, measure_number="1", offset_in_measure=q)


def _ped_hyp(h_type: str, conf: float = 0.7) -> PedagogicalHypothesis:
    return PedagogicalHypothesis(
        hypothesis_id=f"test.{h_type.replace('.', '_')}.000",
        hypothesis_type=h_type,
        source_passage_id="test_passage@[0,4)/detection",
        supporting_semantic_ids=("sem.001",),
        confidence=conf,
        confidence_method="heuristic",
        method_id="test.v1",
        method_version="v1",
    )


def _bundle():
    from passage_practice.semantics.contracts import SemanticBundle, SemanticHypothesis

    hyp = SemanticHypothesis(
        hypothesis_id="test.role_melody.000",
        hypothesis_type="role.melody",
        source_passage_id="test_passage@[0,4)/detection",
        covered_region=ScoreInterval(start=_pos(Fraction(0)), end=_pos(Fraction(4))),
        covered_event_ids=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
        confidence=0.8,
        confidence_method="heuristic",
        method_id="test.v1",
        method_version="v1",
    )
    return SemanticBundle(
        bundle_id="test_passage@[0,4)/detection:bundle:v1",
        source_passage_id="test_passage@[0,4)/detection",
        hypotheses=(hyp,),
        ranked_hypothesis_ids=(hyp.hypothesis_id,),
    )


def _sig(prompt_id: str, selected_value: str) -> LearnerFeedbackSignal:
    return LearnerFeedbackSignal(
        feedback_id=f"fb.{prompt_id}.{selected_value}",
        source_passage_id="test_passage@[0,4)/detection",
        prompt_id=prompt_id,
        answer_kind=AnswerKind.SELECTED_CHOICE,
        selected_value=selected_value,
        method_id="test.v1",
        method_version="v1",
    )


def test_original_bundle_unchanged():
    bundle = _bundle()
    orig_dict = bundle.to_dict()
    hyps = (_ped_hyp("pedagogy.melody_projection", 0.8), _ped_hyp("pedagogy.bass_leap", 0.6))
    sigs = (_sig("hardest_aspect", "melody_stand_out"),)
    _ = build_learner_adjusted_focus(bundle, hyps, sigs)
    assert bundle.to_dict() == orig_dict


def test_deterministic_output():
    bundle = _bundle()
    hyps = (_ped_hyp("pedagogy.melody_projection", 0.8), _ped_hyp("pedagogy.rhythmic_coordination", 0.7))
    sigs = (_sig("hardest_aspect", "both_hands_together"),)
    a1 = build_learner_adjusted_focus(bundle, hyps, sigs)
    a2 = build_learner_adjusted_focus(bundle, hyps, sigs)
    assert a1.to_dict() == a2.to_dict()
    # Round-trip
    revived = type(a1).from_dict(a1.to_dict())
    assert revived == a1


def test_primary_focus_after_boost():
    bundle = _bundle()
    mel = _ped_hyp("pedagogy.melody_projection", 0.75)
    rhythm = _ped_hyp("pedagogy.rhythmic_coordination", 0.80)
    # Base order rhythm > melody, but feedback boosts melody
    hyps = (rhythm, mel)
    sig = _sig("melody_projection", "melody_hidden")
    adjusted = build_learner_adjusted_focus(bundle, hyps, (sig,))
    assert adjusted.primary_focus == "pedagogy.melody_projection"
    assert "pedagogy.rhythmic_coordination" in adjusted.secondary_focuses


def test_feedback_ids_preserved():
    bundle = _bundle()
    hyps = (_ped_hyp("pedagogy.melody_projection"),)
    sigs = (_sig("rhythm", "hands_together_hard"), _sig("jumps", "jumps_hard"))
    adjusted = build_learner_adjusted_focus(bundle, hyps, sigs)
    assert set(adjusted.feedback_ids) == {s.feedback_id for s in sigs}
    assert adjusted.base_semantic_bundle_id == bundle.bundle_id


def test_empty_feedback_preserves_ranking():
    bundle = _bundle()
    hyps = (_ped_hyp("pedagogy.melody_projection", 0.8), _ped_hyp("pedagogy.bass_leap", 0.6))
    adjusted = build_learner_adjusted_focus(bundle, hyps, ())
    assert adjusted.ranked_hypothesis_ids == tuple(h.hypothesis_type for h in hyps)
    assert "no feedback" in adjusted.rationale
