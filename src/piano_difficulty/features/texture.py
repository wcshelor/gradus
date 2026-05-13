"""Texture and vertical-density descriptors.

This family should eventually summarize how many notes sound or attack together,
how dense vertical sonorities are, and how busy the local texture appears from
an onset-centric perspective.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract direct texture statistics from onset groups."""

    raise NotImplementedError("Texture extraction is not implemented yet.")

