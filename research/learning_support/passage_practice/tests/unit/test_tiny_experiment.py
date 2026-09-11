"""Tests for S7.6 tiny learned-model experiment plumbing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from passage_practice.annotation.contracts import AnnotationRecord
from passage_practice.semantics.tiny_experiment import run_tiny_experiment
from passage_practice.semantics.bundle_builder import build_semantic_bundle
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.written_stream import build_written_stream
from passage_practice.passages.selection import select_passage
from fractions import Fraction
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir

FIX = Path(__file__).resolve().parents[1] / "fixtures"
ANNOT = FIX / "annotation"


def _bundle_and_anns(name: str):
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
    anns = tuple(AnnotationRecord.from_dict(d) for d in json.loads((ANNOT / f"{name.split('.')[0]}.json").read_text())) if (ANNOT / f"{name.split('.')[0]}.json").exists() else ()
    # Map semantic_top_voice -> top_voice
    if not anns:
        # Try alternative naming
        alt = name.replace("semantic_", "")
        p = ANNOT / f"{alt.split('.')[0]}.json"
        if p.exists():
            anns = tuple(AnnotationRecord.from_dict(d) for d in json.loads(p.read_text()))
    return bundle, anns


def test_model_output_contract():
    bundle, anns = _bundle_and_anns("semantic_top_voice_melody.musicxml")
    result = run_tiny_experiment([bundle], [anns])
    assert "model_rows" in result
    assert "heuristic_rows" in result
    # Model rows should have same columns and method version
    for row in result["model_rows"]:
        assert "detector_hypothesis_types" in row
        assert "detector_method_versions" in row
        assert any("fake_model.v1@fake_model.v1" in m for m in row["detector_method_versions"])


def test_abstention_behavior():
    # Create an empty bundle that will cause model to still produce (fake model always produces)
    # Instead test abstention count is deterministic and plumbing works for empty annotations
    bundle, anns = _bundle_and_anns("semantic_ambiguity.musicxml")
    result = run_tiny_experiment([bundle], [anns])
    assert isinstance(result["abstention_count"], int)
    # Fake model never abstains in this tiny experiment (always produces one hyp)
    assert result["abstention_count"] == 0


def test_comparison_to_heuristic_baseline():
    bundle1, anns1 = _bundle_and_anns("semantic_top_voice_melody.musicxml")
    bundle2, anns2 = _bundle_and_anns("semantic_accompaniment_pattern.musicxml")
    result = run_tiny_experiment([bundle1, bundle2], [anns1, anns2])
    comp = result["comparison"]
    assert "heuristic_count" in comp
    assert "model_count" in comp
    assert "agreement" in comp
    assert comp["training_data_id"] == "synthetic.tiny.v1"
    # Model and heuristic should have same number of rows (same annotations)
    assert comp["heuristic_count"] == comp["model_count"]
