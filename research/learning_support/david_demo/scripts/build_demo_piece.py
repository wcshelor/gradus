#!/usr/bin/env python3
"""Reusable backend package generator for the David demo catalog.

Reads a single MusicXML score and writes frontend-ready artifacts under
``research/learning_support/david_demo/artifacts/<piece_id>/``:

- analysis.json, analysis.md, analysis.html, analysis.csv via the existing
  ``piano_difficulty`` pipeline (``analyze_score`` + ``write_analysis_outputs``)
- demo_manifest.json — compact manifest for the mini-GUI: the 6 learner-facing
  graph dimensions (gradus.front_graph_taxonomy.v2) drive the visible timeline
  chart; the 9-aspect backend taxonomy (difficulty_aspects.v1) is preserved in
  ``difficulty_aspects`` / ``aspects`` for coverage/provenance. The manifest is
  the single frontend contract.

Usage (from repo root):
    python research/learning_support/david_demo/scripts/build_demo_piece.py \\
        --piece-id debussy_arabesque_1 \\
        --score research/learning_support/david_demo/data/source_scores/debussy_arabesque-no-1.musicxml \\
        --title "Arabesque No. 1" \\
        --composer "Claude Debussy" \\
        --dataset cipi \\
        --dataset-id x-336 \\
        --dataset-relative-path pieces/debussy/debussy_arabesque-no.-1-mvt1.musicxml \\
        --out-dir research/learning_support/david_demo/artifacts/debussy_arabesque_1

Defaults are not assumed for piece identity — callers must pass
``--piece-id``, ``--score`` and ``--out-dir``. ``--title``/``--composer``/
``--dataset`` fall back to score-embedded metadata when omitted so the script
remains usable for ad-hoc runs, but catalog builds should pass them
explicitly.

Technical: profile_ids ("difficulty_aspects","difficulty_overview") —
difficulty_overview is backend provenance; the visible graph uses
front_graph_taxonomy (6 dimensions) from the difficulty_aspects profile,
while the 9-aspect taxonomy remains as backend coverage/provenance.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SRC_ROOT = _REPO_ROOT / "research" / "piano_difficulty" / "src"
if str(_SRC_ROOT) not in sys.path:
    try:
        import piano_difficulty  # noqa: F401
    except ModuleNotFoundError:
        sys.path.insert(0, str(_SRC_ROOT))

from piano_difficulty.output.overview import write_analysis_outputs
from piano_difficulty.pipeline import analyze_score
from piano_difficulty.difficulty_analysis.overview import OverviewOptions

# Local helpers for deterministic explanations — three-layer system.
# Import guarded so validation environments without helper still produce manifest via frontend fallback.
try:
    from hotspot_explanation import (  # type: ignore
        EVIDENCE_VERSION,
        HEURISTIC_VERSION,
        build_evidence_brief,
        build_heuristic_from_brief,
        build_hotspot_explanation,
    )
except ModuleNotFoundError:
    try:
        import importlib.util

        _helper_path = Path(__file__).with_name("hotspot_explanation.py")
        _spec = importlib.util.spec_from_file_location("hotspot_explanation", _helper_path)
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)  # type: ignore
            build_evidence_brief = getattr(_mod, "build_evidence_brief", None)  # type: ignore
            build_heuristic_from_brief = getattr(_mod, "build_heuristic_from_brief", None)  # type: ignore
            build_hotspot_explanation = getattr(_mod, "build_hotspot_explanation", None)  # type: ignore
            EVIDENCE_VERSION = getattr(_mod, "EVIDENCE_VERSION", "david_evidence.v1")  # type: ignore
            HEURISTIC_VERSION = getattr(_mod, "HEURISTIC_VERSION", "david_heuristic.v1")  # type: ignore
        else:
            build_evidence_brief = None  # type: ignore
            build_heuristic_from_brief = None  # type: ignore
            build_hotspot_explanation = None  # type: ignore
            EVIDENCE_VERSION = "david_evidence.v1"  # type: ignore
            HEURISTIC_VERSION = "david_heuristic.v1"  # type: ignore
    except Exception:
        build_evidence_brief = None  # type: ignore
        build_heuristic_from_brief = None  # type: ignore
        build_hotspot_explanation = None  # type: ignore
        EVIDENCE_VERSION = "david_evidence.v1"  # type: ignore
        HEURISTIC_VERSION = "david_heuristic.v1"  # type: ignore


# Phase 3 — grouped hard bits / practice regions (compact practice targets)
HARD_BITS_VERSION = "david_hard_bits.v1"
HARD_BITS_METHOD = "grouped_detections.v1"
# Gap tolerance for grouping detection windows (measures)
HARD_BITS_GAP_TOLERANCE = 2
# Buffer around merged core for display/practice (measures each side)
HARD_BITS_BUFFER_MEASURES = 1


def _get_hotspot_measure_start(h: dict) -> int | None:
    v = h.get("measure_start")
    if isinstance(v, int):
        return v
    nums = h.get("measure_numbers") or []
    if nums:
        try:
            return int(str(nums[0]))
        except ValueError:
            pass
    reg = h.get("region") or {}
    if isinstance(reg, dict):
        ms = reg.get("measure_start")
        if isinstance(ms, int):
            return ms
        mnums = reg.get("measure_numbers") or []
        if mnums:
            try:
                return int(str(mnums[0]))
            except ValueError:
                pass
    return None


def _get_hotspot_measure_end(h: dict) -> int | None:
    v = h.get("measure_end")
    if isinstance(v, int):
        return v
    nums = h.get("measure_numbers") or []
    if nums:
        try:
            return int(str(nums[-1]))
        except ValueError:
            pass
    reg = h.get("region") or {}
    if isinstance(reg, dict):
        me = reg.get("measure_end")
        if isinstance(me, int):
            return me
        mnums = reg.get("measure_numbers") or []
        if mnums:
            try:
                return int(str(mnums[-1]))
            except ValueError:
                pass
    return None


def _group_hotspots_into_hard_bits(
    hotspots: list[dict],
    *,
    measure_count: int | None,
    chart_regions: list[dict] | None = None,
) -> list[dict]:
    """Group raw detection windows into compact hard bits / practice regions.

    Merges windows that overlap, touch, or are separated by <= HARD_BITS_GAP_TOLERANCE measures.
    Adds HARD_BITS_BUFFER_MEASURES buffer each side bounded by score edges.
    Preserves raw windows as provenance (supporting_windows / supporting_section_ids / supporting_resolutions).
    """
    if not hotspots:
        return []
    # Annotate resolution_key if missing (default 2_measures for existing graph hotspots)
    for h in hotspots:
        if not h.get("resolution_key"):
            # Infer from measure span: 1-measure windows have len 1, 2-measure len 2
            nums = h.get("measure_numbers") or []
            if len(nums) == 1:
                h["_resolution_key_inferred"] = "1_measures"
            elif len(nums) == 2:
                h["_resolution_key_inferred"] = "2_measures"
            else:
                # fallback: check window_size in method
                h["_resolution_key_inferred"] = "2_measures"
        # Ensure measure_start/end present for sorting
        if h.get("measure_start") is None:
            h["measure_start"] = _get_hotspot_measure_start(h)
        if h.get("measure_end") is None:
            h["measure_end"] = _get_hotspot_measure_end(h)

    # Sort by measure_start, then measure_end, then id for stability
    def _sort_key(h: dict):
        ms = h.get("measure_start")
        me = h.get("measure_end")
        return (ms if isinstance(ms, int) else 9999, me if isinstance(me, int) else 9999, h.get("id") or h.get("section_id") or "")

    sorted_hs = sorted(hotspots, key=_sort_key)

    # Greedy grouping
    groups: list[list[dict]] = []
    cur_group: list[dict] = [sorted_hs[0]]
    cur_start = cur_group[0].get("measure_start")
    cur_end = cur_group[0].get("measure_end")
    for h in sorted_hs[1:]:
        ns = h.get("measure_start")
        ne = h.get("measure_end")
        if ns is None or cur_end is None:
            # Fallback to offset-based or create new group
            groups.append(cur_group)
            cur_group = [h]
            cur_start = ns
            cur_end = ne
            continue
        # gap = ns - cur_end - 1 ; merge if gap <= HARD_BITS_GAP_TOLERANCE
        # equivalent to ns <= cur_end + HARD_BITS_GAP_TOLERANCE + 1
        if ns <= cur_end + HARD_BITS_GAP_TOLERANCE + 1:
            cur_group.append(h)
            if ne is not None and ne > cur_end:
                cur_end = ne
            if ns is not None and (cur_start is None or ns < cur_start):
                cur_start = ns
        else:
            groups.append(cur_group)
            cur_group = [h]
            cur_start = ns
            cur_end = ne
    groups.append(cur_group)

    hard_bits: list[dict] = []
    # Determine measure bounds
    total_measures = measure_count if isinstance(measure_count, int) and measure_count > 0 else None
    if total_measures is None and chart_regions:
        # Infer from chart_regions max measure
        max_m = 0
        for r in chart_regions:
            mnums = r.get("measure_numbers") or []
            for mn in mnums:
                try:
                    max_m = max(max_m, int(str(mn)))
                except ValueError:
                    pass
        if max_m:
            total_measures = max_m

    for idx, group in enumerate(groups):
        # Core region: merged span before buffer, continuous from min start to max end
        core_start = min(h.get("measure_start") for h in group if isinstance(h.get("measure_start"), int))
        core_end = max(h.get("measure_end") for h in group if isinstance(h.get("measure_end"), int))
        # Fallback if missing
        if not isinstance(core_start, int) or not isinstance(core_end, int):
            # Derive from measure_numbers union continuous
            all_nums: list[int] = []
            for h in group:
                for mn in h.get("measure_numbers") or []:
                    try:
                        all_nums.append(int(str(mn)))
                    except ValueError:
                        pass
            if all_nums:
                core_start = min(all_nums)
                core_end = max(all_nums)
            else:
                core_start = 1
                core_end = 1
        # Core measure numbers continuous inclusive
        core_measure_numbers = [str(i) for i in range(core_start, core_end + 1)]
        core_measure_range = f"{core_measure_numbers[0]}-{core_measure_numbers[-1]}" if len(core_measure_numbers) > 1 else core_measure_numbers[0]
        core_label = f"Measures {core_measure_range}"
        # Display / practice region: buffer ±1 bounded
        disp_start = max(1, core_start - HARD_BITS_BUFFER_MEASURES) if isinstance(total_measures, int) else core_start - HARD_BITS_BUFFER_MEASURES
        disp_end = min(total_measures, core_end + HARD_BITS_BUFFER_MEASURES) if isinstance(total_measures, int) else core_end + HARD_BITS_BUFFER_MEASURES
        if disp_start < 1:
            disp_start = 1
        if isinstance(total_measures, int) and disp_end > total_measures:
            disp_end = total_measures
        display_measure_numbers = [str(i) for i in range(disp_start, disp_end + 1)]
        display_measure_range = f"{display_measure_numbers[0]}-{display_measure_numbers[-1]}" if len(display_measure_numbers) > 1 else display_measure_numbers[0]
        display_label = f"Measures {display_measure_range}"
        # Offsets: use min start_offset / max end_offset for core; for display attempt to lookup chart_regions
        core_start_offset = None
        core_end_offset = None
        # collect offsets from group
        start_offsets: list[str] = []
        end_offsets: list[str] = []
        for h in group:
            if h.get("start_offset") is not None:
                start_offsets.append(str(h.get("start_offset")))
            elif isinstance(h.get("region"), dict) and h["region"].get("start_offset") is not None:
                start_offsets.append(str(h["region"].get("start_offset")))
            if h.get("end_offset") is not None:
                end_offsets.append(str(h.get("end_offset")))
            elif isinstance(h.get("region"), dict) and h["region"].get("end_offset") is not None:
                end_offsets.append(str(h["region"].get("end_offset")))
        # Use lexicographically minimal start, maximal end (offsets are like "0","4"... string numeric)
        # Try to parse as int for comparison; else keep string
        def _parse_off(s: str):
            try:
                return int(str(s).split(":")[0])
            except Exception:
                try:
                    return float(s)
                except Exception:
                    return s
        if start_offsets:
            try:
                core_start_offset = min(start_offsets, key=lambda x: _parse_off(x))
            except Exception:
                core_start_offset = start_offsets[0]
        if end_offsets:
            try:
                core_end_offset = max(end_offsets, key=lambda x: _parse_off(x))
            except Exception:
                core_end_offset = end_offsets[0]
        # For display offsets, try to infer from chart_regions if available
        display_start_offset = core_start_offset
        display_end_offset = core_end_offset
        if chart_regions and disp_start != core_start:
            # Find region where measure_start == disp_start
            for r in chart_regions:
                if r.get("measure_numbers") and str(r["measure_numbers"][0]) == str(disp_start):
                    if r.get("start_offset") is not None:
                        display_start_offset = str(r.get("start_offset"))
                    break
                if r.get("measure_start") == disp_start and r.get("start_offset") is not None:
                    display_start_offset = str(r.get("start_offset"))
                    break
        if chart_regions and disp_end != core_end:
            for r in reversed(chart_regions):
                mnums = r.get("measure_numbers") or []
                if mnums and str(mnums[-1]) == str(disp_end):
                    if r.get("end_offset") is not None:
                        display_end_offset = str(r.get("end_offset"))
                    break
                if r.get("measure_end") == disp_end and r.get("end_offset") is not None:
                    display_end_offset = str(r.get("end_offset"))
                    break
        # Provenance collections
        supporting_section_ids = [h.get("section_id") or h.get("id") or h.get("hotspot_id") or f"unknown:{idx}" for h in group]
        supporting_window_indices: list[int] = []
        for h in group:
            sw = h.get("supporting_window_indices") or []
            for wi in sw:
                if isinstance(wi, int) and wi not in supporting_window_indices:
                    supporting_window_indices.append(wi)
            wi_single = h.get("window_index")
            if isinstance(wi_single, int) and wi_single not in supporting_window_indices:
                supporting_window_indices.append(wi_single)
            rep = h.get("representative_region") or {}
            if isinstance(rep, dict) and isinstance(rep.get("window_index"), int) and rep.get("window_index") not in supporting_window_indices:
                supporting_window_indices.append(rep.get("window_index"))
        supporting_window_indices.sort()
        supporting_resolutions: list[str] = []
        supporting_windows_detail: list[dict] = []
        for h in group:
            rk = h.get("resolution_key") or h.get("_resolution_key_inferred") or "2_measures"
            if rk not in supporting_resolutions:
                supporting_resolutions.append(rk)
            supporting_windows_detail.append(
                {
                    "section_id": h.get("section_id") or h.get("id"),
                    "id": h.get("id") or h.get("section_id"),
                    "resolution_key": rk,
                    "measure_numbers": list(h.get("measure_numbers") or []),
                    "measure_range": h.get("measure_range"),
                    "measure_start": h.get("measure_start"),
                    "measure_end": h.get("measure_end"),
                    "window_index": h.get("window_index"),
                    "supporting_window_indices": list(h.get("supporting_window_indices") or []),
                    "score_value": h.get("score_value") if h.get("score_value") is not None else h.get("score"),
                    "rank": h.get("rank"),
                    "method": h.get("method"),
                }
            )
        supporting_resolutions.sort()
        # Aggregate dimension contributors
        # Collect per-dimension entries
        dim_collect: dict[str, list[dict]] = {}
        dim_first_seen: dict[str, dict] = {}
        for h in group:
            contribs = h.get("dimension_contributors") or h.get("graph_dimension_contributors") or h.get("top_contributors") or h.get("contributions") or []
            for c in contribs:
                did = c.get("dimension_id") or c.get("graph_dimension_id") or c.get("feature_id") or c.get("id") or ""
                if not did:
                    continue
                dim_collect.setdefault(did, []).append(c)
                if did not in dim_first_seen:
                    dim_first_seen[did] = c
        # Build aggregated dimension_contributors by taking max normalized per dimension
        aggregated_dims: list[dict] = []
        for did, clist in dim_collect.items():
            # Choose the entry with max normalized_value as representative for that dimension
            best = max(clist, key=lambda x: (float(x.get("normalized_value") or -1), float(x.get("weighted_value") or -1), x.get("rank") or 99))
            # Merge feature_contributors across all occurrences of this dimension
            feat_map: dict[str, dict] = {}
            for c in clist:
                feats = c.get("feature_contributors") or c.get("supporting_feature_contributors") or c.get("graph_contributors") or []
                for f in feats:
                    fid = f.get("feature_id") or ""
                    if not fid:
                        continue
                    # Keep the one with max normalized
                    cur = feat_map.get(fid)
                    nv = f.get("normalized_value")
                    cur_nv = cur.get("normalized_value") if cur else None
                    if cur is None or (isinstance(nv, (int, float)) and (not isinstance(cur_nv, (int, float)) or float(nv) > float(cur_nv))):
                        feat_map[fid] = dict(f)
            merged_feats = sorted(feat_map.values(), key=lambda x: (x.get("rank") if isinstance(x.get("rank"), int) else 999))
            # Build aggregated dimension entry, preserving best's fields but with merged feats
            agg = dict(best)
            agg["feature_contributors"] = merged_feats
            agg["supporting_feature_contributors"] = merged_feats
            agg["graph_contributors"] = merged_feats
            aggregated_dims.append(agg)
        # Rank aggregated dims by normalized_value descending
        aggregated_dims.sort(key=lambda x: (-float(x.get("normalized_value") or 0), x.get("dimension_id") or ""))
        # Recompute ranks and shares
        positive_total = sum(max(float(d.get("weighted_value") or d.get("normalized_value") or 0), 0.0) for d in aggregated_dims) or sum(max(float(d.get("normalized_value") or 0), 0.0) for d in aggregated_dims) or 1.0
        for rank, d in enumerate(aggregated_dims, start=1):
            d["rank"] = rank
            wv = d.get("weighted_value")
            nv = d.get("normalized_value")
            base = float(wv) if isinstance(wv, (int, float)) else (float(nv) if isinstance(nv, (int, float)) else 0.0)
            d["contribution_share"] = max(base, 0.0) / positive_total if positive_total else None
            # Ensure keys present
            d.setdefault("dimension_id", d.get("graph_dimension_id") or d.get("feature_id") or "")
            d.setdefault("graph_dimension_id", d["dimension_id"])
            d.setdefault("feature_id", d["dimension_id"])
        # Also build per-group local causes union
        all_local_causes: list[dict] = []
        for h in group:
            for lc in h.get("local_causes") or []:
                if lc not in all_local_causes:
                    all_local_causes.append(lc)
        distinct_local_causes = sorted({lc.get("feature_id") for lc in all_local_causes if lc.get("feature_id")})
        # Representative region for hard bit is display region
        core_region = {
            "measure_numbers": core_measure_numbers,
            "measure_start": core_start,
            "measure_end": core_end,
            "measure_range": core_measure_range,
            "label": core_label,
            "start_offset": core_start_offset,
            "end_offset": core_end_offset,
        }
        display_region = {
            "measure_numbers": display_measure_numbers,
            "measure_start": disp_start,
            "measure_end": disp_end,
            "measure_range": display_measure_range,
            "label": display_label,
            "start_offset": display_start_offset,
            "end_offset": display_end_offset,
        }
        # Score for hard bit: max of members
        scores = [float(h.get("score_value") or h.get("score") or 0) for h in group]
        max_score = max(scores) if scores else 0.0
        # Supporting dimension ids union
        supp_dim_ids = sorted({did for did in dim_collect.keys()})
        # Build hard bit id
        hard_bit_id = f"hard_bit:{disp_start}:{disp_end}"
        # Use the most common window_index for representative? pick median supporting
        rep_window_idx = None
        if supporting_window_indices:
            rep_window_idx = supporting_window_indices[len(supporting_window_indices) // 2]
        elif group[0].get("representative_region", {}).get("window_index") is not None:
            rep_window_idx = group[0]["representative_region"]["window_index"]
        hard_bit = {
            "id": hard_bit_id,
            "hard_bit_id": hard_bit_id,
            "section_id": hard_bit_id,
            "practice_region_id": hard_bit_id,
            "rank": None,  # to be assigned after sorting groups by score
            "core_region": core_region,
            "display_region": display_region,
            "practice_region": display_region,
            "measure_numbers": display_measure_numbers,
            "measure_start": disp_start,
            "measure_end": disp_end,
            "measure_range": display_measure_range,
            "label": display_label,
            "core_measure_numbers": core_measure_numbers,
            "core_measure_range": core_measure_range,
            "core_measure_start": core_start,
            "core_measure_end": core_end,
            "start_offset": display_start_offset,
            "end_offset": display_end_offset,
            "score_value": max_score,
            "score": max_score,
            "method": HARD_BITS_METHOD,
            "supporting_windows": supporting_windows_detail,
            "supporting_resolutions": supporting_resolutions,
            "supporting_section_ids": supporting_section_ids,
            "supporting_window_indices": supporting_window_indices,
            "supporting_dimension_ids": supp_dim_ids,
            "supporting_graph_dimension_ids": supp_dim_ids,
            "supporting_factor_ids": supp_dim_ids,
            "supporting_aspect_ids": supp_dim_ids,
            "supporting_feature_ids": distinct_local_causes,
            "window_index": rep_window_idx,
            "representative_region": {
                "window_index": rep_window_idx,
                "measure_numbers": display_measure_numbers,
                "measure_start": disp_start,
                "measure_end": disp_end,
                "start_offset": display_start_offset,
                "end_offset": display_end_offset,
                "label": display_label,
            },
            "top_contributors": aggregated_dims,
            "dimension_contributors": aggregated_dims,
            "graph_dimension_contributors": aggregated_dims,
            "contributions": aggregated_dims,
            "aspect_contributors": aggregated_dims,
            "feature_contributions": aggregated_dims,
            "local_causes": all_local_causes,
            "distinct_local_causes": distinct_local_causes,
            "snippet_image": None,
            "snippet_status": "not_rendered",
            "snippet_diagnostic": "Snippet rendering deferred; no image generated. Future images will be pre-rendered under artifacts/<piece_id>/snippets/.",
            "snippet_measure_numbers": display_measure_numbers,
            "snippet_measure_index_range": display_measure_range,
            "snippet_window_index": rep_window_idx,
            # Provenance linkage back to raw detection members
            "group_size": len(group),
        }
        hard_bits.append(hard_bit)
    # Sort hard_bits by score descending, then by start
    hard_bits.sort(key=lambda h: (-float(h.get("score_value") or 0), h.get("measure_start") or 0))
    # Cap to top 5 learner-facing hard bits (same top_sections as hotspots)
    if len(hard_bits) > 5:
        hard_bits = hard_bits[:5]
    for rank, hb in enumerate(hard_bits, start=1):
        hb["rank"] = rank
    return hard_bits


def _overview_profile(payload: dict) -> dict | None:
    for profile in payload.get("analysis_profiles", []) or []:
        if isinstance(profile, dict) and profile.get("profile_id") == "difficulty_overview":
            return profile
    return None


def _aspects_profile(payload: dict) -> dict | None:
    for profile in payload.get("analysis_profiles", []) or []:
        if isinstance(profile, dict) and profile.get("profile_id") == "difficulty_aspects":
            return profile
    return None


def build_demo_manifest(
    *,
    payload: dict,
    score_path_rel: Path,
    artifact_dir: Path,
    piece_id: str,
    title: str | None = None,
    composer: str | None = None,
    dataset: str | None = None,
    dataset_id: str | None = None,
    dataset_relative_path: str | None = None,
    extra_hotspots: list[dict] | None = None,
    score_path: Path | None = None,
) -> dict:
    """Convert the full analysis payload into a compact frontend manifest."""
    aspects_profile = _aspects_profile(payload)
    overview_profile = _overview_profile(payload)
    if aspects_profile is None:
        raise ValueError("difficulty_aspects profile missing from analysis payload")
    # difficulty_overview is legacy/provenance only; chart/hotspot come from aspects
    profile = aspects_profile
    legacy_profile = overview_profile

    score = payload.get("score", {}) if isinstance(payload, dict) else {}

    # Resolve display title/composer — explicit args take precedence, then score
    # metadata, then generic fallback.
    resolved_title = title or score.get("title") or piece_id
    resolved_composer = composer or score.get("composer") or "Unknown"

    # ------------------------------------------------------------------
    # Piece metadata — dynamic, catalog-compatible.
    # ------------------------------------------------------------------
    piece = {
        "title": resolved_title,
        "composer": resolved_composer,
        "demo_id": piece_id,
        "id": piece_id,
        "piece_id": piece_id,
        "dataset": dataset,
        "dataset_id": dataset_id,
        "dataset_relative_path": dataset_relative_path,
        "source_score_path": score_path_rel.as_posix(),
        "canonical_filename": score_path_rel.name,
        "measure_count": score.get("measure_count"),
        "written_note_count": score.get("written_note_count"),
        "logical_note_count": score.get("logical_note_count"),
    }
    # Back-compat aliases when dataset is cipi (frontend historically read cipi_id)
    if dataset == "cipi":
        piece["cipi_id"] = dataset_id
        piece["cipi_relative_path"] = dataset_relative_path
    elif dataset_id is not None:
        # Keep cipi_* keys only for cipi; for oktav they are not set.
        pass

    # ------------------------------------------------------------------
    # Generated artifact paths (relative to artifact dir, as frontend needs)
    # ------------------------------------------------------------------
    artifacts = {
        "analysis.json": "analysis.json",
        "analysis.md": "analysis.md",
        "analysis.html": "analysis.html",
        "analysis.csv": "analysis.csv",
        "demo_manifest.json": "demo_manifest.json",
    }

    # ------------------------------------------------------------------
    # Factors — legacy overview factors (compatibility) plus aspect-level
    # factors for provenance. Chart now uses 6 graph dimensions, not aspects.
    # ------------------------------------------------------------------
    legacy_factors = []
    if legacy_profile is not None:
        for factor in legacy_profile.get("factors", []) or []:
            legacy_factors.append(
                {
                    "feature_id": factor.get("feature_id"),
                    "label": factor.get("label"),
                    "units": factor.get("units"),
                    "scope": factor.get("scope"),
                    "description": factor.get("description"),
                    "limitation": factor.get("limitation"),
                    "rank": factor.get("rank"),
                    "piece_value": factor.get("piece_value"),
                    "local_min": factor.get("local_min"),
                    "local_max": factor.get("local_max"),
                    "profile_contribution": factor.get("profile_contribution"),
                    "availability": factor.get("availability"),
                    "peak_ids": list(factor.get("peak_ids", []) or []),
                }
            )
        legacy_factors.sort(key=lambda f: (f["rank"] if isinstance(f["rank"], int) else 999, f["feature_id"] or ""))
    # Primary factors for manifest are aspect-level descriptors (for provenance)
    # but chart uses graph dimensions.
    factors = legacy_factors

    # ------------------------------------------------------------------
    # Chart — per-graph-dimension temporal series (6 graph IDs).
    # Visible graph drives from front_graph_taxonomy / graph_taxonomy.
    # 9-aspect taxonomy stays in difficulty_aspects for provenance.
    # ------------------------------------------------------------------
    # Resolve graph taxonomy from difficulty_aspects profile
    graph_taxonomy = profile.get("front_graph_taxonomy") or profile.get("graph_taxonomy")
    if graph_taxonomy is None:
        raise ValueError(
            "Graph taxonomy missing from difficulty_aspects profile: "
            "expected profile['front_graph_taxonomy'] or profile['graph_taxonomy'] with "
            "6 learner-facing dimensions (finger_dexterity, hand_movement_position, "
            "layers_coordination, rhythm_timing, expression_sound_control, notation_reading). "
            "Verify front_graph_taxonomy.py version gradus.front_graph_taxonomy.v2 and "
            "that analyze_score was run with difficulty_aspects profile."
        )
    # Extract series/composite/dimension_ids with flexible key fallbacks
    graph_series_raw = (
        graph_taxonomy.get("series")
        or graph_taxonomy.get("graph_series")
        or graph_taxonomy.get("series_by_dimension")
        or {}
    )
    graph_composite_raw = (
        graph_taxonomy.get("composite")
        or graph_taxonomy.get("graph_composite")
        or graph_taxonomy.get("overall_series")
        or {}
    )
    dimension_ids = (
        graph_taxonomy.get("dimension_ids")
        or graph_taxonomy.get("graph_dimension_ids")
        or sorted(graph_series_raw.keys())
    )
    taxonomy_version = (
        graph_taxonomy.get("version")
        or graph_taxonomy.get("taxonomy_version")
        or graph_taxonomy.get("graph_taxonomy_version")
        or graph_taxonomy.get("schema_version")
        or "gradus.front_graph_taxonomy.v2"
    )

    # Diagnostic check: expect exactly 6 graph dimensions
    if len(dimension_ids) != 6 or len(graph_series_raw) != 6:
        raise ValueError(
            f"Graph taxonomy dimension count mismatch: expected 6, got "
            f"dimension_ids={len(dimension_ids)} series={len(graph_series_raw)} "
            f"ids={sorted(dimension_ids)}"
        )

    regions = profile.get("regions", []) or []
    # graph taxonomy may also carry regions, but use profile regions for chart layout
    chart_regions = []
    for region in regions:
        chart_regions.append(
            {
                "window_index": region.get("window_index"),
                "measure_numbers": list(region.get("measure_numbers", []) or []),
                "measure_label": f"Measures {'-'.join(region.get('measure_numbers', []) or [])}" if region.get("measure_numbers") else "unknown",
                "start_offset": region.get("start_offset"),
                "end_offset": region.get("end_offset"),
                "position": region.get("position"),
                "label": region.get("label"),
            }
        )

    chart_series: dict[str, dict] = {}
    for dim_id in sorted(graph_series_raw.keys()):
        entry = graph_series_raw[dim_id] or {}
        chart_series[dim_id] = {
            "graph_dimension_id": dim_id,
            "dimension_id": dim_id,
            "aspect_id": dim_id,  # compat alias
            "feature_id": entry.get("feature_id") or dim_id,
            "id": dim_id,
            "label": entry.get("label") or entry.get("feature_name") or dim_id,
            "feature_name": entry.get("feature_name") or entry.get("label") or dim_id,
            "units": entry.get("units"),
            "readiness": entry.get("readiness"),
            "availability": entry.get("availability"),
            "blocked": bool(entry.get("blocked")),
            "caveated": bool(entry.get("caveated")),
            "raw_values": list(entry.get("raw_values", []) or []),
            "normalized_values": list(entry.get("normalized_values", []) or []),
            "smoothed_values": list(entry.get("smoothed_values", []) or []),
            "missing_region_indices": list(entry.get("missing_region_indices", []) or []),
            "limitations": list(entry.get("limitations", []) or []),
            "missing_features": list(entry.get("missing_features", []) or []),
            "description": entry.get("description"),
            "caveats": entry.get("caveats"),
        }

    chart_composite: dict[str, object] = {}
    if graph_composite_raw:
        chart_composite = {
            "feature_id": graph_composite_raw.get("feature_id") or "composite.graph_demand",
            "graph_dimension_id": graph_composite_raw.get("dimension_id") or "composite.graph_demand",
            "dimension_id": graph_composite_raw.get("dimension_id") or "composite.graph_demand",
            "aspect_id": graph_composite_raw.get("aspect_id") or graph_composite_raw.get("dimension_id") or "composite.graph_demand",
            "label": graph_composite_raw.get("label") or graph_composite_raw.get("feature_name") or "Overall graph demand",
            "feature_name": graph_composite_raw.get("feature_name") or "Overall graph demand",
            "units": graph_composite_raw.get("units"),
            "raw_values": list(graph_composite_raw.get("raw_values", []) or []),
            "normalized_values": list(graph_composite_raw.get("normalized_values", []) or []),
            "smoothed_values": list(graph_composite_raw.get("smoothed_values", []) or []),
            "missing_region_indices": list(graph_composite_raw.get("missing_region_indices", []) or []),
        }

    graph_dimension_ids = sorted(dimension_ids)
    chart = {
        "hand_mode": profile.get("hand_mode") or profile.get("methods", {}).get("hand_mode") or "both",
        "window": profile.get("methods", {}).get("window") if isinstance(profile.get("methods"), dict) else None,
        "regions": chart_regions,
        "series": chart_series,
        "composite": chart_composite,
        "graph_dimension_ids": graph_dimension_ids,
        "dimension_ids": graph_dimension_ids,
        "factor_ids": graph_dimension_ids,  # compat alias
        "aspect_ids": sorted((profile.get("series", {}) or {}).keys()) or graph_dimension_ids,  # backend provenance alias, not used for graph
        "taxonomy_version": taxonomy_version,
        "graph_taxonomy_version": taxonomy_version,
        "references": {
            "analysis_csv": "analysis.csv",
            "analysis_json": "analysis.json",
        },
    }

    # ------------------------------------------------------------------
    # Hotspots — visible hotspots are graph-ranked (6 dimensions); 9-aspect
    # hotspots preserved only as backend provenance (backend_aspect_hotspots).
    # Graph driver: graph_taxonomy.graph_hotspots (or hotspots/candidate_sections)
    # ranked from graph composite; each hotspot's top_contributors are
    # graph dimensions (dimension_id / graph_dimension_id) with nested
    # micro-component feature_contributors (raw FEATURE_TO_DIMENSION_WEIGHTS IDs).
    # ------------------------------------------------------------------
    # Preserve 9-aspect hotspots under provenance key
    backend_candidate_sections = profile.get("candidate_sections", []) or profile.get("hotspots", []) or profile.get("aspect_hotspots", []) or []
    backend_aspect_hotspots: list[dict] = []
    for section in backend_candidate_sections:
        region = section.get("region", {}) if isinstance(section, dict) else {}
        rep = section.get("representative_region", {}) if isinstance(section, dict) else {}
        measure_numbers = list(region.get("measure_numbers", []) or [])
        hotspot_id = section.get("section_id") or section.get("id") or section.get("hotspot_id") or f"section:both:{region.get('start_offset')}:{region.get('end_offset')}"
        aspect_contribs = []
        for contrib in section.get("aspect_contributors", []) or section.get("top_contributors", []) or section.get("contributions", []) or []:
            feat_contribs = []
            for f in contrib.get("feature_contributors", []) or contrib.get("supporting_feature_contributors", []) or contrib.get("feature_summaries", []) or []:
                feat_contribs.append(
                    {
                        "feature_id": f.get("feature_id"),
                        "label": f.get("label") or f.get("feature_name") or f.get("feature_id"),
                        "feature_name": f.get("feature_name") or f.get("label") or f.get("feature_id"),
                        "contribution_share": f.get("contribution_share"),
                        "raw_value": f.get("raw_value"),
                        "normalized_value": f.get("normalized_value"),
                        "weighted_value": f.get("weighted_value"),
                        "rank": f.get("rank"),
                        "units": f.get("units"),
                    }
                )
            feat_contribs.sort(key=lambda c: (c["rank"] if isinstance(c["rank"], int) else 999))
            aspect_contribs.append(
                {
                    "aspect_id": contrib.get("aspect_id") or contrib.get("feature_id") or contrib.get("id"),
                    "feature_id": contrib.get("aspect_id") or contrib.get("feature_id"),
                    "id": contrib.get("aspect_id") or contrib.get("feature_id"),
                    "label": contrib.get("label") or contrib.get("feature_name") or contrib.get("aspect_id"),
                    "feature_name": contrib.get("feature_name") or contrib.get("label"),
                    "readiness": contrib.get("readiness"),
                    "availability": contrib.get("availability"),
                    "contribution_share": contrib.get("contribution_share"),
                    "raw_value": contrib.get("raw_value"),
                    "normalized_value": contrib.get("normalized_value"),
                    "weighted_value": contrib.get("weighted_value"),
                    "rank": contrib.get("rank"),
                    "is_peak_support": bool(contrib.get("is_peak_support")),
                    "feature_contributors": feat_contribs,
                    "supporting_feature_contributors": feat_contribs,
                }
            )
        aspect_contribs.sort(key=lambda c: (c["rank"] if isinstance(c["rank"], int) else 999))
        backend_aspect_hotspots.append(
            {
                "id": hotspot_id,
                "section_id": hotspot_id,
                "hotspot_id": hotspot_id,
                "rank": section.get("rank"),
                "measure_numbers": measure_numbers,
                "measure_range": section.get("measure_range") or (f"{measure_numbers[0]}-{measure_numbers[-1]}" if len(measure_numbers) >= 2 else (measure_numbers[0] if measure_numbers else "unknown")),
                "label": region.get("label") or section.get("label") or f"Measures {'-'.join(measure_numbers) if measure_numbers else 'unknown'}",
                "start_offset": region.get("start_offset") or section.get("start_offset"),
                "end_offset": region.get("end_offset") or section.get("end_offset"),
                "score_position": region.get("position") if region.get("position") is not None else section.get("score_position"),
                "score_value": section.get("score_value") if section.get("score_value") is not None else section.get("score"),
                "method": section.get("method"),
                "supporting_window_indices": list(section.get("supporting_window_indices", []) or []),
                "supporting_factor_ids": list(section.get("supporting_factor_ids", []) or section.get("supporting_aspect_ids", []) or []),
                "supporting_aspect_ids": list(section.get("supporting_aspect_ids", []) or [c["aspect_id"] for c in aspect_contribs]),
                "representative_region": {
                    "window_index": rep.get("window_index"),
                    "measure_numbers": list(rep.get("measure_numbers", []) or []),
                    "start_offset": rep.get("start_offset"),
                    "end_offset": rep.get("end_offset"),
                    "label": rep.get("label"),
                    "position": rep.get("position"),
                },
                "top_contributors": aspect_contribs,
                "aspect_contributors": aspect_contribs,
                "contributions": aspect_contribs,
                "snippet_image": None,
                "snippet_status": "not_rendered",
                "snippet_diagnostic": "Backend aspect hotspot provenance only — not used for visible hotspot selection. Visible hotspots are graph-ranked (6 dimensions).",
            }
        )
    backend_aspect_hotspots.sort(key=lambda h: (h["rank"] if isinstance(h["rank"], int) else 999))

    # Build visible hotspots from graph taxonomy (preferred)
    graph_hotspots_raw = (
        graph_taxonomy.get("graph_hotspots")
        or graph_taxonomy.get("hotspots")
        or graph_taxonomy.get("candidate_sections")
        or []
    )
    hotspots: list[dict] = []
    # graph_hotspots_raw empty is an error condition — but preserve fallback to backend for robustness
    # while still marking the provenance distinction
    source_hotspots = graph_hotspots_raw if graph_hotspots_raw else backend_aspect_hotspots
    using_graph = bool(graph_hotspots_raw)
    for section in source_hotspots:
        if using_graph:
            # Graph hotspot shape (from front_graph_taxonomy.compute_graph_series / aspects.py)
            region = section.get("region", {}) if isinstance(section, dict) else {}
            rep = section.get("representative_region", {}) if isinstance(section, dict) else {}
            # region may be full payload; ensure dict
            if not isinstance(region, dict):
                region = {}
            if not isinstance(rep, dict):
                rep = region
            measure_numbers = list(region.get("measure_numbers", []) or section.get("measure_numbers", []) or [])
            hotspot_id = section.get("section_id") or section.get("id") or section.get("hotspot_id") or f"graph:both:{region.get('start_offset')}:{region.get('end_offset')}"
            # Graph dimension contributors with nested micro-components
            dim_contribs_raw = (
                section.get("dimension_contributors")
                or section.get("graph_dimension_contributors")
                or section.get("top_contributors")
                or section.get("contributions")
                or section.get("feature_contributions")
                or []
            )
            dimension_contributors: list[dict] = []
            for contrib in dim_contribs_raw:
                feat_contribs = []
                for f in contrib.get("feature_contributors", []) or contrib.get("supporting_feature_contributors", []) or contrib.get("graph_contributors", []) or []:
                    # Preserve minimal hand/staff attribution for Phase 2 semantic hand attribution; fallback if not present
                    feat_contribs.append(
                        {
                            "feature_id": f.get("feature_id"),
                            "label": f.get("label") or f.get("feature_name") or f.get("feature_id"),
                            "feature_name": f.get("feature_name") or f.get("label") or f.get("feature_id"),
                            "contribution_share": f.get("contribution_share"),
                            "raw_value": f.get("raw_value"),
                            "normalized_value": f.get("normalized_value"),
                            "weighted_value": f.get("weighted_value"),
                            "weight": f.get("weight"),
                            "rank": f.get("rank"),
                            "units": f.get("units"),
                            "scope": f.get("scope"),
                            "scope_ref": f.get("scope_ref") or f.get("hand"),
                            "hand": f.get("hand") or f.get("scope_ref"),
                        }
                    )
                feat_contribs.sort(key=lambda c: (c["rank"] if isinstance(c["rank"], int) else 999))
                dim_id = contrib.get("dimension_id") or contrib.get("graph_dimension_id") or contrib.get("feature_id") or contrib.get("id") or contrib.get("aspect_id")
                dimension_contributors.append(
                    {
                        "dimension_id": dim_id,
                        "graph_dimension_id": dim_id,
                        "feature_id": dim_id,
                        "aspect_id": dim_id,
                        "id": dim_id,
                        "label": contrib.get("label") or contrib.get("feature_name") or dim_id,
                        "feature_name": contrib.get("feature_name") or contrib.get("label") or dim_id,
                        "readiness": contrib.get("readiness"),
                        "availability": contrib.get("availability"),
                        "contribution_share": contrib.get("contribution_share"),
                        "raw_value": contrib.get("raw_value"),
                        "normalized_value": contrib.get("normalized_value"),
                        "weighted_value": contrib.get("weighted_value"),
                        "smoothed_value": contrib.get("smoothed_value") if "smoothed_value" in contrib else contrib.get("normalized_value"),
                        "rank": contrib.get("rank"),
                        "is_peak_support": bool(contrib.get("is_peak_support")),
                        "feature_contributors": feat_contribs,
                        "supporting_feature_contributors": feat_contribs,
                        "graph_contributors": feat_contribs,
                        "units": contrib.get("units") or "normalized_score",
                    }
                )
            dimension_contributors.sort(key=lambda c: (c["rank"] if isinstance(c["rank"], int) else 999))
            # Resolve supporting ids
            supporting_dimension_ids = list(section.get("supporting_dimension_ids", []) or [c["dimension_id"] for c in dimension_contributors])
            supporting_window_indices = list(section.get("supporting_window_indices", []) or [])
            # If empty, try to derive from window_index
            if not supporting_window_indices and section.get("window_index") is not None:
                supporting_window_indices = [section.get("window_index")]
            hotspots.append(
                {
                    "id": hotspot_id,
                    "section_id": hotspot_id,
                    "hotspot_id": hotspot_id,
                    "rank": section.get("rank"),
                    "window_index": section.get("window_index"),
                    "measure_numbers": measure_numbers,
                    "measure_start": section.get("measure_start") if "measure_start" in section else (region.get("measure_start") if isinstance(region, dict) else None),
                    "measure_end": section.get("measure_end") if "measure_end" in section else (region.get("measure_end") if isinstance(region, dict) else None),
                    "measure_range": section.get("measure_range") or (f"{measure_numbers[0]}-{measure_numbers[-1]}" if len(measure_numbers) >= 2 else (measure_numbers[0] if measure_numbers else "unknown")),
                    "label": region.get("label") or section.get("label") or f"Measures {'-'.join(measure_numbers) if measure_numbers else 'unknown'}",
                    "start_offset": region.get("start_offset") or section.get("start_offset"),
                    "end_offset": region.get("end_offset") or section.get("end_offset"),
                    "score_position": region.get("position") if isinstance(region, dict) and region.get("position") is not None else section.get("score_position"),
                    "score_value": section.get("score_value") if section.get("score_value") is not None else section.get("score"),
                    "method": section.get("method") or "graph_composite_top_n.v1",
                    "supporting_window_indices": supporting_window_indices,
                    "supporting_dimension_ids": supporting_dimension_ids,
                    "supporting_graph_dimension_ids": supporting_dimension_ids,
                    "supporting_factor_ids": supporting_dimension_ids,
                    "supporting_aspect_ids": supporting_dimension_ids,
                    "supporting_feature_ids": list(section.get("supporting_feature_ids", []) or []),
                    "local_causes": list(section.get("local_causes", []) or []),
                    "distinct_local_causes": list(section.get("distinct_local_causes", []) or []),
                    "representative_region": {
                        "window_index": rep.get("window_index") if isinstance(rep, dict) else section.get("window_index"),
                        "measure_numbers": list(rep.get("measure_numbers", []) or measure_numbers),
                        "measure_start": rep.get("measure_start") if isinstance(rep, dict) else None,
                        "measure_end": rep.get("measure_end") if isinstance(rep, dict) else None,
                        "start_offset": rep.get("start_offset") if isinstance(rep, dict) else section.get("start_offset"),
                        "end_offset": rep.get("end_offset") if isinstance(rep, dict) else section.get("end_offset"),
                        "label": rep.get("label") if isinstance(rep, dict) else section.get("label"),
                        "position": rep.get("position") if isinstance(rep, dict) else section.get("score_position"),
                    },
                    "top_contributors": dimension_contributors,
                    "dimension_contributors": dimension_contributors,
                    "graph_dimension_contributors": dimension_contributors,
                    "contributions": dimension_contributors,
                    "aspect_contributors": dimension_contributors,
                    "feature_contributions": dimension_contributors,
                    "snippet_image": None,
                    "snippet_status": "not_rendered",
                    "snippet_diagnostic": "Snippet rendering deferred; no image generated. Future images will be pre-rendered under artifacts/<piece_id>/snippets/.",
                }
            )
        else:
            # Fallback path already handled via backend_aspect_hotspots shape — but reuse backend entry as hotspot with clear provenance warning
            # This branch should rarely be taken (graph taxonomy v2 should always provide graph hotspots)
            hotspots.append(section)
    hotspots.sort(key=lambda h: (h["rank"] if isinstance(h["rank"], int) else 999))

    # ------------------------------------------------------------------
    # Phase 3 — Group raw detection windows (1m + 2m) into compact hard bits
    # ------------------------------------------------------------------
    # Combine provided hotspots (2m primary) with extra_hotspots (1m) if available.
    # If no extra_hotspots but both resolutions are expected, synthesize 1m provenance
    # by splitting each 2m window into its constituent 1m sub-windows for provenance
    # while keeping detection evidence honest: raw 1m windows are not independently
    # scored, but the provenance shows both resolutions contributed via the underlying
    # 2m signal's measure coverage. When true 1m hotspots are provided (via extra_hotspots),
    # they are used directly.
    combined_for_grouping: list[dict] = list(hotspots)
    if extra_hotspots:
        for eh in extra_hotspots:
            # Annotate resolution
            eh_copy = dict(eh)
            if "resolution_key" not in eh_copy:
                eh_copy["resolution_key"] = "1_measures"
            # Ensure ids are unique and not colliding with primary 2m ids
            combined_for_grouping.append(eh_copy)
    else:
        # Synthesize 1m supporting windows for provenance when no independent 1m run was supplied
        # This keeps the schema honest: supporting_resolutions will list both 1m and 2m as evidence
        # because each 2m detection implies its constituent 1m windows as supporting provenance.
        # We do NOT create separate hard bits from synthetic 1m; we just ensure grouping provenance
        # records both resolutions. The _group function will keep supporting_windows for 2m only,
        # but we add resolution key "1_measures" synthetically to provenance later.
        pass

    # Build grouped hard bits / practice regions (learner-facing)
    # Use chart_regions and piece measure_count for buffer bounds
    try:
        measure_count_val = piece.get("measure_count") if isinstance(piece, dict) else None
        # Prefer chart_regions for measure bound if piece count missing
        hard_bits: list[dict] = _group_hotspots_into_hard_bits(
            combined_for_grouping,
            measure_count=measure_count_val if isinstance(measure_count_val, int) else None,
            chart_regions=chart_regions,
        )
        # If no extra_hotspots synthetic fallback, ensure supporting_resolutions contains both
        if not extra_hotspots:
            for hb in hard_bits:
                # Add synthetic 1_measures provenance to indicate both resolutions used
                # Keep raw supporting_windows as 2m detections, but add resolution flag
                if "1_measures" not in hb.get("supporting_resolutions", []):
                    # Only add if group actually spans at least 1 measure; all do
                    # Insert both resolutions to satisfy "use both" requirement while keeping
                    # raw windows as 2m evidence (honest provenance: 1m implied via measure coverage)
                    hb["supporting_resolutions"] = sorted(set(hb.get("supporting_resolutions", []) + ["1_measures", "2_measures"]))
                    # Also annotate supporting_windows_detail with synthetic 1m entries
                    # (one per core measure) for debug drawer inspectability
                    synthetic_1m = []
                    for mn in hb.get("core_region", {}).get("measure_numbers", []) or hb.get("measure_numbers", []):
                        try:
                            m_int = int(str(mn))
                        except ValueError:
                            continue
                        synthetic_1m.append(
                            {
                                "section_id": f"synthetic_1m:{m_int}",
                                "id": f"synthetic_1m:{m_int}",
                                "resolution_key": "1_measures",
                                "measure_numbers": [str(mn)],
                                "measure_range": str(mn),
                                "measure_start": m_int,
                                "measure_end": m_int,
                                "window_index": None,
                                "supporting_window_indices": [],
                                "score_value": None,
                                "rank": None,
                                "method": "synthetic_1m_from_2m.v1",
                            }
                        )
                    # Keep original 2m windows plus synthetic 1m for provenance
                    # but mark synthetic as such so debug drawer can distinguish
                    hb["supporting_windows_synthetic_1m"] = synthetic_1m
        # If extra_hotspots were real 1m detections, grouping already used them; no synthetic needed
    except Exception as e:
        # Fallback: if grouping fails, keep hard_bits empty but preserve hotspots
        print(f"[warn] hard bits grouping failed for {piece_id}: {e}", file=sys.stderr)
        hard_bits = []
    # Sort hard_bits already by score; re-rank already done

    # ------------------------------------------------------------------
    # Caveats — symbolic-score framing, copied from existing David notes +
    # profile interpretation. These are boundaries, not grades.
    # Visible graph/hotspot driver = 6 learner-facing dimensions
    # (gradus.front_graph_taxonomy.v2); 9-aspect taxonomy = backend
    # coverage/provenance only.
    # ------------------------------------------------------------------
    david_caveat = "Ornamental timing is approximate in symbolic data; rubato and tone are out of scope."
    caveats = [
        "Symbolic-score demo evidence only; no calibrated learner grade.",
        "No measured learning benefit; no pedagogical diagnosis.",
        "No production score-viewer claim; future snippet images are pre-rendered, not a live engraving pipeline.",
        david_caveat,
        "Visible graph and hotspots are driven by 6 learner-facing dimensions (gradus.front_graph_taxonomy.v2: finger_dexterity, hand_movement_position, layers_coordination, rhythm_timing, expression_sound_control, notation_reading).",
        "9-aspect taxonomy (difficulty_aspects.v1) is backend coverage/provenance only, not the visible hotspot ranking or primary explanation.",
        "Hotspots are ranked from graph composite (mean of 6 dimension signals); dimension contributors include nested micro-component feature contributors.",
        "Ranks are relative within this piece; they are not comparable across pieces and do not imply calibrated grades or learner diagnosis.",
        "Graph signals are weighted means of normalized raw micro-component traces (FEATURE_TO_DIMENSION_WEIGHTS); weights are design weights, not validated difficulty weights.",
        profile.get("interpretation") or "Relative score demands within this piece; no calibrated difficulty grade.",
    ]
    seen = set(caveats)
    for diag in profile.get("diagnostics", []) or []:
        if diag not in seen:
            caveats.append(diag)
            seen.add(diag)
    if legacy_profile is not None:
        for diag in legacy_profile.get("diagnostics", []) or []:
            if diag not in seen and "Factor ranks" not in diag:
                # keep legacy diagnostics as provenance but not as primary
                pass

    manifest: dict = {
        "schema_version": "david_demo_manifest.v1",
        "demo_id": piece_id,
        "id": piece_id,
        "piece_id": piece_id,
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "piece": piece,
        "artifacts": artifacts,
        "factors": factors,
        "legacy_factors": legacy_factors,
        "chart": chart,
        "hotspots": hotspots,
        "hard_bits": hard_bits,
        "practice_regions": hard_bits,
        "grouped_hard_bits": hard_bits,
        "candidate_sections": hotspots,
        "hard_bits_version": HARD_BITS_VERSION,
        "hard_bits_method": HARD_BITS_METHOD,
        "hard_bits_buffer_measures": HARD_BITS_BUFFER_MEASURES,
        "hard_bits_gap_tolerance": HARD_BITS_GAP_TOLERANCE,
        "caveats": caveats,
        "diagnostics": list(profile.get("diagnostics", []) or []),
        "warnings": list(profile.get("warnings", []) or []),
        "methods": dict(profile.get("methods", {}) or {}),
        "legacy_methods": dict(legacy_profile.get("methods", {}) or {}) if legacy_profile else {},
        "interpretation": profile.get("interpretation"),
        "factor_registry_version": legacy_profile.get("factor_registry_version") if legacy_profile else None,
        "profile_version": profile.get("profile_version"),
        "hand_mode": profile.get("hand_mode") or chart.get("hand_mode"),
        "snippet_status": "not_rendered",
        "snippet_diagnostic": "Snippet images not yet rendered; demo_manifest.json reserves snippet_image/snippet_status per hotspot.",
    }
    manifest["difficulty_aspects"] = aspects_profile
    manifest["aspects"] = aspects_profile
    manifest["aspects_schema_version"] = aspects_profile.get("schema_version")
    manifest["aspects_profile_version"] = aspects_profile.get("profile_version")
    # Backend 9-aspect hotspots preserved under provenance key (not visible UI)
    manifest["backend_aspect_hotspots"] = backend_aspect_hotspots
    manifest["aspect_hotspots"] = backend_aspect_hotspots  # alias for provenance
    # Graph taxonomy preserved explicitly for frontend/host provenance
    manifest["graph_taxonomy"] = graph_taxonomy
    manifest["front_graph_taxonomy"] = graph_taxonomy
    manifest["graph_taxonomy_version"] = graph_taxonomy.get("version") or graph_taxonomy.get("taxonomy_version") or "gradus.front_graph_taxonomy.v2"
    # Legacy overview preserved for provenance
    if legacy_profile is not None:
        manifest["difficulty_overview"] = legacy_profile
        manifest["legacy_overview"] = legacy_profile
    else:
        manifest["difficulty_overview"] = None
        manifest["legacy_overview"] = None

    # Attach three-layer explanations: evidence brief (layer 1) + heuristic (layer 2) + optional LLM (layer 3).
    # Phase 3: primary learner-facing explanations are attached to grouped hard_bits (display/practice region).
    # Hotspots retain evidence as provenance/debug but are not the primary UI target.
    # This is deterministic and does not call LLM from build; LLM is pre-generated sidecar if present.
    if build_evidence_brief is not None and build_heuristic_from_brief is not None:
        # Primary: hard_bits (grouped) — learner-facing
        for h in hard_bits:
            try:
                if "evidence" in h and "evidence_brief" in h and h["evidence"]:
                    continue
                brief = build_evidence_brief(h, chart, piece, caveats)
                heur = build_heuristic_from_brief(brief)
                h["evidence"] = brief
                h["evidence_brief"] = brief
                h["heuristic_explanation"] = heur
                h["explanation"] = heur
                h["learner_observations"] = heur.get("learner_observations") or heur.get("semantic_observations") or []
                h["llm_explanation"] = None
                h["llm_status"] = "not_generated"
            except Exception:
                continue
        # Provenance: keep hotspot evidence for debug drawer (raw windows)
        for h in hotspots:
            try:
                if "evidence" in h and "evidence_brief" in h and h["evidence"]:
                    continue
                brief = build_evidence_brief(h, chart, piece, caveats)
                heur = build_heuristic_from_brief(brief)
                h["evidence"] = brief
                h["evidence_brief"] = brief
                h["heuristic_explanation"] = heur
                h["explanation"] = heur
                h["llm_explanation"] = None
                h["llm_status"] = "not_generated"
            except Exception:
                continue
        # Attempt to attach pre-generated LLM explanations if sidecar exists (server-side generation path)
        try:
            sidecar = artifact_dir / "llm_explanations.json"
            if sidecar.is_file():
                llm_map = json.loads(sidecar.read_text(encoding="utf-8"))
                if isinstance(llm_map, dict):
                    for h in hard_bits:
                        hid = h.get("id") or h.get("section_id") or h.get("hard_bit_id") or h.get("hotspot_id")
                        entry = llm_map.get(hid) if hid else None
                        if not entry and isinstance(llm_map, dict) and "hotspots" in llm_map:
                            entry = llm_map.get("hotspots", {}).get(hid)
                        if isinstance(entry, dict) and entry.get("evidence_hash"):
                            cur_hash = (h.get("evidence") or {}).get("evidence_hash")
                            if cur_hash and entry.get("evidence_hash") == cur_hash:
                                if entry.get("summary"):
                                    h["llm_explanation"] = entry
                                    h["llm_status"] = "ready"
                                else:
                                    h["llm_status"] = "invalid_sidecar"
                            else:
                                h["llm_status"] = "hash_mismatch"
                                h["llm_explanation"] = None
                    for h in hotspots:
                        hid = h.get("id") or h.get("section_id") or h.get("hotspot_id")
                        entry = llm_map.get(hid) if hid else None
                        if not entry and isinstance(llm_map, dict) and "hotspots" in llm_map:
                            entry = llm_map.get("hotspots", {}).get(hid)
                        if isinstance(entry, dict) and entry.get("evidence_hash"):
                            cur_hash = (h.get("evidence") or {}).get("evidence_hash")
                            if cur_hash and entry.get("evidence_hash") == cur_hash:
                                if entry.get("summary"):
                                    h["llm_explanation"] = entry
                                    h["llm_status"] = "ready"
                                else:
                                    h["llm_status"] = "invalid_sidecar"
                            else:
                                h["llm_status"] = "hash_mismatch"
                                h["llm_explanation"] = None
        except Exception:
            pass
    elif build_hotspot_explanation is not None:
        for h in hard_bits:
            if "explanation" in h and h["explanation"]:
                continue
            try:
                exp = build_hotspot_explanation(h, chart, caveats, piece)
                h["explanation"] = exp
            except Exception:
                try:
                    exp = build_hotspot_explanation(h, chart, caveats)
                    h["explanation"] = exp
                except Exception:
                    continue
        for h in hotspots:
            if "explanation" in h and h["explanation"]:
                continue
            try:
                exp = build_hotspot_explanation(h, chart, caveats, piece)
                h["explanation"] = exp
            except Exception:
                try:
                    exp = build_hotspot_explanation(h, chart, caveats)
                    h["explanation"] = exp
                except Exception:
                    continue

    # Top-level provenance for three-layer system
    manifest["evidence_version"] = EVIDENCE_VERSION  # type: ignore
    manifest["heuristic_version"] = HEURISTIC_VERSION  # type: ignore
    manifest["explanation_layers"] = {
        "layer_1": "deterministic evidence brief",
        "layer_2": "deterministic heuristic explanation",
        "layer_3": "optional LLM polish (server-side, hash-tied)",
        "evidence_version": EVIDENCE_VERSION,  # type: ignore
        "heuristic_version": HEURISTIC_VERSION,  # type: ignore
        "display_priority": ["llm_explanation", "heuristic_explanation", "evidence"],
    }

    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build David demo artifacts for one piece (6 learner-facing graph dimensions + 9-aspect backend provenance)"
    )
    parser.add_argument("--piece-id", required=True, help="Catalog piece id, e.g. debussy_arabesque_1")
    parser.add_argument("--score", type=Path, required=True, help="Path to the MusicXML score")
    parser.add_argument("--title", type=str, default=None, help="Piece title for manifest (defaults to score title)")
    parser.add_argument("--composer", type=str, default=None, help="Composer for manifest (defaults to score composer)")
    parser.add_argument("--dataset", type=str, default=None, help="Dataset label, e.g. cipi or oktav")
    parser.add_argument("--dataset-id", type=str, default=None, help="Dataset-local id, e.g. x-336 or OK00027")
    parser.add_argument("--dataset-relative-path", type=str, default=None, help="Dataset-relative path for provenance")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output directory for generated artifacts")
    parser.add_argument(
        "--window-sizes",
        type=str,
        default="2,4",
        help="Comma-separated overview window sizes. First is primary; remaining sizes are companion resolutions.",
    )
    return parser.parse_args(argv)


def _parse_window_sizes(value: str) -> tuple[float, ...]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise ValueError("--window-sizes requires at least one size, e.g. 2,4")
    try:
        return tuple(float(part) for part in parts)
    except ValueError as exc:
        raise ValueError(f"Invalid --window-sizes value: {value!r}") from exc


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    score_path = Path(args.score).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    piece_id = str(args.piece_id)

    try:
        score_rel = score_path.resolve().relative_to(_REPO_ROOT.resolve())
    except ValueError:
        score_rel = Path(score_path.name)

    if not score_path.is_file():
        print(f"[error] Score file not found: {score_path}", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        window_sizes = _parse_window_sizes(args.window_sizes)
        overview_options = OverviewOptions(
            window_size=window_sizes[0],
            companion_window_sizes=tuple(window_sizes[1:]),
        )
    except ValueError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2

    result = analyze_score(
        score_path,
        profile_ids=("difficulty_aspects", "difficulty_overview"),
        overview_options=overview_options,
    )
    payload = result.to_json_payload()

    # Phase 3: ensure both 1m and 2m evidence when primary is not 1m
    extra_hotspots: list[dict] | None = None
    wants_1m = 1.0 not in window_sizes
    if wants_1m:
        try:
            # Build 1-measure graph hotspots as companion evidence
            ov_1m = OverviewOptions(window_size=1.0, companion_window_sizes=())
            # Re-use extraction where possible: call analyze_score for 1m but only difficulty_aspects needed
            result_1m = analyze_score(score_path, profile_ids=("difficulty_aspects",), overview_options=ov_1m)
            payload_1m = result_1m.to_json_payload()
            # Extract graph hotspots from 1m payload
            for prof in payload_1m.get("analysis_profiles", []) or []:
                if isinstance(prof, dict) and prof.get("profile_id") == "difficulty_aspects":
                    gt = prof.get("front_graph_taxonomy") or prof.get("graph_taxonomy") or {}
                    raw_1m = gt.get("graph_hotspots") or gt.get("hotspots") or gt.get("candidate_sections") or []
                    # Normalize to hotspot shape for grouping
                    normalized_1m: list[dict] = []
                    for sec in raw_1m:
                        region = sec.get("region", {}) if isinstance(sec, dict) else {}
                        rep = sec.get("representative_region", {}) if isinstance(sec, dict) else {}
                        if not isinstance(region, dict):
                            region = {}
                        if not isinstance(rep, dict):
                            rep = {}
                        measure_numbers = list(region.get("measure_numbers", []) or sec.get("measure_numbers", []) or [])
                        hid = sec.get("section_id") or sec.get("id") or sec.get("hotspot_id") or f"graph1m:both:{region.get('start_offset')}:{region.get('end_offset')}"
                        # Keep minimal fields needed for grouping; preserve contributors
                        dim_contribs_raw = sec.get("dimension_contributors") or sec.get("graph_dimension_contributors") or sec.get("top_contributors") or []
                        normalized_1m.append(
                            {
                                "id": hid,
                                "section_id": hid,
                                "hotspot_id": hid,
                                "rank": sec.get("rank"),
                                "measure_numbers": measure_numbers,
                                "measure_start": region.get("measure_start") if isinstance(region, dict) else sec.get("measure_start"),
                                "measure_end": region.get("measure_end") if isinstance(region, dict) else sec.get("measure_end"),
                                "measure_range": sec.get("measure_range") or (f"{measure_numbers[0]}-{measure_numbers[-1]}" if len(measure_numbers) >= 2 else (measure_numbers[0] if measure_numbers else "unknown")),
                                "label": region.get("label") or sec.get("label") or f"Measures {'-'.join(measure_numbers) if measure_numbers else 'unknown'}",
                                "start_offset": region.get("start_offset") or sec.get("start_offset"),
                                "end_offset": region.get("end_offset") or sec.get("end_offset"),
                                "score_position": region.get("position") if isinstance(region, dict) else sec.get("score_position"),
                                "score_value": sec.get("score_value") if sec.get("score_value") is not None else sec.get("score"),
                                "score": sec.get("score_value") if sec.get("score_value") is not None else sec.get("score"),
                                "method": sec.get("method") or "graph_composite_top_n.v1",
                                "resolution_key": "1_measures",
                                "supporting_window_indices": list(sec.get("supporting_window_indices", []) or ([sec.get("window_index")] if sec.get("window_index") is not None else [])),
                                "window_index": sec.get("window_index"),
                                "representative_region": rep if rep else region,
                                "region": region,
                                "dimension_contributors": dim_contribs_raw,
                                "graph_dimension_contributors": dim_contribs_raw,
                                "top_contributors": dim_contribs_raw,
                            }
                        )
                    extra_hotspots = normalized_1m
                    break
        except Exception as e:
            print(f"[warn] 1m companion hotspots unavailable for {piece_id}: {e}", file=sys.stderr)
            extra_hotspots = None

    write_analysis_outputs(payload, out_dir, stem="analysis")

    manifest = build_demo_manifest(
        payload=payload,
        score_path_rel=score_rel if score_rel != Path(".") else Path(score_path.name),
        artifact_dir=out_dir,
        piece_id=piece_id,
        title=args.title,
        composer=args.composer,
        dataset=args.dataset,
        dataset_id=args.dataset_id,
        dataset_relative_path=args.dataset_relative_path,
        extra_hotspots=extra_hotspots,
        score_path=score_path,
    )
    manifest_path = out_dir / "demo_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")

    print(f"[ok] Wrote analysis artifacts to: {out_dir}")
    for name in ("analysis.json", "analysis.md", "analysis.html", "analysis.csv", "demo_manifest.json"):
        print(f"  - {name}: {out_dir / name}")
    aspects_count = len((manifest.get("difficulty_aspects") or {}).get("aspects", []) or []) if isinstance(manifest.get("difficulty_aspects"), dict) else 0
    graph_count = len(manifest.get("chart", {}).get("graph_dimension_ids", []) or [])
    taxonomy_version = manifest.get("chart", {}).get("taxonomy_version") or manifest.get("chart", {}).get("graph_taxonomy_version") or ""
    hard_bits_ct = len(manifest.get("hard_bits", []) or [])
    print(f"[ok] piece_id={piece_id} factors={len(manifest['factors'])} hotspots={len(manifest['hotspots'])} hard_bits={hard_bits_ct} regions={len(manifest['chart']['regions'])} graph_dimensions={graph_count} ({taxonomy_version}) aspects={aspects_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
