"""Tests for S4.6 reading-load pedagogical hypothesis."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.pedagogy.reading_load import build_reading_load_hypothesis
from passage_practice.semantics.contracts import SemanticBundle, SemanticHypothesis


def _pos(q: Fraction) -> ScorePosition:
    return ScorePosition(quarters=q, measure_index=1, measure_number="1", offset_in_measure=q)


def _hyp(h_type: str = "role.melody", conf: float = 0.8) -> SemanticHypothesis:
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
    )


def _bundle(*hyps) -> SemanticBundle:
    if not hyps:
        hyps = (_hyp(),)
    return SemanticBundle(
        bundle_id="test_passage@[0,4)/detection:bundle:v1",
        source_passage_id="test_passage@[0,4)/detection",
        hypotheses=tuple(hyps),
        ranked_hypothesis_ids=tuple(h.hypothesis_id for h in hyps),
    )


def test_missing_layout_unavailable_not_zero():
    bundle = _bundle()
    hyp = build_reading_load_hypothesis(bundle, accidental_count=2, layout_available=False)
    assert hyp is not None
    assert "layout_data_unavailable" in hyp.missing_evidence
    assert any(d.code == "reading_missing_evidence" for d in hyp.diagnostics)


def test_accidentals_alone_not_overclaimed():
    bundle = _bundle()
    hyp_alone = build_reading_load_hypothesis(bundle, accidental_count=1, layout_available=True)
    hyp_combined = build_reading_load_hypothesis(bundle, accidental_count=1, syncopation_proxy_count=1, has_low_redundancy=True, layout_available=True)
    assert hyp_alone is not None and hyp_combined is not None
    assert hyp_alone.confidence < 0.45  # not overclaimed
    assert hyp_combined.confidence > hyp_alone.confidence


def test_combined_evidence_higher():
    bundle = _bundle()
    hyp_one = build_reading_load_hypothesis(bundle, accidental_count=2, layout_available=True)
    hyp_three = build_reading_load_hypothesis(bundle, accidental_count=2, syncopation_proxy_count=2, shortest_duration_ticks=120, has_low_redundancy=True, layout_available=True)
    assert hyp_one is not None and hyp_three is not None
    assert hyp_three.confidence > hyp_one.confidence
    assert any(d.code == "combined_reading_evidence_higher" for d in hyp_three.diagnostics)


def test_no_evidence_returns_none():
    bundle = _bundle()
    hyp = build_reading_load_hypothesis(bundle, accidental_count=0, layout_available=True)
    assert hyp is None


def test_learner_caveat():
    bundle = _bundle()
    hyp_no = build_reading_load_hypothesis(bundle, accidental_count=2, learner_feedback_present=False, layout_available=True)
    hyp_yes = build_reading_load_hypothesis(bundle, accidental_count=2, learner_feedback_present=True, layout_available=True)
    assert hyp_no is not None and hyp_yes is not None
    assert len(hyp_no.learner_caveats) > 0
    assert hyp_yes.learner_caveats == ()


def test_integration_with_real_observations():
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir
    from passage_practice.passages.selection import select_passage
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream
    from passage_practice.observations import observe_accidental_density, observe_syncopation_proxy, observe_shortest_duration
    from passage_practice.passages.investigate import manual_investigation

    FIX = Path(__file__).resolve().parents[1] / "fixtures"
    score = build_score_ir(load_musicxml_document(FIX / "semantic_ambiguity.musicxml"))
    sel = select_passage(score, score_id="semantic_ambiguity.musicxml", start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    inv = manual_investigation(score, score_id="semantic_ambiguity.musicxml", start=Fraction(0), end=Fraction(4), investigation_id="test.reading")
    acc = observe_accidental_density(inv, score)
    sync = observe_syncopation_proxy(inv, score)
    short = observe_shortest_duration(inv, score)
    acc_cnt = acc.observations[0].value if acc.observations else 0
    sync_cnt = sync.observations[0].value if sync.observations else 0
    short_ticks = short.observations[0].value if short.observations else None
    hyp = build_reading_load_hypothesis(bundle, accidental_count=acc_cnt, syncopation_proxy_count=sync_cnt, shortest_duration_ticks=short_ticks, layout_available=False)
    # May be None if acc_cnt 0 and no sync/short; check consistency
    if acc_cnt == 0 and sync_cnt == 0 and short_ticks is None:
        assert hyp is None or "layout_data_unavailable" in hyp.missing_evidence
    else:
        if hyp is not None:
            assert "layout_data_unavailable" in hyp.missing_evidence
