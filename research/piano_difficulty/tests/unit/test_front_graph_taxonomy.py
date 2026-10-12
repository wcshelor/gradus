"""Static taxonomy contract for front-facing graph taxonomy."""

from piano_difficulty.difficulty_analysis.front_graph_taxonomy import (
    FEATURE_TO_DIMENSION_WEIGHTS,
    GRAPH_DIMENSION_IDS,
    GRAPH_TAXONOMY_VERSION,
    get_feature_primary_dimension,
    get_graph_dimensions,
    get_top_features_for_dimension,
    validate_taxonomy,
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
    assert GRAPH_TAXONOMY_VERSION == "gradus.front_graph_taxonomy.v2"
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


def test_span_features_map_primarily_to_hand_movement():
    # pitch_geometry span features must route primarily to hand_movement_position
    for fid in ("pitch_geometry.max_simultaneity_span", "pitch_geometry.mean_simultaneity_span"):
        wmap = FEATURE_TO_DIMENSION_WEIGHTS[fid]
        assert wmap.get("hand_movement_position", 0) >= 0.85, f"{fid} hand weight {wmap}"
        assert get_feature_primary_dimension(fid) == "hand_movement_position"
        # no strong coordination contribution
        assert wmap.get("layers_coordination", 0) == 0 or wmap.get("layers_coordination", 0) <= 0.05
        # no strong dexterity contribution
        assert wmap.get("finger_dexterity", 0) <= 0.05


def test_octave_and_chord_features_map_primarily_to_hand_position():
    # octave_chord_ratio: hand high, finger low, no coordination dominance
    wmap = FEATURE_TO_DIMENSION_WEIGHTS["texture.octave_chord_ratio"]
    assert wmap.get("hand_movement_position", 0) >= 0.80
    assert wmap.get("finger_dexterity", 0) <= 0.05
    assert wmap.get("layers_coordination", 0) <= 0.10
    assert get_feature_primary_dimension("texture.octave_chord_ratio") == "hand_movement_position"
    # chord_count / chord_ratio: hand moderate, weak coordination/dexterity
    for fid in ("texture.chord_count", "texture.chord_ratio"):
        wmap = FEATURE_TO_DIMENSION_WEIGHTS[fid]
        assert wmap.get("hand_movement_position", 0) >= 0.45
        assert wmap.get("layers_coordination", 0) <= 0.15
        assert wmap.get("finger_dexterity", 0) <= 0.05
        assert get_feature_primary_dimension(fid) == "hand_movement_position"


def test_vertical_density_features_do_not_dominate_coordination():
    for fid in (
        "texture.notes_per_onset",
        "texture.simultaneity_density",
        "texture.vertical_density_proxy",
        "statistics.polyphony_rate",
    ):
        wmap = FEATURE_TO_DIMENSION_WEIGHTS[fid]
        # hand_position should be strongest or co-strongest
        assert wmap.get("hand_movement_position", 0) >= wmap.get("layers_coordination", 0), f"{fid} hand should >= coordination {wmap}"
        # coordination if present must be low/moderate texture proxy, not dominant
        assert wmap.get("layers_coordination", 0) <= 0.15, f"{fid} coordination {wmap} too high"
        assert wmap.get("finger_dexterity", 0) <= 0.05, f"{fid} dexterity {wmap} too high"


def test_chord_type_counts_map_to_hand_position_not_coordination():
    for fid in ("statistics.triad_count", "statistics.seventh_chord_count", "statistics.ninth_chord_count"):
        wmap = FEATURE_TO_DIMENSION_WEIGHTS[fid]
        assert wmap.get("hand_movement_position", 0) >= 0.45
        assert wmap.get("layers_coordination", 0) <= 0.15
        assert wmap.get("finger_dexterity", 0) <= 0.05
        assert get_feature_primary_dimension(fid) == "hand_movement_position"


def test_aligned_hand_onsets_not_strong_coordination():
    for fid in ("coordination.aligned_hand_onset_count", "coordination.aligned_hand_onset_ratio"):
        wmap = FEATURE_TO_DIMENSION_WEIGHTS[fid]
        # must NOT map strongly to layers_coordination
        assert "layers_coordination" not in wmap or wmap["layers_coordination"] <= 0.10, f"{fid} should not dominate coordination {wmap}"
        # if kept, only weak rhythm_timing context is allowed
        if "rhythm_timing" in wmap:
            assert wmap["rhythm_timing"] <= 0.30


def test_true_coordination_signals_remain():
    # asynchronous and subdivision mismatch remain strong coordination contributors
    assert FEATURE_TO_DIMENSION_WEIGHTS["coordination.asynchronous_hand_onset_count"]["layers_coordination"] >= 0.60
    assert FEATURE_TO_DIMENSION_WEIGHTS["coordination.subdivision_mismatch_proxy"]["layers_coordination"] >= 0.50
    assert FEATURE_TO_DIMENSION_WEIGHTS["rhythm.polyrhythm_measure_ratio"]["layers_coordination"] >= 0.30
    assert FEATURE_TO_DIMENSION_WEIGHTS["rhythm.polyrhythm_flag"]["layers_coordination"] >= 0.30
    assert FEATURE_TO_DIMENSION_WEIGHTS["rhythm.asymmetric_tuplet_measure_ratio"]["layers_coordination"] >= 0.10


def test_finger_dexterity_not_driven_by_span_chord_octave():
    span_chord_features = [
        "pitch_geometry.max_simultaneity_span",
        "pitch_geometry.mean_simultaneity_span",
        "texture.octave_chord_ratio",
        "texture.chord_count",
        "texture.chord_ratio",
        "statistics.triad_count",
        "statistics.seventh_chord_count",
        "statistics.ninth_chord_count",
    ]
    for fid in span_chord_features:
        assert FEATURE_TO_DIMENSION_WEIGHTS[fid].get("finger_dexterity", 0) <= 0.05, f"{fid} finger_dexterity too high"


def test_rhythm_note_density_not_strong_finger_dexterity():
    # Finger Dexterity should not be strongly driven by generic note density
    wmap = FEATURE_TO_DIMENSION_WEIGHTS["rhythm.note_density"]
    assert wmap.get("finger_dexterity", 0) <= 0.10, f"note_density finger_dexterity {wmap} too high"
    assert get_feature_primary_dimension("rhythm.note_density") == "rhythm_timing"
    assert wmap.get("rhythm_timing", 0) >= 0.50
    # hand position captures chord/octave stacking, not dexterity
    assert wmap.get("hand_movement_position", 0) >= 0.15
    assert wmap.get("layers_coordination", 0) <= 0.05


def test_rhythm_attack_density_primary_rhythm_light_finger():
    wmap = FEATURE_TO_DIMENSION_WEIGHTS["rhythm.attack_density"]
    assert get_feature_primary_dimension("rhythm.attack_density") == "rhythm_timing"
    assert wmap.get("rhythm_timing", 0) >= 0.60, f"attack_density rhythm_timing {wmap}"
    # still contributes lightly to Finger Dexterity, not strongly
    assert 0 < wmap.get("finger_dexterity", 0) <= 0.20, f"attack_density finger {wmap}"
    assert wmap.get("layers_coordination", 0) <= 0.05


def test_rhythm_shortest_values_primary_rhythm():
    for fid, expected_rhythm, max_finger in [
        ("rhythm.shortest_written_duration", 0.70, 0.15),
        ("rhythm.significant_shortest_value", 0.75, 0.10),
    ]:
        wmap = FEATURE_TO_DIMENSION_WEIGHTS[fid]
        assert get_feature_primary_dimension(fid) == "rhythm_timing", f"{fid} primary {wmap}"
        assert wmap.get("rhythm_timing", 0) >= expected_rhythm, f"{fid} rhythm_timing {wmap}"
        assert wmap.get("finger_dexterity", 0) <= max_finger, f"{fid} finger {wmap}"


def test_articulation_features_primarily_control_expression():
    for fid in (
        "expression.articulated_note_ratio",
        "expression.articulation_density",
        "expression.staccato_note_ratio",
        "expression.accent_note_ratio",
        "expression.strong_accent_note_ratio",
    ):
        wmap = FEATURE_TO_DIMENSION_WEIGHTS[fid]
        assert get_feature_primary_dimension(fid) == "expression_sound_control", f"{fid} primary {wmap}"
        assert wmap.get("expression_sound_control", 0) >= 0.60, f"{fid} control {wmap}"
        assert wmap.get("finger_dexterity", 0) <= 0.15, f"{fid} finger_dexterity {wmap} too high"
        # should not route strongly to coordination
        assert wmap.get("layers_coordination", 0) <= 0.05, f"{fid} coordination {wmap} too high"
        # rhythm_timing should be modest
        assert wmap.get("rhythm_timing", 0) <= 0.15, f"{fid} rhythm_timing {wmap} too high"


def test_tenuto_very_low_finger_dexterity():
    wmap = FEATURE_TO_DIMENSION_WEIGHTS["expression.tenuto_note_ratio"]
    assert get_feature_primary_dimension("expression.tenuto_note_ratio") == "expression_sound_control"
    assert wmap.get("expression_sound_control", 0) >= 0.65, f"tenuto control {wmap}"
    assert wmap.get("finger_dexterity", 0) <= 0.05, f"tenuto finger_dexterity {wmap} too high"
    assert wmap.get("rhythm_timing", 0) <= 0.10, f"tenuto rhythm {wmap}"
    assert wmap.get("layers_coordination", 0) <= 0.05


def test_validate_taxonomy_passes_and_debug_helper():
    validate_taxonomy()
    # debug helper should list hand features at top for hand_movement_position
    top_hand = get_top_features_for_dimension("hand_movement_position", limit=5)
    top_ids = [fid for fid, _ in top_hand]
    # at least one span/octave feature appears among top hand contributors (or near top)
    # check broader top-10 to be robust
    top_hand_10 = [fid for fid, _ in get_top_features_for_dimension("hand_movement_position", limit=10)]
    assert any(fid in top_hand_10 for fid in ("pitch_geometry.max_simultaneity_span", "texture.octave_chord_ratio", "leaps.max_melodic_leap"))
    # coordination top should be true coordination signals, not vertical density
    top_coord = [fid for fid, _ in get_top_features_for_dimension("layers_coordination", limit=5)]
    assert any(fid in top_coord for fid in ("coordination.asynchronous_hand_onset_count", "coordination.subdivision_mismatch_proxy", "rhythm.polyrhythm_measure_ratio"))


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
