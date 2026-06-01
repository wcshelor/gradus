"""Top-level package for the piano difficulty descriptor extractor.

The package is organized around a stable pipeline:

1. load score data,
2. normalize parser output into a parser-independent IR,
3. build reusable analysis views,
4. extract direct descriptors,
5. aggregate and export results.

The current implementation supports a narrow single-file MusicXML-family path
that normalizes into `ScoreIR`, extracts direct v0 descriptors, and can layer a
reference-profile difficulty analysis on top.
"""

from .pipeline import AnalysisResult, ExtractionResult, analyze_score, extract_score

__all__ = ["AnalysisResult", "ExtractionResult", "analyze_score", "extract_score"]
