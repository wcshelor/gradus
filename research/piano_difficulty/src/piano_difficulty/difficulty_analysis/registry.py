"""Difficulty-profile registry."""

from __future__ import annotations

from piano_difficulty.difficulty_analysis.models import DifficultyProfile
from piano_difficulty.difficulty_analysis.overview import DifficultyOverviewProfile
from piano_difficulty.difficulty_analysis.scoreanalyzer_reference import (
    ScoreAnalyzerReferenceProfile,
)

PROFILE_REGISTRY: dict[str, DifficultyProfile] = {
    "difficulty_overview": DifficultyOverviewProfile(),
    "scoreanalyzer_reference": ScoreAnalyzerReferenceProfile(),
}


def resolve_profiles(profile_ids: tuple[str, ...]) -> list[DifficultyProfile]:
    missing = [profile_id for profile_id in profile_ids if profile_id not in PROFILE_REGISTRY]
    if missing:
        available = ", ".join(sorted(PROFILE_REGISTRY))
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Unknown profile(s): {missing_text}. Available profiles: {available}.")
    return [PROFILE_REGISTRY[profile_id] for profile_id in profile_ids]
