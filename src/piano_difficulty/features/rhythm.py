"""Direct rhythm descriptors.

The initial scope should stay close to observable score facts:

- note density,
- attack density,
- shortest written duration,
- tuplet counts.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract rhythm descriptors from normalized notes and measures."""

    raise NotImplementedError("Rhythm extraction is not implemented yet.")

