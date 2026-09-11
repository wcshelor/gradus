"""Tests for the S1.6 empty/no-supported-hypothesis payload fixture.

Fixture provenance: fully synthetic, hand-authored for S1.6. No score
material, no licensed content, no participant data. Detector version
strings are illustrative runnable-again provenance (the S3 registry owns
real detector IDs); passage/bundle IDs are synthetic and collide with
nothing. Fixture registry: this file is self-describing; the T02.2
selection manifest is out of scope and untouched.
"""

from __future__ import annotations

import json
from pathlib import Path

from passage_practice.models.diagnostics import Severity
from passage_practice.semantics.contracts import (
    SEMANTIC_BUNDLE_SCHEMA_VERSION,
    SemanticBundle,
)

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "semantic_no_supported_hypothesis.json"
)

EXPECTED = {
    "bundle_id": "bundle.empty.1",
    "diagnostics": [
        {
            "code": "no_supported_hypothesis",
            "message": "no detector met its minimum evidence threshold",
            "schema_version": "diagnostic.v1",
            "severity": "info",
        }
    ],
    "hypotheses": [],
    "method_versions": ["melody_salience@v1", "bass_anchor@v1"],
    "observation_refs": [],
    "ranked_hypothesis_ids": [],
    "schema_version": "semantic_bundle.v1",
    "source_passage_id": "passage.empty.1",
    "view_refs": [],
}


def _load() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_schema_version():
    assert _load()["schema_version"] == SEMANTIC_BUNDLE_SCHEMA_VERSION


def test_fixture_round_trips():
    bundle = SemanticBundle.from_dict(_load())
    assert bundle.to_dict() == _load()
    assert SemanticBundle.from_dict(bundle.to_dict()) == bundle


def test_fixture_diagnostic_assertions():
    bundle = SemanticBundle.from_dict(_load())
    assert bundle.hypotheses == ()
    assert bundle.ranked_hypothesis_ids == ()
    assert len(bundle.diagnostics) == 1
    (diagnostic,) = bundle.diagnostics
    assert diagnostic.code == "no_supported_hypothesis"
    assert diagnostic.severity is Severity.INFO
    assert diagnostic.message != ""
    # Runnable-again provenance survives the nothing-found case: the run
    # recorded which detector versions produced no finding.
    assert bundle.method_versions != ()


def test_fixture_content_is_frozen():
    assert _load() == EXPECTED


def test_fixture_presents_no_finding():
    # "No semantic finding should be presented" means exactly this: the
    # consumer sees zero hypotheses, not a low-confidence filler.
    bundle = SemanticBundle.from_dict(_load())
    assert list(bundle.hypotheses) == []
