"""Unit tests for promoted Yan-style statistical descriptors."""

from pathlib import Path

import pytest

from piano_difficulty.features import extract_all
from piano_difficulty.pipeline import extract_score
from tests.harness.shared.matrix_features import select_feature_columns
from tests.harness.shared.runtime_matrix_export import _flatten_feature_records


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"


def test_promoted_statistics_match_yan_harness_on_fixture():
    """Runtime statistics should reproduce Yan-harness fixture expectations."""
    from tests.harness.yan2023.extractor import extract_first_pass_from_path
    from tests.harness.yan2023.implementation_audit import FEATURE_FIXTURE_EXPECTATIONS

    _, yan_values = extract_first_pass_from_path(FIXTURE)
    yan_map = {v.slot_id: v.value for v in yan_values}

    res = extract_score(FIXTURE)
    runtime_by_id = {f.feature_id: f.value for f in res.features}

    # Map Yan slot -> runtime feature_id for high-priority promoted set
    mapping = {
        "pitch_mean_es": "statistics.pitch_mean",
        "deviation_of_pitch_es": "statistics.pitch_std",
        "pitch_entropy_es": "statistics.pitch_entropy",
        "deviation_of_pitch_from_C4_es": "statistics.deviation_from_c4",
        "mean_of_note_duration_es": "statistics.duration_mean",
        "deviation_of_note_duration_es": "statistics.duration_std",
        "pitch_variability_es": "statistics.pitch_variability",
        "note_duration_variability_es": "statistics.duration_variability",
        "black_key_rate_es": "statistics.black_key_rate",
        "polyphony_rate_es": "statistics.polyphony_rate",
        "triad_es": "statistics.triad_count",
        "seventh_chord_es": "statistics.seventh_chord_count",
        "ninth_chord_es": "statistics.ninth_chord_count",
        "length": "metadata.length_quarters",
        "tempo": "metadata.primary_tempo",
        "key_signature": "metadata.key_signature",
    }

    for yan_slot, runtime_id in mapping.items():
        expected = FEATURE_FIXTURE_EXPECTATIONS[yan_slot]
        # Also compare to live Yan value
        yan_live = yan_map[yan_slot]
        assert yan_live == pytest.approx(expected, abs=1e-9)
        runtime_val = runtime_by_id[runtime_id]
        assert float(runtime_val) == pytest.approx(float(expected), abs=1e-9), f"{runtime_id} mismatch"


def test_statistics_feature_records_have_expected_units_and_diagnostics():
    res = extract_score(FIXTURE)
    by_id = {f.feature_id: f for f in res.features}
    assert by_id["statistics.pitch_mean"].units == "midi"
    assert by_id["statistics.pitch_std"].units == "midi"
    assert by_id["statistics.pitch_entropy"].units == "bits"
    assert by_id["statistics.deviation_from_c4"].units == "semitones"
    assert by_id["statistics.duration_mean"].units == "quarter_notes"
    assert by_id["statistics.polyphony_rate"].units == "ratio"
    assert by_id["statistics.triad_count"].units == "chords"
    assert by_id["metadata.length_quarters"].units == "quarter_notes"
    assert by_id["metadata.primary_tempo"].units == "bpm"
    assert by_id["metadata.key_signature"].units == "fifths"
    # diagnostics should mention Yan harness provenance
    for fid in ["statistics.pitch_mean", "statistics.black_key_rate", "metadata.primary_tempo"]:
        assert any("Yan-harness" in d for d in by_id[fid].diagnostics)


def test_matrix_features_runtime_statistical_selects_promoted_columns():
    res = extract_score(FIXTURE)
    row = _flatten_feature_records(res.features)
    available = list(row.keys())

    report = select_feature_columns(available, "runtime_statistical")
    assert "statistics_pitch_mean" in report.selected_columns
    assert "statistics_pitch_std" in report.selected_columns
    assert "statistics_pitch_entropy" in report.selected_columns
    assert "statistics_deviation_from_c4" in report.selected_columns
    assert "statistics_duration_mean" in report.selected_columns
    assert "statistics_duration_std" in report.selected_columns
    assert "statistics_pitch_variability" in report.selected_columns
    assert "statistics_duration_variability" in report.selected_columns
    assert "statistics_black_key_rate" in report.selected_columns
    assert "statistics_polyphony_rate" in report.selected_columns
    assert "statistics_triad_count" in report.selected_columns
    assert "metadata_length_quarters" in report.selected_columns
    assert "metadata_primary_tempo" in report.selected_columns
    assert "metadata_key_signature" in report.selected_columns
    assert report.missing_prefixes == ()
    assert report.missing_exact_columns == ()


def test_matrix_features_runtime_yan_overlap_includes_promoted_statistics():
    res = extract_score(FIXTURE)
    row = _flatten_feature_records(res.features)
    available = list(row.keys())

    report = select_feature_columns(available, "runtime_yan_overlap")
    # Must include at least one statistics column now runtime-native
    stats_selected = [c for c in report.selected_columns if c.startswith("statistics_")]
    assert len(stats_selected) >= 10
    # metadata compact predictors should be present
    assert "metadata_length_quarters" in report.selected_columns
    assert "metadata_primary_tempo" in report.selected_columns
