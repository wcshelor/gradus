"""Tests for S5.4 feedback mapping rules."""

from __future__ import annotations

import pytest

from passage_practice.learner_feedback.contracts import AnswerKind, LearnerFeedbackSignal
from passage_practice.learner_feedback.mapping import map_feedback
from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.pedagogy.contracts import PedagogicalHypothesis
from fractions import Fraction


def _hyp(h_type: str) -> PedagogicalHypothesis:
    return PedagogicalHypothesis(
        hypothesis_id=f"test.{h_type.replace('.', '_')}.000",
        hypothesis_type=h_type,
        source_passage_id="test_passage@[0,4)/detection",
        supporting_semantic_ids=("sem.001",),
        confidence=0.7,
        confidence_method="heuristic",
        method_id="test.v1",
        method_version="v1",
    )


def _sig(prompt_id: str, selected_value: str, answer_kind: AnswerKind = AnswerKind.SELECTED_CHOICE) -> LearnerFeedbackSignal:
    return LearnerFeedbackSignal(
        feedback_id="fb.test",
        source_passage_id="test_passage@[0,4)/detection",
        prompt_id=prompt_id,
        answer_kind=answer_kind,
        selected_value=selected_value,
        method_id="test.v1",
        method_version="v1",
    )


def test_melody_answer_boosts_melody_projection():
    sig = _sig("hardest_aspect", "melody_stand_out")
    adj = map_feedback(sig)
    assert "pedagogy.melody_projection" in adj.boosted_ids
    assert not adj.preserved


def test_rhythm_answer_boosts_coordination():
    sig = _sig("hardest_aspect", "both_hands_together")
    adj = map_feedback(sig)
    assert "pedagogy.rhythmic_coordination" in adj.boosted_ids

    sig2 = _sig("rhythm", "hands_together_hard")
    adj2 = map_feedback(sig2)
    assert "pedagogy.rhythmic_coordination" in adj2.boosted_ids


def test_something_else_preserves_score_hypotheses():
    sig = _sig("hardest_aspect", "something_else")
    adj = map_feedback(sig)
    assert adj.preserved is True
    assert adj.boosted_ids == ()
    assert any(d.code == "feedback_preserved" for d in adj.diagnostics)

    sig2 = LearnerFeedbackSignal(
        feedback_id="fb.test2",
        source_passage_id="test_passage@[0,4)/detection",
        prompt_id="hardest_aspect",
        answer_kind=AnswerKind.SOMETHING_ELSE,
        selected_value="something_else",
        method_id="test.v1",
        method_version="v1",
    )
    adj2 = map_feedback(sig2)
    assert adj2.preserved is True


def test_melody_hidden_boosts_melody_projection():
    sig = _sig("melody_projection", "melody_hidden")
    adj = map_feedback(sig)
    assert "pedagogy.melody_projection" in adj.boosted_ids


def test_not_sure_requests_more_evidence():
    sig = _sig("melody_projection", "not_sure")
    adj = map_feedback(sig)
    assert adj.request_more_evidence is True
