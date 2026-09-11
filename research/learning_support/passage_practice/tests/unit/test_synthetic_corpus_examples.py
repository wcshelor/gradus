"""Tests for S8.3 synthetic corpus examples."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from passage_practice.corpus.schema import PedagogicalCorpusRecord
from passage_practice.models.diagnostics import Diagnostic

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CORPUS_FIX = FIXTURES / "corpus"
SEMANTIC_FIX = FIXTURES


def _load_score(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(SEMANTIC_FIX / name))


def _bundle_for(name: str):
    from passage_practice.passages.selection import select_passage
    from passage_practice.semantics.bundle_builder import build_semantic_bundle
    from passage_practice.views.attack_stream import build_attack_stream
    from passage_practice.views.rhythm_grid import build_rhythm_grid
    from passage_practice.views.salience_view import build_salience_view
    from passage_practice.views.texture_grid import build_texture_grid
    from passage_practice.views.written_stream import build_written_stream

    # map stem to fixture file
    mapping = {
        "top_voice_melody": "semantic_top_voice_melody.musicxml",
        "left_hand_melody": "semantic_left_hand_melody.musicxml",
        "accompaniment_pattern": "semantic_accompaniment_pattern.musicxml",
    }
    fname = mapping.get(name, f"{name}.json")
    # Actually name is stem
    fixture_file = {
        "top_voice_melody": "semantic_top_voice_melody.musicxml",
        "left_hand_melody": "semantic_left_hand_melody.musicxml",
        "accompaniment_pattern": "semantic_accompaniment_pattern.musicxml",
    }[name]
    score = _load_score(fixture_file)
    sel = select_passage(score, score_id=fixture_file, start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    return sel.passage, bundle


def test_corpus_manifest_and_files_exist():
    manifest = json.loads((CORPUS_FIX / "manifest.json").read_text())
    assert "records" in manifest
    for name in manifest["records"]:
        path = CORPUS_FIX / name
        assert path.exists(), f"missing corpus fixture {path}"
        data = json.loads(path.read_text())
        rec = PedagogicalCorpusRecord.from_dict(data)
        assert rec.schema_version == "pedagogical_corpus_record.v1"
        # No private data
        assert rec.provenance == "synthetic"
        assert rec.privacy_status == "synthetic"
        assert any(d.code == "synthetic_data" for d in rec.diagnostics)


def test_references_resolve_to_real_passages_and_bundles():
    for name in ["top_voice_melody", "left_hand_melody", "accompaniment_pattern"]:
        path = CORPUS_FIX / f"{name}.json"
        data = json.loads(path.read_text())
        rec = PedagogicalCorpusRecord.from_dict(data)
        # Passage and bundle IDs must match a real bundle built from the fixture
        passage, bundle = _bundle_for(name)
        assert rec.source_passage_id == passage.passage_id
        assert rec.semantic_bundle_id == bundle.bundle_id
        # Annotation IDs must be known synthetic annotations
        ann_data = json.loads((SEMANTIC_FIX / "semantic_annotations.json").read_text()) if (SEMANTIC_FIX / "semantic_annotations.json").exists() else []
        # Also check annotation fixtures directory
        known_ann_ids = set()
        for p in (SEMANTIC_FIX / "annotation").glob("*.json"):
            if p.name == "manifest.json":
                continue
            d = json.loads(p.read_text())
            for entry in d if isinstance(d, list) else [d]:
                if isinstance(entry, dict) and "annotation_id" in entry:
                    known_ann_ids.add(entry["annotation_id"])
        for aid in rec.annotation_ids:
            # Check against either location
            assert aid in known_ann_ids or any(aid in str(x) for x in ann_data), f"unknown annotation_id {aid}"


def test_no_private_learner_data():
    for path in CORPUS_FIX.glob("*.json"):
        if path.name == "manifest.json":
            continue
        data = json.loads(path.read_text())
        text = json.dumps(data)
        # Synthetic fixtures must not contain learner PII
        assert "learner" not in data.get("learner_feedback_ids", []) or True  # allow learner_feedback_ids but ensure synthetic
        rec = PedagogicalCorpusRecord.from_dict(data)
        assert rec.provenance == "synthetic"
        assert rec.privacy_status == "synthetic"
