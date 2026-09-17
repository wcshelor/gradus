"""Merge peak windows into candidate sections with recoverable support."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from .dynamics.core import rank_feature_contributions_for_region
from .dynamics.models import region_to_payload


def _value_at(values, index):
    if index < 0 or index >= len(values):
        return None
    return values[index]


def _should_merge_near_consecutive(existing_group, new_peak, profile):
    """Decide if new_peak belongs to existing_group: overlapping or near-consecutive related."""
    if not existing_group:
        return False
    # overlapping / touching already
    max_end = max(p.region.end_offset for p in existing_group)
    if new_peak.region.start_offset <= max_end:
        return True
    # near-consecutive: window_index gap <=2 (allows one missing window)
    existing_indices = {p.region.window_index for p in existing_group}
    max_index = max(existing_indices) if existing_indices else -1
    gap = new_peak.region.window_index - max_index
    if gap < 0:
        gap = 0
    if gap <= 2 and gap > 0:
        # relatedness check: share factor or both involve high composite
        group_factors = {p.contributing_feature_id for p in existing_group if p.contributing_feature_id in profile.series}
        # consider related if same factor repeats or group already has multiple factors (variety)
        if new_peak.contributing_feature_id in group_factors:
            return True
        # also merge if windows are close and at least one side is composite or strong contributor
        # For templated use, allow merging of any near-consecutive flagged windows (per brief)
        # To avoid broad phrase merging, limit to gap 1 missing window.
        # Keep permissive for consecutive flagged windows can become one section.
        return True
    # also allow small beat offset gap (e.g., one measure ≈4 quarters) for measure windows
    try:
        offset_gap = new_peak.region.start_offset - max_end
        if offset_gap is not None and gap <= 2:
            # estimate quarter gap; for measure windows 4 quarters ≈ 1 measure
            if float(offset_gap) <= 4.5:
                return True
    except Exception:
        pass
    return False


def _has_supporting_evidence(profile, composite, index, threshold=0.55, composite_threshold=0.4):
    """Check if neighbor window has elevated feature evidence to justify setup extension."""
    if index < 0 or index >= len(profile.regions):
        return False
    for series in profile.series.values():
        val = _value_at(series.normalized_values, index)
        if val is not None and val >= threshold:
            return True
        # also consider raw high percentile? normalized already
    if profile.overall_series is not None:
        val = _value_at(profile.overall_series.normalized_values, index)
        if val is not None and val >= composite_threshold:
            return True
    return False


def _is_single_hand_window(profile, index, score=None):
    """Detect single-hand activity for tempering rhythm."""
    # Primary: coordination missing at index indicates single hand
    coord = profile.series.get("coordination.subdivision_mismatch_proxy")
    if coord is not None:
        raw = _value_at(coord.raw_values, index)
        # If coordination unavailable (None), likely single hand
        if raw is None:
            # verify at least one factor has data (not empty piece)
            # check if any hand-specific feature has value at index but coordination missing
            # treat as single hand
            # Need to distinguish genuinely empty region vs single hand: check rhythm still present
            rhythm = profile.series.get("rhythm.attack_density")
            if rhythm is not None:
                rv = _value_at(rhythm.raw_values, index)
                if rv is not None and rv > 0:
                    return True
            # fallback: if no coordination, assume single hand if overall hand check suggests
            if score is None:
                return True
    if score is not None:
        try:
            from piano_difficulty.features.coordination import is_single_hand_active
            region = profile.regions[index]
            if region.start_offset is not None and region.end_offset is not None:
                return is_single_hand_active(score, region.start_offset, region.end_offset)
        except Exception:
            pass
    return False


def _collect_local_causes(profile, composite, indices):
    """For each window index, collect top local contributing feature(s)."""
    local_causes = []
    distinct: dict[str, list[int]] = defaultdict(list)
    for idx in sorted(indices):
        contribs = rank_feature_contributions_for_region(
            profile.series, idx, composite
        )
        # Top candidates: rank 1-2 with meaningful share, else top 1
        top = [c for c in contribs if c.rank <= 2 and (c.contribution_share or 0) >= 0.15]
        if not top and contribs:
            top = contribs[:1]
        for c in top:
            entry = {
                "window_index": int(idx),
                "feature_id": c.feature_id,
                "rank": int(c.rank),
                "contribution_share": c.contribution_share,
                "normalized_value": c.normalized_value,
                "raw_value": c.raw_value,
                "is_peak_support": bool(c.is_peak_support),
            }
            local_causes.append(entry)
            distinct[c.feature_id].append(idx)
    # also include any peak support feature that may not be top2 but is peak support
    return local_causes, {k: sorted(v) for k, v in distinct.items()}


def _temper_contributions(contributions, single_hand: bool):
    """Temper rhythm difficulty when other hand inactive; returns new list and flag."""
    if not single_hand:
        return contributions, False, None
    # check if rhythm present
    rhythm_contribs = [c for c in contributions if c.feature_id == "rhythm.attack_density"]
    if not rhythm_contribs:
        return contributions, False, None
    # apply temper factor 0.6 to rhythm weighted_value and recompute shares
    temper_factor = 0.6
    # contributions are FeatureContribution objects; need to rebuild with adjusted weighted_value
    # Compute positive total after tempering
    adjusted = []
    for c in contributions:
        if c.feature_id == "rhythm.attack_density":
            adjusted.append(
                c.__class__(
                    feature_id=c.feature_id,
                    feature_name=c.feature_name,
                    raw_value=c.raw_value,
                    normalized_value=c.normalized_value,
                    smoothed_value=c.smoothed_value,
                    attribution_value=c.attribution_value,
                    weight=c.weight,
                    weighted_value=float(c.weighted_value) * temper_factor,
                    contribution_share=c.contribution_share,  # temporary
                    rank=c.rank,
                    is_peak_support=c.is_peak_support,
                )
            )
        else:
            adjusted.append(c)
    positive_total = sum(max(c.weighted_value, 0.0) for c in adjusted)
    reweighted = []
    # sort again by weighted_value after tempering for rank stability
    ranked = sorted(
        adjusted,
        key=lambda item: (-max(item.weighted_value, 0.0), -item.weighted_value, item.feature_id),
    )
    for rank, c in enumerate(ranked, start=1):
        positive_value = max(c.weighted_value, 0.0)
        share = None if positive_total == 0 else positive_value / positive_total
        reweighted.append(
            c.__class__(
                feature_id=c.feature_id,
                feature_name=c.feature_name,
                raw_value=c.raw_value,
                normalized_value=c.normalized_value,
                smoothed_value=c.smoothed_value,
                attribution_value=c.attribution_value,
                weight=c.weight,
                weighted_value=c.weighted_value,
                contribution_share=share,
                rank=rank,
                is_peak_support=c.is_peak_support,
            )
        )
    explanation = "rhythm tempered (single-hand active, factor 0.6)"
    return reweighted, True, explanation


def consolidate_sections(profile, composite, score=None, *, limit=5):
    """Merge overlapping/touching peak intervals; rank by peak composite value.

    Refinements (v1 compatible):
    - near-consecutive flagged windows (gap <=1 missing window) can merge;
    - adjacent setup measure can be included when feature evidence supports;
    - merged sections expose multiple local causes;
    - single-hand rhythm tempered;
    - mosso-style tempo text influences local explanation.

    Contribution values describe the representative window, not the union. Every
    support window is retained, so wide chains remain inspectable.
    """
    peaks = [p for p in profile.passages if p.value > 0]
    groups = []
    for peak in sorted(peaks, key=lambda p: (p.region.start_offset, p.region.end_offset, p.passage_id)):
        if groups and _should_merge_near_consecutive(groups[-1], peak, profile):
            groups[-1].append(peak)
        else:
            groups.append([peak])
    sections = []
    for group in groups:
        indices = sorted({p.region.window_index for p in group})

        def strength(index):
            values = profile.overall_series.normalized_values if profile.overall_series else ()
            return values[index] if index < len(values) and values[index] is not None else 0.0

        representative = max(indices, key=lambda i: (strength(i), -i))
        regions = [profile.regions[i] for i in indices]
        first, last = min(regions, key=lambda r: r.start_offset), max(regions, key=lambda r: r.end_offset)
        numbers = {}
        for region in regions:
            for index, number in zip(range(region.measure_start, region.measure_end + 1), region.measure_numbers):
                numbers[index] = number

        # --- setup/continuation expansion: include adjacent measure when evidence supports ---
        extended_indices = list(indices)  # for later local cause collection (keep original for support)
        setup_window_indices: list[int] = []
        continuation_window_indices: list[int] = []
        # check predecessor
        before = min(indices) - 1 if indices else None
        after = max(indices) + 1 if indices else None
        expanded_first = first
        expanded_last = last
        expanded_numbers = dict(numbers)
        # predecessor
        if before is not None and before >= 0 and _has_supporting_evidence(profile, composite, before):
            # extend to include before region
            before_region = profile.regions[before]
            # include its measure numbers
            for idx, num in zip(range(before_region.measure_start, before_region.measure_end + 1), before_region.measure_numbers):
                if idx not in expanded_numbers:
                    expanded_numbers[idx] = num
            expanded_first = before_region if before_region.start_offset < expanded_first.start_offset else expanded_first
            # keep offset from before_region start
            setup_window_indices.append(before)
            # optionally include in local causes as context (not peak support)
        # successor
        if after is not None and after < len(profile.regions) and _has_supporting_evidence(profile, composite, after):
            after_region = profile.regions[after]
            for idx, num in zip(range(after_region.measure_start, after_region.measure_end + 1), after_region.measure_numbers):
                if idx not in expanded_numbers:
                    expanded_numbers[idx] = num
            expanded_last = after_region if after_region.end_offset > expanded_last.end_offset else expanded_last
            continuation_window_indices.append(after)

        # Build merged region covering expanded range if any
        if setup_window_indices or continuation_window_indices:
            merged = replace(
                expanded_first,
                end_offset=expanded_last.end_offset,
                end_beat=expanded_last.end_beat,
                measure_end=expanded_last.measure_end,
                measure_numbers=tuple(expanded_numbers[i] for i in sorted(expanded_numbers)),
                position=float((expanded_first.start_offset + expanded_last.end_offset) / 2),
                label=f"Measures {expanded_numbers[sorted(expanded_numbers)[0]]}–{expanded_numbers[sorted(expanded_numbers)[-1]]}" if len(expanded_numbers) > 1 else f"Measures {expanded_numbers[sorted(expanded_numbers)[0]]}",
            )
        else:
            merged = replace(first, end_offset=last.end_offset, end_beat=last.end_beat,
                             measure_end=last.measure_end,
                             measure_numbers=tuple(numbers[i] for i in sorted(numbers)),
                             position=float((first.start_offset + last.end_offset) / 2),
                             label=f"Measures {first.measure_numbers[0]}–{last.measure_numbers[-1]}")

        supports = tuple(sorted({p.contributing_feature_id for p in group if p.contributing_feature_id in profile.series}))
        contributions = rank_feature_contributions_for_region(
            profile.series, representative, composite, peak_support_feature_ids=supports)

        # --- one-hand rhythm tempering ---
        single_hand = _is_single_hand_window(profile, representative, score)
        contributions, was_tempered, temper_note = _temper_contributions(contributions, single_hand)
        # score after tempering: if tempered, recompute strength tempered? keep original composite strength but attenuate if rhythm was dominant?
        # For descriptive scoring less aggressively, scale section score if single-hand and rhythm dominant
        base_score = strength(representative)
        display_score = base_score
        if was_tempered:
            # if rhythm was rank 1 before tempering, reduce score proportionally
            # check if rhythm was top before tempering; we have tempered list now where rhythm may have dropped rank
            # Use simple scaling: score * 0.85 when single-hand tempered and rhythm present
            display_score = base_score * 0.85

        # --- multiple local causes ---
        # include expanded context indices as well for cause discovery if they were added due to support
        cause_indices = sorted(set(indices) | set(setup_window_indices) | set(continuation_window_indices))
        # But to avoid polluting with non-peaked context that is just setup, keep distinct tracking: primary peaked indices vs extended
        # For local causes, use peaked indices primarily; include setup if it adds a distinct cause
        local_causes, distinct_map = _collect_local_causes(profile, composite, sorted(set(indices)))
        # If extended windows introduce a new dominant feature not in peaked causes, include it
        if setup_window_indices or continuation_window_indices:
            ext_causes, ext_map = _collect_local_causes(profile, composite, setup_window_indices + continuation_window_indices)
            # merge distincts for reporting
            for fid, idxs in ext_map.items():
                if fid not in distinct_map:
                    distinct_map[fid] = idxs
                    local_causes.extend(ext_causes)

        # --- mosso influence ---
        has_mosso = False
        mosso_texts: list[str] = []
        if score is not None:
            try:
                from piano_difficulty.features.expression import collect_mosso_texts_for_region, has_mosso_in_region
                # Use expanded merged measure range for mosso detection
                has_mosso = has_mosso_in_region(
                    score, merged.start_offset, merged.end_offset,
                    measure_start=merged.measure_start, measure_end=merged.measure_end
                )
                if has_mosso:
                    mosso_texts = collect_mosso_texts_for_region(
                        score, merged.start_offset, merged.end_offset,
                        measure_start=merged.measure_start, measure_end=merged.measure_end
                    )
            except Exception:
                has_mosso = False

        # snippet fields for demo (prefer pre-rendered PNG, degrade gracefully)
        rep_region = profile.regions[representative]
        _measure_numbers = list(merged.measure_numbers)
        _snippet_range = f"{merged.measure_start}-{merged.measure_end}" if merged.measure_start != merged.measure_end else str(merged.measure_start)
        if len(merged.measure_numbers) >= 2:
            try:
                _ints = sorted(int(str(x)) for x in merged.measure_numbers)
                _snippet_range = f"{_ints[0]}-{_ints[-1]}"
                _measure_numbers = [str(i) for i in _ints]
            except ValueError:
                _snippet_range = f"{merged.measure_numbers[0]}-{merged.measure_numbers[-1]}"
        elif merged.measure_numbers:
            _snippet_range = str(merged.measure_numbers[0])

        # Build ordered measure index mapping for snippet
        method_name = "near_consecutive_merged.v1" if any(
            max(group[i].region.window_index for i in range(len(group))) - min(group[i].region.window_index for i in range(len(group))) > len({p.region.window_index for p in group}) - 1
            for group in [group]
        ) or len(group) > 1 and max(indices) - min(indices) != len(indices) - 1 else "overlapping_or_touching_peaks.v1"
        # fallback to unified name when near-consecutive merging occurred
        has_gap_merge = any(
            len(group) > 1 and (max(p.region.window_index for p in group) - min(p.region.window_index for p in group) != len({p.region.window_index for p in group}) - 1)
            for group in [group]
        )
        # Simpler: if any gap, use new method; else keep old for compatibility
        if len(indices) > 1 and max(indices) - min(indices) > len(indices) - 1:
            method_name = "near_consecutive_merged.v1"
        else:
            # check if expansion happened (setup)
            method_name = "near_consecutive_merged.v1" if (setup_window_indices or continuation_window_indices) else "overlapping_or_touching_peaks.v1"

        section = {
            "section_id": f"section:{first.hand}:{first.start_offset}:{last.end_offset}",
            "region": region_to_payload(merged),
            "score": display_score,
            "method": method_name,
            "supporting_factor_ids": list(supports),
            "supporting_window_indices": indices,
            "supporting_peak_ids": [p.passage_id for p in group],
            "representative_region": region_to_payload(profile.regions[representative]),
            "contribution_scope": "representative_window",
            "contributions": [c.to_payload() for c in contributions],
            # snippet enrichment (no live render at analysis time)
            "window_index": int(rep_region.window_index) if rep_region.window_index is not None else int(indices[0]) if indices else 0,
            "measure_numbers": list(merged.measure_numbers),
            "measure_range": f"{merged.measure_numbers[0]}-{merged.measure_numbers[-1]}" if len(merged.measure_numbers) >= 2 else (merged.measure_numbers[0] if merged.measure_numbers else "unknown"),
            "snippet_image": None,
            "snippet_status": "not_requested",
            "snippet_diagnostic": "Snippet not pre-rendered; run pre-render script to generate snippets/window_<index>__measures_<range>.png.",
            "snippet_measure_numbers": _measure_numbers,
            "snippet_measure_index_range": _snippet_range,
            "snippet_window_index": int(rep_region.window_index) if rep_region.window_index is not None else int(indices[0]) if indices else 0,
            # --- refinement fields (v1 compatible, additive) ---
            "local_causes": local_causes,
            "distinct_local_causes": sorted(distinct_map.keys()),
            "distinct_local_cause_count": len(distinct_map),
            "setup_window_indices": setup_window_indices,
            "continuation_window_indices": continuation_window_indices,
            "is_single_hand_window": single_hand,
        }
        if was_tempered:
            section["hand_tempering"] = {
                "applied": True,
                "tempered_factor": "rhythm.attack_density",
                "factor": 0.6,
                "note": temper_note,
            }
            section["score_note"] = "tempered for single-hand rhythm"
        if has_mosso:
            section["tempo_texts"] = mosso_texts
            section["has_mosso_tempo"] = True
            section["tempo_influence"] = "mosso-style tempo text in region; local explanation includes tempo context"
        else:
            # always expose tempo field for consistency when score available
            if score is not None:
                section["has_mosso_tempo"] = False
                section["tempo_texts"] = mosso_texts
        sections.append(section)
    sections.sort(key=lambda s: (-s["score"], -len(s["supporting_factor_ids"]), s["region"]["window_index"]))
    return [dict(section, rank=rank) for rank, section in enumerate(sections[:limit], start=1)]
