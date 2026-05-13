"""Melodic and relocation-oriented descriptors.

The first pass should focus on simple direct quantities such as mean leap size,
maximum leap size, and threshold exceedance counts by hand.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract direct leap statistics from hand-specific logical note streams."""

    raise NotImplementedError("Leap extraction is not implemented yet.")

