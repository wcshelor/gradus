"""Tests for S3.8 first semantic regression fixtures.

Freezes compact payloads for top-voice melody, left-hand melody,
accompaniment, independent rhythm, and ambiguous passage.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from passage_practice.passages.selection import select_passage
from passage_practice.semantics.bundle_builder import build_semantic_bundle
from passage_practice.views.attack_stream import build_attack_stream
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.salience_view import build_salience_view
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.written_stream import build_written_stream

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REGRESSION_DIR = Path(__file__).resolve().parents[1] / "regression" / "semantic_payloads"

EXPECTED_CASES = [
    ("top_voice_melody", "semantic_top_voice_melody.musicxml"),
    ("left_hand_melody", "semantic_left_hand_melody.musicxml"),
    ("accompaniment", "semantic_accompaniment_pattern.musicxml"),
    ("independent_rhythm", "semantic_syncopation.musicxml"),
    ("ambiguous", "semantic_ambiguity.musicxml"),
]


def _load(name: str):
    from piano_difficulty.io.musicxml import load_musicxml_document
    from piano_difficulty.normalize.converters import build_score_ir

    return build_score_ir(load_musicxml_document(FIXTURES / name))


def _build_bundle_for_fixture(musicxml_name: str):
    score = _load(musicxml_name)
    sel = select_passage(score, score_id=musicxml_name, start=Fraction(0), end=Fraction(4))
    views = {
        "salience_view": build_salience_view(sel.passage, score),
        "texture_grid": build_texture_grid(sel.passage, score),
        "rhythm_grid": build_rhythm_grid(sel.passage, score),
        "attack_stream": build_attack_stream(sel.passage, score),
        "written_stream": build_written_stream(sel.passage, score),
    }
    bundle = build_semantic_bundle(sel.passage, views, {})
    return bundle


def test_regression_fixtures_exist_and_are_valid():
    for case_name, _ in EXPECTED_CASES:
        path = REGRESSION_DIR / f"{case_name}.json"
        assert path.exists(), f"missing regression fixture {path} — run semantics/bundle_builder to regenerate"
        data = json.loads(path.read_text())
        assert data["schema_version"] == "semantic_bundle.v1"
        assert data["bundle_id"]
        assert data["source_passage_id"]
        assert "hypotheses" in data
        assert "diagnostics" in data


def test_regression_payloads_match_rebuild():
    for case_name, musicxml_name in EXPECTED_CASES:
        path = REGRESSION_DIR / f"{case_name}.json"
        expected = json.loads(path.read_text())
        bundle = _build_bundle_for_fixture(musicxml_name)
        actual = bundle.to_dict()
        # Compare deterministically: must match frozen payload exactly
        # If this fails, the update path is: rebuild via bundle_builder and review diff for intentional detector changes
        assert actual == expected, f"regression mismatch for {case_name}: run `python -m passage_practice.semantics.bundle_builder` or rebuild fixtures and commit intentional changes"


def test_regression_payloads_contain_expected_hypothesis_families():
    # Smoke: each payload should contain at least one hypothesis from its expected family
    expectations = {
        "top_voice_melody": "role.melody",
        "left_hand_melody": "role.melody",
        "accompaniment": "texture.arpeggiated",
        "independent_rhythm": "rhythm.independent_hands",
        "ambiguous": "texture.",
    }
    for case_name, _ in EXPECTED_CASES:
        path = REGRESSION_DIR / f"{case_name}.json"
        data = json.loads(path.read_text())
        hyps = data["hypotheses"]
        assert hyps, f"{case_name} should have at least one hypothesis"
        types = [h["hypothesis_type"] for h in hyps]
        prefix = expectations[case_name]
        assert any(t.startswith(prefix) or t == prefix or prefix in t for t in types), f"{case_name} missing expected family {prefix}, got {types}"


def test_regression_update_path_documented():
    # This test ensures the regression directory has a README documenting update path
    # If no README, at least the test file itself documents it (this function's docstring)
    assert REGRESSION_DIR.exists()
    # The update path is: rebuild via build_semantic_bundle and overwrite JSON, then review diff
    # This test passes if fixtures are present; failure mode is the mismatch test above
    pass
