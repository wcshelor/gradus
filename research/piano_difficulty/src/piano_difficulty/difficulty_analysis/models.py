"""Core difficulty-analysis data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from piano_difficulty.pipeline import ExtractionResult


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
    legacy_label: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "dimension_id": self.dimension_id,
            "mark": self.mark,
            "raw_value": self.raw_value,
            "raw_units": self.raw_units,
            "summary": self.summary,
            "source_span": self.source_span,
            "diagnostics": list(self.diagnostics),
            "notable_measures": list(self.notable_measures),
        }
        if self.legacy_label is not None:
            payload["legacy_label"] = self.legacy_label
        return payload


@dataclass(slots=True)
class AnalysisProfileResult:
    profile_id: str
    profile_version: str
    overall_score: float | None
    dimensions: list[AnalysisDimensionResult]
    scoreanalyzer_legacy_grade: str | None = None
    diagnostics: list[str] = field(default_factory=list)
    notable_measures: list[int] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "overall_score": self.overall_score,
            "dimensions": [dimension.to_payload() for dimension in self.dimensions],
            "diagnostics": list(self.diagnostics),
            "notable_measures": list(self.notable_measures),
        }
        if self.scoreanalyzer_legacy_grade is not None:
            payload["scoreanalyzer_legacy_grade"] = self.scoreanalyzer_legacy_grade
        return payload


class DifficultyProfile(Protocol):
    profile_id: str
    profile_version: str

    def analyze(self, extraction: "ExtractionResult") -> AnalysisProfileResult:
        """Analyze one extracted score."""
