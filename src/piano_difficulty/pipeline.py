"""End-to-end orchestration for score extraction.

This module should eventually become the narrowest high-level API exposed by the
package. It is responsible for connecting IO, normalization, validation,
feature extraction, aggregation, and export-oriented data shaping.

Implementation target:

- accept a path to one supported score file,
- load and validate the score,
- normalize into `ScoreIR`,
- build shared analysis views,
- run configured extractor families,
- return a structured extraction result with diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from piano_difficulty.aggregation.measure_summary import summarize_measures
from piano_difficulty.aggregation.piece_summary import summarize_piece
from piano_difficulty.difficulty_analysis.registry import resolve_profiles
from piano_difficulty.features import extract_all
from piano_difficulty.features.base import FeatureRecord
from piano_difficulty.io.musicxml import load_musicxml_document
from piano_difficulty.normalize.schema import ScoreIR
from piano_difficulty.normalize.converters import build_score_ir
from piano_difficulty.output.json_export import to_json_payload
from piano_difficulty.validation.sanity_checks import run_sanity_checks


@dataclass(slots=True)
class ExtractionResult:
    """Structured result for one score extraction run."""

    score: ScoreIR
    features: list[FeatureRecord]
    piece_summary: dict[str, object]
    measure_summaries: list[dict[str, object]]

    def to_json_payload(self) -> dict[str, object]:
        """Return a JSON-serializable payload for this result."""

        return to_json_payload(
            self.score,
            features=self.features,
            piece_summary=self.piece_summary,
            measure_summaries=self.measure_summaries,
            analysis_profiles=[],
        )


@dataclass(slots=True)
class AnalysisResult:
    """Structured result for one extraction plus difficulty-profile analysis."""

    extraction: ExtractionResult
    analysis_profiles: list[object]

    def to_json_payload(self) -> dict[str, object]:
        return to_json_payload(
            self.extraction.score,
            features=self.extraction.features,
            piece_summary=self.extraction.piece_summary,
            measure_summaries=self.extraction.measure_summaries,
            analysis_profiles=[
                profile.to_payload()
                for profile in self.analysis_profiles
            ],
        )


def extract_score(path: str | Path) -> ExtractionResult:
    """Extract a normalized score representation and features from one file.

    The single-file path intentionally stays narrow: load raw MusicXML-family
    input, normalize into `ScoreIR`, run direct v0 feature families, then build
    lightweight summaries for JSON export.
    """

    document = load_musicxml_document(path)
    score = build_score_ir(document)
    score.diagnostics.extend(run_sanity_checks(score))

    features = extract_all(score)
    piece_summary = summarize_piece(features)
    measure_summaries = summarize_measures(features)

    return ExtractionResult(
        score=score,
        features=features,
        piece_summary=piece_summary,
        measure_summaries=measure_summaries,
    )


def analyze_score(
    path: str | Path,
    *,
    profile_ids: tuple[str, ...] = ("scoreanalyzer_reference",),
) -> AnalysisResult:
    """Extract one score and apply registered difficulty profiles."""

    extraction = extract_score(path)
    profiles = resolve_profiles(profile_ids)
    return AnalysisResult(
        extraction=extraction,
        analysis_profiles=[profile.analyze(extraction) for profile in profiles],
    )
