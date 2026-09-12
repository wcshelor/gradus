"""Tests for S8.6 corpus evaluation checklist."""

from __future__ import annotations

from pathlib import Path

from passage_practice.corpus.evaluation import Checklist, load_checklist, evaluate_checklist, QUESTIONS, REQUIRED_DIMENSIONS


def test_checklist_covers_all_dimensions():
    checklist = load_checklist()
    assert checklist.covers_all_dimensions()
    result = evaluate_checklist(checklist)
    assert result["covers_all_dimensions"] is True
    for dim in REQUIRED_DIMENSIONS:
        assert result["dimensions"][dim] is True
    assert result["question_count"] == len(QUESTIONS)
    assert len(QUESTIONS) == 10


def test_checklist_questions_match_document():
    doc = Path(__file__).resolve().parents[2] / "docs" / "corpus_evaluation_checklist.md"
    assert doc.exists(), f"missing checklist doc {doc}"
    text = doc.read_text()
    for qid, question in QUESTIONS.items():
        assert qid in text, f"question {qid} missing from doc"
        assert question in text, f"question {qid} canonical text missing from doc: {question!r}"


def test_checklist_rejects_incomplete():
    import pytest

    with pytest.raises(ValueError):
        Checklist(version="corpus_evaluation_checklist.v1", questions=("P1", "P2"))

    # Wrong version
    with pytest.raises(ValueError):
        Checklist(version="wrong", questions=tuple(sorted(QUESTIONS)))


def test_no_real_participant_data():
    # Checklist must be synthetic-only; ensure no PII field
    checklist = load_checklist()
    assert "participant" not in str(checklist.questions).lower()
    doc = (Path(__file__).resolve().parents[2] / "docs" / "corpus_evaluation_checklist.md").read_text()
    assert "no real participant data" in doc.lower()
