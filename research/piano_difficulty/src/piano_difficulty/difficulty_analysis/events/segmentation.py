"""Metric-driven segmentation inside a flagged passage.

Primary input is already-extracted TemporalFeatureSeries (normalized values).
No note access.  Detects feature-change boundaries that suggest distinct
playable challenges: leap spikes, register expansion, sustained texture,
density shifts, coordination changes, repeated contour plateaus.

The note layer (note_inspection.py) answers "what musical thing caused it".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from piano_difficulty.difficulty_analysis.dynamics.models import DifficultyProfile
from piano_difficulty.temporal.windows import ScoreRegion


@dataclass(frozen=True, slots=True)
class SegmentCandidate:
    """One metric-coherent sub-span inside the flagged region."""

    window_indices: tuple[int, ...]
    span: ScoreRegion
    boundary_reason: str
    supporting_feature_ids: tuple[str, ...]
    confidence: float
    diagnostics: tuple[str, ...] = ()
    # lightweight evidence per feature
    evidence: tuple[dict[str, Any], ...] = ()


# Tunable thresholds — deliberately conservative for v1.
DELTA_SPIKE = 0.35  # normalized delta that warrants a boundary
SUSTAIN_THRESHOLD = 0.55  # normalized value considered "sustained high"
PLATEAU_TOLERANCE = 0.12  # max variation inside repeated-pattern plateau
DENSITY_DELTA = 0.30
COORDINATION_DELTA = 0.25


def _value_at(series: Any, idx: int) -> float | None:
    try:
        return series.normalized_values[idx]  # type: ignore[index]
    except Exception:
        return None


def _norm_delta(series: Any, a: int, b: int) -> float | None:
    va = _value_at(series, a)
    vb = _value_at(series, b)
    if va is None or vb is None:
        return None
    return vb - va


def _is_sustained_high(series: Any, indices: list[int]) -> bool:
    vals = [_value_at(series, i) for i in indices]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return False
    return all(v >= SUSTAIN_THRESHOLD for v in vals)


def _is_plateau(series: Any, indices: list[int]) -> bool:
    vals = [_value_at(series, i) for i in indices]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return False
    return (max(vals) - min(vals)) <= PLATEAU_TOLERANCE and all(v >= 0.4 for v in vals)


def _build_span(regions: list[ScoreRegion], indices: list[int]) -> ScoreRegion | None:
    if not indices:
        return None
    # regions is ordered by window_index
    by_idx = {r.window_index: r for r in regions}
    # Use min/max window_index to find boundaries
    ordered = sorted(indices)
    first = by_idx.get(ordered[0])
    last = by_idx.get(ordered[-1])
    if first is None or last is None:
        return None
    # Merge by taking first.start_offset .. last.end_offset
    from dataclasses import replace

    # Collect measure numbers across span
    numbers: dict[int, str] = {}
    for idx in ordered:
        r = by_idx.get(idx)
        if r is None:
            continue
        for mi, num in zip(range(r.measure_start, r.measure_end + 1), r.measure_numbers):
            numbers[mi] = num
    sorted_mi = sorted(numbers)
    if not sorted_mi:
        return first
    merged = replace(
        first,
        end_offset=last.end_offset,
        end_beat=last.end_beat,
        measure_end=last.measure_end,
        measure_numbers=tuple(numbers[i] for i in sorted_mi),
        position=float((first.start_offset + last.end_offset) / 2) if first.start_offset is not None and last.end_offset is not None else first.position,
        label=f"Measures {numbers[sorted_mi[0]]}-{numbers[sorted_mi[-1]]}" if len(sorted_mi) > 1 else f"Measure {numbers[sorted_mi[0]]}",
    )
    return merged


def segment_by_metrics(
    profile: DifficultyProfile,
    flagged_region: ScoreRegion,
    *,
    min_segment_windows: int = 1,
) -> list[SegmentCandidate]:
    """Return metric-coherent sub-spans inside flagged_region.

    Strategy (hybrid, metric-first):
    - Determine which window_indices belong to flagged_region by offset overlap.
    - Compute per-feature deltas between consecutive flagged windows.
    - Insert boundaries where a subset of features spikes or drops significantly
      while others stay flat/sustained.  Repeated contour (plateau) keeps windows together.
    - If no clear boundaries, return single segment marked uncertain.

    The caller (labeling) may later confirm with note inspection.
    """
    regions = list(profile.regions)
    if not regions or flagged_region.start_offset is None or flagged_region.end_offset is None:
        return []

    # Flagged windows: those overlapping [start, end)
    flagged_indices: list[int] = []
    for r in regions:
        if r.start_offset is None or r.end_offset is None:
            continue
        if r.end_offset <= flagged_region.start_offset or r.start_offset >= flagged_region.end_offset:
            continue
        flagged_indices.append(r.window_index)
    flagged_indices.sort()
    if not flagged_indices:
        # fallback: match by measure range
        for r in regions:
            if flagged_region.measure_start <= r.measure_start <= flagged_region.measure_end or flagged_region.measure_start <= r.measure_end <= flagged_region.measure_end:
                if r.window_index not in flagged_indices:
                    flagged_indices.append(r.window_index)
        flagged_indices.sort()
    if not flagged_indices:
        return []
    if len(flagged_indices) == 1:
        span = _build_span(regions, flagged_indices)
        if span is None:
            return []
        return [
            SegmentCandidate(
                window_indices=tuple(flagged_indices),
                span=span,
                boundary_reason="single_window_flagged",
                supporting_feature_ids=(),
                confidence=0.45,
                diagnostics=("single flagged window — no internal boundary",),
            )
        ]

    # Collect feature ids that have at least one non-None in flagged range
    candidate_fids: list[str] = []
    for fid, series in profile.series.items():
        vals = [_value_at(series, i) for i in flagged_indices]
        if any(v is not None for v in vals):
            candidate_fids.append(fid)
    # also consider composite if present
    if profile.overall_series is not None:
        # not required for segmentation but helpful for diagnostics
        pass

    # Compute boundary scores between consecutive flagged windows
    # boundary_score[k] = index after flagged_indices[k] (i.e., between k and k+1)
    boundary_scores: list[tuple[int, float, list[str]]] = []  # (pos, score, fids)
    for k in range(len(flagged_indices) - 1):
        a = flagged_indices[k]
        b = flagged_indices[k + 1]
        score = 0.0
        supporting: list[str] = []
        for fid in candidate_fids:
            series = profile.series.get(fid)
            if series is None:
                continue
            delta = _norm_delta(series, a, b)
            if delta is None:
                continue
            ad = abs(delta)
            # Weight leap/register/span deltas higher
            weight = 1.0
            if fid.startswith("leaps.") or fid.startswith("pitch_geometry.") or fid == "metadata.pitch_range":
                weight = 1.4
            elif fid.startswith("texture.") or fid.startswith("coordination."):
                weight = 1.1
            # Spike threshold
            thresh = DELTA_SPIKE
            if fid.startswith("rhythm.") and "density" in fid:
                thresh = DENSITY_DELTA
            if fid.startswith("coordination."):
                thresh = COORDINATION_DELTA
            if ad >= thresh:
                score += ad * weight
                supporting.append(fid)
            elif ad >= thresh * 0.6:
                score += ad * weight * 0.5
                # not added to supporting unless strong
        # Bonus if at least two independent aspects spike together
        distinct_aspects = {fid.split(".")[0] for fid in supporting}
        if len(distinct_aspects) >= 2 and score > 0:
            score *= 1.15
        boundary_scores.append((k, score, supporting))

    # Decide which boundaries to keep: score above median+std or absolute threshold
    # Use simple absolute threshold for v1: score >= 0.4
    kept_boundaries: list[int] = []
    for k, score, supporting in boundary_scores:
        if score >= 0.40 and len(supporting) >= 1:
            # Suppress boundary if both sides are plateau of same repeated pattern
            # Check if plateau spans across boundary — then don't split
            plateau_fids = []
            for fid in supporting:
                series = profile.series.get(fid)
                if series is None:
                    continue
                # look at 2 windows around boundary
                left_idx = flagged_indices[k]
                right_idx = flagged_indices[k + 1]
                # if both windows are part of a larger plateau, don't split on this feature alone
                # Use 3-window window for plateau detection
                window_for_plateau = flagged_indices[max(0, k - 1) : k + 3]
                if _is_plateau(series, window_for_plateau):
                    plateau_fids.append(fid)
            # if all supporting fids are plateau -> suppress
            if plateau_fids and len(plateau_fids) == len(supporting):
                continue
            kept_boundaries.append(k)

    # Build segments from kept boundaries
    if not kept_boundaries:
        # No clear internal structure — check for sustained vs spike distinction
        # If last window has strong leap/register spike vs earlier sustained texture/density,
        # still split arrival
        # Look at last boundary specifically with lower threshold
        if boundary_scores:
            last_k, last_score, last_supp = boundary_scores[-1]
            leap_or_span = [f for f in last_supp if f.startswith("leaps.") or f.startswith("pitch_geometry.") or f == "metadata.pitch_range"]
            if leap_or_span and last_score >= 0.25:
                kept_boundaries = [last_k]
            else:
                # Check sustained texture early vs leap late
                early = flagged_indices[:-1]
                late = flagged_indices[-1:]
                sustained_texture = any(
                    _is_sustained_high(profile.series[fid], early)
                    for fid in candidate_fids
                    if fid.startswith("texture.") or fid == "rhythm.attack_density"
                )
                late_leap = any(
                    (_value_at(profile.series[fid], late[0]) or 0) >= 0.75
                    for fid in candidate_fids
                    if fid.startswith("leaps.") or fid.startswith("pitch_geometry.")
                )
                if sustained_texture and late_leap:
                    kept_boundaries = [len(flagged_indices) - 2]
        if not kept_boundaries:
            span = _build_span(regions, flagged_indices)
            if span is None:
                return []
            # Single uncertain segment
            return [
                SegmentCandidate(
                    window_indices=tuple(flagged_indices),
                    span=span,
                    boundary_reason="no_clear_metric_boundary",
                    supporting_feature_ids=tuple(candidate_fids[:4]),
                    confidence=0.38,
                    diagnostics=("no feature delta exceeded threshold inside flagged span — single blended event, manual review suggested",),
                )
            ]

    # Split indices by kept boundaries
    segments: list[SegmentCandidate] = []
    start = 0
    for b in kept_boundaries:
        seg_indices = flagged_indices[start : b + 1]
        span = _build_span(regions, seg_indices)
        if span is not None and len(seg_indices) >= min_segment_windows:
            # supporting ids = those that spiked at or inside segment
            supp = set()
            for k in range(start, b + 1):
                if k < len(boundary_scores):
                    _, _, fids = boundary_scores[k]
                    supp.update(fids)
            # also add sustained features
            for fid in candidate_fids:
                series = profile.series.get(fid)
                if series is not None and _is_sustained_high(series, seg_indices):
                    supp.add(fid)
            segments.append(
                SegmentCandidate(
                    window_indices=tuple(seg_indices),
                    span=span,
                    boundary_reason="metric_delta_boundary" if b in kept_boundaries else "sustained_plateau",
                    supporting_feature_ids=tuple(sorted(supp)[:6]),
                    confidence=min(0.85, 0.55 + len(supp) * 0.07),
                    diagnostics=(f"boundary after window {flagged_indices[b]}",),
                )
            )
        start = b + 1
    # tail segment
    tail = flagged_indices[start:]
    if tail:
        span = _build_span(regions, tail)
        if span is not None:
            supp = set()
            for fid in candidate_fids:
                series = profile.series.get(fid)
                if series is not None:
                    vals = [_value_at(series, i) for i in tail]
                    if any(v is not None and v >= 0.5 for v in vals):
                        supp.add(fid)
            segments.append(
                SegmentCandidate(
                    window_indices=tuple(tail),
                    span=span,
                    boundary_reason="metric_delta_boundary" if kept_boundaries else "tail",
                    supporting_feature_ids=tuple(sorted(supp)[:6]),
                    confidence=min(0.85, 0.55 + len(supp) * 0.07),
                    diagnostics=(f"tail segment windows {tail}",),
                )
            )
    return segments
