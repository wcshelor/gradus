"""Front-facing graph taxonomy: learner-visible presentation layer over raw features.

Version: gradus.front_graph_taxonomy.v1
Stable dimension IDs and feature-to-dimension weight table as documented in
research/piano_difficulty/docs/front_facing_graph_taxonomy.md.

This is a presentation/graph layer over existing raw features, normalized temporal
traces, and difficulty aspect/profile machinery. It does not replace the 9-aspect
backend taxonomy and does not alter raw feature extraction formulas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

GRAPH_TAXONOMY_VERSION = "gradus.front_graph_taxonomy.v1"

# Stable graph dimension IDs -> labels
_GRAPH_DIMENSIONS: Tuple[Dict[str, str], ...] = (
    {
        "id": "finger_dexterity",
        "label": "Finger Dexterity",
        "description": "Finger-level execution demand: fast or intricate patterns, short written values, articulation precision, repeated attacks, and chord or pitch patterns that make finger control more demanding.",
        "caveats": "Does not include large relocations across the keyboard unless the feature also implies finger-level complexity; does not include notation that is primarily a reading burden.",
    },
    {
        "id": "hand_movement_position",
        "label": "Hand Movement / Position",
        "description": "Spatial demand at the keyboard: reaches, stretches, leaps, register shifts, hand relocation, cross-staff movement, and awkward hand positions.",
        "caveats": "Does not include finger speed without spatial relocation; visual reading burden except where notation implies physical relocation.",
    },
    {
        "id": "layers_coordination",
        "label": "Layers & Coordination",
        "description": "Demand from managing multiple things at once: layered texture, polyphony, inter-hand independence, chordal density, asynchronous onsets, and hand-role separation.",
        "caveats": "Does not include rhythm difficulty that is only about subdivision or duration variety; does not include expression markings that do not imply layered control.",
    },
    {
        "id": "rhythm_timing",
        "label": "Rhythm & Timing",
        "description": "Temporal demand: density in time, subdivision variety, tuplets, polyrhythm, meter/tempo changes, duration variability, and timing independence.",
        "caveats": "Does not include physical movement that happens to occur quickly unless the feature explicitly captures timing pressure; does not include expressive timing nuance beyond what the score encodes.",
    },
    {
        "id": "expression_sound_control",
        "label": "Expression & Sound Control",
        "description": "Sound-shaping demand that is explicitly visible in the score: dynamics, articulations, hairpins, staff-specific control, and written changes that ask the learner to shape tone or balance.",
        "caveats": "Does not include unnotated interpretation, tone production, rubato, or performance nuance as a scored fact; does not claim actual performer velocity or musical maturity.",
    },
    {
        "id": "notation_reading",
        "label": "Notation / Reading",
        "description": "Visual and symbolic decoding burden: accidentals, key context, clef changes, ledger lines, cross-staff notation, and other score-reading demands.",
        "caveats": "Does not include texture that only looks dense because many notes sound together; does not include motor difficulty after the score has already been decoded. Kept as own dimension with deeper notation semantics deferred.",
    },
)

# Helper map for lookups
GRAPH_DIMENSION_IDS: Tuple[str, ...] = tuple(d["id"] for d in _GRAPH_DIMENSIONS)
GRAPH_DIMENSION_LABELS: Dict[str, str] = {d["id"]: d["label"] for d in _GRAPH_DIMENSIONS}
GRAPH_DIMENSIONS_BY_ID: Dict[str, Dict[str, str]] = {d["id"]: d for d in _GRAPH_DIMENSIONS}

# Feature -> dimension weight table (sparse, weights >0 <=1)
# Draft contributions from docs/front_facing_graph_taxonomy.md (design weights, not validated difficulty weights)
# Context-only features (metadata.length_quarters, measure_count, note_count, page_count) are intentionally excluded.
FEATURE_TO_DIMENSION_WEIGHTS: Dict[str, Dict[str, float]] = {
    # rhythm
    "rhythm.note_density": {"rhythm_timing": 0.55, "finger_dexterity": 0.35, "layers_coordination": 0.10},
    "rhythm.attack_density": {"rhythm_timing": 0.55, "finger_dexterity": 0.35, "layers_coordination": 0.10},
    "rhythm.shortest_written_duration": {"rhythm_timing": 0.65, "finger_dexterity": 0.35},
    "rhythm.tuplet_count": {"rhythm_timing": 0.75, "finger_dexterity": 0.15, "layers_coordination": 0.10},
    "rhythm.duration_value_ratio": {"rhythm_timing": 0.90, "finger_dexterity": 0.10},
    "rhythm.significant_shortest_value": {"rhythm_timing": 0.75, "finger_dexterity": 0.25},
    "rhythm.asymmetric_tuplet_measure_ratio": {"rhythm_timing": 0.75, "layers_coordination": 0.15, "finger_dexterity": 0.10},
    "rhythm.polyrhythm_measure_ratio": {"rhythm_timing": 0.65, "layers_coordination": 0.35},
    "rhythm.polyrhythm_flag": {"rhythm_timing": 0.65, "layers_coordination": 0.35},
    # leaps
    "leaps.mean_melodic_leap": {"hand_movement_position": 0.90, "finger_dexterity": 0.10},
    "leaps.max_melodic_leap": {"hand_movement_position": 0.90, "finger_dexterity": 0.10},
    "leaps.count_ge_5": {"hand_movement_position": 0.90, "finger_dexterity": 0.10},
    "leaps.count_ge_8": {"hand_movement_position": 0.90, "finger_dexterity": 0.10},
    "leaps.count_ge_12": {"hand_movement_position": 0.90, "finger_dexterity": 0.10},
    "leaps.timed_difficult_displacement_ratio": {"hand_movement_position": 0.75, "rhythm_timing": 0.10, "finger_dexterity": 0.10, "layers_coordination": 0.05},
    "leaps.max_timed_difficult_displacement": {"hand_movement_position": 0.75, "rhythm_timing": 0.10, "finger_dexterity": 0.10, "layers_coordination": 0.05},
    "leaps.timed_difficult_displacement_count": {"hand_movement_position": 0.75, "rhythm_timing": 0.10, "finger_dexterity": 0.10, "layers_coordination": 0.05},
    # pitch_geometry
    "pitch_geometry.max_simultaneity_span": {"hand_movement_position": 0.80, "finger_dexterity": 0.15, "layers_coordination": 0.05},
    "pitch_geometry.mean_simultaneity_span": {"hand_movement_position": 0.80, "finger_dexterity": 0.15, "layers_coordination": 0.05},
    "pitch_geometry.register_range": {"hand_movement_position": 0.85, "rhythm_timing": 0.15},
    # texture
    "texture.notes_per_onset": {"layers_coordination": 0.60, "hand_movement_position": 0.20, "finger_dexterity": 0.10, "expression_sound_control": 0.10},
    "texture.simultaneity_density": {"layers_coordination": 0.70, "hand_movement_position": 0.15, "expression_sound_control": 0.10, "finger_dexterity": 0.05},
    "texture.vertical_density_proxy": {"layers_coordination": 0.65, "hand_movement_position": 0.10, "finger_dexterity": 0.10, "expression_sound_control": 0.10, "rhythm_timing": 0.05},
    "texture.chord_count": {"layers_coordination": 0.55, "hand_movement_position": 0.25, "finger_dexterity": 0.15, "expression_sound_control": 0.05},
    "texture.chord_ratio": {"layers_coordination": 0.55, "hand_movement_position": 0.25, "finger_dexterity": 0.15, "expression_sound_control": 0.05},
    "texture.octave_chord_ratio": {"hand_movement_position": 0.55, "layers_coordination": 0.30, "finger_dexterity": 0.10, "expression_sound_control": 0.05},
    # coordination
    "coordination.aligned_hand_onset_count": {"layers_coordination": 0.70, "rhythm_timing": 0.30},
    "coordination.asynchronous_hand_onset_count": {"layers_coordination": 0.70, "rhythm_timing": 0.25, "hand_movement_position": 0.05},
    "coordination.aligned_hand_onset_ratio": {"layers_coordination": 0.75, "rhythm_timing": 0.25},
    "coordination.subdivision_mismatch_proxy": {"layers_coordination": 0.55, "rhythm_timing": 0.45},
    # notation
    "notation.accidental_density": {"notation_reading": 0.90, "finger_dexterity": 0.10},
    "notation.accidental_count": {"notation_reading": 0.90, "finger_dexterity": 0.10},
    "notation.accidental_ratio": {"notation_reading": 0.90, "finger_dexterity": 0.10},
    "notation.clef_change_count": {"notation_reading": 0.85, "hand_movement_position": 0.15},
    "notation.cross_staff_note_count": {"notation_reading": 0.60, "layers_coordination": 0.25, "hand_movement_position": 0.15},
    "notation.ledger_line_burden": {"notation_reading": 0.90, "hand_movement_position": 0.10},
    # expression
    "expression.articulated_note_ratio": {"expression_sound_control": 0.50, "finger_dexterity": 0.35, "rhythm_timing": 0.10, "layers_coordination": 0.05},
    "expression.articulation_density": {"finger_dexterity": 0.40, "expression_sound_control": 0.40, "rhythm_timing": 0.15, "layers_coordination": 0.05},
    "expression.staccato_note_ratio": {"expression_sound_control": 0.55, "finger_dexterity": 0.30, "rhythm_timing": 0.10, "layers_coordination": 0.05},
    "expression.accent_note_ratio": {"expression_sound_control": 0.55, "finger_dexterity": 0.30, "rhythm_timing": 0.10, "layers_coordination": 0.05},
    "expression.strong_accent_note_ratio": {"expression_sound_control": 0.55, "finger_dexterity": 0.30, "rhythm_timing": 0.10, "layers_coordination": 0.05},
    "expression.tenuto_note_ratio": {"expression_sound_control": 0.55, "finger_dexterity": 0.30, "rhythm_timing": 0.10, "layers_coordination": 0.05},
    "expression.dynamic_marking_count": {"expression_sound_control": 0.90, "rhythm_timing": 0.05, "layers_coordination": 0.05},
    "expression.dynamic_marking_rate": {"expression_sound_control": 0.90, "rhythm_timing": 0.05, "layers_coordination": 0.05},
    "expression.dynamic_change_count": {"expression_sound_control": 0.90, "rhythm_timing": 0.05, "layers_coordination": 0.05},
    "expression.dynamic_range_span": {"expression_sound_control": 0.90, "rhythm_timing": 0.05, "layers_coordination": 0.05},
    "expression.wedge_start_count": {"expression_sound_control": 0.80, "rhythm_timing": 0.15, "layers_coordination": 0.05},
    "expression.crescendo_start_count": {"expression_sound_control": 0.80, "rhythm_timing": 0.15, "layers_coordination": 0.05},
    "expression.diminuendo_start_count": {"expression_sound_control": 0.80, "rhythm_timing": 0.15, "layers_coordination": 0.05},
    "expression.staff_specific_dynamic_ratio": {"expression_sound_control": 0.70, "layers_coordination": 0.30},
    # statistics
    "statistics.pitch_mean": {"hand_movement_position": 0.30},
    "statistics.pitch_std": {"hand_movement_position": 0.55},
    "statistics.pitch_entropy": {"hand_movement_position": 0.35, "finger_dexterity": 0.10, "layers_coordination": 0.10},
    "statistics.deviation_from_c4": {"hand_movement_position": 0.55},
    "statistics.duration_mean": {"rhythm_timing": 0.70, "finger_dexterity": 0.15},
    "statistics.duration_std": {"rhythm_timing": 0.70, "finger_dexterity": 0.15},
    "statistics.duration_variability": {"rhythm_timing": 0.70, "finger_dexterity": 0.15},
    "statistics.black_key_rate": {"notation_reading": 0.45, "finger_dexterity": 0.25, "hand_movement_position": 0.20},
    "statistics.polyphony_rate": {"layers_coordination": 0.75, "hand_movement_position": 0.10, "expression_sound_control": 0.10, "finger_dexterity": 0.05},
    "statistics.triad_count": {"layers_coordination": 0.45, "hand_movement_position": 0.35, "finger_dexterity": 0.15, "expression_sound_control": 0.05},
    "statistics.seventh_chord_count": {"layers_coordination": 0.45, "hand_movement_position": 0.35, "finger_dexterity": 0.15, "expression_sound_control": 0.05},
    "statistics.ninth_chord_count": {"layers_coordination": 0.45, "hand_movement_position": 0.35, "finger_dexterity": 0.15, "expression_sound_control": 0.05},
    # metadata (excluding context-only)
    "metadata.primary_tempo": {"rhythm_timing": 0.50, "finger_dexterity": 0.20},
    "metadata.tempo_change_count": {"rhythm_timing": 0.45, "expression_sound_control": 0.40},
    "metadata.meter_change_count": {"rhythm_timing": 0.70, "layers_coordination": 0.10},
    "metadata.key_signature": {"notation_reading": 0.75, "finger_dexterity": 0.10},
    "metadata.key_change_count": {"notation_reading": 0.75, "rhythm_timing": 0.10, "expression_sound_control": 0.10},
    "metadata.pitch_range": {"hand_movement_position": 0.75},
}

# Context-only features (non-scoring) - explicitly excluded from graph layer
CONTEXT_ONLY_FEATURES = (
    "metadata.length_quarters",
    "metadata.measure_count",
    "metadata.note_count",
    "metadata.page_count",
)


def get_graph_dimensions():
    """Return list of dimension metadata dicts."""
    return list(_GRAPH_DIMENSIONS)


def get_weight_table():
    """Return copy of weight table."""
    return {fid: dict(weights) for fid, weights in FEATURE_TO_DIMENSION_WEIGHTS.items()}


def validate_taxonomy():
    """Validate static contract (used by tests)."""
    assert len(_GRAPH_DIMENSIONS) == 6
    ids = set(GRAPH_DIMENSION_IDS)
    assert len(ids) == 6
    for fid, dims in FEATURE_TO_DIMENSION_WEIGHTS.items():
        for dim_id, w in dims.items():
            assert dim_id in ids, f"{fid} maps to unknown dimension {dim_id}"
            assert 0 < w <= 1, f"{fid}->{dim_id} weight {w} out of (0,1]"
        assert len(dims) >= 1
        assert len(dims) <= 5  # sparse
    # sparse enough: average mapping per feature should be modest
    avg = sum(len(v) for v in FEATURE_TO_DIMENSION_WEIGHTS.values()) / len(FEATURE_TO_DIMENSION_WEIGHTS)
    assert avg <= 3.0, f"average mappings per feature {avg} too dense"
    # anchor mappings
    assert FEATURE_TO_DIMENSION_WEIGHTS["leaps.max_melodic_leap"]["hand_movement_position"] >= 0.85
    assert FEATURE_TO_DIMENSION_WEIGHTS["notation.accidental_density"]["notation_reading"] >= 0.85
    assert "layers_coordination" in FEATURE_TO_DIMENSION_WEIGHTS["coordination.subdivision_mismatch_proxy"]
    assert "rhythm_timing" in FEATURE_TO_DIMENSION_WEIGHTS["coordination.subdivision_mismatch_proxy"]
    assert FEATURE_TO_DIMENSION_WEIGHTS["expression.dynamic_range_span"]["expression_sound_control"] >= 0.85
    # context excluded
    for ctx in CONTEXT_ONLY_FEATURES:
        assert ctx not in FEATURE_TO_DIMENSION_WEIGHTS


# --- Graph series computation ---

def compute_graph_series(
    feature_series: dict,
    regions,
    *,
    hand_mode: str = "both",
):
    """Compute graph-dimension series from normalized feature traces.

    Multiplies normalized feature traces by graph-dimension weights and aggregates
    per graph dimension per region/window via weighted mean.

    Preserves contributor information (raw feature IDs, weighted contributions).
    Reuses existing difficulty dynamics machinery (feature_series already normalized).

    Returns:
      graph_series: dict[dimension_id -> series_payload]
      graph_contributors_per_window: list[ dict[dimension_id -> list[contrib]] ]
      composite: overall graph composite series payload (mean of graph dimensions)
    """
    n = len(regions)
    # Prepare output containers
    graph_series: Dict[str, Dict] = {}
    # per window per dimension contributors
    per_window_contributors: list[Dict[str, list]] = [{} for _ in range(n)]

    # For each dimension, compute weighted mean trace
    for dim in _GRAPH_DIMENSIONS:
        dim_id = dim["id"]
        raw_vals: list[float | None] = []
        norm_vals: list[float | None] = []
        smoothed: list[float | None] = []
        # collect contributing feature ids for this dimension
        contributing_fids = [fid for fid, wmap in FEATURE_TO_DIMENSION_WEIGHTS.items() if dim_id in wmap]

        for idx in range(n):
            weighted_sum = 0.0
            weight_total = 0.0
            contribs: list[Tuple[str, float, float, float]] = []  # fid, norm, weighted, weight
            for fid in contributing_fids:
                series = feature_series.get(fid)
                if series is None:
                    continue
                # handle both TemporalFeatureSeries object and dict payload
                if isinstance(series, dict):
                    norm_list = series.get("normalized_values") or series.get("normalizedValues") or []
                else:
                    norm_list = getattr(series, "normalized_values", [])
                if idx >= len(norm_list):
                    continue
                norm_val = norm_list[idx]
                if norm_val is None:
                    continue
                try:
                    v = float(norm_val)
                except Exception:
                    continue
                w = FEATURE_TO_DIMENSION_WEIGHTS[fid][dim_id]
                weighted = v * w
                weighted_sum += weighted
                weight_total += w
                # also fetch raw for contributor detail
                if isinstance(series, dict):
                    raw_list = series.get("raw_values", [])
                    raw_val = raw_list[idx] if idx < len(raw_list) else None
                    units = series.get("units")
                    feature_name = series.get("feature_name") or fid
                else:
                    raw_val = series.raw_values[idx] if idx < len(series.raw_values) else None
                    units = getattr(series, "units", None)
                    feature_name = getattr(series, "feature_name", None) or fid
                contribs.append((fid, v, weighted, w, raw_val, units, feature_name))

            if weight_total == 0:
                raw_vals.append(None)
                norm_vals.append(None)
                smoothed.append(None)
                per_window_contributors[idx][dim_id] = []
            else:
                # weighted mean in [0,1]
                mean_val = weighted_sum / weight_total
                raw_vals.append(mean_val)
                norm_vals.append(mean_val)
                smoothed.append(mean_val)
                # rank contributors by weighted value descending
                contribs.sort(key=lambda x: x[2], reverse=True)
                total_weighted_positive = sum(max(c[2], 0.0) for c in contribs) or 1.0
                ranked = []
                for rank, (fid, norm_v, weighted_v, w, raw_v, units, feature_name) in enumerate(contribs, start=1):
                    share = max(weighted_v, 0.0) / total_weighted_positive if total_weighted_positive else None
                    # Keep top 6 contributors per window per dimension for brevity
                    ranked.append(
                        {
                            "feature_id": fid,
                            "feature_name": feature_name,
                            "label": feature_name,
                            "raw_value": raw_v,
                            "normalized_value": norm_v,
                            "smoothed_value": norm_v,
                            "weighted_value": weighted_v,
                            "weight": w,
                            "contribution_share": share,
                            "rank": rank,
                            "units": units,
                        }
                    )
                # store top 5-6
                per_window_contributors[idx][dim_id] = ranked[:6]

        # Build series payload similar to aspect series
        missing_indices = [i for i, v in enumerate(norm_vals) if v is None]
        series_payload = {
            "feature_id": dim_id,
            "dimension_id": dim_id,
            "graph_dimension_id": dim_id,
            "feature_name": dim["label"],
            "label": dim["label"],
            "name": dim["label"],
            "description": dim["description"],
            "caveats": dim["caveats"],
            "provenance": "front_graph_taxonomy",
            "readiness": "ready",
            "status": "ready",
            "availability": "available",
            "temporal_adaptation": "weighted_mean_of_feature_normalized",
            "hand_mode": hand_mode,
            "extractor_name": "front_graph_taxonomy",
            "extractor_config": {"contributing_feature_ids": sorted(contributing_fids)},
            "units": "normalized_score",
            "source_scope": "graph_dimension",
            "source_scope_ref": dim_id,
            "regions": _regions_to_payload(regions),
            "raw_values": raw_vals,
            "normalized_values": norm_vals,
            "smoothed_values": smoothed,
            "missing_region_indices": missing_indices,
            "transformation_metadata": {
                "aggregation": "weighted_mean_of_feature_normalized",
                "contributing_feature_ids": sorted(contributing_fids),
                "contributing_feature_count": len(contributing_fids),
                "weights": {fid: FEATURE_TO_DIMENSION_WEIGHTS[fid][dim_id] for fid in contributing_fids},
            },
            "contributing_feature_ids": sorted(contributing_fids),
        }
        graph_series[dim_id] = series_payload

    # Composite overall graph demand: mean of graph dimension normalized values per window
    composite_raw: list[float | None] = []
    composite_norm: list[float | None] = []
    composite_smooth: list[float | None] = []
    for idx in range(n):
        vals = []
        for dim_id, series in graph_series.items():
            v = series["normalized_values"][idx]
            if v is not None:
                vals.append(float(v))
        if vals:
            mean = sum(vals) / len(vals)
            composite_raw.append(mean)
            composite_norm.append(mean)
            composite_smooth.append(mean)
        else:
            composite_raw.append(None)
            composite_norm.append(None)
            composite_smooth.append(None)

    composite_payload = {
        "feature_id": "composite.graph_demand",
        "dimension_id": "composite.graph_demand",
        "feature_name": "Overall graph demand",
        "label": "Overall difficulty",
        "provenance": "front_graph_composite",
        "units": "normalized_score",
        "regions": _regions_to_payload(regions),
        "raw_values": composite_raw,
        "normalized_values": composite_norm,
        "smoothed_values": composite_smooth,
        "missing_region_indices": [i for i, v in enumerate(composite_norm) if v is None],
        "transformation_metadata": {
            "aggregation": "mean_of_graph_dimension_normalized",
            "included_dimension_ids": sorted(graph_series.keys()),
            "included_count": len(graph_series),
        },
        "availability_notes": ["Composite is descriptive mean of graph dimension signals, not a calibrated grade"],
    }

    return graph_series, per_window_contributors, composite_payload


def _regions_to_payload(regions):
    """Convert regions to payload dicts (handles both ScoreRegion objects and already-payload dicts)."""
    payloads = []
    for r in regions:
        if isinstance(r, dict):
            payloads.append(r)
        else:
            # Attempt to use region_to_payload if available, else build minimal
            try:
                from piano_difficulty.difficulty_analysis.dynamics.models import region_to_payload

                payloads.append(region_to_payload(r))
            except Exception:
                payloads.append(
                    {
                        "window_index": getattr(r, "window_index", None),
                        "measure_start": getattr(r, "measure_start", None),
                        "measure_end": getattr(r, "measure_end", None),
                        "measure_numbers": list(getattr(r, "measure_numbers", [])),
                        "start_offset": str(getattr(r, "start_offset", "")),
                        "end_offset": str(getattr(r, "end_offset", "")),
                        "position": getattr(r, "position", None),
                        "hand": getattr(r, "hand", None),
                        "label": getattr(r, "label", None),
                    }
                )
    return payloads
