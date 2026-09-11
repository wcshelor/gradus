"""Tests for S7.4 heuristic baseline export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from passage_practice.annotation.contracts import AnnotationRecord
from passage_practice.annotation.export import export_baseline_comparison
from passage_practice.semantics.bundle_builder import build_semantic_bundle
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.written_stream import build_written_stream
from passage_practice.passages.selection import select_passage
from fractions import Fraction

FIX = Path(__file__).resolve().parents[1] / "fixtures"
ANNOT = FIX / "annotation"


def _bundle_for(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    score = build_score_ir(load_musicxml_document(FIX / name))
    sel = select_passage(score, score_id=name, start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    return bundle


def test_stable_columns_and_method_versions():
    bundle = _bundle_for("semantic_top_voice_melody.musicxml")
    data = json.loads((ANNOT / "top_voice_melody.json").read_text())
    anns = tuple(AnnotationRecord.from_dict(d) for d in data)
    rows = export_baseline_comparison(bundle, anns)
    assert len(rows) == len(anns)
    for row in rows:
        assert "source_passage_id" in row
        assert "annotation_id" in row
        assert "label_family" in row
        assert "label_value" in row
        assert "detector_hypothesis_types" in row
        assert "detector_method_versions" in row
        assert "source_refs" in row
        # Stable columns: method versions include expected detector IDs
        assert any("melody_salience.v1@v1" in m for m in row["detector_method_versions"])


def test_source_refs_and_determinism():
    bundle = _bundle_for("semantic_top_voice_melody.musicxml")
    data = json.loads((ANNOT / "top_voice_melody.json").read_text())
    anns = tuple(AnnotationRecord.from_dict(d) for d in data)
    rows1 = export_baseline_comparison(bundle, anns)
    rows2 = export_baseline_comparison(bundle, anns)
    assert rows1 == rows2
    # Source refs should be resolvable and sorted
    for row in rows1:
        assert row["source_refs"] == sorted(row["source_refs"])


def test_empty_annotations_still_exports():
    bundle = _bundle_for("semantic_ambiguity.musicxml")
    rows = export_baseline_comparison(bundle, ())
    assert rows == []
