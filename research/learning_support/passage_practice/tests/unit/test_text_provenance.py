"""Tests for S8.2 source provenance fields for pedagogical text."""

from __future__ import annotations

import pytest

from passage_practice.corpus.text_provenance import PedagogicalText, TextSourceCategory
from passage_practice.models.diagnostics import Diagnostic, Severity


def _synthetic_text(category: TextSourceCategory, **overrides):
    base = dict(
        text_id="text.001",
        content="Synthetic pedagogical text for testing.",
        source_category=category,
        provenance="synthetic",
        diagnostics=(Diagnostic(code="synthetic_data", severity=Severity.INFO, message="synthetic"),),
    )
    base.update(overrides)
    return PedagogicalText(**base)


def test_all_four_categories_accepted():
    for cat in TextSourceCategory:
        overrides: dict = {}
        if cat == TextSourceCategory.LITERATURE_PARAPHRASE:
            overrides["source_ref"] = "lit.test.001"
        txt = _synthetic_text(cat, **overrides)
        assert txt.source_category == cat
        data = txt.to_dict()
        revived = PedagogicalText.from_dict(data)
        assert revived == txt


def test_literature_paraphrase_requires_source_ref():
    with pytest.raises(ValueError, match="source_ref"):
        _synthetic_text(TextSourceCategory.LITERATURE_PARAPHRASE, text_id="text.lit.missing")
    # Also via from_dict without source_ref
    data = _synthetic_text(
        TextSourceCategory.LITERATURE_PARAPHRASE,
        text_id="text.lit.ok",
        source_ref="lit.ok.001",
    ).to_dict()
    data.pop("source_ref")
    with pytest.raises(ValueError, match="source_ref"):
        PedagogicalText.from_dict(data)


def test_unsupported_category_rejected():
    data = _synthetic_text(TextSourceCategory.TEACHER_AUTHORED).to_dict()
    data["source_category"] = "unsupported_category"
    with pytest.raises(ValueError, match="unknown source_category"):
        PedagogicalText.from_dict(data)
    # Also test direct enum validation via string
    with pytest.raises((ValueError, TypeError)):
        PedagogicalText(
            text_id="text.002",
            content="x",
            source_category="not_a_category",  # type: ignore
            provenance="synthetic",
        )


def test_literature_paraphrase_carries_source_ref():
    txt = _synthetic_text(
        TextSourceCategory.LITERATURE_PARAPHRASE,
        text_id="text.lit.001",
        content="Paraphrased literature insight.",
        source_ref="lit.sight_reading.001",
        author_id="researcher.synthetic",
    )
    assert txt.source_ref == "lit.sight_reading.001"
    data = txt.to_dict()
    assert data["source_ref"] == "lit.sight_reading.001"
    revived = PedagogicalText.from_dict(data)
    assert revived.source_ref == "lit.sight_reading.001"


def test_system_generated_vs_teacher_authored_distinction():
    teacher = _synthetic_text(TextSourceCategory.TEACHER_AUTHORED, text_id="text.teacher.001", author_id="teacher.synthetic")
    system = _synthetic_text(TextSourceCategory.SYSTEM_GENERATED, text_id="text.system.001", author_id="system.v1")
    assert teacher.source_category != system.source_category
    assert teacher.to_dict()["source_category"] == "teacher_authored"
    assert system.to_dict()["source_category"] == "system_generated"


def test_synthetic_only_for_committed_fixtures():
    txt = _synthetic_text(TextSourceCategory.TEACHER_AUTHORED)
    assert txt.provenance == "synthetic"
    assert any(d.code == "synthetic_data" for d in txt.diagnostics)
    # Human provenance allowed but not for synthetic fixtures
    human = _synthetic_text(TextSourceCategory.TEACHER_AUTHORED, provenance="human", text_id="text.human.001")
    assert human.provenance == "human"
