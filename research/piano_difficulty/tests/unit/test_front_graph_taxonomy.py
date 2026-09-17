"""Static taxonomy contract for front-facing graph taxonomy."""

from piano_difficulty.difficulty_analysis.front_graph_taxonomy import (
    FEATURE_TO_DIMENSION_WEIGHTS,
    GRAPH_DIMENSION_IDS,
    GRAPH_TAXONOMY_VERSION,
    get_graph_dimensions,
)


def test_all_six_dimensions_exist():
    dims = get_graph_dimensions()
    assert len(dims) == 6
    assert set(GRAPH_DIMENSION_IDS) == {
        "finger_dexterity",
        "hand_movement_position",
        "layers_coordination",
        "rhythm_timing",
        "expression_sound_control",
        "notation_reading",
    }
    # version stable
    assert GRAPH_TAXONOMY_VERSION == "gradus.front_graph_taxonomy.v1"
    for dim in dims:
        assert "id" in dim and "label" in dim and "description" in dim


def test_mapping_targets_are_known_dimensions():
    known = set(GRAPH_DIMENSION_IDS)
    for fid, wmap in FEATURE_TO_DIMENSION_WEIGHTS.items():
        for dim_id in wmap:
            assert dim_id in known, f"{fid} maps to unknown {dim_id}"


def test_weights_in_range():
    for fid, wmap in FEATURE_TO_DIMENSION_WEIGHTS.items():
        for dim_id, w in wmap.items():
            assert 0 < w <= 1, f"{fid}->{dim_id} weight {w} out of (0,1]"


def test_mappings_sparse_enough():
    # Most features have 1-2 dims, average should be low to preserve contrast
    avg = sum(len(v) for v in FEATURE_TO_DIMENSION_WEIGHTS.values()) / len(FEATURE_TO_DIMENSION_WEIGHTS)
    assert avg <= 3.0, f"average mappings per feature {avg} too dense"
    # No feature maps to all six
    for fid, wmap in FEATURE_TO_DIMENSION_WEIGHTS.items():
        assert len(wmap) <= 5
        assert len(wmap) >= 1


def test_anchor_mappings_stable():
    assert FEATURE_TO_DIMENSION_WEIGHTS["leaps.max_melodic_leap"]["hand_movement_position"] >= 0.85
    assert FEATURE_TO_DIMENSION_WEIGHTS["notation.accidental_density"]["notation_reading"] >= 0.85
    assert "layers_coordination" in FEATURE_TO_DIMENSION_WEIGHTS["coordination.subdivision_mismatch_proxy"]
    assert "rhythm_timing" in FEATURE_TO_DIMENSION_WEIGHTS["coordination.subdivision_mismatch_proxy"]
    assert FEATURE_TO_DIMENSION_WEIGHTS["expression.dynamic_range_span"]["expression_sound_control"] >= 0.85


def test_context_only_excluded():
    for ctx in ("metadata.length_quarters", "metadata.measure_count", "metadata.note_count", "metadata.page_count"):
        assert ctx not in FEATURE_TO_DIMENSION_WEIGHTS


def test_graph_series_nonempty_and_contributors():
    from pathlib import Path
    from piano_difficulty.pipeline import analyze_score

    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "feature_fixture.musicxml"
    payload = analyze_score(fixture).to_json_payload()
    aspects = next(p for p in payload["analysis_profiles"] if p["profile_id"] == "difficulty_aspects")
    gt = aspects.get("front_graph_taxonomy") or aspects.get("graph_taxonomy")
    assert gt is not None
    assert gt["version"] == GRAPH_TAXONOMY_VERSION
    # six dimensions
    assert len(gt["dimensions"]) == 6
    # nonempty series
    for dim_id, series in gt["series"].items():
        assert len(series["normalized_values"]) > 0
        assert any(v is not None for v in series["normalized_values"])
        # contributor detail present where existing output supports it
        # per-window contributors should preserve raw feature IDs
        # check at least one window has contributors
    assert len(gt["contributors_per_window"]) > 0
    # known feature families contribute to expected dimensions
    # e.g., leaps family should contribute to Hand Movement
    hand_series = gt["series"]["hand_movement_position"]
    assert "leaps.max_melodic_leap" in hand_series["contributing_feature_ids"]
    # rhythm family to rhythm_timing
    rhythm_series = gt["series"]["rhythm_timing"]
    assert "rhythm.attack_density" in rhythm_series["contributing_feature_ids"]
    # graph hotspots refined metadata present
    hotspots = gt.get("hotspots") or []
    if hotspots:
        hs = hotspots[0]
        assert "local_causes" in hs
        assert "distinct_local_causes" in hs
        assert "setup_window_indices" in hs
        assert "has_mosso_tempo" in hs
