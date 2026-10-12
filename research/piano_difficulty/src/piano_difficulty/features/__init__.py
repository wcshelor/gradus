"""Feature extractor modules.

The first implementation pass should only include direct, low-assumption
descriptors that remain useful regardless of how pedagogy research later
weights or interprets them.
"""

from __future__ import annotations

from . import (
    coordination,
    expression,
    hand_shape,
    leaps,
    metadata,
    notation,
    pitch_geometry,
    rhythm,
    statistics,
    texture,
)
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR

EXTRACTOR_MODULES = (
    metadata,
    rhythm,
    pitch_geometry,
    leaps,
    texture,
    coordination,
    notation,
    expression,
    statistics,
    hand_shape,
)


def extract_all(score: ScoreIR) -> list[FeatureRecord]:
    """Run all v0 direct feature families in registry order."""

    records: list[FeatureRecord] = []
    for module in EXTRACTOR_MODULES:
        records.extend(module.extract(score))
    return records


__all__ = ["EXTRACTOR_MODULES", "extract_all"]
