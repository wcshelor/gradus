"""Public overview assembled from promoted Difficulty Dynamics components."""

from dataclasses import dataclass, replace
from fractions import Fraction
from math import isfinite
from pathlib import Path

from piano_difficulty.features.registry import DEFAULT_FACTOR_IDS, REGISTRY_VERSION, resolve_factors
from piano_difficulty.features import extract_all
from piano_difficulty.temporal.selection import select_region
from .dynamics.core import build_difficulty_profile, _resolve_feature_record
from .dynamics.models import (
    CompositeConfig, DifficultyDynamicsConfig, NormalizationConfig,
    PeakDetectionConfig, WindowStrategyConfig,
)
from .sections import consolidate_sections


def _resolution_key(window: str, size: float) -> str:
    size_str = f"{float(size):g}"
    if window == "measure":
        return f"{size_str}_measures"
    return f"{size_str}_beats"


@dataclass(frozen=True)
class OverviewOptions:
    window: str = "measure"
    window_size: float = 2
    stride: float = 1
    hand: str = "both"
    top_sections: int = 5
    feature_ids: tuple[str, ...] = DEFAULT_FACTOR_IDS
    companion_window_sizes: tuple[float, ...] = (4,)

    def __post_init__(self):
        if self.window not in {"measure", "beat"} or self.hand not in {"both", "left", "right"}:
            raise ValueError("Unsupported window or hand selection.")
        if any(not isfinite(v) or v <= 0 for v in (self.window_size, self.stride)):
            raise ValueError("Window size and stride must be finite and positive.")
        if self.window == "measure" and any(int(v) != v for v in (self.window_size, self.stride)):
            raise ValueError("Measure windows require integer sizes and strides.")
        if not isinstance(self.top_sections, int) or self.top_sections < 1:
            raise ValueError("top_sections must be a positive integer.")
        if not self.feature_ids or len(set(self.feature_ids)) != len(self.feature_ids):
            raise ValueError("Select at least one factor, without duplicates.")
        resolve_factors(self.feature_ids)
        # Validate companion window sizes; keep tuple form
        if not isinstance(self.companion_window_sizes, tuple):
            raise ValueError("companion_window_sizes must be a tuple.")
        if len(set(self.companion_window_sizes)) != len(self.companion_window_sizes):
            raise ValueError("companion_window_sizes must not contain duplicates.")
        for v in self.companion_window_sizes:
            if not isinstance(v, (int, float)) or not isfinite(float(v)) or float(v) <= 0:
                raise ValueError("Companion window sizes must be finite and positive.")
            if self.window == "measure" and int(float(v)) != float(v):
                raise ValueError("Measure windows require integer sizes and strides.")
            if float(v) == float(self.window_size):
                raise ValueError("companion_window_sizes must not duplicate window_size.")

    @property
    def window_sizes(self) -> tuple[float, ...]:
        """All window sizes with primary first."""
        return (float(self.window_size),) + tuple(float(v) for v in self.companion_window_sizes)


@dataclass
class DifficultyAnalysisResult:
    payload: dict

    def to_payload(self):
        return self.payload


class DifficultyOverviewProfile:
    profile_id = "difficulty_overview"
    profile_version = "1"

    def analyze(self, extraction, options=None):
        options = options or OverviewOptions()
        hands = (options.hand,) if options.hand != "both" else ("both", "right", "left")
        views = {}
        for hand in hands:
            if hand != "both" and not any(f.scope != "coordination" for f in resolve_factors(options.feature_ids)):
                continue
            if hand != "both" and not any(n.hand == hand for n in extraction.score.logical_notes):
                continue
            views[hand] = _build_view(extraction, replace(options, hand=hand))
        # Preserve a meaningful empty result when the requested hand is absent.
        if options.hand not in views:
            views[options.hand] = _build_view(extraction, options)
        main = views[options.hand]
        return DifficultyAnalysisResult({
            "schema_version": "difficulty_overview.v1",
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "factor_registry_version": REGISTRY_VERSION,
            "interpretation": "Relative score demands within this piece; no calibrated difficulty grade.",
            "factor_ranking_method": "mean within-piece normalized value across analysis windows",
            "hand_mode": options.hand,
            **main,
            "hand_views": {hand: view for hand, view in views.items() if hand != options.hand},
            "diagnostics": [
                "Factor ranks describe contributions to this chosen profile, not measured learner difficulty.",
                "Constant factors have no local peak; raw values remain visible.",
                "Attack selection omits sustains entering a window; original written durations are retained.",
                "Evidence IDs identify region inputs, not a causal or event-level difficulty attribution.",
                "Hand labels use the parser's conservative staff-based inference.",
                "Transitions crossing a window start are omitted; overlapping windows reduce this boundary effect.",
                *main["warnings"],
            ],
        })


def _build_single_resolution_view(extraction, options, window_size: float):
    """Build the overview view for a single window size without companion merging."""
    factors = [f for f in resolve_factors(options.feature_ids)
               if options.hand == "both" or f.scope != "coordination"]
    if not factors:
        raise ValueError("No selected factors support the requested hand.")
    composite = CompositeConfig(weights={f.feature_id: f.weight for f in factors})
    config = DifficultyDynamicsConfig(
        experiment_name="difficulty_overview",
        score_path=extraction.score.source_path or Path("score.musicxml"),
        feature_ids=tuple(f.feature_id for f in factors),
        hand_mode=options.hand,
        window=WindowStrategyConfig(
            kind=options.window, size=int(window_size) if options.window == "measure" else int(window_size) if float(window_size).is_integer() else 1,
            step=int(options.stride) if options.window == "measure" else int(options.stride) if float(options.stride).is_integer() else 1,
            beat_size=window_size, beat_step=options.stride),
        normalization=NormalizationConfig(method="min_max"),
        composite=composite, peaks=PeakDetectionConfig(top_n=options.top_sections),
        overview_mode=True,
    )
    # For measure windows, ensure size/step are integers; for beat windows pass-through via beat fields
    if options.window == "measure":
        config = replace(config, window=replace(config.window, size=int(window_size), step=int(options.stride), beat_size=window_size, beat_step=options.stride))
    else:
        config = replace(config, window=replace(config.window, beat_size=window_size, beat_step=options.stride))
    profile = build_difficulty_profile(extraction.score, config)
    profile = replace(profile, passages=tuple(p for p in profile.passages if p.value > 0))
    piece_records = extraction.features
    if options.hand != "both" and profile.regions:
        whole_region = replace(
            profile.regions[0], end_offset=max(m.end for m in extraction.score.measures))
        piece_records = extract_all(select_region(extraction.score, whole_region))
    summaries = []
    for factor in factors:
        series = profile.series[factor.feature_id]
        valid = [v for v in series.normalized_values if v is not None]
        raw = [v for v in series.raw_values if v is not None]
        piece_value = _resolve_feature_record(
            piece_records, factor.feature_id, options.hand, hand_aggregation="max")[0]
        if not raw:
            piece_value = None
        summaries.append({
            **factor.to_payload(), "units": series.units or factor.units,
            "piece_value": piece_value,
            "local_min": min(raw) if raw else None, "local_max": max(raw) if raw else None,
            "profile_contribution": sum(valid) / len(valid) * factor.weight if valid else None,
            "availability": "available" if raw else "unavailable",
            "peak_ids": [p.passage_id for p in profile.passages if p.contributing_feature_id == factor.feature_id],
        })
    summaries.sort(key=lambda f: (-(f["profile_contribution"] or 0), f["feature_id"]))
    for rank, summary in enumerate(summaries, start=1):
        summary["rank"] = rank
    evidence = []
    for region in profile.regions:
        selection = select_region(extraction.score, region)
        evidence.append({
            "window_index": region.window_index,
            "written_note_ids": [n.note_id for n in selection.written_notes],
            "logical_note_ids": [n.note_id for n in selection.logical_notes],
            "source_note_ids": sorted({i for n in selection.logical_notes for i in n.source_note_ids}),
            "scope": "region_input_events",
        })
    temporal = profile.to_payload()
    warnings = list(profile.warnings)
    if not extraction.score.logical_notes:
        warnings.append("No logical note attacks were found in this score.")
    if any(n.hand is None for n in extraction.score.logical_notes):
        warnings.append("Some attacks have no inferred hand and are omitted from hand-specific profiles.")
    try:
        candidate_sections = consolidate_sections(profile, composite, extraction.score, limit=options.top_sections)
    except TypeError:
        candidate_sections = consolidate_sections(profile, composite, limit=options.top_sections)
    return {
        "factors": summaries, "regions": temporal["regions"], "series": temporal["series"],
        "composite": temporal["overall_series"],
        "factor_peaks": [p for p in temporal["passages"] if p["contributing_feature_id"] in profile.series],
        "composite_peaks": [p for p in temporal["passages"] if p["contributing_feature_id"] not in profile.series],
        "candidate_sections": candidate_sections,
        "region_evidence": evidence, "warnings": warnings,
        "methods": profile.metadata,
        "_profile": profile,
        "_composite": composite,
    }


def _resolution_entry(view: dict, window_size: float, window: str) -> dict:
    return {
        "window_size": float(window_size),
        "window": window,
        "resolution_key": _resolution_key(window, window_size),
        "regions": view["regions"],
        "series": view["series"],
        "composite": view["composite"],
        "candidate_sections": view["candidate_sections"],
        "factor_peaks": view["factor_peaks"],
        "composite_peaks": view["composite_peaks"],
        "region_evidence": view["region_evidence"],
        "methods": view["methods"],
        "factors": view["factors"],
        "warnings": view["warnings"],
    }


def _parse_offset(value) -> Fraction | None:
    if value is None:
        return None
    try:
        return Fraction(str(value))
    except Exception:
        return None


def _merge_sections_across_resolutions(primary_view: dict, companion_views: dict[float, dict], options) -> list[dict]:
    primary_key = _resolution_key(options.window, options.window_size)
    per_resolution: dict[str, list[dict]] = {}
    per_resolution[primary_key] = list(primary_view.get("candidate_sections") or [])
    for size, view in companion_views.items():
        key = _resolution_key(options.window, size)
        per_resolution[key] = list(view.get("candidate_sections") or [])

    # Collect all sections with resolution annotation
    annotated: list[tuple[dict, str]] = []
    for res_key, sections in per_resolution.items():
        for sec in sections:
            annotated.append((sec, res_key))

    if not annotated:
        return []

    def _sort_key(item):
        sec, _ = item
        reg = sec.get("region") or {}
        ms = reg.get("measure_start")
        me = reg.get("measure_end")
        off = _parse_offset(reg.get("start_offset"))
        return (ms if isinstance(ms, int) else 0, me if isinstance(me, int) else 0, float(off) if off is not None else 0, sec.get("section_id", ""))

    annotated.sort(key=_sort_key)

    groups: list[list[tuple[dict, str]]] = []
    for sec, res_key in annotated:
        reg = sec.get("region") or {}
        ms = reg.get("measure_start")
        if ms is None:
            ms = 0
        if not groups:
            groups.append([(sec, res_key)])
            continue
        last = groups[-1]
        max_end = max((s.get("region", {}).get("measure_end", ms) for s, _ in last), default=ms)
        # also consider offset overlap
        if isinstance(ms, int) and isinstance(max_end, int) and ms <= max_end + 1:
            last.append((sec, res_key))
            continue
        # fallback offset check for beat windows
        s_off = _parse_offset(reg.get("start_offset"))
        try:
            group_max_off = max((_parse_offset(s.get("region", {}).get("end_offset")) for s, _ in last if _parse_offset(s.get("region", {}).get("end_offset")) is not None), default=None)
            if s_off is not None and group_max_off is not None and s_off <= group_max_off:
                last.append((sec, res_key))
                continue
        except Exception:
            pass
        groups.append([(sec, res_key)])

    combined: list[dict] = []
    for group in groups:
        secs = [s for s, _ in group]
        res_keys = sorted({rk for _, rk in group})
        # merged measure range
        measure_starts = [s.get("region", {}).get("measure_start") for s in secs if isinstance(s.get("region", {}).get("measure_start"), int)]
        measure_ends = [s.get("region", {}).get("measure_end") for s in secs if isinstance(s.get("region", {}).get("measure_end"), int)]
        min_start = min(measure_starts) if measure_starts else 0
        max_end = max(measure_ends) if measure_ends else min_start
        # measure_numbers union
        all_numbers: list[str] = []
        for s in secs:
            nums = s.get("region", {}).get("measure_numbers") or []
            all_numbers.extend([str(n) for n in nums])
            # also include measure_numbers at top-level
            if not nums:
                nums2 = s.get("measure_numbers") or []
                all_numbers.extend([str(n) for n in nums2])
        # deduplicate preserve order sorted by int if possible
        uniq: dict[str, None] = {}
        for n in all_numbers:
            uniq[n] = None
        # try numeric sort
        try:
            sorted_numbers = sorted(uniq.keys(), key=lambda x: int(x))
        except ValueError:
            sorted_numbers = sorted(uniq.keys())
        # If still mismatched with measure range, fallback to generating range from min_start to max_end+1 numbers
        if not sorted_numbers:
            sorted_numbers = [str(i) for i in range(min_start + 1, max_end + 2)] if measure_starts else []

        # offsets
        start_offsets = [_parse_offset(s.get("region", {}).get("start_offset")) for s in secs]
        end_offsets = [_parse_offset(s.get("region", {}).get("end_offset")) for s in secs]
        start_offsets = [o for o in start_offsets if o is not None]
        end_offsets = [o for o in end_offsets if o is not None]
        min_off = min(start_offsets) if start_offsets else None
        max_off = max(end_offsets) if end_offsets else None

        # start_beat/end_beat similarly
        start_beats = [_parse_offset(s.get("region", {}).get("start_beat")) for s in secs]
        end_beats = [_parse_offset(s.get("region", {}).get("end_beat")) for s in secs]
        start_beats = [o for o in start_beats if o is not None]
        end_beats = [o for o in end_beats if o is not None]
        min_beat = min(start_beats) if start_beats else min_off
        max_beat = max(end_beats) if end_beats else max_off

        position = None
        if min_off is not None and max_off is not None:
            try:
                position = float((min_off + max_off) / 2)
            except Exception:
                position = None

        # build merged region payload (synthesize)
        first_reg = secs[0].get("region", {}) if secs else {}
        score_id = first_reg.get("score_id")
        hand = first_reg.get("hand")
        label = f"Measures {sorted_numbers[0]}–{sorted_numbers[-1]}" if len(sorted_numbers) > 1 else f"Measures {sorted_numbers[0]}" if sorted_numbers else first_reg.get("label")
        merged_region = {
            "score_id": score_id,
            "window_index": min((s.get("region", {}).get("window_index", 0) for s in secs if isinstance(s.get("region", {}).get("window_index"), int)), default=0),
            "measure_start": min_start,
            "measure_end": max_end,
            "measure_numbers": sorted_numbers,
            "start_offset": str(min_off) if min_off is not None else first_reg.get("start_offset"),
            "end_offset": str(max_off) if max_off is not None else first_reg.get("end_offset"),
            "start_beat": str(min_beat) if min_beat is not None else first_reg.get("start_beat"),
            "end_beat": str(max_beat) if max_beat is not None else first_reg.get("end_beat"),
            "position": position if position is not None else first_reg.get("position"),
            "hand": hand,
            "label": label,
        }

        # score max
        scores = [float(s.get("score", 0) or 0) for s in secs]
        max_score = max(scores) if scores else 0.0

        # union factor ids
        union_factors: set[str] = set()
        for s in secs:
            for fid in s.get("supporting_factor_ids") or []:
                union_factors.add(fid)

        # per-resolution details
        per_res_detail: dict[str, dict] = {}
        for rk in res_keys:
            related = [s for s, k in group if k == rk]
            per_res_detail[rk] = {
                "section_ids": [s.get("section_id") for s in related],
                "window_indices": sorted({s.get("window_index") if s.get("window_index") is not None else s.get("region", {}).get("window_index") for s in related if (s.get("window_index") is not None or s.get("region", {}).get("window_index") is not None)}),
                "scores": [float(s.get("score", 0) or 0) for s in related],
                "supporting_window_indices": sorted({idx for s in related for idx in (s.get("supporting_window_indices") or [])}),
                "supporting_factor_ids": sorted({fid for s in related for fid in (s.get("supporting_factor_ids") or [])}),
            }
            # also expose region measure ranges per resolution (list for JSON round-trip)
            per_res_detail[rk]["measure_ranges"] = [[s.get("region", {}).get("measure_start"), s.get("region", {}).get("measure_end")] for s in related]

        # primary representative
        primary_sections = [s for s, k in group if k == primary_key]
        primary_rep = None
        primary_section_id = None
        representative_region = None
        if primary_sections:
            # choose max score among primary
            best = max(primary_sections, key=lambda s: float(s.get("score", 0) or 0))
            primary_rep = best
            primary_section_id = best.get("section_id")
            representative_region = best.get("representative_region") or best.get("region")

        if representative_region is None and secs:
            # fallback to first's representative
            representative_region = secs[0].get("representative_region") or secs[0].get("region")

        # supporting window indices per resolution union
        # build combined id
        combined_id = f"combined:{':'.join(sorted(res_keys))}:{min_start}:{max_end}"

        combined.append({
            "combined_section_id": combined_id,
            "section_id": combined_id,
            "region": merged_region,
            "measure_numbers": sorted_numbers,
            "measure_range": f"{sorted_numbers[0]}-{sorted_numbers[-1]}" if len(sorted_numbers) > 1 else (sorted_numbers[0] if sorted_numbers else ""),
            "measure_start": min_start,
            "measure_end": max_end,
            "score": max_score,
            "score_method": "max",
            "method": "merged_overlapping_or_touching.v1",
            "supporting_resolutions": res_keys,
            "per_resolution": per_res_detail,
            "supporting_factor_ids": sorted(union_factors),
            "supporting_window_indices_by_resolution": {rk: per_res_detail[rk]["supporting_window_indices"] for rk in res_keys},
            "supporting_section_ids_by_resolution": {rk: per_res_detail[rk]["section_ids"] for rk in res_keys},
            "primary_section_id": primary_section_id,
            "primary_representative_section": primary_rep,
            "representative_region": representative_region,
            "section_count": len(secs),
            "supporting_section_ids": [s.get("section_id") for s in secs],
        })

    combined.sort(key=lambda s: (-float(s.get("score", 0) or 0), -len(s.get("supporting_factor_ids") or []), s.get("region", {}).get("measure_start", 0)))
    for rank, sec in enumerate(combined, start=1):
        sec["rank"] = rank
    # Limit to top_sections? Use primary limit for now, but keep all if fewer than limit*2?
    # To preserve both spikes and phrases, keep up to limit with expansion: allow up to top_sections merged groups, but if more groups than limit, trim
    limit = primary_view.get("methods", {}).get("peaks", {}).get("top_n") or options.top_sections
    if len(combined) > limit:
        combined = combined[:limit]
        for idx, sec in enumerate(combined, start=1):
            sec["rank"] = idx
    return combined


def _build_view(extraction, options):
    primary_view = _build_single_resolution_view(extraction, options, float(options.window_size))
    # companion views
    companion_sizes_raw = tuple(getattr(options, "companion_window_sizes", ()) or ())
    # dedupe and exclude primary already validated but be safe
    seen: set[float] = set()
    companion_views: dict[float, dict] = {}
    for sz in companion_sizes_raw:
        fsz = float(sz)
        if fsz in seen:
            continue
        seen.add(fsz)
        if fsz == float(options.window_size):
            continue
        # validate measure integer
        if options.window == "measure" and int(fsz) != fsz:
            continue
        companion_views[fsz] = _build_single_resolution_view(extraction, options, fsz)

    # Build resolution_views
    resolution_views: dict[str, dict] = {}
    primary_key = _resolution_key(options.window, float(options.window_size))
    resolution_views[primary_key] = _resolution_entry(primary_view, float(options.window_size), options.window)
    for fsz, view in companion_views.items():
        key = _resolution_key(options.window, fsz)
        resolution_views[key] = _resolution_entry(view, fsz, options.window)

    # Combined sections
    combined = _merge_sections_across_resolutions(primary_view, companion_views, options)

    # Methods window_resolutions
    window_resolutions = {
        "window": options.window,
        "stride": float(options.stride),
        "primary_size": float(options.window_size),
        "companion_sizes": [float(s) for s in companion_sizes_raw],
        "sizes": [float(options.window_size), *[float(s) for s in companion_sizes_raw]],
        "primary_resolution_key": primary_key,
        "resolution_keys": sorted(resolution_views.keys()),
        "final_window_behavior": primary_view["methods"].get("window", {}).get("final_window_behavior", "include"),
    }

    # Enrich primary view methods
    enriched_methods = dict(primary_view["methods"])
    enriched_methods["window_resolutions"] = window_resolutions

    # Strip internal helpers
    primary_view.pop("_profile", None)
    primary_view.pop("_composite", None)
    for v in companion_views.values():
        v.pop("_profile", None)
        v.pop("_composite", None)

    # Return primary fields plus new multi-resolution fields
    result = {
        **primary_view,
        "methods": enriched_methods,
        "resolution_views": resolution_views,
        "combined_candidate_sections": combined,
    }
    return result
