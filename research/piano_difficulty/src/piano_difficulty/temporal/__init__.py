"""Temporal analysis helpers for windowed score profiling."""

from __future__ import annotations

from .transform import NormalizationConfig, SmoothingConfig, normalize_series, smooth_series
from .windows import (
    BeatWindowSpec,
    FinalWindowBehavior,
    HandMode,
    MeasureWindowSpec,
    ScoreRegion,
    build_beat_regions,
    build_measure_regions,
    build_measure_windows,
)

__all__ = [
    "BeatWindowSpec",
    "FinalWindowBehavior",
    "HandMode",
    "MeasureWindowSpec",
    "NormalizationConfig",
    "ScoreRegion",
    "SmoothingConfig",
    "build_beat_regions",
    "build_measure_regions",
    "build_measure_windows",
    "normalize_series",
    "smooth_series",
]
