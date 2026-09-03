"""Compatibility re-export for temporal window helpers."""

from __future__ import annotations

from piano_difficulty.temporal.windows import (
    BeatWindowSpec,
    FinalWindowBehavior,
    HandMode,
    MeasureWindowSpec,
    ScoreRegion,
    WindowStrategy,
    build_beat_regions,
    build_measure_regions,
    build_measure_windows,
)

__all__ = [
    "BeatWindowSpec",
    "FinalWindowBehavior",
    "HandMode",
    "MeasureWindowSpec",
    "ScoreRegion",
    "WindowStrategy",
    "build_beat_regions",
    "build_measure_regions",
    "build_measure_windows",
]
