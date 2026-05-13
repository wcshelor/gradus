"""Inter-hand coordination descriptors.

The scaffold reserves this family for direct coordination facts that do not yet
depend on pedagogy-sensitive weighting:

- aligned versus asynchronous hand attacks,
- simple subdivision mismatch counts,
- overlap patterns that reflect independent activity.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract direct inter-hand coordination descriptors."""

    raise NotImplementedError("Coordination extraction is not implemented yet.")

