"""Metadata and score-context descriptors.

This family should eventually cover stable score-level facts such as measure
count, note count, pitch range, and the number of key, meter, or tempo changes.
These are low-risk features to implement early because they are direct and easy
to validate against tiny fixtures.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract score-level metadata and context descriptors."""

    raise NotImplementedError("Metadata extraction is not implemented yet.")

