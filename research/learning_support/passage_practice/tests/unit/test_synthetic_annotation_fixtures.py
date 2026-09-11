"""Tests for S7.3 synthetic annotation fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from passage_practice.annotation.contracts import AnnotationRecord, AnnotatorRole, PrivacyStatus
from passage_practice.models.diagnostics import Diagnostic

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "annotation"
SEMANTIC_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_fixture_validity():
    for path in FIXTURES.glob("*.json"):
        if path.name == "manifest.json":
            continue
        data = json.loads(path.read_text())
        assert isinstance(data, list) and len(data) > 0, f"{path} empty"
        for rec_dict in data:
            rec = AnnotationRecord.from_dict(rec_dict)
            assert rec.annotator_role == AnnotatorRole.SYNTHETIC
            assert rec.privacy_status == PrivacyStatus.SYNTHETIC
            assert rec.provenance == "synthetic"
            # Round-trip deterministic
            assert AnnotationRecord.from_dict(rec.to_dict()) == rec


def test_annotation_to_passage_reference_resolution():
    from fractions import Fraction
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir
    from passage_practice.passages.selection import select_passage

    mapping = {
        "top_voice_melody": "semantic_top_voice_melody.musicxml",
        "left_hand_melody": "semantic_left_hand_melody.musicxml",
        "accompaniment_pattern": "semantic_accompaniment_pattern.musicxml",
        "syncopation": "semantic_syncopation.musicxml",
        "ambiguity": "semantic_ambiguity.musicxml",
    }
    for name, musicxml in mapping.items():
        ann_path = FIXTURES / f"{name}.json"
        data = json.loads(ann_path.read_text())
        score = build_score_ir(load_musicxml_document(SEMANTIC_FIXTURES / musicxml))
        sel = select_passage(score, score_id=musicxml, start=Fraction(0), end=Fraction(4))
        assert sel.passage.passage_id.endswith("/detection")
        for rec_dict in data:
            rec = AnnotationRecord.from_dict(rec_dict)
            # Annotation passage should match selected passage (suffix may include file prefix)
            assert rec.source_passage_id == sel.passage.passage_id, f"{name} mismatch {rec.source_passage_id} vs {sel.passage.passage_id}"
            # No private data: ensure no real learner IDs
            assert "learner" not in rec.annotation_id or "synthetic" in rec.annotation_id or rec.annotator_role == AnnotatorRole.SYNTHETIC
