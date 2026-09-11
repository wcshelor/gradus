"""Tests for S5.2 LearnerFeedbackSignal contract."""

from __future__ import annotations

import pytest

from passage_practice.learner_feedback.contracts import AnswerKind, LearnerFeedbackSignal, RetentionScope
from passage_practice.models.diagnostics import Diagnostic, Severity


def test_serialization_round_trip():
    sig = LearnerFeedbackSignal(
        feedback_id="fb.001",
        source_passage_id="test_passage@[0,4)/detection",
        prompt_id="hardest_aspect",
        answer_kind=AnswerKind.SELECTED_CHOICE,
        selected_value="melody_projection",
        method_id="test.v1",
        method_version="v1",
        retention_scope=RetentionScope.SESSION,
        diagnostics=(Diagnostic(code="synthetic_data", severity=Severity.INFO, message="synthetic"),),
    )
    data = sig.to_dict()
    revived = LearnerFeedbackSignal.from_dict(data)
    assert revived == sig


def test_missing_passage_rejected():
    with pytest.raises(ValueError):
        LearnerFeedbackSignal(
            feedback_id="fb.002",
            source_passage_id="",
            prompt_id="hardest_aspect",
            answer_kind=AnswerKind.SELECTED_CHOICE,
            selected_value="rhythm",
            method_id="test.v1",
            method_version="v1",
        )


def test_unsupported_answer_kind_rejected():
    with pytest.raises(ValueError):
        LearnerFeedbackSignal.from_dict(
            {
                "schema_version": "learner_feedback_signal.v1",
                "feedback_id": "fb.003",
                "source_passage_id": "test_passage@[0,4)/detection",
                "prompt_id": "hardest_aspect",
                "answer_kind": "unsupported_kind",
                "method_id": "test.v1",
                "method_version": "v1",
            }
        )


def test_synthetic_free_text_accepted():
    sig = LearnerFeedbackSignal(
        feedback_id="fb.004",
        source_passage_id="test_passage@[0,4)/detection",
        prompt_id="hardest_aspect",
        answer_kind=AnswerKind.FREE_TEXT,
        free_text="The jumps feel hard (synthetic)",
        method_id="test.v1",
        method_version="v1",
        diagnostics=(Diagnostic(code="synthetic_data", severity=Severity.INFO, message="synthetic"),),
    )
    data = sig.to_dict()
    revived = LearnerFeedbackSignal.from_dict(data)
    assert revived.free_text == "The jumps feel hard (synthetic)"
    assert revived.answer_kind == AnswerKind.FREE_TEXT


def test_selected_choice_requires_selected_value():
    with pytest.raises(ValueError):
        LearnerFeedbackSignal(
            feedback_id="fb.005",
            source_passage_id="test_passage@[0,4)/detection",
            prompt_id="hardest_aspect",
            answer_kind=AnswerKind.SELECTED_CHOICE,
            method_id="test.v1",
            method_version="v1",
        )
