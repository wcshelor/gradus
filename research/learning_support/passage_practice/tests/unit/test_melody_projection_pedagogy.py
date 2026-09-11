"""Tests for S4.3 melody-projection pedagogical hypothesis."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.pedagogy.melody_projection import build_melody_projection_hypothesis
from passage_practice.semantics.contracts import SemanticBundle, SemanticHypothesis

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=1, measure_number="1", offset_in_measure=q)


def _hyp(h_type: str, conf: float = 0.8, criteria=(), contradictory=(), missing=()) -> SemanticHypothesis:
    return SemanticHypothesis(
        hypothesis_id=f"test.{h_type.replace('.', '_')}.000",
        hypothesis_type=h_type,
        source_passage_id="test_passage@[0,4)/detection",
        covered_region=ScoreInterval(start=_pos(Fraction(0)), end=_pos(Fraction(4))),
        covered_event_ids=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
        confidence=conf,
        confidence_method="heuristic",
        method_id="test.v1",
        method_version="v1",
        satisfied_criteria=tuple(criteria),
        contradictory_criteria=tuple(contradictory),
        missing_evidence=tuple(missing),
    )


def _bundle(*hyps) -> SemanticBundle:
    return SemanticBundle(
        bundle_id="test_passage@[0,4)/detection:bundle:v1",
        source_passage_id="test_passage@[0,4)/detection",
        hypotheses=tuple(hyps),
        ranked_hypothesis_ids=tuple(h.hypothesis_id for h in hyps),
    )


def test_evidence_present_yields_hypothesis():
    melody = _hyp("role.melody", conf=0.85, criteria=("top_voice",))
    texture = _hyp("texture.melody_plus_accompaniment", conf=0.8, criteria=("melody_plus_arpeggiated",))
    bundle = _bundle(melody, texture)
    hyp = build_melody_projection_hypothesis(bundle)
    assert hyp is not None
    assert hyp.hypothesis_type == "pedagogy.melody_projection"
    assert hyp.source_passage_id == bundle.source_passage_id
    assert hyp.learner_question == "question.melody_hidden"
    assert "pedagogy.melody_projection" in hyp.hypothesis_type


def test_learner_data_absent_adds_caveat():
    melody = _hyp("role.melody", conf=0.85)
    texture = _hyp("texture.melody_plus_accompaniment")
    bundle = _bundle(melody, texture)
    hyp_no_learner = build_melody_projection_hypothesis(bundle, learner_feedback_present=False)
    hyp_with_learner = build_melody_projection_hypothesis(bundle, learner_feedback_present=True)
    assert hyp_no_learner is not None and hyp_with_learner is not None
    assert len(hyp_no_learner.learner_caveats) > 0
    assert hyp_with_learner.learner_caveats == ()
    assert hyp_no_learner.learner_question is not None
    assert hyp_with_learner.learner_question is None


def test_contradiction_blocks_or_reduces_confidence():
    melody = _hyp("role.melody", conf=0.85, criteria=("monophonic_texture",))
    bundle = _bundle(melody)
    hyp = build_melody_projection_hypothesis(bundle)
    # Contradiction via contraindication monophonic_texture should prevent hypothesis
    assert hyp is None


def test_confidence_derived_from_semantics():
    melody = _hyp("role.melody", conf=0.9)
    texture = _hyp("texture.melody_plus_accompaniment", conf=0.9)
    bundle = _bundle(melody, texture)
    hyp = build_melody_projection_hypothesis(bundle)
    assert hyp is not None
    # Base conf min=0.9, no texture missing, learner absent => 0.9*0.9=0.81
    assert abs(hyp.confidence - 0.81) < 1e-6
    # With texture support missing, confidence lower
    bundle2 = _bundle(melody)
    hyp2 = build_melody_projection_hypothesis(bundle2)
    assert hyp2 is not None
    assert hyp2.confidence < hyp.confidence


def test_integration_with_real_bundle():
    # Use real semantic bundle from regression
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir
    from passage_practice.passages.selection import select_passage
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream

    score = build_score_ir(load_musicxml_document(FIXTURES / "semantic_top_voice_melody.musicxml"))
    sel = select_passage(score, score_id="semantic_top_voice_melody.musicxml", start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    hyp = build_melody_projection_hypothesis(bundle)
    assert hyp is not None
    assert hyp.learner_question == "question.melody_hidden"
    assert hyp.candidate_objectives
    assert hyp.candidate_strategies
