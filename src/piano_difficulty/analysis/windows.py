"""Window construction helpers.

Windowed views are not required for the very first extractor output, but they
should have a reserved home now because local difficulty and hotspot analysis are
core project goals.
"""

from __future__ import annotations

from piano_difficulty.normalize.schema import MeasureIR


def build_measure_windows(
    measures: list[MeasureIR],
    size: int,
    step: int = 1,
) -> list[tuple[MeasureIR, ...]]:
    """Construct fixed-size measure windows for later local analysis."""

    raise NotImplementedError("Measure window construction is not implemented yet.")

