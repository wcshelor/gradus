"""Tests for S4.5 rhythmic coordination pedagogical hypothesis."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.pedagogy.rhythmic_coordination import build_rhythmic_coordination_hypothesis
from passage_practice.semantics.contracts import SemanticBundle, SemanticHypothesis

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=1, measure_number="1", offset_in_measure=q)


def _hyp(h_type: str, conf: float = 0.8, criteria=(), contradictory=()) -> SemanticHypothesis:
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
    )


def _bundle(*hyps) -> SemanticBundle:
    return SemanticBundle(
        bundle_id="test_passage@[0,4)/detection:bundle:v1",
        source_passage_id="test_passage@[0,4)/detection",
        hypotheses=tuple(hyps),
        ranked_hypothesis_ids=tuple(h.hypothesis_id for h in hyps),
    )


def test_aligned_hands_negative_returns_none():
    # Aligned hands bundle has common_attack but no independent_hands
    aligned = _hyp("rhythm.common_attack_skeleton", conf=0.8, criteria=("common_attacks",))
    bundle = _bundle(aligned)
    hyp = build_rhythmic_coordination_hypothesis(bundle)
    assert hyp is None


def test_staggered_hands_positive_yields_hypothesis():
    indep = _hyp("rhythm.independent_hands", conf=0.82, criteria=("staggered_onsets",))
    bundle = _bundle(indep)
    hyp = build_rhythmic_coordination_hypothesis(bundle, hand_alignment_ratio=20)
    assert hyp is not None
    assert hyp.hypothesis_type == "pedagogy.rhythmic_coordination"
    assert hyp.learner_question == "question.hands_together"
    # High staggered but moderate alignment still positive


def test_low_confidence_when_rhythm_evidence_incomplete():
    indep_low = _hyp("rhythm.independent_hands", conf=0.55, criteria=("staggered_onsets",))
    bundle = _bundle(indep_low)
    hyp = build_rhythmic_coordination_hypothesis(bundle, hand_alignment_ratio=None)
    assert hyp is not None
    # Incomplete evidence should lower confidence vs original
    assert hyp.confidence < 0.55
    assert any(d.code == "rhythm_evidence_incomplete" for d in hyp.diagnostics)


def test_hand_alignment_high_contradicts():
    indep = _hyp("rhythm.independent_hands", conf=0.85)
    bundle = _bundle(indep)
    hyp = build_rhythmic_coordination_hypothesis(bundle, hand_alignment_ratio=90)
    assert hyp is None


def test_learner_caveat():
    indep = _hyp("rhythm.independent_hands", conf=0.8)
    bundle = _bundle(indep)
    hyp_no = build_rhythmic_coordination_hypothesis(bundle, hand_alignment_ratio=20, learner_feedback_present=False)
    hyp_yes = build_rhythmic_coordination_hypothesis(bundle, hand_alignment_ratio=20, learner_feedback_present=True)
    assert hyp_no is not None and hyp_yes is not None
    assert len(hyp_no.learner_caveats) > 0
    assert hyp_yes.learner_caveats == ()


def test_integration_with_real_bundle():
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir
    from passage_practice.passages.selection import select_passage
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream

    score = build_score_ir(load_musicxml_document(FIXTURES / "semantic_syncopation.musicxml"))
    sel = select_passage(score, score_id="semantic_syncopation.musicxml", start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    # This fixture has syncopation but check independent_hands presence
    has_indep = any(h.hypothesis_type == "rhythm.independent_hands" for h in bundle.hypotheses)
    hyp = build_rhythmic_coordination_hypothesis(bundle, hand_alignment_ratio=30)
    if has_indep:
        assert hyp is not None
    else:
        assert hyp is None
