"""Merge peak windows into candidate sections with recoverable support."""

from dataclasses import replace

from .dynamics.core import rank_feature_contributions_for_region
from .dynamics.models import region_to_payload


def consolidate_sections(profile, composite, *, limit=5):
    """Merge overlapping/touching peak intervals; rank by peak composite value.

Contribution values describe the representative window, not the union. Every
support window is retained, so wide chains remain inspectable.
"""
    peaks = [p for p in profile.passages if p.value > 0]
    groups = []
    for peak in sorted(peaks, key=lambda p: (p.region.start_offset, p.region.end_offset, p.passage_id)):
        if groups and peak.region.start_offset <= max(p.region.end_offset for p in groups[-1]):
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
        merged = replace(first, end_offset=last.end_offset, end_beat=last.end_beat,
                         measure_end=last.measure_end,
                         measure_numbers=tuple(numbers[i] for i in sorted(numbers)),
                         position=float((first.start_offset + last.end_offset) / 2),
                         label=f"Measures {first.measure_numbers[0]}–{last.measure_numbers[-1]}")
        supports = tuple(sorted({p.contributing_feature_id for p in group if p.contributing_feature_id in profile.series}))
        contributions = rank_feature_contributions_for_region(
            profile.series, representative, composite, peak_support_feature_ids=supports)
        sections.append({
            "section_id": f"section:{first.hand}:{first.start_offset}:{last.end_offset}",
            "region": region_to_payload(merged),
            "score": strength(representative),
            "method": "overlapping_or_touching_peaks.v1",
            "supporting_factor_ids": list(supports),
            "supporting_window_indices": indices,
            "supporting_peak_ids": [p.passage_id for p in group],
            "representative_region": region_to_payload(profile.regions[representative]),
            "contribution_scope": "representative_window",
            "contributions": [c.to_payload() for c in contributions],
        })
    sections.sort(key=lambda s: (-s["score"], -len(s["supporting_factor_ids"]), s["region"]["window_index"]))
    return [dict(section, rank=rank) for rank, section in enumerate(sections[:limit], start=1)]
