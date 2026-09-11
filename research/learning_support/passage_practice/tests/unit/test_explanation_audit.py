"""Tests for S8.5 explanation-audit."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from passage_practice.corpus.explanation_audit import audit_explanation, mock_llm_explanation, template_explanation
from passage_practice.corpus.explanation_brief import build_explanation_brief

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CORPUS_FIX = FIXTURES / "corpus"


def _bundle_for(name: str):
    from passage_practice.passages.selection import select_passage
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    mapping = {
        "top_voice_melody": "semantic_top_voice_melody.musicxml",
        "accompaniment_pattern": "semantic_accompaniment_pattern.musicxml",
    }
    fname = mapping[name]
    score = build_score_ir(load_musicxml_document(FIXTURES / fname))
    sel = select_passage(score, score_id=fname, start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    return bundle


def _corpus_record(stem: str):
    from passage_practice.corpus.schema import PedagogicalCorpusRecord

    path = CORPUS_FIX / f"{stem}.json"
    data = json.loads(path.read_text())
    return PedagogicalCorpusRecord.from_dict(data)


def test_template_output_contains_no_unsupported_claims():
    bundle = _bundle_for("top_voice_melody")
    corpus = _corpus_record("top_voice_melody")
    brief = build_explanation_brief(bundle, corpus)
    text = template_explanation(brief)
    violations = audit_explanation(text, brief)
    assert violations == [], f"template introduced unsupported claims: {violations}"
    # Template must be deterministic
    assert template_explanation(brief) == text


def test_mock_llm_output_path_and_audit_detection():
    bundle = _bundle_for("accompaniment_pattern")
    # This bundle likely has texture/accompaniment but not harmony cadence
    brief = build_explanation_brief(bundle)
    # Grounded LLM path should pass
    good = mock_llm_explanation(brief, inject_unsupported=False)
    assert audit_explanation(good, brief) == []
    # Injected harmony claim should be flagged when brief lacks harmony
    # If brief already has harmony, choose a different injection: use learner
    # For this fixture, brief likely lacks harmony, so injection should violate
    bad = mock_llm_explanation(brief, inject_unsupported=True)
    violations = audit_explanation(bad, brief)
    # Should detect at least one violation (harmony) when harmony not supported
    bundle_types = {h.hypothesis_type for h in bundle.hypotheses}
    has_harmony = any(t.startswith("harmony.") for t in bundle_types)
    if not has_harmony:
        assert len(violations) >= 1
        assert any("harmony" in v["required_claim"] for v in violations)
    else:
        # If harmony already supported, injection is not a violation (grounded)
        assert violations == [] or any("harmony" in v["required_claim"] for v in violations)


def test_audit_catches_learner_claim_without_evidence():
    bundle = _bundle_for("top_voice_melody")
    brief = build_explanation_brief(bundle)
    # Brief without learner_issue should flag learner claim
    has_learner = any(t.startswith("learner_issue.") for t in brief.supported_claims)
    text_with_learner = "The learner finds this difficult due to hands together."
    violations = audit_explanation(text_with_learner, brief)
    if not has_learner:
        assert any("learner" in v["keyword"] for v in violations)
    else:
        assert violations == []


def test_audit_does_not_flag_supported_melody_claim():
    bundle = _bundle_for("top_voice_melody")
    # This bundle should have melody evidence
    has_melody = any("role.melody" in h.hypothesis_type for h in bundle.hypotheses)
    assert has_melody, "top_voice fixture should have melody hypothesis"
    brief = build_explanation_brief(bundle)
    text = "Melody likely in top voice."
    violations = audit_explanation(text, brief)
    assert violations == []
