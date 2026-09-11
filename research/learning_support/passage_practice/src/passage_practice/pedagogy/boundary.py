"""Pedagogical input boundary validator — S4.1.

Design refs:
- docs/pedagogical_input_boundary.md (§ Rejection rules)
- docs/semantic_music_extraction_plan.md Layer 6 (pedagogical hypotheses)
- passage_practice/semantics/contracts.py (SemanticBundle/Hypothesis)
- passage_practice/models/investigation.py (DifficultyEvidence)
- passage_practice/models/source.py (SourceRef, resolve_ref)

Only structured evidence may feed pedagogical hypotheses:
- SemanticBundle/SemanticHypothesis (with resolvable passage refs)
- DifficultyEvidence (validated, optional hotspot_id only when real)
- ScoreIR via SourceRef (must resolve)
- Learner feedback via existing JournalEntry report_refs (verbatim, not advice)

Raw free-text advice (e.g. "play more musically") is rejected at the contract
boundary — it must never become a rule input or hypothesis field. Unsupported
score refs are rejected with a diagnostic, not silent hypotheses.
"""

from __future__ import annotations

from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref


def validate_pedagogical_inputs(
    *,
    semantic_bundle: Any | None = None,
    score: Any | None = None,
    passage: Any | None = None,
    covered_event_refs: tuple[SourceRef, ...] | None = None,
    advice_text: str | None = None,
    free_text_diagnosis: str | None = None,
) -> tuple[bool, tuple[Diagnostic, ...]]:
    """Validate that pedagogical inputs respect the S4.1 boundary.

    Returns (is_valid, diagnostics). Raises on free-text advice contract
    violations (caller error), returns invalid+diagnostics for unsupported
    score refs (recoverable input error).

    - If ``advice_text`` or ``free_text_diagnosis`` is not None, raises
      ``ValueError`` — raw advice is not a valid input, even empty string is
      rejected (the API must not expose it).
    - If ``covered_event_refs`` is provided, each ref must resolve in ``score``
      when ``score`` is given; otherwise diagnostic ``unsupported_passage_ref``
      is returned and valid is False. Empty tuple is invalid (no provenance).
    - If ``semantic_bundle`` is provided, its ``source_passage_id`` must match
      ``passage.passage_id`` when both are given; mismatch yields diagnostic.
    - At least one of semantic_bundle/covered_event_refs must be meaningful for
      a real call, but this validator does not enforce that here — higher layers
      (rules) do. This keeps S4.1 focused on the two contract rejections.
    """
    if advice_text is not None:
        raise ValueError(
            "advice_text is not a valid pedagogical input; use structured "
            "PedagogicalHypothesis fields and template-derived labels"
        )
    if free_text_diagnosis is not None:
        raise ValueError(
            "free_text_diagnosis is not a valid pedagogical input; use "
            "supporting_observation_ids / satisfied_criteria + confidence bands"
        )

    diagnostics: list[Diagnostic] = []

    if covered_event_refs is not None:
        if not isinstance(covered_event_refs, tuple):
            raise TypeError("covered_event_refs must be tuple[SourceRef, ...]")
        if not covered_event_refs:
            diagnostics.append(
                Diagnostic(
                    code="unsupported_passage_ref",
                    severity=Severity.WARNING,
                    message="covered_event_ids must be non-empty; no provenance for empty hypotheses",
                )
            )
            return False, tuple(diagnostics)
        for ref in covered_event_refs:
            if not isinstance(ref, SourceRef):
                raise TypeError(f"covered_event_refs must contain SourceRef, got {type(ref).__name__}")
            if ref.kind not in (SourceKind.LOGICAL_NOTE, SourceKind.WRITTEN_NOTE):
                diagnostics.append(
                    Diagnostic(
                        code="unsupported_passage_ref",
                        severity=Severity.WARNING,
                        message=f"unsupported SourceKind {ref.kind!r} for pedagogical coverage; use logical/written note refs",
                    )
                )
                return False, tuple(diagnostics)
            if score is not None:
                resolved = resolve_ref(score, ref)
                if resolved is None:
                    diagnostics.append(
                        Diagnostic(
                            code="unresolvable_score_ref",
                            severity=Severity.WARNING,
                            message=f"SourceRef {ref.id!r} does not resolve in the provided score",
                        )
                    )
                    return False, tuple(diagnostics)

    if semantic_bundle is not None and passage is not None:
        bundle_pid = getattr(semantic_bundle, "source_passage_id", None)
        passage_pid = getattr(passage, "passage_id", None)
        if bundle_pid is not None and passage_pid is not None and bundle_pid != passage_pid:
            diagnostics.append(
                Diagnostic(
                    code="unsupported_passage_ref",
                    severity=Severity.WARNING,
                    message=f"semantic bundle passage {bundle_pid!r} does not match passage {passage_pid!r}",
                )
            )
            return False, tuple(diagnostics)

    return True, tuple(diagnostics)


__all__ = ["validate_pedagogical_inputs"]
