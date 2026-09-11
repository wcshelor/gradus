"""Tests for S3.1 detector interface and registry.

Covers unsupported view diagnostic, deterministic ordering, detector selection by family.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from passage_practice.models.passage import Passage, PassagePurpose
from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScorePosition
from passage_practice.semantics.registry import BaseDetector, DetectorRegistry, DetectorSpec
from passage_practice.semantics.contracts import SemanticHypothesis


def _passage(pid="passage.1") -> Passage:
    return Passage(
        passage_id=pid,
        score_id="score.1",
        start=ScorePosition(quarters=Fraction(0), measure_index=0),
        end=ScorePosition(quarters=Fraction(4), measure_index=1),
        purpose=PassagePurpose.DETECTION,
        method_id="test",
        method_version="v1",
        event_refs=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
    )


class _FakeMelodyDetector(BaseDetector):
    def __init__(self, did="melody.salience.v1", required=("rhythm_grid", "texture_grid"), optional=("salience_view",)):
        super().__init__(
            DetectorSpec(
                detector_id=did,
                detector_version="v1",
                hypothesis_types=("role.melody",),
                required_views=required,
                optional_views=optional,
                supported_subset="top-voice melody heuristic",
                known_limitations=("no slur evidence",),
            )
        )

    def detect(self, passage, views, observations, *, investigation=None, score=None):
        missing = self._missing_required_diagnostics(views)
        if missing is not None:
            return (), missing
        # Minimal hypothesis for testing; requires a valid covered_region and event
        from passage_practice.models.time import ScoreInterval, ScorePosition

        hyp = SemanticHypothesis(
            hypothesis_id=f"{self.spec.detector_id}:hyp.1",
            hypothesis_type="role.melody",
            source_passage_id=passage.passage_id,
            covered_region=ScoreInterval(
                start=ScorePosition(quarters=Fraction(0), measure_index=0),
                end=ScorePosition(quarters=Fraction(4), measure_index=1),
            ),
            covered_event_ids=(SourceRef(id="n1", kind=SourceKind.LOGICAL_NOTE),),
            confidence=0.6,
            confidence_method="heuristic",
            method_id=self.spec.detector_id,
            method_version=self.spec.detector_version,
            supporting_observation_ids=(),
            satisfied_criteria=("top_voice",),
        )
        return (hyp,), ()


class _FakeBassDetector(BaseDetector):
    def __init__(self, did="bass.anchor.v1"):
        super().__init__(
            DetectorSpec(
                detector_id=did,
                detector_version="v1",
                hypothesis_types=("role.bass",),
                required_views=("texture_grid",),
                supported_subset="lowest-voice bass heuristic",
                known_limitations=(),
            )
        )

    def detect(self, passage, views, observations, *, investigation=None, score=None):
        missing = self._missing_required_diagnostics(views)
        if missing is not None:
            return (), missing
        return (), ()


class _FakeRhythmDetector(BaseDetector):
    def __init__(self, did="rhythm.independent.v1"):
        super().__init__(
            DetectorSpec(
                detector_id=did,
                detector_version="v1",
                hypothesis_types=("rhythm.independent_hands", "rhythm.syncopated_layer"),
                required_views=("rhythm_grid",),
                supported_subset="hand alignment heuristic",
                known_limitations=(),
            )
        )

    def detect(self, passage, views, observations, *, investigation=None, score=None):
        missing = self._missing_required_diagnostics(views)
        if missing is not None:
            return (), missing
        return (), ()


# --- Unsupported view diagnostic ---


def test_unsupported_view_diagnostic():
    det = _FakeMelodyDetector(required=("rhythm_grid", "salience_view"), optional=())
    passage = _passage()
    # Provide only rhythm_grid, missing salience_view
    views = {"rhythm_grid": object()}
    hyps, diags = det.detect(passage, views, {})
    assert hyps == ()
    codes = {d.code for d in diags}
    assert "missing_required_view" in codes
    assert "unsupported_view" in codes
    # Message mentions detector id and missing view
    assert any(det.spec.detector_id in d.message for d in diags)
    assert any("salience_view" in d.message for d in diags)

    # With all required views, no unsupported diagnostic
    views_full = {"rhythm_grid": object(), "salience_view": object(), "texture_grid": object()}
    # FakeMelodyDetector requires rhythm_grid+texture_grid; give both plus optional salience
    det2 = _FakeMelodyDetector(required=("rhythm_grid", "texture_grid"))
    hyps2, diags2 = det2.detect(passage, {"rhythm_grid": object(), "texture_grid": object()}, {})
    assert len(hyps2) == 1
    assert not any(d.code == "missing_required_view" for d in diags2)
    assert not any(d.code == "unsupported_view" for d in diags2)


def test_registry_selectable_for_respects_required_views():
    registry = DetectorRegistry()
    registry.register(_FakeMelodyDetector(did="melody.salience.v1", required=("rhythm_grid", "texture_grid")))
    registry.register(_FakeBassDetector(did="bass.anchor.v1"))
    registry.register(_FakeRhythmDetector(did="rhythm.independent.v1"))

    # Only rhythm_grid available → only rhythm detector selectable
    sel = registry.selectable_for({"rhythm_grid"})
    assert [d.spec.detector_id for d in sel] == ["rhythm.independent.v1"]

    # Both rhythm+texture → melody + bass + rhythm (bass requires texture)
    sel2 = registry.selectable_for({"rhythm_grid", "texture_grid"})
    assert set(d.spec.detector_id for d in sel2) == {"melody.salience.v1", "bass.anchor.v1", "rhythm.independent.v1"}

    # Empty available → none selectable
    assert registry.selectable_for(set()) == []


# --- Deterministic ordering ---


def test_deterministic_ordering():
    registry = DetectorRegistry()
    # Register in non-sorted order
    registry.register(_FakeRhythmDetector(did="rhythm.independent.v1"))
    registry.register(_FakeMelodyDetector(did="melody.salience.v1"))
    registry.register(_FakeBassDetector(did="bass.anchor.v1"))

    # list_all must be sorted by detector_id regardless of insertion order
    assert [d.spec.detector_id for d in registry.list_all()] == [
        "bass.anchor.v1",
        "melody.salience.v1",
        "rhythm.independent.v1",
    ]
    # A second registry with different insertion order yields same order
    registry2 = DetectorRegistry()
    registry2.register(_FakeBassDetector(did="bass.anchor.v1"))
    registry2.register(_FakeRhythmDetector(did="rhythm.independent.v1"))
    registry2.register(_FakeMelodyDetector(did="melody.salience.v1"))
    assert [d.spec.detector_id for d in registry2.list_all()] == [
        "bass.anchor.v1",
        "melody.salience.v1",
        "rhythm.independent.v1",
    ]
    # selectable_for also deterministic (sorted)
    sel = registry.selectable_for({"rhythm_grid", "texture_grid"})
    assert [d.spec.detector_id for d in sel] == sorted([d.spec.detector_id for d in sel])


# --- Detector selection by family ---


def test_detector_selection_by_family():
    registry = DetectorRegistry()
    registry.register(_FakeMelodyDetector(did="melody.salience.v1"))
    registry.register(_FakeBassDetector(did="bass.anchor.v1"))
    registry.register(_FakeRhythmDetector(did="rhythm.independent.v1"))
    # Family prefix "role." matches melody and bass but not rhythm
    role_dets = registry.by_family("role.")
    assert set(d.spec.detector_id for d in role_dets) == {"melody.salience.v1", "bass.anchor.v1"}
    # Specific family "role.melody"
    melody_dets = registry.by_family("role.melody")
    assert [d.spec.detector_id for d in melody_dets] == ["melody.salience.v1"]
    # Rhythm family
    rhythm_dets = registry.by_family("rhythm.")
    assert [d.spec.detector_id for d in rhythm_dets] == ["rhythm.independent.v1"]
    # Also test deterministic ordering within family filter
    registry2 = DetectorRegistry()
    registry2.register(_FakeBassDetector(did="bass.anchor.v1"))
    registry2.register(_FakeMelodyDetector(did="melody.salience.v1"))
    assert [d.spec.detector_id for d in registry2.by_family("role.")] == [
        "bass.anchor.v1",
        "melody.salience.v1",
    ]


def test_registry_rejects_duplicate_and_unknown():
    registry = DetectorRegistry()
    registry.register(_FakeMelodyDetector(did="melody.salience.v1"))
    with pytest.raises(ValueError):
        registry.register(_FakeMelodyDetector(did="melody.salience.v1"))
    with pytest.raises(KeyError):
        registry.get("nonexistent.v1")
    assert "melody.salience.v1" in registry
    assert "nonexistent.v1" not in registry


def test_detector_spec_validates():
    # hypothesis_type must contain dot
    with pytest.raises(ValueError):
        DetectorSpec(detector_id="bad.v1", detector_version="v1", hypothesis_types=("rolemelody",))
    # required and optional overlap
    with pytest.raises(ValueError):
        DetectorSpec(
            detector_id="bad2.v1",
            detector_version="v1",
            hypothesis_types=("role.melody",),
            required_views=("texture_grid",),
            optional_views=("texture_grid",),
        )
    # duplicate view
    with pytest.raises(ValueError):
        DetectorSpec(
            detector_id="bad3.v1",
            detector_version="v1",
            hypothesis_types=("role.melody",),
            required_views=("rhythm_grid", "rhythm_grid"),
        )
