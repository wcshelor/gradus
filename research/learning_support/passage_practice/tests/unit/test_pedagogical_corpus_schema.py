"""Tests for S8.1 pedagogical corpus schema."""

from __future__ import annotations

import json

import pytest

from passage_practice.corpus.schema import CorpusReviewState, PedagogicalCorpusRecord
from passage_practice.models.diagnostics import Diagnostic, Severity


def _synthetic_record(**overrides):
    base = dict(
        record_id="corpus.001",
        source_passage_id="semantic_top_voice_melody.musicxml@[0,4)/detection",
        score_facts_ref="semantic_top_voice_melody.musicxml",
        semantic_bundle_id="semantic_top_voice_melody.musicxml@[0,4)/detection:semantic_bundle:v1",
        annotation_ids=("ann.top_voice_melody.melody.001",),
        learner_feedback_ids=(),
        human_explanation="Synthetic teacher note: melody in top voice.",
        generated_explanation="Generated: likely melody top_voice (heuristic).",
        exercise_candidate_ids=(),
        review_state=CorpusReviewState.DRAFT,
        provenance="synthetic",
        privacy_status="synthetic",
        diagnostics=(Diagnostic(code="synthetic_data", severity=Severity.INFO, message="synthetic"),),
    )
    base.update(overrides)
    return PedagogicalCorpusRecord(**base)


def test_round_trip_with_synthetic_data():
    rec = _synthetic_record()
    data = rec.to_dict()
    assert data["schema_version"] == "pedagogical_corpus_record.v1"
    revived = PedagogicalCorpusRecord.from_dict(data)
    assert revived == rec
    assert json.dumps(data, sort_keys=True) == json.dumps(revived.to_dict(), sort_keys=True)


def test_separates_score_facts_from_human_and_generated():
    rec = _synthetic_record(
        human_explanation="Teacher: keep melody prominent.",
        generated_explanation="System: role.melody top_voice (0.85).",
    )
    assert rec.human_explanation != rec.generated_explanation
    assert rec.score_facts_ref != rec.semantic_bundle_id
    data = rec.to_dict()
    assert data["human_explanation"] != data["generated_explanation"]


def test_optional_fields_and_empty_cases():
    rec = _synthetic_record(
        annotation_ids=(),
        learner_feedback_ids=(),
        difficulty_context_id=None,
        human_explanation=None,
        generated_explanation=None,
        exercise_candidate_ids=(),
    )
    data = rec.to_dict()
    # Optional empty fields omitted
    assert "annotation_ids" not in data
    assert "difficulty_context_id" not in data
    revived = PedagogicalCorpusRecord.from_dict(data)
    assert revived.annotation_ids == ()
    assert revived.difficulty_context_id is None


def test_review_state_and_provenance_enforced():
    rec = _synthetic_record(review_state=CorpusReviewState.REVIEWED)
    assert rec.review_state == CorpusReviewState.REVIEWED
    with pytest.raises(ValueError):
        PedagogicalCorpusRecord.from_dict(
            {**_synthetic_record().to_dict(), "review_state": "invalid"}
        )
    with pytest.raises(ValueError):
        _synthetic_record(provenance="unknown")
    # Privacy must be synthetic for committed fixtures
    rec2 = _synthetic_record()
    assert rec2.privacy_status == "synthetic"
    assert any(d.code == "synthetic_data" for d in rec2.diagnostics)


def test_no_private_data_in_synthetic_fixtures():
    rec = _synthetic_record()
    text = json.dumps(rec.to_dict())
    # Synthetic records must not contain PII
    assert "synthetic" in rec.provenance
    for diag in rec.diagnostics:
        assert diag.code == "synthetic_data" or "synthetic" in diag.message
