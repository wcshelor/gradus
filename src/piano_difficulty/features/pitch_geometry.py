"""Pitch geometry and hand-span descriptors.

This family should eventually report measurable properties such as:

- maximum simultaneity span by hand,
- mean simultaneity span,
- register range,
- local expansion or contraction behavior.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract pitch-geometry descriptors from onset groups and note streams."""

    raise NotImplementedError("Pitch geometry extraction is not implemented yet.")

