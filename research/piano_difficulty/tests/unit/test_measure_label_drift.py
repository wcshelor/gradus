"""Focused diagnostics for measure-label drift: internal index vs printed number."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from piano_difficulty.analysis.reference_metrics import compute_reference_metrics
from piano_difficulty.difficulty_analysis.aspects import DifficultyAspectsProfile
from piano_difficulty.difficulty_analysis.dynamics.core import _build_hotspots, build_difficulty_profile
from piano_difficulty.difficulty_analysis.dynamics.models import (
    CompositeConfig,
    DifficultyDynamicsConfig,
    DifficultyHotspot,
    DifficultyPassage,
    NormalizationConfig,
    PeakDetectionConfig,
    WindowStrategyConfig,
    region_to_payload,
)
from piano_difficulty.normalize.schema import MeasureIR, ScoreIR, WrittenNoteIR
from piano_difficulty.pipeline import analyze_score  # noqa: F401
from piano_difficulty.temporal.windows import MeasureWindowSpec, ScoreRegion, build_measure_regions
from piano_difficulty.features.base import FeatureRecord


def _offset_measures() -> list[MeasureIR]:
    """Three measures with internal indices 1,2,3 but printed numbers 0,1,2 (pickup).

    Mimics pickup where printed 0 is an anacrusis not counted in musical labeling,
    causing internal vs printed offset of 1.
    """
    measures = []
    for idx, printed in [(1, "0"), (2, "1"), (3, "2")]:
        # Each measure is 4 quarters long for simplicity
        start = Fraction((idx - 1) * 4, 1)
        end = Fraction(idx * 4, 1)
        measures.append(
            MeasureIR(
                measure_index=idx,
                measure_number=printed,
                start=start,
                end=end,
            )
        )
    return measures


def _score_with_offset_and_tuplet() -> ScoreIR:
    measures = _offset_measures()
    # Put a tuplet note in internal measure 2 (printed "1") on right hand
    # and a non-tuplet note in left hand same measure to trigger polyrhythm detection
    # Polyrhythm detection checks right vs left tuplet signatures per measure.
    notes = [
        WrittenNoteIR(
            note_id="n1",
            pitch_midi=60,
            onset=Fraction(4, 1),  # inside measure 2 (4..8)
            duration=Fraction(1, 1),
            staff=1,
            voice="1",
            hand="right",
            measure_index=2,
            duration_type="quarter",
            tuplet_actual=3,
            tuplet_normal=2,
        ),
        WrittenNoteIR(
            note_id="n2",
            pitch_midi=48,
            onset=Fraction(4, 1),
            duration=Fraction(1, 1),
            staff=2,
            voice="2",
            hand="left",
            measure_index=2,
            duration_type="quarter",
            # no tuplet on left
        ),
        # Also add a note in measure 3 (internal 3, printed 2) straight
        WrittenNoteIR(
            note_id="n3",
            pitch_midi=62,
            onset=Fraction(8, 1),
            duration=Fraction(1, 1),
            staff=1,
            voice="1",
            hand="right",
            measure_index=3,
            duration_type="quarter",
        ),
    ]
    # Need at least one logical note too for some pipelines, but reference metrics uses written_notes
    from piano_difficulty.normalize.schema import LogicalNoteIR

    logical = [
        LogicalNoteIR(
            note_id=n.note_id,
            pitch_midi=n.pitch_midi,
            onset=n.onset,
            duration=n.duration,
            staff=n.staff,
            voice=n.voice,
            hand=n.hand,
            measure_index=n.measure_index,
        )
        for n in notes
    ]
    return ScoreIR(
        source_path=Path("drift_fixture.musicxml"),
        title="Drift Fixture",
        measures=measures,
        written_notes=notes,
        logical_notes=logical,
    )


def test_region_payload_preserves_both_internal_and_printed_numbers() -> None:
    measures = _offset_measures()
    score = ScoreIR(source_path=Path("pickup.musicxml"), measures=measures)
    regions = build_measure_regions(score, MeasureWindowSpec(size=2, step=1))
    # First window covers internal 1-2, printed 0-1
    region = regions[0]
    payload = region_to_payload(region)
    assert payload["measure_start"] == 1
    assert payload["measure_end"] == 2
    assert payload["measure_numbers"] == ["0", "1"]
    # Label must use printed numbers, not internal
    assert payload["label"] == "window 1: measures 0-1"
    # Also direct region fields
    assert region.measure_start == 1
    assert region.measure_numbers == ("0", "1")

    # Second window internal 2-3 printed 1-2
    region2 = regions[1]
    payload2 = region_to_payload(region2)
    assert payload2["measure_start"] == 2
    assert payload2["measure_end"] == 3
    assert payload2["measure_numbers"] == ["1", "2"]
    assert payload2["label"] == "window 2: measures 1-2"


def test_build_measure_regions_maps_offset_correctly_with_step() -> None:
    measures = _offset_measures()
    score = ScoreIR(source_path=Path("pickup.musicxml"), measures=measures)
    # Non-overlapping windows size 1: each region maps one internal index to printed number
    regions = build_measure_regions(score, MeasureWindowSpec(size=1, step=1))
    assert len(regions) == 3
    for region, expected in zip(regions, [(1, "0"), (2, "1"), (3, "2")]):
        assert region.measure_start == expected[0]
        assert region.measure_end == expected[0]
        assert region.measure_numbers == (expected[1],)
        # Single-measure label
        assert region.label == f"window {region.window_index+1}: measure {expected[1]}"


def test_hotspot_payload_exposes_internal_and_printed_drift_diagnostics() -> None:
    measures = _offset_measures()
    score = ScoreIR(source_path=Path("pickup.musicxml"), measures=measures)
    regions = build_measure_regions(score, MeasureWindowSpec(size=2, step=1))
    # Create a hotspot for window 1 (internal 2-3, printed 1-2)
    region = regions[1]  # internal 2-3 printed 1-2
    passage = DifficultyPassage(
        passage_id="test:1:1",
        region=region,
        score_position=region.position,
        value=0.9,
        contributing_feature_id="rhythm.tuplet_count",
        rank=1,
        method="top_n",
    )
    hotspot = DifficultyHotspot(
        hotspot_id="pickup:1",
        region=region,
        score_position=region.position,
        support_count=1,
        supporting_feature_ids=("rhythm.tuplet_count",),
        supporting_passages=(passage,),
        best_value=0.9,
        best_feature_id="rhythm.tuplet_count",
        best_rank=1,
        methods=("top_n",),
        method="consensus_peak_support",
    )
    payload = hotspot.to_payload()
    # Explicit top-level diagnostic fields
    assert payload["measure_start"] == 2
    assert payload["measure_end"] == 3
    assert payload["measure_index_start"] == 2
    assert payload["measure_index_end"] == 3
    assert payload["measure_index_range"] == "2-3"
    assert payload["measure_numbers"] == ["1", "2"]
    assert payload["measure_range"] == "1-2"
    assert payload["label"] == "window 2: measures 1-2"
    assert payload["window_index"] == 1
    # Nested region also preserves both
    assert payload["region"]["measure_start"] == 2
    assert payload["region"]["measure_numbers"] == ["1", "2"]

    # Passage payload also exposes same diagnostics
    p_payload = passage.to_payload()
    assert p_payload["measure_start"] == 2
    assert p_payload["measure_index_start"] == 2
    assert p_payload["measure_numbers"] == ["1", "2"]


def test_rhythm_tuplet_polyrhythm_traceable_to_printed_measure() -> None:
    score = _score_with_offset_and_tuplet()
    metrics = compute_reference_metrics(score)
    # Tuplet detected by internal index 2
    assert 2 in metrics.asymmetric_tuplet_measures
    assert 2 in metrics.polyrhythm_measures
    # Verify that internal 2 maps to printed "1"
    idx_to_printed = {m.measure_index: m.measure_number for m in score.measures}
    assert idx_to_printed[2] == "1"
    # Build windows: size 1 so each measure isolated
    regions = build_measure_regions(score, MeasureWindowSpec(size=1, step=1))
    # Find region for internal 2
    region_internal_2 = next(r for r in regions if r.measure_start == 2)
    assert region_internal_2.measure_numbers == ("1",)
    payload = region_to_payload(region_internal_2)
    assert payload["measure_start"] == 2
    assert payload["measure_numbers"] == ["1"]
    # Diagnostic: we can trace tuplet internal index to printed number via region
    tuplet_internal = metrics.asymmetric_tuplet_measures[0]
    # lookup printed number for that internal index
    printed_for_tuplet = idx_to_printed[tuplet_internal]
    # Region covering that internal index must expose same printed number
    assert printed_for_tuplet == region_internal_2.measure_numbers[0]

    # Also test window size 2 covering tuple measure plus next
    regions_w2 = build_measure_regions(score, MeasureWindowSpec(size=2, step=1))
    # Window 0: internal 1-2 printed 0-1 contains tuplet
    w0 = regions_w2[0]
    assert w0.measure_start == 1
    assert w0.measure_numbers == ("0", "1")
    # Window 1: internal 2-3 printed 1-2 also contains tuplet
    w1 = regions_w2[1]
    assert w1.measure_start == 2
    assert w1.measure_numbers == ("1", "2")
    # Ensure rhythm feature contributor using internal index is traceable via region payload
    # Simulate hotspot for window containing tuplet
    passage = DifficultyPassage(
        passage_id="rhythm:0:1",
        region=w0,
        score_position=w0.position,
        value=1.0,
        contributing_feature_id="rhythm.tuplet_count",
        rank=1,
        method="top_n",
    )
    hotspot = DifficultyHotspot(
        hotspot_id="drift:0",
        region=w0,
        score_position=w0.position,
        support_count=1,
        supporting_feature_ids=("rhythm.tuplet_count",),
        supporting_passages=(passage,),
        best_value=1.0,
        best_feature_id="rhythm.tuplet_count",
        best_rank=1,
        methods=("top_n",),
        method="consensus_peak_support",
    )
    h_payload = hotspot.to_payload()
    # Hotspot must allow distinguishing printed label from internal indices
    assert h_payload["label"] == "window 1: measures 0-1"
    assert h_payload["measure_index_range"] == "1-2"
    assert h_payload["measure_range"] == "0-1"
    # The tuplet internal index 2 is within hotspot's internal range
    assert h_payload["measure_index_start"] <= tuplet_internal <= h_payload["measure_index_end"]
    # And its printed number "1" is within hotspot's printed numbers
    assert "1" in h_payload["measure_numbers"]


def test_aspect_hotspot_payload_exposes_internal_and_printed() -> None:
    score = _score_with_offset_and_tuplet()
    # Use DifficultyAspectsProfile to generate hotspots; need at least some temporal signal
    # Build extraction via pipeline's extract_all -> use analyze_score helper with tmp file
    # Instead construct extraction manually via extract_all and wrap
    from piano_difficulty.features import extract_all

    # Need to ensure score has enough notes to generate rhythmic signal per window
    # The profile builds windows and aspect series; we test hotspot diagnostic fields exist
    class _FakeExtraction:
        def __init__(self, s):
            self.score = s
            self.features = extract_all(s)

    extraction = _FakeExtraction(score)
    profile = DifficultyAspectsProfile()
    # Use default window size 2, step 1 via options None
    result = profile.analyze(extraction, options=None)
    payload = result.to_payload()
    regions = payload["regions"]
    hotspots = payload.get("hotspots") or payload.get("candidate_sections")
    assert hotspots and len(hotspots) > 0
    # Check first hotspot has both internal and printed diagnostics
    h = hotspots[0]
    assert "measure_numbers" in h
    assert "measure_range" in h
    # New explicit internal fields
    assert "measure_start" in h or "measure_index_start" in h
    assert h.get("measure_index_start") is not None or h.get("measure_start") is not None
    assert h.get("measure_index_end") is not None or h.get("measure_end") is not None
    assert "measure_index_range" in h
    # Verify internal indices align with region payload
    assert h["region"]["measure_start"] == h["measure_start"] or h["region"]["measure_start"] == h["measure_index_start"]
    assert h["representative_region"]["measure_numbers"] == h["measure_numbers"]
    # Label must be derived from printed numbers, not internal
    # Since our pickup offset makes them differ, check label does not equal internal range string unless coincidence
    # Example: if hotspot covers internal 1-2, label should be measures 0-1 not 1-2
    # We can at least assert label contains printed numbers
    for mnum in h["measure_numbers"]:
        assert mnum in h["label"]
    # Also ensure window_index diagnostic present
    assert "window_index" in h


def test_aspect_hotspot_window_label_not_using_internal_indices() -> None:
    # Directly test _region_label behavior via build_measure_regions with offset
    measures = _offset_measures()
    score = ScoreIR(source_path=Path("pickup.musicxml"), measures=measures)
    regions = build_measure_regions(score, MeasureWindowSpec(size=2, step=1))
    # Window 1 should be labeled with printed numbers "0-1", not internal "1-2"
    assert regions[0].label == "window 1: measures 0-1"
    assert regions[0].label != "window 1: measures 1-2"
    # Even though measure_start is 1, label shows 0
    assert regions[0].measure_start == 1
    assert regions[0].measure_numbers[0] == "0"
