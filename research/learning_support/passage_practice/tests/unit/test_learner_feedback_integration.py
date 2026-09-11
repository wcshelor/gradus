"""S5.6 feedback integration tests — passage -> semantic -> pedagogy -> feedback -> adjusted focus.

Covers increase, decrease, reject, and no-op cases, with original bundle
preservation check.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.learner_feedback.adjusted_focus import build_learner_adjusted_focus
from passage_practice.learner_feedback.contracts import AnswerKind, LearnerFeedbackSignal
from passage_practice.semantics.bundle_builder import build_semantic_bundle
from passage_practice.pedagogy.integration import build_pedagogical_report
from passage_practice.passages.selection import select_passage
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.written_stream import build_written_stream

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _bundle_and_report(name: str):
    score = _load(name)
    sel = select_passage(score, score_id=name, start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    report = build_pedagogical_report(bundle)
    return bundle, report


def test_increase_melody_hidden_boosts():
    bundle, report = _bundle_and_report("semantic_top_voice_melody.musicxml")
    # This fixture has melody projection; boost it via feedback
    sig = LearnerFeedbackSignal(
        feedback_id="fb.increase.001",
        source_passage_id=bundle.source_passage_id,
        prompt_id="melody_projection",
        answer_kind=AnswerKind.SELECTED_CHOICE,
        selected_value="melody_hidden",
        method_id="test.v1",
        method_version="v1",
    )
    hyps = report.pedagogical_hypotheses
    # Ensure melody projection is present in base
    assert any(h.hypothesis_type == "pedagogy.melody_projection" for h in hyps)
    adjusted = build_learner_adjusted_focus(bundle, hyps, (sig,))
    assert adjusted.primary_focus == "pedagogy.melody_projection"
    # Verify boosted diagnostic present
    assert any(d.code == "feedback_boosted" for d in adjusted.diagnostics)


def test_decrease_hands_together_ok_demotes():
    bundle, report = _bundle_and_report("semantic_syncopation.musicxml")
    hyps = report.pedagogical_hypotheses
    # For syncopation, rhythmic coordination may be present; use demoting feedback
    # Choose a passage that yields rhythmic coordination, or synthesize hyps directly
    # If no rhythmic hypothesis in this fixture, synthesize a minimal set
    from passage_practice.pedagogy.contracts import PedagogicalHypothesis

    # Ensure we have a rhythmic hypothesis to demote
    rhythmic = PedagogicalHypothesis(
        hypothesis_id=f"{bundle.source_passage_id}:rhythmic_coordination:test",
        hypothesis_type="pedagogy.rhythmic_coordination",
        source_passage_id=bundle.source_passage_id,
        supporting_semantic_ids=("sem.001",),
        confidence=0.70,
        confidence_method="heuristic",
        method_id="test.v1",
        method_version="v1",
    )
    melody = PedagogicalHypothesis(
        hypothesis_id=f"{bundle.source_passage_id}:melody_projection:test",
        hypothesis_type="pedagogy.melody_projection",
        source_passage_id=bundle.source_passage_id,
        supporting_semantic_ids=("sem.002",),
        confidence=0.65,
        confidence_method="heuristic",
        method_id="test.v1",
        method_version="v1",
    )
    hyps2 = (rhythmic, melody)
    sig = LearnerFeedbackSignal(
        feedback_id="fb.decrease.001",
        source_passage_id=bundle.source_passage_id,
        prompt_id="rhythm",
        answer_kind=AnswerKind.SELECTED_CHOICE,
        selected_value="hands_together_ok",
        method_id="test.v1",
        method_version="v1",
    )
    adjusted = build_learner_adjusted_focus(bundle, hyps2, (sig,))
    # hands_together_ok demotes rhythmic coordination
    assert "pedagogy.rhythmic_coordination" in adjusted.deprioritized_ids
    assert adjusted.primary_focus != "pedagogy.rhythmic_coordination"


def test_reject_something_else_preserves():
    bundle, report = _bundle_and_report("semantic_top_voice_melody.musicxml")
    hyps = report.pedagogical_hypotheses
    orig_order = tuple(h.hypothesis_type for h in hyps)
    sig = LearnerFeedbackSignal(
        feedback_id="fb.reject.001",
        source_passage_id=bundle.source_passage_id,
        prompt_id="hardest_aspect",
        answer_kind=AnswerKind.SOMETHING_ELSE,
        selected_value="something_else",
        method_id="test.v1",
        method_version="v1",
    )
    adjusted = build_learner_adjusted_focus(bundle, hyps, (sig,))
    # Preserved: ranking unchanged except demoted empty
    assert adjusted.ranked_hypothesis_ids == orig_order
    assert any(d.code == "feedback_preserved_in_focus" for d in adjusted.diagnostics)


def test_no_op_not_sure_requests_evidence():
    bundle, report = _bundle_and_report("semantic_top_voice_melody.musicxml")
    hyps = report.pedagogical_hypotheses
    sig = LearnerFeedbackSignal(
        feedback_id="fb.noop.001",
        source_passage_id=bundle.source_passage_id,
        prompt_id="melody_projection",
        answer_kind=AnswerKind.SELECTED_CHOICE,
        selected_value="not_sure",
        method_id="test.v1",
        method_version="v1",
    )
    adjusted = build_learner_adjusted_focus(bundle, hyps, (sig,))
    assert any(d.code == "request_more_evidence" for d in adjusted.diagnostics)
    # No boost/demote, preserved ranking
    assert adjusted.primary_focus == (hyps[0].hypothesis_type if hyps else None)


def test_original_bundle_unchanged_through_full_pipeline():
    bundle, report = _bundle_and_report("semantic_ambiguity.musicxml")
    orig_dict = bundle.to_dict()
    sig = LearnerFeedbackSignal(
        feedback_id="fb.preserve.001",
        source_passage_id=bundle.source_passage_id,
        prompt_id="hardest_aspect",
        answer_kind=AnswerKind.SELECTED_CHOICE,
        selected_value="melody_stand_out",
        method_id="test.v1",
        method_version="v1",
    )
    _ = build_learner_adjusted_focus(bundle, report.pedagogical_hypotheses, (sig,))
    assert bundle.to_dict() == orig_dict
