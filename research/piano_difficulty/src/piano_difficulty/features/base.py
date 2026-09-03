"""Shared feature record types and extractor interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from piano_difficulty.normalize.schema import ScoreIR


@dataclass(slots=True)
class FeatureRecord:
    """One extracted descriptor value plus traceability metadata."""

    feature_id: str
    scope: str
    scope_ref: str
    value: float | int | str
    units: str | None = None
    reliability: str = "direct"
    source_span: dict[str, int | None] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)


class FeatureExtractor(Protocol):
    """Protocol implemented by feature family modules."""

    feature_family: str

    def extract(self, score: ScoreIR) -> list[FeatureRecord]:
        """Return feature records for one normalized score."""

