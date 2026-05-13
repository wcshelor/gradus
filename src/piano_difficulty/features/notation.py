"""Notation and reading-complexity descriptors.

This family should eventually operate on written-note tokens and measure context
rather than logical attack events. Early direct features include accidental
density, clef changes, cross-staff notation counts, and ledger-line burden.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.normalize.schema import ScoreIR


def extract(score: ScoreIR) -> list[FeatureRecord]:
    """Extract notation-sensitive descriptors from written score objects."""

    raise NotImplementedError("Notation extraction is not implemented yet.")

