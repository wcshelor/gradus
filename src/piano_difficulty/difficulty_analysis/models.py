"""Core difficulty-analysis data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from piano_difficulty.pipeline import ExtractionResult


def mark_to_label(mark: float | int | None) -> str | None:
    if mark is None:
        return None
    if mark < 1.5:
        return "beginner"
    if mark < 2.5:
        return "intermediate"
    if mark < 3.5:
        return "advanced"
    return "virtuoso"


@dataclass(slots=True)
class AnalysisDimensionResult:
    dimension_id: str
    mark: int | None
    raw_value: float | int | None
    raw_units: str | None
    summary: str
    source_span: dict[str, int | None]
    diagnostics: list[str] = field(default_factory=list)
    notable_measures: list[int] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "dimension_id": self.dimension_id,
            "mark": self.mark,
            "label": mark_to_label(self.mark),
            "raw_value": self.raw_value,
            "raw_units": self.raw_units,
            "summary": self.summary,
            "source_span": self.source_span,
            "diagnostics": list(self.diagnostics),
            "notable_measures": list(self.notable_measures),
        }


@dataclass(slots=True)
class AnalysisProfileResult:
    profile_id: str
    profile_version: str
    overall_score: float | None
    overall_label: str | None
    dimensions: list[AnalysisDimensionResult]
    diagnostics: list[str] = field(default_factory=list)
    notable_measures: list[int] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "overall_score": self.overall_score,
            "overall_label": self.overall_label,
            "dimensions": [dimension.to_payload() for dimension in self.dimensions],
            "diagnostics": list(self.diagnostics),
            "notable_measures": list(self.notable_measures),
        }


class DifficultyProfile(Protocol):
    profile_id: str
    profile_version: str

    def analyze(self, extraction: "ExtractionResult") -> AnalysisProfileResult:
        """Analyze one extracted score."""
