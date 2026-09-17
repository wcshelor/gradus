from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import json

import pytest

from piano_difficulty.analysis.grouping import group_onsets, group_onsets_by_hand
from piano_difficulty.difficulty_analysis.overview import DifficultyOverviewProfile, OverviewOptions
from piano_difficulty.difficulty_analysis.dynamics.core import build_difficulty_profile
from piano_difficulty.difficulty_analysis.dynamics.models import (
    DifficultyDynamicsConfig, NormalizationConfig, WindowStrategyConfig,
)
from piano_difficulty.features import extract_all
from piano_difficulty.normalize.schema import ScoreIR, MeasureIR, WrittenNoteIR, LogicalNoteIR
from piano_difficulty.pipeline import ExtractionResult, analyze_score
from piano_difficulty.temporal.selection import select_region
from piano_difficulty.temporal.windows import BeatWindowSpec, build_beat_regions
from piano_difficulty.output.overview import write_analysis_outputs


def synthetic_score():
    score = ScoreIR(title="Synthetic isolated demand", measures=[
        MeasureIR(i, str(i + 1), Fraction(i * 4), Fraction((i + 1) * 4)) for i in range(6)])
    for i in range(6):
        pitches = [60, 84, 60, 84, 60, 84, 60, 84] if i == 2 else [60]
        for j, pitch in enumerate(pitches):
            onset = Fraction(i * 4) + Fraction(j, 2)
            note_id = f"r{i}:{j}"
            score.written_notes.append(WrittenNoteIR(note_id, pitch, onset, Fraction(1, 2), 1, "1", hand="right", measure_index=i))
            score.logical_notes.append(LogicalNoteIR("logical:" + note_id, pitch, onset, Fraction(1, 2), 1, "1",
                                                     hand="right", measure_index=i, source_note_ids=(note_id,)))
        note_id = f"l{i}"
        score.written_notes.append(WrittenNoteIR(note_id, 48, Fraction(i * 4), Fraction(4), 2, "2", hand="left", measure_index=i))
        score.logical_notes.append(LogicalNoteIR("logical:" + note_id, 48, Fraction(i * 4), Fraction(4), 2, "2",
                                                 hand="left", measure_index=i, source_note_ids=(note_id,)))
    score.onset_groups = [*group_onsets(score.logical_notes), *group_onsets_by_hand(score.logical_notes)]
    return score


def overview(score, **kwargs):
    extraction = ExtractionResult(score, extract_all(score), {}, [])
    return DifficultyOverviewProfile().analyze(extraction, OverviewOptions(**kwargs)).to_payload()


def test_known_density_and_leap_peak_with_source_evidence():
    score = synthetic_score()
    before = deepcopy(score)
    payload = overview(score, window_size=1)
    assert score == before
    assert payload["schema_version"] == "difficulty_overview.v1"
    density = payload["series"]["rhythm.attack_density"]
    assert density["raw_values"] == [0.25, 0.25, 2.0, 0.25, 0.25, 0.25]
    assert density["normalized_values"] == [0, 0, 1, 0, 0, 0]
    assert len(payload["candidate_sections"]) == 1
    section = payload["candidate_sections"][0]
    assert section["region"]["measure_numbers"] == ["3"]
    assert section["supporting_window_indices"] == [2]
    assert sum(c["contribution_share"] or 0 for c in section["contributions"]) == pytest.approx(1)
    evidence = payload["region_evidence"][2]
    assert "r2:7" in evidence["written_note_ids"]
    assert evidence["scope"] == "region_input_events"
    assert payload["hand_views"]["left"]["candidate_sections"] == []
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_flat_piece_has_no_invented_peaks():
    score = synthetic_score()
    score.logical_notes = [n for n in score.logical_notes if n.hand == "left"]
    score.written_notes = [n for n in score.written_notes if n.hand == "left"]
    score.onset_groups = [*group_onsets(score.logical_notes), *group_onsets_by_hand(score.logical_notes)]
    payload = overview(score, window_size=1)
    assert payload["candidate_sections"] == []
    assert payload["factor_peaks"] == []


def test_beat_selection_is_exact_and_does_not_mutate_durations():
    score = synthetic_score()
    regions = build_beat_regions(score, BeatWindowSpec(size=Fraction(1, 2), step=Fraction(1, 2), hand="right"))
    region = regions[16]
    selected = select_region(score, region)
    assert [n.note_id for n in selected.written_notes] == ["r2:0"]
    assert selected.measures[0].start == 8
    assert selected.measures[0].end == Fraction(17, 2)
    assert selected.written_notes[0].duration == Fraction(1, 2)
    assert all(n.hand == "right" for n in selected.logical_notes)
    assert not any(n.note_id == "logical:l2" for n in select_region(score, regions[17]).logical_notes)
    payload = overview(score, window="beat", window_size=0.5, stride=0.5, hand="right")
    assert payload["series"]["rhythm.attack_density"]["raw_values"][16:24] == [2.0] * 8
    assert payload["methods"]["selection_policy"] == "exact_attack_interval"


def test_drop_short_final_beat_window_across_measures():
    score = synthetic_score()
    regions = build_beat_regions(score, BeatWindowSpec(size=10, step=20, final_window_behavior="drop"))
    assert len(regions) == 1
    assert regions[0].end_offset == 10


def test_hand_profiles_do_not_duplicate_coordination():
    payload = overview(synthetic_score(), hand="right", window_size=1)
    assert "coordination.subdivision_mismatch_proxy" not in payload["series"]
    assert payload["series"]["leaps.max_melodic_leap"]["raw_values"][2] == 24
    density = next(f for f in payload["factors"] if f["feature_id"] == "rhythm.attack_density")
    assert density["piece_value"] == pytest.approx(13 / 24)


def test_unknown_hands_are_missing_not_zero_difficulty():
    score = synthetic_score()
    score.logical_notes = [replace(n, hand=None) for n in score.logical_notes]
    score.written_notes = [replace(n, hand=None) for n in score.written_notes]
    score.onset_groups = group_onsets(score.logical_notes)
    payload = overview(score, window_size=1)
    assert all(v is None for v in payload["series"]["leaps.max_melodic_leap"]["raw_values"])
    assert all(v is None for v in payload["series"]["coordination.subdivision_mismatch_proxy"]["raw_values"])
    assert any("no inferred hand" in message for message in payload["warnings"])


@pytest.mark.parametrize("options", [
    {"window_size": 0}, {"stride": float("nan")}, {"window_size": 1.5},
    {"hand": "voice1"}, {"top_sections": 0}, {"feature_ids": ("unknown.feature",)},
])
def test_invalid_options_fail_explicitly(options):
    with pytest.raises(ValueError):
        OverviewOptions(**options)


def test_peak_remains_in_known_spike_under_stride_change():
    for stride in (1, 0.5):
        payload = overview(synthetic_score(), window="beat", window_size=2, stride=stride)
        peaks = [p for p in payload["factor_peaks"] if p["contributing_feature_id"] == "rhythm.attack_density"]
        best = min(peaks, key=lambda p: p["rank"])
        assert Fraction(best["region"]["start_offset"]) >= 8
        assert Fraction(best["region"]["end_offset"]) <= 12


def test_source_text_cannot_inject_html(tmp_path):
    from piano_difficulty.output.overview import render_html
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
    payload = analyze_score(fixture, profile_ids=("difficulty_overview",)).to_json_payload()
    payload["score"]["title"] = "<script>alert(1)</script>"
    rendered = render_html(payload, payload["analysis_profiles"][0])
    # The injected title must be escaped; the report's own tooltip script is legitimate and allowed.
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered or "&lt;script&gt;" in rendered
    # Ensure the legitimate UI script for graph polish exists but does not expose raw injection
    assert rendered.count("<script") == 1  # only the tooltip helper script


def test_legacy_harness_imports_promoted_engine():
    from tests.harness.difficulty_dynamics.core import build_difficulty_profile as harness_build
    assert harness_build is build_difficulty_profile
    score = synthetic_score()
    config = DifficultyDynamicsConfig("compatibility", Path("synthetic.musicxml"),
                                     ("rhythm.attack_density",),
                                     normalization=NormalizationConfig(method="min_max"),
                                     window=WindowStrategyConfig(size=1))
    profile = harness_build(score, config)
    assert profile.series["rhythm.attack_density"].raw_values == (0.25, 0.25, 2, 0.25, 0.25, 0.25)


def test_runtime_outputs_and_explicit_legacy_profile(tmp_path):
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "real_mxl_basic_grand_staff.mxl"
    result = analyze_score(fixture)
    paths = write_analysis_outputs(result.to_json_payload(), tmp_path)
    assert set(paths) == {"json", "md", "html", "csv"}
    saved = json.loads(Path(paths["json"]).read_text())
    assert saved["analysis_profiles"][0]["schema_version"] == "difficulty_aspects.v1"
    assert saved["analysis_profiles"][1]["schema_version"] == "difficulty_overview.v1"
    assert "Difficulty Aspects" in Path(paths["md"]).read_text()
    assert "<svg" in Path(paths["html"]).read_text()
    legacy = analyze_score(fixture, profile_ids=("scoreanalyzer_reference",)).to_json_payload()
    assert [p["profile_id"] for p in legacy["analysis_profiles"]] == ["scoreanalyzer_reference"]
