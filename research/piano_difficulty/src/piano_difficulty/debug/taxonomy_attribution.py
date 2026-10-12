"""Debug-only taxonomy attribution for front-facing graph dimensions.

This module is intentionally loud as internal debugging infrastructure.
It is NOT learner-facing feedback, NOT pedagogy copy, and NOT a new scoring model.
It reuses existing graph contributor machinery (front_graph_taxonomy.compute_graph_series,
difficulty_dynamics core, feature glossaries) to expose why a selected dimension is
high for a given measure range.

Do not change scoring behavior. Do not claim passages are objectively hard.
Do not generate learner advice. Do not use LLM prose as source of truth.

Output answers: "Which exact feature path made this taxonomy/dimension high?"
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

from piano_difficulty.difficulty_analysis.front_graph_taxonomy import (
    FEATURE_TO_DIMENSION_WEIGHTS,
    GRAPH_DIMENSION_IDS,
    GRAPH_DIMENSIONS_BY_ID,
    GRAPH_TAXONOMY_VERSION,
)
from piano_difficulty.difficulty_analysis.overview import OverviewOptions

# Reuse glossaries from hotspot_explanation (deterministic, no LLM)
try:
    from research.learning_support.david_demo.scripts.hotspot_explanation import FEATURE_GLOSSARY as _DAVID_DEMO_FEATURE_GLOSSARY
except Exception:
    _DAVID_DEMO_FEATURE_GLOSSARY = {}

# Fallback glossary for features not in David list (use humanized feature_id)
_FEATURE_GLOSSARY_FALLBACK: dict[str, str] = {
    "hand_shape.octave_onset_rate": "octave onset rate",
    "hand_shape.large_span_onset_rate": "large span onset rate",
    "hand_shape.mean_large_span_burden": "mean large span burden",
    "hand_shape.wide_chord_density": "wide chord density",
    "hand_position.max_center_shift": "max center shift",
    "hand_position.mean_center_shift": "mean center shift",
    "hand_position.large_center_shift_rate": "large center shift rate",
    "statistics.pitch_mean": "average pitch height",
    "statistics.polyphony_rate": "polyphony rate",
    "statistics.triad_count": "triad count",
    "statistics.seventh_chord_count": "seventh chord count",
    "statistics.ninth_chord_count": "ninth chord count",
}

# Proxy and category definitions for layers_coordination explicit surfacing
PROXY_FEATURES: set[str] = {
    "coordination.subdivision_mismatch_proxy",
}

TEXTURE_PROXY_IN_COORDINATION: set[str] = {
    "texture.notes_per_onset",
    "texture.simultaneity_density",
    "texture.vertical_density_proxy",
    "texture.chord_count",
    "texture.chord_ratio",
    "statistics.polyphony_rate",
    "statistics.triad_count",
    "statistics.seventh_chord_count",
    "statistics.ninth_chord_count",
    "statistics.pitch_entropy",
}

RHYTHM_POLYRHYTHM_IN_COORDINATION: set[str] = {
    "rhythm.polyrhythm_measure_ratio",
    "rhythm.polyrhythm_flag",
    "rhythm.asymmetric_tuplet_measure_ratio",
    "rhythm.tuplet_count",
}

COORDINATION_DIRECT: set[str] = {
    "coordination.asynchronous_hand_onset_count",
    "coordination.subdivision_mismatch_proxy",
}

COORDINATION_ALIGNED: set[str] = {
    "coordination.aligned_hand_onset_count",
    "coordination.aligned_hand_onset_ratio",
}

DEBUG_SCHEMA = "debug.taxonomy_attribution.v1"
DEBUG_LABEL = "DEBUG ONLY: Taxonomy Attribution"


def parse_measures_arg(arg: str) -> list[int]:
    """Parse measure range string into sorted unique ints.

    Supports "12-16", "12", "12,14,16", "12-16,20" and en-dash variants.
    """
    if not arg or not arg.strip():
        raise ValueError("measures argument is empty")
    # Normalize en-dash/em-dash to hyphen
    cleaned = arg.replace("–", "-").replace("—", "-").strip()
    result: set[int] = set()
    for part in cleaned.split(","):
        p = part.strip()
        if not p:
            continue
        if "-" in p:
            # Handle range like "12-16"
            sides = p.split("-", 1)
            if len(sides) != 2:
                raise ValueError(f"invalid measures segment {p!r}")
            try:
                start = int(sides[0].strip())
                end = int(sides[1].strip())
            except ValueError as exc:
                raise ValueError(f"invalid measure range {p!r}: must be integers") from exc
            if start > end:
                raise ValueError(f"invalid measure range {p!r}: start > end")
            for v in range(start, end + 1):
                result.add(v)
        else:
            try:
                result.add(int(p))
            except ValueError as exc:
                raise ValueError(f"invalid measure {p!r}: must be integer or range") from exc
    if not result:
        raise ValueError(f"no measures parsed from {arg!r}")
    return sorted(result)


def _human_label_for_feature(feature_id: str, feature_name: str | None = None) -> str:
    # Prefer DAVID_DEMO glossary, then fallback, then humanized feature_id
    if feature_id in _DAVID_DEMO_FEATURE_GLOSSARY:
        return _DAVID_DEMO_FEATURE_GLOSSARY[feature_id]
    if feature_id in _FEATURE_GLOSSARY_FALLBACK:
        return _FEATURE_GLOSSARY_FALLBACK[feature_id]
    if feature_name and feature_name != feature_id:
        return feature_name
    # Humanize: replace dots/underscores
    return feature_id.replace(".", " · ").replace("_", " ")


def _categorize_layers_coordination_feature(fid: str) -> str:
    if fid == "coordination.subdivision_mismatch_proxy":
        return "coordination.subdivision_mismatch_proxy"
    if fid == "coordination.asynchronous_hand_onset_count":
        return "coordination.asynchronous_hand_onset_count"
    if fid in COORDINATION_ALIGNED:
        return "coordination.aligned_hand_onset_ratio/count"
    if fid in RHYTHM_POLYRHYTHM_IN_COORDINATION:
        return "rhythm/polyrhythm"
    if fid in TEXTURE_PROXY_IN_COORDINATION:
        return "texture (weak mapping)"
    return "other"


def _is_proxy_feature(fid: str, dimension: str) -> bool:
    if fid in PROXY_FEATURES:
        return True
    # Texture features weakly mapped into coordination are proxies in that context
    if dimension == "layers_coordination" and fid in TEXTURE_PROXY_IN_COORDINATION:
        return True
    return False


def _build_onsets_detail(score, measures_set: set[int]) -> list[dict[str, Any]]:
    """Per-measure onset drilldown for coordination."""
    from piano_difficulty.features._common import measures_by_index  # type: ignore

    # Build measure index -> measure IR
    m_by_idx = measures_by_index(score)
    detail: list[dict[str, Any]] = []
    for m in score.measures:
        # Determine printed number int if possible
        try:
            printed_num = int(str(m.measure_number).strip())
        except Exception:
            printed_num = None
        # Check if measure belongs to requested set: printed number is authoritative; measure_index is 1-based per ScoreIR
        belongs = False
        if printed_num is not None and printed_num in measures_set:
            belongs = True
        elif printed_num is not None and str(m.measure_number) in {str(x) for x in measures_set}:
            belongs = True
        elif m.measure_index in measures_set:
            belongs = True
        elif str(m.measure_number) in {str(x) for x in measures_set}:
            belongs = True
        if not belongs:
            continue

        # Collect offsets for this measure
        right_offsets: set[Fraction] = set()
        left_offsets: set[Fraction] = set()
        for note in score.logical_notes:
            if note.measure_index != m.measure_index:
                continue
            if note.hand not in {"right", "left"}:
                continue
            offset = note.onset - m.start if m.start is not None else note.onset
            if note.hand == "right":
                right_offsets.add(offset)
            elif note.hand == "left":
                left_offsets.add(offset)

        aligned = right_offsets & left_offsets
        union = right_offsets | left_offsets
        mismatched = union - aligned

        detail.append(
            {
                "measure_number": str(m.measure_number),
                "measure_index": int(m.measure_index),
                "measure_start": str(m.start) if m.start is not None else None,
                "measure_end": str(m.end) if m.end is not None else None,
                "right_hand_offsets": sorted([str(o) for o in right_offsets]),
                "left_hand_offsets": sorted([str(o) for o in left_offsets]),
                "aligned_offsets": sorted([str(o) for o in aligned]),
                "mismatched_offsets": sorted([str(o) for o in mismatched]),
                "right_hand_offset_count": len(right_offsets),
                "left_hand_offset_count": len(left_offsets),
                "aligned_offset_count": len(aligned),
                "mismatched_offset_count": len(mismatched),
                "union_offset_count": len(union),
            }
        )
    # Sort by measure_index
    detail.sort(key=lambda d: d["measure_index"])
    return detail


def _compute_feature_piece_stats(feature_series: dict, fid: str) -> tuple[float | None, float | None, dict | None]:
    """Return (min, max, norm_meta) for a feature's raw values across windows."""
    series = feature_series.get(fid)
    if series is None:
        return None, None, None
    raw = list(getattr(series, "raw_values", []))
    # Filter numeric
    numeric = [float(v) for v in raw if v is not None]
    if not numeric:
        return None, None, getattr(series, "transformation_metadata", None)
    # Get normalization metadata if available
    meta = getattr(series, "transformation_metadata", {}) or {}
    norm_meta = meta.get("normalization") if isinstance(meta, dict) else None
    # Also direct from transformation_metadata
    # norm_meta may contain minimum/maximum
    piece_min = None
    piece_max = None
    if isinstance(norm_meta, dict):
        piece_min = norm_meta.get("minimum")
        piece_max = norm_meta.get("maximum")
    if piece_min is None or piece_max is None:
        piece_min = min(numeric) if numeric else None
        piece_max = max(numeric) if numeric else None
    return piece_min, piece_max, norm_meta


def build_debug_attribution_payload(
    score_path: str | Path,
    measures_arg: str,
    dimension_id: str,
    *,
    overview_options: OverviewOptions | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    """Build debug attribution payload for given score/masures/dimension.

    Reuses existing graph contributor machinery (compute_graph_series).
    Does not change scoring formulas.
    """
    if dimension_id not in GRAPH_DIMENSION_IDS:
        raise ValueError(f"unknown dimension {dimension_id!r}; expected one of {GRAPH_DIMENSION_IDS}")

    measures = parse_measures_arg(measures_arg)
    measures_set = set(measures)

    if overview_options is None:
        overview_options = OverviewOptions()

    # Load score and build full analysis to expose score metadata
    from piano_difficulty.pipeline import analyze_score
    from piano_difficulty.difficulty_analysis.dynamics.core import build_difficulty_profile
    from piano_difficulty.difficulty_analysis.dynamics.models import (
        CompositeConfig,
        DifficultyDynamicsConfig,
        NormalizationConfig,
        PeakDetectionConfig,
        WindowStrategyConfig,
    )
    from piano_difficulty.difficulty_analysis.front_graph_taxonomy import compute_graph_series
    from piano_difficulty.difficulty_analysis.aspects import TEMPORAL_FEATURE_IDS

    # Use analyze_score to get score IR and verify parsing, but also rebuild profile for accurate attribution
    # analyze_score loads file; if path does not exist, it will raise.
    try:
        analysis_result = analyze_score(str(score_path), profile_ids=("difficulty_aspects", "difficulty_overview"), overview_options=overview_options)
        score = analysis_result.extraction.score
    except Exception as exc:
        raise ValueError(f"failed to load/analyze score {score_path!r}: {exc}") from exc

    # Build difficulty profile with same window settings as aspects
    union_ids = tuple(sorted(set(TEMPORAL_FEATURE_IDS)))
    config = DifficultyDynamicsConfig(
        experiment_name="debug_taxonomy_attribution",
        score_path=Path(score_path) if isinstance(score_path, (str, Path)) else Path(str(score.source_path or "score.musicxml")),
        feature_ids=union_ids,
        hand_mode=getattr(overview_options, "hand", "both"),
        window=WindowStrategyConfig(
            kind=getattr(overview_options, "window", "measure"),
            size=int(getattr(overview_options, "window_size", 2)),
            step=int(getattr(overview_options, "stride", 1)),
            beat_size=getattr(overview_options, "window_size", 2),
            beat_step=getattr(overview_options, "stride", 1),
        ),
        normalization=NormalizationConfig(method="min_max"),
        composite=CompositeConfig(enabled=False),
        peaks=PeakDetectionConfig(top_n=int(getattr(overview_options, "top_sections", 5))),
        overview_mode=True,
    )
    # Handle beat vs measure specifics? keep as measure default.

    try:
        profile = build_difficulty_profile(score, config)
    except Exception as exc:
        raise RuntimeError(f"failed to build difficulty profile: {exc}") from exc

    feature_series = profile.series
    regions = list(profile.regions)

    # Compute graph series and contributors (reuse machinery)
    from piano_difficulty.difficulty_analysis.front_graph_taxonomy import compute_graph_series as _cgs

    graph_series, per_window_contributors, graph_composite = _cgs(
        feature_series,
        regions,
        hand_mode=config.hand_mode,
    )

    # Find overlapping windows: any region where measure_numbers intersect measures_set
    overlapping_indices: list[int] = []
    for idx, region in enumerate(regions):
        # region.measure_numbers is tuple[str]
        # Also region.measure_start/end are indices
        hit = False
        for mn in list(getattr(region, "measure_numbers", ())):
            try:
                mn_int = int(str(mn).strip())
                if mn_int in measures_set:
                    hit = True
                    break
            except Exception:
                if str(mn) in {str(x) for x in measures}:
                    hit = True
                    break
        if not hit:
            # Fallback: check measure_start/end index range (measure_index is 1-based per ScoreIR)
            start_idx = getattr(region, "measure_start", None)
            end_idx = getattr(region, "measure_end", None)
            if isinstance(start_idx, int) and isinstance(end_idx, int):
                for mi in range(start_idx, end_idx + 1):
                    if mi in measures_set:
                        hit = True
                        break
        if hit:
            overlapping_indices.append(idx)

    dim_info = GRAPH_DIMENSIONS_BY_ID[dimension_id]
    # Build windows payload
    windows_payload: list[dict[str, Any]] = []
    for idx in overlapping_indices:
        region = regions[idx]
        series = graph_series[dimension_id]
        raw_vals = list(series.get("raw_values") or [])
        norm_vals = list(series.get("normalized_values") or [])
        smoothed_vals = list(series.get("smoothed_values") or [])
        raw_v = raw_vals[idx] if idx < len(raw_vals) else None
        norm_v = norm_vals[idx] if idx < len(norm_vals) else None
        smoothed_v = smoothed_vals[idx] if idx < len(smoothed_vals) else None
        # region payload
        from piano_difficulty.difficulty_analysis.dynamics.models import region_to_payload

        rp = region_to_payload(region)
        windows_payload.append(
            {
                "window_index": int(region.window_index),
                "measure_start": int(region.measure_start) if isinstance(region.measure_start, int) else region.measure_start,
                "measure_end": int(region.measure_end) if isinstance(region.measure_end, int) else region.measure_end,
                "measure_numbers": list(getattr(region, "measure_numbers", [])),
                "measure_range": f"{rp.get('measure_numbers', ['?'])[0]}-{rp.get('measure_numbers', ['?'])[-1]}" if len(rp.get("measure_numbers", [])) >= 2 else (rp.get("measure_numbers", ["?"])[0] if rp.get("measure_numbers") else "?"),
                "label": getattr(region, "label", None) or rp.get("label"),
                "start_offset": rp.get("start_offset"),
                "end_offset": rp.get("end_offset"),
                "start_beat": rp.get("start_beat"),
                "end_beat": rp.get("end_beat"),
                "position": getattr(region, "position", None),
                "dimension_raw": raw_v,
                "dimension_normalized": norm_v,
                "dimension_smoothed": smoothed_v,
                "region_payload": rp,
            }
        )

    # If no overlapping windows, windows_payload stays empty and warnings issued

    # Build contributors per window
    contributors_per_window: list[dict[str, Any]] = []
    # For aggregated ranking, collect weighted sums
    agg: dict[str, dict[str, Any]] = {}
    for idx in overlapping_indices:
        contribs = []
        raw_list = []
        if idx < len(per_window_contributors):
            dim_contribs = per_window_contributors[idx].get(dimension_id, [])
            for c in dim_contribs:
                fid = c.get("feature_id")
                piece_min, piece_max, norm_meta = _compute_feature_piece_stats(feature_series, fid)
                # Determine proxy flags and category
                is_proxy = _is_proxy_feature(fid, dimension_id)
                category = _categorize_layers_coordination_feature(fid) if dimension_id == "layers_coordination" else None
                # Weight is already in contributor; also get from weight table
                weight = c.get("weight") if c.get("weight") is not None else FEATURE_TO_DIMENSION_WEIGHTS.get(fid, {}).get(dimension_id)
                # Piece stats for normalization visibility
                raw_val = c.get("raw_value")
                norm_val = c.get("normalized_value")
                # Label
                label = _human_label_for_feature(fid, c.get("feature_name") or c.get("label"))
                # Units
                units = c.get("units")
                # Source scope info
                src_scope = None
                src_scope_ref = None
                series_obj = feature_series.get(fid)
                if series_obj is not None:
                    src_scope = getattr(series_obj, "source_scope", None)
                    src_scope_ref = getattr(series_obj, "source_scope_ref", None)
                # Normalization note: if high normalized but raw small-ish, flag
                norm_note = None
                if isinstance(norm_val, (int, float)) and isinstance(raw_val, (int, float)) and piece_min is not None and piece_max is not None and piece_max != piece_min:
                    # normalized already reflects piece scaling; note that normalized is piece-relative
                    norm_note = f"normalized is min-max within piece (raw {raw_val:.3g} in piece range [{piece_min:.3g}, {piece_max:.3g}])"
                    # Additional flag if raw is not large in absolute terms but normalized high due to narrow piece range
                    span = piece_max - piece_min
                    if span < 0.3 and norm_val >= 0.6:
                        norm_note += "; high normalized reflects narrow piece range, not large absolute raw"
                    elif norm_val >= 0.6 and (raw_val - piece_min) / span >= 0.6:
                        norm_note += "; high normalized corresponds to relatively high raw within piece"
                elif isinstance(norm_val, (int, float)):
                    norm_note = "normalized is min-max within piece; raw not available for piece range"
                entry = {
                    "feature_id": fid,
                    "label": label,
                    "human_label": label,
                    "plain": label,
                    "feature_name": c.get("feature_name") or label,
                    "raw_value": raw_val,
                    "normalized_value": norm_val,
                    "smoothed_value": c.get("smoothed_value"),
                    "weight": weight,
                    "weighted_value": c.get("weighted_value"),
                    "contribution_share": c.get("contribution_share"),
                    "units": units,
                    "source_scope": src_scope,
                    "source_scope_ref": src_scope_ref,
                    "window_index": int(idx),
                    "measure_numbers": list(getattr(regions[idx], "measure_numbers", [])) if idx < len(regions) else [],
                    "window_label": getattr(regions[idx], "label", None) if idx < len(regions) else None,
                    "is_proxy": bool(is_proxy),
                    "proxy_kind": "proxy" if fid in PROXY_FEATURES else ("texture proxy (weak mapping)" if dimension_id == "layers_coordination" and fid in TEXTURE_PROXY_IN_COORDINATION else None),
                    "category": category,
                    "piece_raw_min": piece_min,
                    "piece_raw_max": piece_max,
                    "normalization_note": norm_note,
                    "rank": c.get("rank"),
                }
                contribs.append(entry)
                # Aggregate
                if fid not in agg:
                    agg[fid] = {
                        "feature_id": fid,
                        "label": label,
                        "weight": weight,
                        "total_weighted": 0.0,
                        "total_share": 0.0,
                        "max_normalized": -1.0,
                        "raw_values": [],
                        "norm_values": [],
                        "is_proxy": bool(is_proxy),
                        "category": category,
                        "units": units,
                        "count": 0,
                    }
                agg[fid]["total_weighted"] += float(c.get("weighted_value") or 0.0)
                agg[fid]["total_share"] += float(c.get("contribution_share") or 0.0)
                agg[fid]["max_normalized"] = max(agg[fid]["max_normalized"], float(norm_val) if isinstance(norm_val, (int, float)) else -1)
                agg[fid]["raw_values"].append(raw_val)
                agg[fid]["norm_values"].append(norm_val)
                agg[fid]["count"] += 1

        contributors_per_window.append(
            {
                "window_index": int(idx),
                "measure_numbers": list(getattr(regions[idx], "measure_numbers", [])) if idx < len(regions) else [],
                "contributors": contribs,
            }
        )

    # Aggregated contributors ranking (mean weighted_value across overlapping windows)
    aggregated: list[dict[str, Any]] = []
    for fid, data in agg.items():
        cnt = data["count"] or 1
        avg_weighted = data["total_weighted"] / cnt
        avg_share = data["total_share"] / cnt if data["total_share"] else None
        # For piece stats, fetch one
        piece_min, piece_max, _ = _compute_feature_piece_stats(feature_series, fid)
        # Take representative raw/norm as mean
        raw_vals = [v for v in data["raw_values"] if isinstance(v, (int, float))]
        norm_vals = [v for v in data["norm_values"] if isinstance(v, (int, float))]
        rep_raw = sum(raw_vals) / len(raw_vals) if raw_vals else None
        rep_norm = sum(norm_vals) / len(norm_vals) if norm_vals else None
        aggregated.append(
            {
                "feature_id": fid,
                "label": data["label"],
                "human_label": data["label"],
                "weight": data["weight"],
                "avg_weighted_value": avg_weighted,
                "avg_contribution_share": avg_share,
                "max_normalized_value": data["max_normalized"] if data["max_normalized"] >= 0 else None,
                "representative_raw_value": rep_raw,
                "representative_normalized_value": rep_norm,
                "is_proxy": data["is_proxy"],
                "proxy_kind": "proxy" if fid in PROXY_FEATURES else ("texture proxy (weak mapping)" if dimension_id == "layers_coordination" and fid in TEXTURE_PROXY_IN_COORDINATION else None),
                "category": data["category"],
                "units": data["units"],
                "piece_raw_min": piece_min,
                "piece_raw_max": piece_max,
                "window_count": cnt,
            }
        )
    aggregated.sort(key=lambda x: (-x["avg_weighted_value"], - (x["max_normalized_value"] or 0), x["feature_id"]))

    # Build breakdown for layers_coordination specifically
    breakdown: dict[str, Any] | None = None
    if dimension_id == "layers_coordination":
        # Categorize aggregated contributors
        categories: dict[str, list[dict]] = defaultdict(list)
        for entry in aggregated:
            cat = entry.get("category") or _categorize_layers_coordination_feature(entry["feature_id"])
            categories[cat].append(entry)
        # Summarize per category
        breakdown = {
            "note": "Explicit surfacing for layers_coordination: which feature paths drive the score",
            "categories": {},
        }
        for cat_name in [
            "coordination.subdivision_mismatch_proxy",
            "coordination.asynchronous_hand_onset_count",
            "coordination.aligned_hand_onset_ratio/count",
            "rhythm/polyrhythm",
            "texture (weak mapping)",
            "other",
        ]:
            items = categories.get(cat_name, [])
            if items:
                breakdown["categories"][cat_name] = [
                    {
                        "feature_id": i["feature_id"],
                        "label": i["label"],
                        "avg_weighted_value": i["avg_weighted_value"],
                        "weight": i["weight"],
                        "max_normalized": i["max_normalized_value"],
                        "is_proxy": i["is_proxy"],
                    }
                    for i in items
                ]
        # Also add whether each path is present/high
        # Add explicit flagged booleans
        breakdown["has_subdivision_mismatch_proxy"] = any(e["feature_id"] == "coordination.subdivision_mismatch_proxy" for e in aggregated)
        breakdown["has_async"] = any(e["feature_id"] == "coordination.asynchronous_hand_onset_count" for e in aggregated)
        breakdown["has_aligned_proxy"] = any(e["feature_id"] in COORDINATION_ALIGNED for e in aggregated)
        breakdown["has_rhythm_polyrhythm"] = any(e["feature_id"] in RHYTHM_POLYRHYTHM_IN_COORDINATION for e in aggregated)
        breakdown["has_texture_proxy"] = any(e["feature_id"] in TEXTURE_PROXY_IN_COORDINATION for e in aggregated)
        # Add weights for context
        breakdown["weight_note"] = "texture features weakly mapped into coordination (weight <=0.15) are texture proxies, not true coordination"

    # Build warnings
    warnings: list[str] = []
    warnings.append("DEBUG ONLY: Internal attribution — not learner-facing, not pedagogy, not a scoring model.")
    warnings.append("All values are descriptive and relative within this piece (min-max normalized across windows). Not a calibrated grade or learner diagnosis.")
    if not overlapping_indices:
        warnings.append(f"No analysis windows overlap requested measures {measures_arg!r} (parsed {measures}). Check measure numbering (printed vs index).")
        warnings.append("Dimension values unavailable for requested range; no contributors to show.")
    else:
        # Proxy warnings
        proxy_contribs = [e for e in aggregated if e.get("is_proxy")]
        if proxy_contribs:
            proxy_ids = ", ".join(e["feature_id"] for e in proxy_contribs[:5])
            warnings.append(f"Proxy-based features contribute here: {proxy_ids}. Interpret as score-encoding proxies, not direct difficulty proof.")
        if dimension_id == "layers_coordination":
            # Specific coordination warnings
            if any(e["feature_id"] == "coordination.subdivision_mismatch_proxy" for e in aggregated):
                warnings.append("layers_coordination includes coordination.subdivision_mismatch_proxy — explicitly a proxy; different onset patterns are not uniformly difficult.")
            if any(e["feature_id"] in TEXTURE_PROXY_IN_COORDINATION for e in aggregated):
                warnings.append("Some contributors are texture features weakly mapped into coordination (weight <=0.15) as texture proxy, not true inter-hand independence.")
            if any(e["feature_id"] in COORDINATION_ALIGNED for e in aggregated):
                warnings.append("Aligned-hand onsets (coordination.aligned_hand_onset_count/ratio) weakly map to rhythm_timing only, not to layers_coordination as difficulty — they reflect coincident attacks, not independence.")
            if not any(e["feature_id"] in {"coordination.asynchronous_hand_onset_count", "coordination.subdivision_mismatch_proxy", "rhythm.polyrhythm_measure_ratio", "rhythm.polyrhythm_flag", "rhythm.asymmetric_tuplet_measure_ratio"} for e in aggregated):
                warnings.append("No strong coordination signals (async onsets, subdivision mismatch, polyrhythm) dominate this window; high score is carried by weak/texture proxies or other families.")
        # Normalization visibility
        for e in aggregated[:3]:
            if e.get("max_normalized_value") is not None and e["max_normalized_value"] >= 0.6:
                pmn = e.get("piece_raw_min")
                pmx = e.get("piece_raw_max")
                rep_raw = e.get("representative_raw_value")
                if pmn is not None and pmx is not None and pmx != pmn:
                    span = pmx - pmn
                    # If raw is modest in absolute terms but normalized high due to piece scaling, note
                    warnings.append(
                        f"High normalized for {e['feature_id']} (max {e['max_normalized_value']:.2f}) reflects within-piece min-max [{pmn:.3g}, {pmx:.3g}]; raw {rep_raw:.3g} is relative within this piece, not an absolute threshold."
                    )
    # Add disclaimer about not claiming hard
    warnings.append("Do not claim this passage is objectively hard; do not generate learner-facing advice from this debug output.")

    # Why high summary (technical, not pedagogical)
    if not overlapping_indices:
        why_high = f"DEBUG: No overlapping windows for measures {measures_arg} and dimension {dimension_id}; cannot attribute — check measure range and window config (size {getattr(overview_options, 'window_size', 2)}, stride {getattr(overview_options, 'stride', 1)})."
    elif not aggregated:
        why_high = f"DEBUG: Dimension {dimension_id} has no contributing feature values for overlapping windows {measures_arg}; graph signal is empty for this range."
    else:
        top = aggregated[:3]
        parts = []
        for e in top:
            share = e.get("avg_contribution_share")
            share_str = f", share {share:.0%}" if isinstance(share, float) else ""
            proxy_tag = " [proxy]" if e.get("is_proxy") else ""
            cat = f" [{e.get('category')}]" if dimension_id == "layers_coordination" and e.get("category") else ""
            parts.append(f"{e['feature_id']}{proxy_tag}{cat} (weight {e['weight']:.2f}, avg weighted {e['avg_weighted_value']:.3f}{share_str}, max norm {e['max_normalized_value']:.2f} ) raw {e['representative_raw_value']:.3g} in piece [{e['piece_raw_min']:.3g}, {e['piece_raw_max']:.3g}]")
        dim_vals = []
        for w in windows_payload:
            dim_vals.append(f"w{w['window_index']} {w['measure_range']} raw {w['dimension_raw']:.3f} norm {w['dimension_normalized']:.3f}" if w['dimension_normalized'] is not None else f"w{w['window_index']} n/a")
        dim_str = "; ".join(dim_vals[:3])
        why_high = (
            f"DEBUG: Dimension {dimension_id} ({dim_info.get('label')}) in measures {measures_arg} shows overlapping windows [{dim_str}]. "
            f"High signal is attributable to weighted feature paths (design weights from {GRAPH_TAXONOMY_VERSION}, not validated difficulty weights): "
            + "; ".join(parts)
            + ". Values are weighted mean of within-piece min-max normalized traces; high normalized reflects ranking within this piece, not absolute difficulty."
        )
        if dimension_id == "layers_coordination":
            # Add explicit breakdown sentence
            cat_summary = []
            if breakdown:
                for cat_name, items in breakdown.get("categories", {}).items():
                    top_cat = items[0]
                    cat_summary.append(f"{cat_name}: {top_cat['feature_id']} (avg weighted {top_cat['avg_weighted_value']:.3f})")
            if cat_summary:
                why_high += f" Breakdown: {'; '.join(cat_summary)}."

    # Onsets detail if requested
    onsets_detail: list[dict[str, Any]] | None = None
    if detail == "onsets":
        onsets_detail = _build_onsets_detail(score, measures_set)

    payload: dict[str, Any] = {
        "schema": DEBUG_SCHEMA,
        "debug": True,
        "debug_label": DEBUG_LABEL,
        "taxonomy_version": GRAPH_TAXONOMY_VERSION,
        "score": {
            "path": str(score_path),
            "title": score.title,
            "composer": score.composer,
            "measure_count": len(score.measures),
            "logical_note_count": len(score.logical_notes),
        },
        "request": {
            "measures_str": measures_arg,
            "measures_parsed": measures,
            "dimension_id": dimension_id,
            "dimension_label": dim_info.get("label"),
            "dimension_description": dim_info.get("description"),
            "dimension_caveats": dim_info.get("caveats"),
            "window": {
                "kind": getattr(overview_options, "window", "measure"),
                "size": float(getattr(overview_options, "window_size", 2)),
                "step": float(getattr(overview_options, "stride", 1)),
                "hand": getattr(overview_options, "hand", "both"),
            },
            "detail": detail,
        },
        "dimension": {
            "id": dimension_id,
            "label": dim_info.get("label"),
            "description": dim_info.get("description"),
            "caveats": dim_info.get("caveats"),
        },
        "windows": windows_payload,
        "overlapping_window_indices": overlapping_indices,
        "total_window_count": len(regions),
        "contributors_per_window": contributors_per_window,
        "aggregated_contributors": aggregated,
        "breakdown": breakdown,
        "why_high_summary": why_high,
        "warnings": warnings,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    if onsets_detail is not None:
        payload["onsets_detail"] = onsets_detail
        # Also include per-measure coordination summary for quick debug
        payload["onsets_detail_note"] = "DEBUG: Per-measure right/left offsets; aligned offsets reflect coincident hand attacks, mismatched offsets reflect subdivision mismatch proxy context."

    return payload


def render_debug_attribution_markdown(payload: dict[str, Any]) -> str:
    """Render markdown for debug attribution payload (loud debug header)."""
    lines: list[str] = []
    lines.append(f"# {payload.get('debug_label') or DEBUG_LABEL}")
    lines.append("")
    lines.append("> **WARNING: DEBUG-ONLY INTERNAL INFRASTRUCTURE — NOT LEARNER-FACING. No calibrated grade, no learner diagnosis, no pedagogical advice. Uses design weights (front_graph_taxonomy).**")
    lines.append("")

    score = payload.get("score", {})
    req = payload.get("request", {})
    dim = payload.get("dimension", {})

    lines.append("## Score")
    lines.append("")
    lines.append(f"- Path: `{score.get('path')}`")
    lines.append(f"- Title: {score.get('title') or 'Untitled'}")
    lines.append(f"- Composer: {score.get('composer') or 'Unknown'}")
    lines.append(f"- Measures in score: {score.get('measure_count')}")
    lines.append(f"- Logical notes: {score.get('logical_note_count')}")
    lines.append("")

    lines.append("## Request")
    lines.append("")
    lines.append(f"- Measures: `{req.get('measures_str')}` → parsed {req.get('measures_parsed')}")
    lines.append(f"- Dimension: `{req.get('dimension_id')}` — {dim.get('label') or ''}")
    if dim.get("description"):
        lines.append(f"  - Description: {dim.get('description')}")
    if dim.get("caveats"):
        lines.append(f"  - Caveats: {dim.get('caveats')}")
    win = req.get("window", {})
    lines.append(f"- Window: kind={win.get('kind')} size={win.get('size')} step={win.get('step')} hand={win.get('hand')}")
    lines.append(f"- Taxonomy: {payload.get('taxonomy_version')}")
    lines.append(f"- Generated: {payload.get('generated_at')}")
    lines.append("")

    windows = payload.get("windows", [])
    lines.append("## Overlapping analysis window(s)")
    lines.append("")
    if not windows:
        lines.append(f"- No windows overlap measures {req.get('measures_str')!r}. Check measure numbers (printed MusicXML numbers) and window config.")
        lines.append(f"- Total windows in profile: {payload.get('total_window_count')}")
        lines.append("")
    else:
        lines.append(f"- Found {len(windows)} overlapping window(s) out of {payload.get('total_window_count')} total (window size {win.get('size')}, stride {win.get('step')}).")
        lines.append("")
        lines.append("| window | measure_range | measure_numbers | label | dimension raw | dimension normalized |")
        lines.append("|---|---|---|---|---|---|")
        for w in windows:
            raw = w.get("dimension_raw")
            norm = w.get("dimension_normalized")
            raw_s = f"{raw:.4f}" if isinstance(raw, (int, float)) else "—"
            norm_s = f"{norm:.4f}" if isinstance(norm, (int, float)) else "—"
            mn = ",".join(str(x) for x in w.get("measure_numbers", []))
            lines.append(f"| {w.get('window_index')} | {w.get('measure_range')} | {mn} | {w.get('label') or ''} | {raw_s} | {norm_s} |")
        lines.append("")

    # Aggregated contributors
    agg = payload.get("aggregated_contributors", [])
    lines.append(f"## Ranked contributing features for `{req.get('dimension_id')}`")
    lines.append("")
    if not agg:
        lines.append("- No contributors available for this dimension/range (dimension signal empty or no overlapping windows).")
        lines.append("")
    else:
        lines.append(f"- Aggregated across {len(windows)} overlapping window(s); ranked by avg weighted value (weight × normalized). Weights are design weights from {payload.get('taxonomy_version')}, not validated difficulty weights.")
        lines.append("")
        lines.append("| rank | feature_id | label | raw | normalized | weight | avg weighted | avg share | units | source scope | proxy? | piece range |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for rank, c in enumerate(agg, start=1):
            raw = c.get("representative_raw_value")
            norm = c.get("max_normalized_value") if c.get("max_normalized_value") is not None else c.get("representative_normalized_value")
            raw_s = f"{raw:.3g}" if isinstance(raw, (int, float)) else "—"
            norm_s = f"{norm:.3f}" if isinstance(norm, (int, float)) else "—"
            weighted_s = f"{c.get('avg_weighted_value'):.3f}" if isinstance(c.get("avg_weighted_value"), (int, float)) else "—"
            share = c.get("avg_contribution_share")
            share_s = f"{share:.1%}" if isinstance(share, float) else "—"
            weight_s = f"{c.get('weight'):.2f}" if isinstance(c.get("weight"), (int, float)) else "—"
            proxy_s = c.get("proxy_kind") or ("proxy" if c.get("is_proxy") else "")
            prange = ""
            if c.get("piece_raw_min") is not None and c.get("piece_raw_max") is not None:
                prange = f"[{c.get('piece_raw_min'):.3g}, {c.get('piece_raw_max'):.3g}]"
            else:
                prange = "—"
            fid = c.get("feature_id") or ""
            label = c.get("label") or ""
            units = c.get("units") or ""
            scope = c.get("is_proxy") and "proxy" or ""  # placeholder? use source scope not available in agg? Actually agg lacks source scope; add empty
            # Try to include source scope if available from per-window first contributor
            # For brevity use empty
            lines.append(f"| {rank} | `{fid}` | {label} | {raw_s} | {norm_s} | {weight_s} | {weighted_s} | {share_s} | {units} |  | {proxy_s} | {prange} |")
        lines.append("")
        # Also per-window tables (compact)
        per_win = payload.get("contributors_per_window", [])
        if len(per_win) > 1 or (len(per_win) == 1 and len(per_win[0].get("contributors", [])) > 0):
            lines.append("### Per-window contributors (ranked, weight × normalized)")
            lines.append("")
            for pw in per_win:
                contribs = pw.get("contributors", [])
                if not contribs:
                    continue
                lines.append(f"#### Window {pw.get('window_index')} (measures {','.join(str(x) for x in pw.get('measure_numbers', []))})")
                lines.append("")
                lines.append("| rank | feature_id | raw | normalized | weight | weighted | share | proxy? | normalization |")
                lines.append("|---|---|---|---|---|---|---|---|---|")
                for c in contribs[:6]:
                    raw = c.get("raw_value")
                    norm = c.get("normalized_value")
                    raw_s = f"{raw:.3g}" if isinstance(raw, (int, float)) else "—"
                    norm_s = f"{norm:.3f}" if isinstance(norm, (int, float)) else "—"
                    weighted_s = f"{c.get('weighted_value'):.3f}" if isinstance(c.get("weighted_value"), (int, float)) else "—"
                    share = c.get("contribution_share")
                    share_s = f"{share:.1%}" if isinstance(share, float) else "—"
                    weight_s = f"{c.get('weight'):.2f}" if isinstance(c.get("weight"), (int, float)) else "—"
                    proxy_s = c.get("proxy_kind") or ("proxy" if c.get("is_proxy") else "")
                    note = c.get("normalization_note") or ""
                    # Truncate note for table
                    if len(note) > 80:
                        note = note[:77] + "..."
                    lines.append(f"| {c.get('rank')} | `{c.get('feature_id')}` | {raw_s} | {norm_s} | {weight_s} | {weighted_s} | {share_s} | {proxy_s} | {note} |")
                lines.append("")

    # Breakdown for layers_coordination
    breakdown = payload.get("breakdown")
    if breakdown and req.get("dimension_id") == "layers_coordination":
        lines.append("## `layers_coordination` breakdown — which path made this high? (debug)")
        lines.append("")
        lines.append("- Explicit surfacing per required output:")
        lines.append("")
        for cat_name in [
            "coordination.subdivision_mismatch_proxy",
            "coordination.asynchronous_hand_onset_count",
            "coordination.aligned_hand_onset_ratio/count",
            "rhythm/polyrhythm",
            "texture (weak mapping)",
            "other",
        ]:
            items = breakdown.get("categories", {}).get(cat_name)
            if items:
                lines.append(f"  - **{cat_name}**:")
                for it in items[:3]:
                    proxy_tag = " [proxy]" if it.get("is_proxy") else ""
                    lines.append(f"    - `{it['feature_id']}` weight {it['weight']:.2f} avg weighted {it['avg_weighted_value']:.3f} max norm {it['max_normalized']:.2f}{proxy_tag}")
            else:
                lines.append(f"  - **{cat_name}**: — not among top contributors for this range")
        lines.append("")
        lines.append(f"- Has subdivision_mismatch_proxy: {breakdown.get('has_subdivision_mismatch_proxy')}")
        lines.append(f"- Has async hand onset: {breakdown.get('has_async')}")
        lines.append(f"- Has aligned proxy: {breakdown.get('has_aligned_proxy')}")
        lines.append(f"- Has rhythm/polyrhythm: {breakdown.get('has_rhythm_polyrhythm')}")
        lines.append(f"- Has texture proxy: {breakdown.get('has_texture_proxy')}")
        lines.append(f"- Note: {breakdown.get('weight_note')}")
        lines.append("")

    # Why high summary
    lines.append("## Why high — technical, not pedagogical (debug)")
    lines.append("")
    lines.append(payload.get("why_high_summary", ""))
    lines.append("")

    # Warnings
    lines.append("## Warnings (debug)")
    lines.append("")
    for w in payload.get("warnings", []):
        lines.append(f"- {w}")
    lines.append("")

    # Onsets detail
    if payload.get("onsets_detail") is not None:
        lines.append("## Detail: onsets drilldown (coordination) — optional `--detail onsets`")
        lines.append("")
        lines.append("- Per-measure right-hand offsets, left-hand offsets, aligned offsets, mismatched offsets (offsets are onset - measure.start).")
        lines.append("")
        lines.append("| measure | measure_index | right offsets | left offsets | aligned | mismatched | union |")
        lines.append("|---|---|---|---|---|---|---|")
        for d in payload.get("onsets_detail", []):
            ro = ",".join(d.get("right_hand_offsets", []))
            lo = ",".join(d.get("left_hand_offsets", []))
            ao = ",".join(d.get("aligned_offsets", []))
            mo = ",".join(d.get("mismatched_offsets", []))
            # Truncate long offset lists
            if len(ro) > 40:
                ro = ro[:37] + "..."
            if len(lo) > 40:
                lo = lo[:37] + "..."
            lines.append(f"| {d.get('measure_number')} | {d.get('measure_index')} | {ro or '—'} ({d.get('right_hand_offset_count')}) | {lo or '—'} ({d.get('left_hand_offset_count')}) | {ao or '—'} ({d.get('aligned_offset_count')}) | {mo or '—'} ({d.get('mismatched_offset_count')}) | {d.get('union_offset_count')} |")
        lines.append("")
        if payload.get("onsets_detail_note"):
            lines.append(f"- {payload.get('onsets_detail_note')}")
            lines.append("")

    # Provenance footer
    lines.append("---")
    lines.append(f"*DEBUG ONLY — schema {payload.get('schema')} — taxonomy {payload.get('taxonomy_version')} — generated {payload.get('generated_at')}*")
    lines.append("")

    return "\n".join(lines)


def render_debug_attribution_json(payload: dict[str, Any]) -> str:
    """Stable JSON for machine-readable debug output."""
    # Ensure deterministic key order and serializable types
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)


__all__ = [
    "DEBUG_LABEL",
    "DEBUG_SCHEMA",
    "PROXY_FEATURES",
    "build_debug_attribution_payload",
    "parse_measures_arg",
    "render_debug_attribution_json",
    "render_debug_attribution_markdown",
]
