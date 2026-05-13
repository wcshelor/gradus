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

from pathlib import Path

from piano_difficulty.normalize.schema import ScoreIR


def extract_score(path: str | Path) -> ScoreIR:
    """Extract a normalized score representation and features from one file.

    The final implementation should return a richer extraction result object,
    likely containing `ScoreIR`, feature records, summaries, and diagnostics.
    `ScoreIR` is used here as the placeholder return type so the scaffold stays
    simple while the package contracts are being established.
    """

    raise NotImplementedError("Pipeline orchestration is not implemented yet.")

