"""Piece-level aggregation helpers.

Feature extractors should produce localizable raw facts. This module should
eventually summarize those facts at the whole-piece level without destroying the
underlying traceability metadata.
"""

from __future__ import annotations

from piano_difficulty.features.base import FeatureRecord


def summarize_piece(features: list[FeatureRecord]) -> dict[str, object]:
    """Aggregate raw feature records into a piece-level summary payload."""

    raise NotImplementedError("Piece aggregation is not implemented yet.")

