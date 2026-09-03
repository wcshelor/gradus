"""Shared analysis helpers built on top of normalized score objects."""

from __future__ import annotations

from piano_difficulty.analysis.windows import (
    BeatWindowSpec,
    MeasureWindowSpec,
    ScoreRegion,
    build_beat_regions,
    build_measure_regions,
    build_measure_windows,
)

__all__ = [
    "BeatWindowSpec",
    "MeasureWindowSpec",
    "ScoreRegion",
    "build_beat_regions",
    "build_measure_regions",
    "build_measure_windows",
]
