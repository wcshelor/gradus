"""Non-mutating attack selection for descriptive temporal analysis."""

from dataclasses import replace

from piano_difficulty.analysis.grouping import group_onsets, group_onsets_by_hand
from piano_difficulty.normalize.schema import ScoreIR
from piano_difficulty.temporal.windows import ScoreRegion


def select_region(score: ScoreIR, region: ScoreRegion) -> ScoreIR:
    """Select attacks in [start, end), retaining original written durations.

Measure contexts are clipped for rate denominators. This is an analysis view,
not an exportable excerpt. Sustains entering the region are not new attacks.
"""
    start, end = region.start_offset, region.end_offset
    if start is None or end is None or start >= end:
        raise ValueError("Selection requires a non-empty exact score interval.")
    hand = region.hand
    def selected(event):
        return start <= event.onset < end and (hand not in {"left", "right"} or event.hand == hand)
    measures = [replace(m, start=max(start, m.start), end=min(end, m.end))
                for m in score.measures if m.start < end and m.end > start]
    indices = {m.measure_index for m in measures}
    logical = [n for n in score.logical_notes if selected(n)]
    return ScoreIR(
        source_path=score.source_path, title=score.title, composer=score.composer,
        measures=measures,
        written_notes=[n for n in score.written_notes if selected(n)],
        logical_notes=logical, rests=[n for n in score.rests if selected(n)],
        directions=[d for d in score.directions if d.measure_index in indices],
        clefs=[c for c in score.clefs if c.measure_index in indices],
        onset_groups=[*group_onsets(logical), *group_onsets_by_hand(logical)],
        diagnostics=list(score.diagnostics),
    )
