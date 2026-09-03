"""Difficulty-analysis package."""

from piano_difficulty.difficulty_analysis.markdown import render_markdown_report
from piano_difficulty.difficulty_analysis.models import (
    AnalysisDimensionResult,
    AnalysisProfileResult,
    DifficultyProfile,
)
from piano_difficulty.difficulty_analysis.registry import PROFILE_REGISTRY, resolve_profiles
from piano_difficulty.difficulty_analysis.scoreanalyzer_reference import (
    ScoreAnalyzerReferenceProfile,
    mark_chords,
    mark_displacement,
    mark_harmony,
    mark_length,
    mark_rhythm,
    mark_speed,
    mark_tonality,
)

__all__ = [
    "AnalysisDimensionResult",
    "AnalysisProfileResult",
    "DifficultyProfile",
    "PROFILE_REGISTRY",
    "ScoreAnalyzerReferenceProfile",
    "mark_chords",
    "mark_displacement",
    "mark_harmony",
    "mark_length",
    "mark_rhythm",
    "mark_speed",
    "mark_tonality",
    "render_markdown_report",
    "resolve_profiles",
]
