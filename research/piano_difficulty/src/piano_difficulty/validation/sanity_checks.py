"""Score sanity checks.

These checks should run after normalization and before extraction to catch
structural problems early and report them as diagnostics instead of producing
misleading descriptor values.
"""

from __future__ import annotations

from piano_difficulty.normalize.schema import DiagnosticIR, ScoreIR


def run_sanity_checks(score: ScoreIR) -> list[DiagnosticIR]:
    """Return diagnostics for obvious structural or supportability issues."""

    diagnostics: list[DiagnosticIR] = []

    if not score.measures:
        diagnostics.append(
            DiagnosticIR(
                code="missing_measures",
                severity="error",
                message="ScoreIR contains no measures.",
            )
        )

    if not score.written_notes:
        diagnostics.append(
            DiagnosticIR(
                code="missing_written_notes",
                severity="warning",
                message="ScoreIR contains no written notes.",
            )
        )

    if not score.logical_notes:
        diagnostics.append(
            DiagnosticIR(
                code="missing_logical_notes",
                severity="warning",
                message="ScoreIR contains no logical note events.",
            )
        )

    known_staves = {
        event.staff
        for event in [*score.written_notes, *score.rests]
        if event.staff is not None
    }
    if known_staves and not ({1, 2} <= known_staves):
        diagnostics.append(
            DiagnosticIR(
                code="incomplete_grand_staff",
                severity="info",
                message=(
                    "ScoreIR does not contain both staff 1 and staff 2 events; "
                    "hand-specific descriptors may be partial."
                ),
            )
        )

    return diagnostics
