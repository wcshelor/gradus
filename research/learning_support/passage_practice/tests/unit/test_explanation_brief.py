"""Tests for S8.4 evidence-grounded explanation brief."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from passage_practice.corpus.explanation_brief import ExplanationBrief, build_explanation_brief
from passage_practice.corpus.schema import PedagogicalCorpusRecord
from passage_practice.models.diagnostics import Diagnostic

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
        "left_hand_melody": "semantic_left_hand_melody.musicxml",
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
    path = CORPUS_FIX / f"{stem}.json"
    data = json.loads(path.read_text())
    return PedagogicalCorpusRecord.from_dict(data)


def test_unsupported_claims_absent():
    bundle = _bundle_for("top_voice_melody")
    corpus = _corpus_record("top_voice_melody")
    brief = build_explanation_brief(bundle, corpus)
    # Supported claims must be subset of bundle hypothesis types
    bundle_types = {h.hypothesis_type for h in bundle.hypotheses}
    for claim in brief.supported_claims:
        assert claim in bundle_types, f"unsupported claim {claim!r} not in bundle"
    # Must not invent harmony or learner trait claims not in bundle
    for claim in brief.supported_claims:
        assert not claim.startswith("learner_trait")  # never allowed
    # Check allowed families
    from passage_practice.corpus.explanation_brief import ALLOWED_CLAIM_FAMILIES

    for claim in brief.supported_claims:
        assert any(claim.startswith(f.rstrip(".")) for f in ALLOWED_CLAIM_FAMILIES)


def test_uncertainty_wording_fields_present():
    bundle = _bundle_for("top_voice_melody")
    brief = build_explanation_brief(bundle)
    assert brief.uncertainty_wording  # non-empty
    assert brief.confidence_bands
    # Each wording entry must have claim_type and wording
    for entry in brief.uncertainty_wording:
        assert "claim_type" in entry
        assert "wording" in entry
        assert entry["wording"] in ("likely", "may", "possible", "unsupported")
    for entry in brief.confidence_bands:
        assert "claim_type" in entry
        assert "band" in entry
        assert entry["band"] in ("high", "medium", "low", "unsupported")
    # Caveats must mention uncertainty
    assert any("uncertainty" in c for c in brief.caveats)


def test_round_trip_and_determinism():
    bundle = _bundle_for("top_voice_melody")
    corpus = _corpus_record("top_voice_melody")
    brief1 = build_explanation_brief(bundle, corpus)
    brief2 = build_explanation_brief(bundle, corpus)
    assert brief1 == brief2
    data = brief1.to_dict()
    revived = ExplanationBrief.from_dict(data)
    assert revived == brief1
    assert json.dumps(data, sort_keys=True) == json.dumps(revived.to_dict(), sort_keys=True)


def test_brief_without_corpus_context():
    bundle = _bundle_for("left_hand_melody")
    brief = build_explanation_brief(bundle, None)
    assert brief.corpus_record_id is None
    assert any("no_corpus_context" in c for c in brief.caveats)
    # Still grounded
    assert set(brief.supported_claims) <= {h.hypothesis_type for h in bundle.hypotheses}
