"""Score sanity checks.

These checks should run after normalization and before extraction to catch
structural problems early and report them as diagnostics instead of producing
misleading descriptor values.
"""

from __future__ import annotations

from piano_difficulty.normalize.schema import DiagnosticIR, ScoreIR


def run_sanity_checks(score: ScoreIR) -> list[DiagnosticIR]:
    """Return diagnostics for obvious structural or supportability issues."""

    raise NotImplementedError("Sanity checks are not implemented yet.")

