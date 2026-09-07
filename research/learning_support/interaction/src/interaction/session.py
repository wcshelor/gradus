"""Minimal deterministic interaction surface — LS-08.

A small local harness over existing contracts (no UI, no model, no new
inference). Composes `ContextStore` selection, user-selected passage
investigation, pitch-transition observations, and the grounded transition
aid. See `research/learning_support/first_slice.md` (S1–S7) and the
three-area plan LS-08.

Dependency direction: this harness (interaction) may import learner-context
and passage-practice contracts; neither imports this layer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Any

from learner_context.models import (
    AssistanceRequest,
    AssistanceResult,
    ContextPermission,
    ContextSummary,
    JournalEntry,
)
from learner_context.store import ContextStore, SelectedContext
from passage_practice.aids import suggest_transition_practice
from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.investigation import PassageInvestigation
from passage_practice.models.observations import ObservationResult
from passage_practice.observations import observe_pitch_transitions
from passage_practice.passages.investigate import (
    UnresolvableRegion,
    manual_investigation,
    whole_piece_investigation,
)

HARNESS_METHOD_ID = "interaction_harness"
HARNESS_METHOD_VERSION = "v1"

HARNESS_LIMITATIONS = (
    "Interaction harness only; not a diagnosis of playing ability.",
    "No model was consulted; free text kept verbatim.",
)


@dataclass(frozen=True, slots=True)
class JournalConfirmation:
    """Receipt for a journal-only save: stored, never analyzed."""

    entry: JournalEntry
    permission: ContextPermission
    aid_generated: bool = False
    message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.entry, JournalEntry):
            raise TypeError("entry must be JournalEntry")
        if not isinstance(self.permission, ContextPermission):
            raise TypeError("permission must be ContextPermission")
        if self.aid_generated is not False:
            raise ValueError("journal-only saves must not generate an aid")


@dataclass(frozen=True, slots=True)
class ContextView:
    """Exactly what the store currently holds: no hidden summaries."""

    entries: tuple[JournalEntry, ...] = ()
    permissions: tuple[ContextPermission, ...] = ()
    summaries: tuple[ContextSummary, ...] = ()

    def __post_init__(self) -> None:
        for name in ("entries", "permissions", "summaries"):
            if not isinstance(getattr(self, name), tuple):
                raise TypeError(f"{name} must be tuple")


@dataclass(frozen=True, slots=True)
class HelpResponse:
    """One help request, with score/observation/aid/report layers separate."""

    request: AssistanceRequest
    selected: SelectedContext
    result: AssistanceResult
    investigation: PassageInvestigation | None = None
    observations: ObservationResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request, AssistanceRequest):
            raise TypeError("request must be AssistanceRequest")
        if not isinstance(self.selected, SelectedContext):
            raise TypeError("selected must be SelectedContext")
        if not isinstance(self.result, AssistanceResult):
            raise TypeError("result must be AssistanceResult")
        if self.investigation is not None and not isinstance(
            self.investigation, PassageInvestigation
        ):
            raise TypeError("investigation must be PassageInvestigation or None")
        if self.observations is not None and not isinstance(
            self.observations, ObservationResult
        ):
            raise TypeError("observations must be ObservationResult or None")


class InteractionSession:
    """Deterministic harness holding one `ContextStore` (in memory)."""

    def __init__(self, store: ContextStore | None = None) -> None:
        if store is not None and not isinstance(store, ContextStore):
            raise TypeError(
                f"store must be ContextStore or None, got {type(store).__name__}"
            )
        self._store = store if store is not None else ContextStore()

    @property
    def store(self) -> ContextStore:
        return self._store

    # -- journal-only path (S4: no analysis, no aid) ----------------------

    def save_note(self, entry: JournalEntry, *, saved: bool = False) -> JournalConfirmation:
        """Store a note verbatim; never runs investigation, observation, or aid."""
        if not isinstance(entry, JournalEntry):
            raise TypeError(f"entry must be JournalEntry, got {type(entry).__name__}")
        if not isinstance(saved, bool):
            raise TypeError(f"saved must be bool, got {saved!r}")
        permission = self._store.add_entry(entry, saved=saved)
        scope_word = "saved" if saved else "session-only"
        return JournalConfirmation(
            entry=entry,
            permission=permission,
            message=(
                f"note {entry.entry_id!r} stored verbatim as {scope_word}; "
                "no analysis or aid generated"
            ),
        )

    def inspect_context(self) -> ContextView:
        """Show current entries, their permissions, and current summaries only."""
        entries = self._store.list_entries()
        return ContextView(
            entries=entries,
            permissions=tuple(self._store.get_permission(e.entry_id) for e in entries),
            summaries=self._store.current_summaries(),
        )

    def correct_note(
        self,
        entry_id: str,
        *,
        new_id: str,
        text: str,
        recorded_at: str,
        practice_note: str | None = None,
        tags: tuple[str, ...] = (),
        fields: dict[str, str] | None = None,
        saved: bool | None = None,
    ) -> JournalEntry:
        """Append a correction revision; the original stays dated, not selected."""
        return self._store.correct_entry(
            entry_id,
            new_id=new_id,
            text=text,
            recorded_at=recorded_at,
            practice_note=practice_note,
            tags=tags,
            fields=fields,
            saved=saved,
        )

    def delete_note(self, entry_id: str) -> None:
        """Delete an entry; it influences nothing further (no hidden memory)."""
        self._store.delete_entry(entry_id)

    def set_excluded(self, entry_id: str, excluded: bool = True) -> ContextPermission:
        """Exclude (or re-include) an entry for future selection."""
        return self._store.set_excluded(entry_id, excluded=excluded)

    # -- help path (S1–S3, S5–S7) ------------------------------------------

    def request_help(
        self,
        request: AssistanceRequest,
        *,
        score: Any | None = None,
        score_id: str | None = None,
        start: Fraction | None = None,
        end: Fraction | None = None,
        whole_piece: bool = False,
        hand: str | None = None,
    ) -> HelpResponse:
        """Investigate, observe, and suggest from the request plus permitted context.

        `score` is an already-loaded score object; this layer parses nothing.
        When `start`/`end` are omitted, the request's own region is used.
        Incomplete or unresolvable input yields an aid-shaped abstention,
        never a guess and never a learner diagnosis.
        """
        if not isinstance(request, AssistanceRequest):
            raise TypeError(
                f"request must be AssistanceRequest, got {type(request).__name__}"
            )
        if not isinstance(whole_piece, bool):
            raise TypeError(f"whole_piece must be bool, got {whole_piece!r}")
        selected = self._store.select_context(request)
        reports = selected.entries
        report_ids = tuple(e.entry_id for e in reports)

        if score is None:
            return HelpResponse(
                request=request,
                selected=selected,
                result=self._abstain(
                    request,
                    rationale=(
                        "No score was provided with this request, so no passage "
                        "could be located and no score evidence examined."
                    ),
                    limitations=(
                        "A score is required before passage observations can be made.",
                    )
                    + HARNESS_LIMITATIONS,
                    diagnostics=(
                        Diagnostic(
                            code="missing_score",
                            severity=Severity.ERROR,
                            message="request_help needs an already-loaded score object",
                        ),
                    ),
                    report_refs=report_ids,
                ),
            )
        resolved_score_id = score_id if score_id is not None else request.piece_id
        if resolved_score_id is None:
            return HelpResponse(
                request=request,
                selected=selected,
                result=self._abstain(
                    request,
                    rationale=(
                        "No score identity (score_id/piece_id) was given, so the "
                        "passage cannot be attributed to a score version."
                    ),
                    limitations=(
                        "Score identity is required; refusing to attach evidence silently.",
                    )
                    + HARNESS_LIMITATIONS,
                    diagnostics=(
                        Diagnostic(
                            code="missing_score_id",
                            severity=Severity.ERROR,
                            message="pass score_id or set request.piece_id",
                        ),
                    ),
                    report_refs=report_ids,
                ),
            )
        investigation_id = f"{request.request_id}:investigation"
        try:
            if whole_piece:
                investigation = whole_piece_investigation(
                    score,
                    score_id=resolved_score_id,
                    investigation_id=investigation_id,
                    requested_hand=hand,
                    report_refs=report_ids,
                )
            else:
                bounds = (start, end)
                if bounds == (None, None) and request.region is not None:
                    bounds = (
                        request.region.start.quarters,
                        request.region.end.quarters,
                    )
                if bounds[0] is None or bounds[1] is None:
                    return HelpResponse(
                        request=request,
                        selected=selected,
                        result=self._abstain(
                            request,
                            rationale=(
                                "No passage region was selected (neither explicit "
                                "bounds nor a request region), so there is no "
                                "passage to investigate."
                            ),
                            limitations=(
                                "Select a passage or request the whole piece; "
                                "the region will not be guessed.",
                            )
                            + HARNESS_LIMITATIONS,
                            diagnostics=(
                                Diagnostic(
                                    code="unresolved_region",
                                    severity=Severity.ERROR,
                                    message="missing start/end and request.region is None",
                                ),
                            ),
                            report_refs=report_ids,
                        ),
                    )
                if not isinstance(bounds[0], Fraction) or not isinstance(
                    bounds[1], Fraction
                ):
                    raise TypeError("start/end must be Fraction (exact score time)")
                investigation = manual_investigation(
                    score,
                    score_id=resolved_score_id,
                    start=bounds[0],
                    end=bounds[1],
                    investigation_id=investigation_id,
                    requested_hand=hand,
                    report_refs=report_ids,
                )
        except UnresolvableRegion as exc:
            return HelpResponse(
                request=request,
                selected=selected,
                result=self._abstain(
                    request,
                    rationale=(
                        f"The selected region could not be resolved to score "
                        f"events ({exc.reason}); no evidence was fabricated."
                    ),
                    limitations=(
                        "Clarify the region with exact score time or a known "
                        "measure; ambiguous locations are not guessed.",
                    )
                    + HARNESS_LIMITATIONS,
                    diagnostics=tuple(exc.diagnostics)
                    or (
                        Diagnostic(
                            code=f"region_{exc.reason}",
                            severity=Severity.ERROR,
                            message=str(exc),
                        ),
                    ),
                    report_refs=report_ids,
                ),
            )
        observations = observe_pitch_transitions(investigation, score, hand=hand)
        effective = replace(request, investigation_ref=investigation.investigation_id)
        aid = suggest_transition_practice(effective, observations, reports=reports)
        return HelpResponse(
            request=request,
            selected=selected,
            result=aid,
            investigation=investigation,
            observations=observations,
        )

    @staticmethod
    def _abstain(
        request: AssistanceRequest,
        *,
        rationale: str,
        limitations: tuple[str, ...],
        diagnostics: tuple[Diagnostic, ...],
        report_refs: tuple[str, ...],
    ) -> AssistanceResult:
        return AssistanceResult(
            result_id=f"{request.request_id}:interaction-abstention",
            request_ref=request.request_id,
            need=request.question or request.intent.value,
            rationale=rationale,
            limitations=limitations,
            method_id=HARNESS_METHOD_ID,
            method_version=HARNESS_METHOD_VERSION,
            report_refs=report_refs,
            diagnostics=diagnostics,
        )


__all__ = [
    "HARNESS_LIMITATIONS",
    "HARNESS_METHOD_ID",
    "HARNESS_METHOD_VERSION",
    "ContextView",
    "HelpResponse",
    "InteractionSession",
    "JournalConfirmation",
]
