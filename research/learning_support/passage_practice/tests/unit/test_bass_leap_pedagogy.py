"""Tests for S4.4 bass/leap targeting pedagogical hypothesis."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.pedagogy.bass_leap import build_bass_leap_hypothesis
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


def test_leap_positive_yields_hypothesis():
    bass = _hyp("role.bass", conf=0.82, criteria=("low_register", "lowest_voice"))
    bundle = _bundle(bass)
    hyp = build_bass_leap_hypothesis(bundle, leap_count=2)
    assert hyp is not None
    assert hyp.hypothesis_type == "pedagogy.bass_leap"
    assert hyp.source_passage_id == bundle.source_passage_id
    assert hyp.learner_question == "question.bass_leaps"
    assert hyp.candidate_objectives
    assert hyp.candidate_strategies


def test_smooth_bass_negative_returns_none():
    bass = _hyp("role.bass", conf=0.82, criteria=("low_register",))
    bundle = _bundle(bass)
    hyp = build_bass_leap_hypothesis(bundle, leap_count=0)
    assert hyp is None
    # Also without explicit leap_count and no leap criteria, should be None
    hyp2 = build_bass_leap_hypothesis(bundle)
    assert hyp2 is None


def test_learner_caveat_when_absent():
    bass = _hyp("role.bass", conf=0.85)
    bundle = _bundle(bass)
    hyp_no = build_bass_leap_hypothesis(bundle, leap_count=1, learner_feedback_present=False)
    hyp_yes = build_bass_leap_hypothesis(bundle, leap_count=1, learner_feedback_present=True)
    assert hyp_no is not None and hyp_yes is not None
    assert len(hyp_no.learner_caveats) > 0
    assert hyp_yes.learner_caveats == ()
    assert hyp_no.learner_question is not None
    assert hyp_yes.learner_question is None


def test_integration_with_real_bundle_and_observations():
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir
    from passage_practice.passages.selection import select_passage
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream
    from passage_practice.observations import observe_leap_frequency
    from passage_practice.passages.investigate import manual_investigation

    score = build_score_ir(load_musicxml_document(FIXTURES / "semantic_accompaniment_pattern.musicxml"))
    sel = select_passage(score, score_id="semantic_accompaniment_pattern.musicxml", start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    # Get leap count from observations
    inv = manual_investigation(score, score_id="semantic_accompaniment_pattern.musicxml", start=Fraction(0), end=Fraction(4), investigation_id="test.bass_leap")
    leap_result = observe_leap_frequency(inv, score)
    leap_cnt = leap_result.observations[0].value if leap_result.observations else 0
    hyp = build_bass_leap_hypothesis(bundle, leap_count=leap_cnt)
    # For accompaniment pattern, may not have bass; we test both paths
    if any(h.hypothesis_type == "role.bass" for h in bundle.hypotheses):
        # If bass present, leap presence determines
        if leap_cnt > 0:
            assert hyp is not None
        else:
            assert hyp is None
    else:
        # No bass => no hypothesis regardless of leap
        assert hyp is None


def test_missing_bass_returns_none():
    texture = _hyp("texture.arpeggiated", conf=0.8)
    bundle = _bundle(texture)
    hyp = build_bass_leap_hypothesis(bundle, leap_count=5)
    assert hyp is None
