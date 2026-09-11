"""Tests for S7.5 model interface behind detector contract."""

from __future__ import annotations

import pytest

from passage_practice.semantics.model_interface import ModelSemanticAdapter, make_fake_model_fn
from passage_practice.semantics.registry import DetectorSpec
from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.time import ScorePosition
from fractions import Fraction
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.written_stream import build_written_stream
from pathlib import Path
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.converters import build_score_ir
from passage_practice.passages.selection import select_passage


def _bundle_views(name: str):
    FIX = Path(__file__).resolve().parents[1] / "fixtures"
    score = build_score_ir(load_musicxml_document(FIX / name))
    sel = select_passage(score, score_id=name, start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    return sel.passage, views


def test_fake_model_adapter_deterministic():
    passage, views = _bundle_views("semantic_top_voice_melody.musicxml")
    spec = DetectorSpec(
        detector_id="fake_model.v1",
        detector_version="v1",
        hypothesis_types=("role.melody",),
        required_views=("salience_view",),
    )
    fn = make_fake_model_fn(hypothesis_type="role.melody", confidence=0.80, method_version="fake_model.v1")
    adapter = ModelSemanticAdapter(spec, fn, model_version="fake_model.v1", training_data_id="synthetic.tiny.v1")
    hyps1, diags1 = adapter.detect(passage, views, {})
    hyps2, diags2 = adapter.detect(passage, views, {})
    assert hyps1 == hyps2
    assert diags1 == diags2
    assert hyps1[0].method_version == "fake_model.v1"
    assert hyps1[0].confidence_method == "learned"


def test_version_metadata_required():
    from passage_practice.semantics.registry import DetectorSpec

    spec = DetectorSpec(
        detector_id="fake_model.v1",
        detector_version="v1",
        hypothesis_types=("role.melody",),
        required_views=("salience_view",),
    )
    fn = make_fake_model_fn()
    with pytest.raises(ValueError):
        ModelSemanticAdapter(spec, fn, model_version="", training_data_id="synthetic.tiny.v1")
    with pytest.raises(ValueError):
        ModelSemanticAdapter(spec, fn, model_version="fake_model.v1", training_data_id="")


def test_model_adapter_uses_detector_contract():
    passage, views = _bundle_views("semantic_top_voice_melody.musicxml")
    spec = DetectorSpec(
        detector_id="fake_model.v1",
        detector_version="v1",
        hypothesis_types=("role.bass",),
        required_views=("salience_view",),
    )
    fn = make_fake_model_fn(hypothesis_type="role.bass", method_version="fake_model.v1")
    adapter = ModelSemanticAdapter(spec, fn, model_version="fake_model.v1")
    hyps, diags = adapter.detect(passage, views, {})
    assert hyps[0].hypothesis_type == "role.bass"
    assert any(d.code == "model_version" for d in diags)
    assert any(d.code == "training_data_id" for d in diags)
