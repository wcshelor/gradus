from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import pytest

from piano_difficulty.analysis.windows import MeasureWindowSpec, ScoreRegion, build_measure_regions, build_measure_windows
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import MeasureIR, ScoreIR
from piano_difficulty.temporal.windows import BeatWindowSpec, build_beat_regions
from piano_difficulty.cli.main import build_parser

from tests.harness.difficulty_dynamics.config import load_difficulty_dynamics_config
from tests.harness.difficulty_dynamics.core import (
    _build_composite_series,
    _build_hotspots,
    _feature_provenance,
    _resolve_feature_record,
    detect_peaks,
    export_profile_rows,
    normalize_series,
    rank_feature_contributions_for_region,
    smooth_series,
)
from tests.harness.difficulty_dynamics.exports import export_hotspots_csv, render_summary_markdown
from tests.harness.difficulty_dynamics.runner import _region_axis_value, _select_plot_feature_series
from tests.harness.difficulty_dynamics.models import (
    CompositeConfig,
    DifficultyPassage,
    DifficultyProfile,
    NormalizationConfig,
    PeakDetectionConfig,
    SmoothingConfig,
    TemporalFeatureSeries,
)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "harness" / "difficulty_dynamics" / "configs" / "demo.yaml"


def test_build_measure_windows_supports_overlapping_windows_and_partial_final_window() -> None:
    measures = _measures(1, 5)

    overlapping = build_measure_windows(measures, size=2, step=1, include_partial_final=True)
    assert [tuple(measure.measure_index for measure in window) for window in overlapping] == [
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5,),
    ]

    non_overlapping = build_measure_windows(measures, size=2, step=2, include_partial_final=True)
    assert [tuple(measure.measure_index for measure in window) for window in non_overlapping] == [
        (1, 2),
        (3, 4),
        (5,),
    ]

    dropped = build_measure_windows(measures, size=2, step=2, include_partial_final=False)
    assert [tuple(measure.measure_index for measure in window) for window in dropped] == [
        (1, 2),
        (3, 4),
    ]


def test_build_measure_regions_preserves_region_ordering_and_positions() -> None:
    score = _score_with_measures(1, 4)
    regions = build_measure_regions(score, MeasureWindowSpec(size=2, step=1, hand="both"))

    assert [region.window_index for region in regions] == [0, 1, 2, 3]
    assert [(region.measure_start, region.measure_end) for region in regions] == [
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 4),
    ]
    assert regions[0].measure_numbers == ("1", "2")
    assert regions[0].label == "window 1: measures 1-2 [both]"
    assert regions[0].position is not None
    assert regions[0].start_offset == Fraction(0, 1)


def test_build_beat_regions_supports_overlapping_and_partial_final_windows() -> None:
    score = _score_with_measures(1, 2, measure_duration=Fraction(4, 1))
    regions = build_beat_regions(
        score,
        BeatWindowSpec(size=Fraction(3, 1), step=Fraction(3, 1), hand="both"),
    )

    assert [region.window_index for region in regions] == [0, 1, 2]
    assert regions[-1].start_offset == Fraction(6, 1)
    assert regions[-1].end_offset == Fraction(8, 1)
    assert regions[-1].label == "beat window 3: 6..8 [both]"


def test_normalization_handles_constant_series_safely() -> None:
    values = [2.0, 2.0, 2.0]

    min_max, min_max_meta = normalize_series(values, NormalizationConfig(method="min_max"))
    z_score, z_score_meta = normalize_series(values, NormalizationConfig(method="z_score"))
    robust, robust_meta = normalize_series(values, NormalizationConfig(method="robust"))

    assert min_max == [0.0, 0.0, 0.0]
    assert z_score == [0.0, 0.0, 0.0]
    assert robust == [0.0, 0.0, 0.0]
    assert min_max_meta["constant_series"] is True
    assert z_score_meta["constant_series"] is True
    assert robust_meta["constant_series"] is True


def test_normalization_preserves_raw_values_when_disabled() -> None:
    values = [1.0, None, 3.5]

    normalized, metadata = normalize_series(values, NormalizationConfig(method="none"))

    assert normalized == [1.0, None, 3.5]
    assert metadata["method"] == "none"


def test_smoothing_supports_centered_and_trailing_windows() -> None:
    values = [1.0, 3.0, 5.0, 7.0]

    centered, centered_meta = smooth_series(values, SmoothingConfig(method="moving_average", window_size=3, centered=True))
    trailing, trailing_meta = smooth_series(values, SmoothingConfig(method="trailing_moving_average", window_size=2, centered=False))

    assert centered == pytest.approx([2.0, 3.0, 5.0, 6.0])
    assert trailing == pytest.approx([1.0, 2.0, 4.0, 6.0])
    assert centered_meta["edge_handling"] == "truncate"
    assert trailing_meta["method"] == "trailing_moving_average"


def test_composite_series_supports_weighted_and_unweighted_aggregation() -> None:
    regions = _regions()
    series_a = _series("feature.a", regions, [0.0, 1.0, None], "repo_native")
    series_b = _series("feature.b", regions, [1.0, 1.0, 1.0], "repo_native")

    composite = _build_composite_series(
        regions=list(regions),
        selected_series={"feature.a": series_a, "feature.b": series_b},
        config=CompositeConfig(enabled=True, feature_ids=("feature.a", "feature.b"), weights={"feature.b": 2.0}),
    )

    assert composite.raw_values == pytest.approx((2 / 3, 1.0))
    assert composite.normalized_values == pytest.approx((2 / 3, 1.0))
    assert composite.transformation_metadata["weights"]["feature.b"] == 2.0
    assert composite.missing_region_indices == ()


def test_composite_series_excludes_missing_when_configured() -> None:
    regions = _regions()
    series_a = _series("feature.a", regions, [0.0, None, 1.0], "repo_native")
    series_b = _series("feature.b", regions, [1.0, 1.0, 1.0], "repo_native")

    composite = _build_composite_series(
        regions=list(regions),
        selected_series={"feature.a": series_a, "feature.b": series_b},
        config=CompositeConfig(enabled=True, feature_ids=("feature.a", "feature.b"), exclude_missing=True, minimum_valid_features=2),
    )

    assert composite.raw_values[1] is None
    assert composite.missing_region_indices == (1,)


def test_feature_resolution_prefers_hand_specific_values_and_aggregates_both_hands() -> None:
    records = [
        FeatureRecord("leaps.mean_melodic_leap", "hand", "left", 3.0, "semitones"),
        FeatureRecord("leaps.mean_melodic_leap", "hand", "right", 5.0, "semitones"),
        FeatureRecord("rhythm.note_density", "piece", "all", 1.25, "notes_per_quarter"),
    ]

    left = _resolve_feature_record(records, "leaps.mean_melodic_leap", "left")
    both = _resolve_feature_record(records, "leaps.mean_melodic_leap", "both")
    piece = _resolve_feature_record(records, "rhythm.note_density", "right")

    assert left[0] == 3.0
    assert both[0] == pytest.approx(4.0)
    assert both[2] == "hand_mean"
    assert piece[0] == 1.25


def test_peak_detection_supports_top_n_percentile_and_local_maxima() -> None:
    regions = _regions(4)
    series = _series("feature.a", regions, [0.1, 0.8, 0.3, 0.9], "repo_native", smoothed=[0.1, 0.8, 0.3, 0.9])

    top_n = detect_peaks(series, PeakDetectionConfig(method="top_n", top_n=2))
    percentile = detect_peaks(series, PeakDetectionConfig(method="percentile", percentile=0.75))
    local = detect_peaks(series, PeakDetectionConfig(method="local_maxima", minimum_separation=1))

    assert [passage.region.window_index for passage in top_n] == [3, 1]
    assert top_n[0].rank == 1
    assert percentile[0].threshold == 0.8
    assert {passage.region.window_index for passage in local} == {1, 3}


def test_hotspot_tagging_combines_supporting_feature_and_composite_peaks() -> None:
    regions = _regions(3)
    passages = (
        DifficultyPassage(
            passage_id="feature.a:0:1",
            region=regions[0],
            score_position=regions[0].position,
            value=0.8,
            contributing_feature_id="feature.a",
            rank=1,
            method="top_n",
        ),
        DifficultyPassage(
            passage_id="feature.b:0:1",
            region=regions[0],
            score_position=regions[0].position,
            value=0.9,
            contributing_feature_id="feature.b",
            rank=1,
            method="top_n",
        ),
        DifficultyPassage(
            passage_id="composite.difficulty:0:1",
            region=regions[0],
            score_position=regions[0].position,
            value=0.95,
            contributing_feature_id="composite.difficulty",
            rank=1,
            method="top_n",
        ),
        DifficultyPassage(
            passage_id="feature.a:2:1",
            region=regions[2],
            score_position=regions[2].position,
            value=0.7,
            contributing_feature_id="feature.a",
            rank=1,
            method="top_n",
        ),
    )

    hotspots = _build_hotspots(passages)

    assert [hotspot.region.window_index for hotspot in hotspots] == [0, 2]
    assert hotspots[0].support_count == 3
    assert hotspots[0].best_feature_id == "composite.difficulty"
    assert hotspots[0].best_value == 0.95
    assert set(hotspots[0].supporting_feature_ids) == {"feature.a", "feature.b", "composite.difficulty"}


def test_feature_contribution_ranking_uses_region_values_weights_and_peak_support() -> None:
    regions = _regions(3)
    series_a = _series("feature.a", regions, [1.0, 8.0, 3.0], "repo_native", normalized=[0.1, 0.8, 0.3])
    series_b = _series("feature.b", regions, [4.0, 6.0, 2.0], "repo_native", normalized=[0.4, 0.6, 0.2])
    series_c = _series("feature.c", regions, [7.0, 5.0, 1.0], "repo_native", normalized=[0.7, 0.5, 0.1])

    contributions = rank_feature_contributions_for_region(
        {
            "feature.a": series_a,
            "feature.b": series_b,
            "feature.c": series_c,
        },
        1,
        CompositeConfig(feature_ids=("feature.a", "feature.b", "feature.c"), weights={"feature.b": 2.0}),
        peak_support_feature_ids=("feature.a",),
    )

    assert [contribution.feature_id for contribution in contributions] == ["feature.b", "feature.a", "feature.c"]
    assert contributions[0].weighted_value == pytest.approx(1.2)
    assert contributions[0].contribution_share == pytest.approx(1.2 / 2.5)
    assert contributions[1].is_peak_support is True
    assert contributions[2].raw_value == 5.0


def test_plot_selection_limits_to_top_contributors_and_uses_measure_axis_by_default() -> None:
    regions = _regions(3)
    series_a = _series("feature.a", regions, [1.0, 5.0, 3.0], "repo_native", normalized=[0.1, 0.5, 0.3])
    series_b = _series("feature.b", regions, [4.0, 9.0, 2.0], "repo_native", normalized=[0.4, 0.9, 0.2])
    series_c = _series("feature.c", regions, [0.1, 0.1, 0.1], "repo_native", normalized=[0.1, 0.1, 0.1])
    passages = (
        DifficultyPassage(
            passage_id="feature.a:1:1",
            region=regions[1],
            score_position=regions[1].position,
            value=0.8,
            contributing_feature_id="feature.a",
            rank=1,
            method="top_n",
        ),
        DifficultyPassage(
            passage_id="feature.b:1:1",
            region=regions[1],
            score_position=regions[1].position,
            value=0.9,
            contributing_feature_id="feature.b",
            rank=1,
            method="top_n",
        ),
    )
    profile = DifficultyProfile(
        schema="difficulty_dynamics.profile",
        schema_version="difficulty_dynamics.v1",
        score_id="demo",
        score_title="Demo",
        score_composer="Composer",
        source_path="demo.musicxml",
        regions=regions,
        series={"feature.a": series_a, "feature.b": series_b, "feature.c": series_c},
        overall_series=None,
        passages=passages,
        hard_spots=tuple(
            _build_hotspots(
                passages,
                {"feature.a": series_a, "feature.b": series_b, "feature.c": series_c},
                CompositeConfig(feature_ids=("feature.a", "feature.b", "feature.c")),
            )
        ),
        metadata={},
    )

    selected = _select_plot_feature_series(profile, top_contributor_count=2)

    assert [series.feature_id for series in selected] == ["feature.b", "feature.a"]
    assert _region_axis_value(
        ScoreRegion(score_id="demo", window_index=0, measure_start=10, measure_end=13, position=42.0, hand="both"),
        "measure",
    ) == pytest.approx(11.5)
    assert _region_axis_value(
        ScoreRegion(score_id="demo", window_index=0, measure_start=10, measure_end=13, position=42.0, hand="both"),
        "score_position",
    ) == pytest.approx(42.0)


def test_hotspot_payload_includes_ranked_feature_contributions() -> None:
    regions = _regions(2)
    series_a = _series("feature.a", regions, [1.0, 9.0], "repo_native", normalized=[0.1, 0.9])
    series_b = _series("feature.b", regions, [5.0, 7.0], "repo_native", normalized=[0.5, 0.7])
    passages = (
        DifficultyPassage(
            passage_id="feature.a:1:1",
            region=regions[1],
            score_position=regions[1].position,
            value=0.9,
            contributing_feature_id="feature.a",
            rank=1,
            method="top_n",
        ),
    )

    hotspots = _build_hotspots(
        passages,
        {"feature.a": series_a, "feature.b": series_b},
        CompositeConfig(feature_ids=("feature.a", "feature.b")),
    )
    payload = hotspots[0].to_payload()

    assert payload["feature_contributions"]
    assert payload["feature_contributions"][0]["feature_id"] == "feature.a"
    assert payload["feature_contributions"][0]["is_peak_support"] is True


def test_hotspot_csv_export_flattens_hotspots_and_contributions(tmp_path: Path) -> None:
    regions = _regions(2)
    series_a = _series("feature.a", regions, [1.0, 9.0], "repo_native", normalized=[0.1, 0.9])
    series_b = _series("feature.b", regions, [5.0, 7.0], "repo_native", normalized=[0.5, 0.7])
    profile = DifficultyProfile(
        schema="difficulty_dynamics.profile",
        schema_version="difficulty_dynamics.v1",
        score_id="demo",
        score_title="Demo",
        score_composer="Composer",
        source_path="demo.musicxml",
        regions=regions,
        series={"feature.a": series_a, "feature.b": series_b},
        overall_series=None,
        passages=(
            DifficultyPassage(
                passage_id="feature.a:1:1",
                region=regions[1],
                score_position=regions[1].position,
                value=0.9,
                contributing_feature_id="feature.a",
                rank=1,
                method="top_n",
            ),
        ),
        hard_spots=tuple(
            _build_hotspots(
                (
                    DifficultyPassage(
                        passage_id="feature.a:1:1",
                        region=regions[1],
                        score_position=regions[1].position,
                        value=0.9,
                        contributing_feature_id="feature.a",
                        rank=1,
                        method="top_n",
                    ),
                ),
                {"feature.a": series_a, "feature.b": series_b},
                CompositeConfig(feature_ids=("feature.a", "feature.b")),
            )
        ),
        metadata={},
    )

    output_path = tmp_path / "difficulty_hotspots.csv"
    export_hotspots_csv(profile, output_path)

    rows = output_path.read_text(encoding="utf-8").splitlines()
    assert rows
    assert "contributor_feature_id" in rows[0]
    assert "feature.a" in rows[1]


def test_markdown_summary_lists_top_hotspots_and_contributors() -> None:
    regions = _regions(2)
    series_a = _series("feature.a", regions, [1.0, 9.0], "repo_native", normalized=[0.1, 0.9])
    series_b = _series("feature.b", regions, [5.0, 7.0], "repo_native", normalized=[0.5, 0.7])
    hard_spots = tuple(
        _build_hotspots(
            (
                DifficultyPassage(
                    passage_id="feature.a:1:1",
                    region=regions[1],
                    score_position=regions[1].position,
                    value=0.9,
                    contributing_feature_id="feature.a",
                    rank=1,
                    method="top_n",
                ),
            ),
            {"feature.a": series_a, "feature.b": series_b},
            CompositeConfig(feature_ids=("feature.a", "feature.b")),
        )
    )
    profile = DifficultyProfile(
        schema="difficulty_dynamics.profile",
        schema_version="difficulty_dynamics.v1",
        score_id="demo",
        score_title="Demo",
        score_composer="Composer",
        source_path="demo.musicxml",
        regions=regions,
        series={"feature.a": series_a, "feature.b": series_b},
        overall_series=None,
        passages=(),
        hard_spots=hard_spots,
        metadata={},
    )

    report = render_summary_markdown(profile)

    assert "Difficulty Dynamics Summary" in report
    assert "Top Hard Spots" in report
    assert "feature.a" in report


def test_profile_rows_preserve_raw_normalized_and_smoothed_values() -> None:
    regions = _regions()
    series = _series("rhythm.note_density", regions, [0.1, 0.9], "yan2023", normalized=[0.0, 1.0], smoothed=[0.2, 0.8])
    composite = _series("composite.difficulty", regions, [0.2, 0.8], "repo_native", normalized=[0.2, 0.8], smoothed=[0.25, 0.75])
    profile = DifficultyProfile(
        schema="difficulty_dynamics.profile",
        schema_version="difficulty_dynamics.v1",
        score_id="demo",
        score_title="Demo",
        score_composer="Composer",
        source_path="demo.musicxml",
        regions=regions,
        series={"rhythm.note_density": series},
        overall_series=composite,
        passages=(
            DifficultyPassage(
                passage_id="composite.difficulty:0:1",
                region=regions[0],
                score_position=regions[0].position,
                value=0.8,
                contributing_feature_id="composite.difficulty",
                rank=1,
                method="top_n",
            ),
        ),
        metadata={},
    )

    rows = export_profile_rows(profile)

    assert len(rows) == 4
    assert rows[0]["raw_value"] == 0.1
    assert rows[0]["normalized_value"] == 0.0
    assert rows[0]["smoothed_value"] == 0.2
    assert rows[-1]["feature_id"] == "composite.difficulty"


def test_provenance_marks_yan_derivatives_and_repo_native_features() -> None:
    assert _feature_provenance("rhythm.note_density") == "yan2023"
    assert _feature_provenance("leaps.mean_melodic_leap") == "repo_native"


def test_demo_config_validates_and_resolves_repo_relative_paths() -> None:
    config = load_difficulty_dynamics_config(CONFIG_PATH)

    assert config.experiment_name == "difficulty_dynamics_demo"
    assert config.score_path == (Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml").resolve()
    assert config.window.size == 1
    assert config.normalization.method == "min_max"


def test_cli_exposes_difficulty_dynamics_alias() -> None:
    parser = build_parser()
    args = parser.parse_args(["dynamics", "demo.yaml"])
    assert args.command == "dynamics"


def _score_with_measures(start: int, end: int, *, measure_duration: Fraction = Fraction(1, 1)) -> ScoreIR:
    return ScoreIR(
        source_path=Path("demo.musicxml"),
        title="Demo",
        composer="Composer",
        measures=_measures(start, end, measure_duration=measure_duration),
    )


def _measures(start: int, end: int, *, measure_duration: Fraction = Fraction(1, 1)) -> list[MeasureIR]:
    measures: list[MeasureIR] = []
    for index in range(start, end + 1):
        measures.append(
            MeasureIR(
                measure_index=index,
                measure_number=str(index),
                start=measure_duration * Fraction(index - start, 1),
                end=measure_duration * Fraction(index - start + 1, 1),
            )
        )
    return measures


def _regions(count: int = 2) -> tuple[ScoreRegion, ...]:
    regions: list[ScoreRegion] = []
    for index in range(count):
        regions.append(
            ScoreRegion(
                score_id="demo",
                window_index=index,
                measure_start=index + 1,
                measure_end=index + 1,
                position=index + 0.5,
                hand="both",
            )
        )
    return tuple(regions)


def _series(
    feature_id: str,
    regions: tuple[ScoreRegion, ...],
    raw_values: list[float | None],
    provenance: str,
    *,
    normalized: list[float | None] | None = None,
    smoothed: list[float | None] | None = None,
) -> TemporalFeatureSeries:
    normalized_values = normalized if normalized is not None else raw_values
    smoothed_values = smoothed if smoothed is not None else normalized_values
    return TemporalFeatureSeries(
        feature_id=feature_id,
        feature_name=feature_id,
        provenance=provenance,
        temporal_adaptation="measure_window",
        hand_mode="both",
        extractor_name="tests",
        units="units",
        regions=regions,
        raw_values=tuple(raw_values),
        normalized_values=tuple(normalized_values),
        smoothed_values=tuple(smoothed_values),
    )
