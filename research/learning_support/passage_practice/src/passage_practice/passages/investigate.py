"""User-selected investigation entry — LS-05 (D-013 accepted).

Builds `PassageInvestigation` envelopes from exact regions without computing
any difficulty profile. User selection, reported concern, and measured
difficulty stay in distinct fields: the passage carries score evidence, a
`reported_concern` diagnostic carries learner report references opaquely
(this layer must not import learner contracts), and measured difficulty
travels only in the optional validated `difficulty` collection.

Design refs:
- docs/contracts.md: Passage investigation request — D-013
- docs/decisions.md: D-013; research/learning_support/first_slice.md S1–S5
- passages/selection.py (WP-02 T02.3–T02.5)

The analyzer-suggested route is preserved as the other entry point: it uses
the same envelope with `ANALYZER_SUGGESTED` origin and optional real
evidence, translated by T05.2 (not here). No nonzero-score gate exists at
this boundary — empty difficulty and zero scores are valid.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.investigation import (
    DifficultyEvidence,
    PassageInvestigation,
    SelectionOrigin,
)
from passage_practice.models.passage import PassagePurpose

from .selection import (
    SELECTION_METHOD_ID,
    SELECTION_METHOD_VERSION,
    UnresolvableRegion,
    select_passage,
    whole_piece_range,
)

MANUAL_METHOD_ID = "manual_region_selection"
MANUAL_METHOD_VERSION = "v1"
WHOLE_PIECE_METHOD_ID = "whole_piece_selection"


def _concern_diagnostic(report_refs: tuple[str, ...]) -> Diagnostic:
    for ref in report_refs:
        if not isinstance(ref, str) or not ref:
            raise ValueError(f"report_refs must contain non-empty str, got {ref!r}")
    return Diagnostic(
        code="reported_concern",
        severity=Severity.INFO,
        message="learner-reported concern attached opaquely; not score evidence",
        context={"report_refs": list(report_refs)},
    )


def manual_investigation(
    score: Any,
    *,
    score_id: str,
    start: Fraction,
    end: Fraction,
    investigation_id: str,
    requested_hand: str | None = None,
    report_refs: tuple[str, ...] = (),
    difficulty: tuple[DifficultyEvidence, ...] = (),
    purpose: PassagePurpose = PassagePurpose.DETECTION,
    method_id: str = MANUAL_METHOD_ID,
    method_version: str = MANUAL_METHOD_VERSION,
) -> PassageInvestigation:
    """Investigate an exact user-selected region; no profile is computed."""
    if not isinstance(report_refs, tuple):
        raise TypeError("report_refs must be tuple")
    if not isinstance(difficulty, tuple):
        raise TypeError("difficulty must be tuple")
    selected = select_passage(
        score,
        score_id=score_id,
        start=start,
        end=end,
        purpose=purpose,
    )
    diagnostics = list(selected.diagnostics)
    if report_refs:
        diagnostics.append(_concern_diagnostic(report_refs))
    return PassageInvestigation(
        investigation_id=investigation_id,
        passage=selected.passage,
        selection_origin=SelectionOrigin.USER_SELECTED,
        method_id=method_id,
        method_version=method_version,
        requested_hand=requested_hand,
        difficulty=difficulty,
        diagnostics=tuple(diagnostics),
    )


def whole_piece_investigation(
    score: Any,
    *,
    score_id: str,
    investigation_id: str,
    requested_hand: str | None = None,
    report_refs: tuple[str, ...] = (),
    method_id: str = WHOLE_PIECE_METHOD_ID,
    method_version: str = MANUAL_METHOD_VERSION,
) -> PassageInvestigation:
    """Investigate the whole piece; an explicit whole-piece outcome."""
    span = whole_piece_range(score)
    investigation = manual_investigation(
        score,
        score_id=score_id,
        start=span.start.quarters,
        end=span.end.quarters,
        investigation_id=investigation_id,
        requested_hand=requested_hand,
        report_refs=report_refs,
        method_id=method_id,
        method_version=method_version,
    )
    whole = Diagnostic(
        code="whole_piece",
        severity=Severity.INFO,
        message="whole-piece request resolved to the full measure span",
    )
    return PassageInvestigation(
        investigation_id=investigation.investigation_id,
        passage=investigation.passage,
        selection_origin=investigation.selection_origin,
        method_id=investigation.method_id,
        method_version=investigation.method_version,
        requested_hand=investigation.requested_hand,
        difficulty=investigation.difficulty,
        diagnostics=investigation.diagnostics + (whole,),
    )


__all__ = [
    "MANUAL_METHOD_ID",
    "MANUAL_METHOD_VERSION",
    "WHOLE_PIECE_METHOD_ID",
    "UnresolvableRegion",
    "manual_investigation",
    "whole_piece_investigation",
]
