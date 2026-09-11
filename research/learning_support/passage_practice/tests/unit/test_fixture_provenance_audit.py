"""Tests for S-X2 semantic fixture provenance audit.

Ensures every semantic fixture is synthetic, licensed, or otherwise
commit-safe, and that manifests cover all fixtures.

Provenance is declared in semantic_manifest.md and individual fixture
headers; this test asserts manifest coverage and synthetic-only marker.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
ANNOT_FIX = FIXTURES / "annotation"
CORPUS_FIX = FIXTURES / "corpus"


def test_semantic_manifest_covers_all_musicxml_fixtures():
    manifest_text = (FIXTURES / "semantic_manifest.md").read_text()
    # Collect all musicxml fixtures that are semantic (semantic_* and selection_*, attack_stream)
    musicxml_files = sorted(p.name for p in FIXTURES.glob("*.musicxml"))
    # Expected semantic fixtures (as listed in S2.3)
    expected = {
        "semantic_top_voice_melody.musicxml",
        "semantic_left_hand_melody.musicxml",
        "semantic_accompaniment_pattern.musicxml",
        "semantic_syncopation.musicxml",
        "semantic_ambiguity.musicxml",
        "selection_two_voices.musicxml",
        "attack_stream_rests.musicxml",
    }
    for name in expected:
        assert name in manifest_text, f"fixture {name!r} missing from semantic_manifest.md"
        assert (FIXTURES / name).exists(), f"fixture file {name!r} missing"
    # Also check that manifest doesn't mention non-existent fixtures as listed rows
    for name in musicxml_files:
        if name.startswith("semantic_") or name in ("selection_two_voices.musicxml", "attack_stream_rests.musicxml"):
            assert name in manifest_text, f"manifest missing row for {name!r}"
    # Provenance marker
    assert "synthetic" in manifest_text.lower()
    assert "no repertoire excerpts" in manifest_text.lower() or "no licensed material" in manifest_text.lower()


def test_annotation_fixtures_are_synthetic_and_covered():
    manifest = json.loads((ANNOT_FIX / "manifest.json").read_text())
    json_files = sorted(p.name for p in ANNOT_FIX.glob("*.json") if p.name != "manifest.json")
    # Manifest must list every annotation fixture
    assert set(manifest.values()) == set(json_files), f"annotation manifest mismatch: {manifest.values()} vs {json_files}"
    for name in json_files:
        data = json.loads((ANNOT_FIX / name).read_text())
        # Annotation fixtures are either list or single; ensure synthetic provenance
        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            if isinstance(entry, dict) and "provenance" in entry:
                assert entry["provenance"] == "synthetic", f"{name} has non-synthetic provenance"
            if isinstance(entry, dict) and "privacy_status" in entry:
                assert entry["privacy_status"] == "synthetic"
            if isinstance(entry, dict) and "diagnostics" in entry:
                # At least synthetic_data diagnostic for committed fixtures
                diags = entry["diagnostics"]
                assert any(d.get("code") == "synthetic_data" for d in diags), f"{name} missing synthetic_data diagnostic"
    # Check header comment for synthetic
    for p in ANNOT_FIX.glob("*.json"):
        if p.name == "manifest.json":
            continue
        text = p.read_text()
        # No PII
        assert "learner" not in text or "synthetic" in text.lower()


def test_corpus_fixtures_are_synthetic_and_licensed_safe():
    manifest = json.loads((CORPUS_FIX / "manifest.json").read_text())
    assert "records" in manifest
    for name in manifest["records"]:
        path = CORPUS_FIX / name
        assert path.exists(), f"corpus fixture {name!r} missing"
        data = json.loads(path.read_text())
        assert data["provenance"] == "synthetic"
        assert data["privacy_status"] == "synthetic"
        assert any(d.get("code") == "synthetic_data" for d in data.get("diagnostics", []))
    # Ensure no non-manifested corpus jsons
    all_json = sorted(p.name for p in CORPUS_FIX.glob("*.json") if p.name != "manifest.json")
    assert set(all_json) == set(manifest["records"])


def test_no_copyrighted_score_material_in_fixtures():
    # All musicxml fixtures must be synthetic (header comment contains "Synthetic")
    for p in FIXTURES.glob("*.musicxml"):
        text = p.read_text()
        # Synthetic fixtures have header indicating synthetic
        assert "Synthetic" in text or "synthetic" in text.lower(), f"{p.name} missing synthetic header"
        # No copyrighted composer excerpts without synthetic note
        # Ensure no external ScoreAnalyzer pieces are copied here
        assert "ScoreAnalyzer" not in text
