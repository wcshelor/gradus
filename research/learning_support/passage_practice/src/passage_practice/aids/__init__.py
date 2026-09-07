"""One grounded text-only pedagogical aid — LS-07.

`transition_practice` suggests naming and isolating consecutive pitch moves
before practicing tempo, grounded in LS-06 pitch-transition observations.
This integration layer sits above observations and references learner
contracts; low-level passage observation code imports nothing learner-side.

Design refs: plan LS-07, first_slice.md N2, pedagogy_knowledge_base.md
(provenance restraint: this aid is `prototype_unvalidated`).

Selection rule (deterministic, uncalibrated): the aid applies when at least
one pitch-transition observation reaches `NOTABLE_TRANSITION_SEMITONES` in
absolute value. Learner reports select/frame the aid and are referenced
separately; they never alter score values. A region-scoped report that does
not overlap the observed regions yields a mismatch caveat, not a diagnosis.
Empty or below-threshold evidence yields an aid-shaped abstention
(`suggestion=None` with rationale and limitations), never a confident claim
about the learner. Effectiveness is unproven; the rationale says so.
"""

from __future__ import annotations

from learner_context.models import (
    AssistanceRequest,
    AssistanceResult,
    EntryScope,
    JournalEntry,
)

from passage_practice.models.observations import Observation, ObservationResult

AID_METHOD_ID = "transition_practice_aid"
AID_METHOD_VERSION = "v1"
AID_OBJECTIVE = "objective.isolate_consecutive_pitch_moves"
AID_PROVENANCE = "prototype_unvalidated"
NOTABLE_TRANSITION_SEMITONES = 7  # uncalibrated heuristic threshold


def _direction_word(value: int) -> str:
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "unison"


def _notable(observations: tuple[Observation, ...]) -> list[Observation]:
    return [
        o for o in observations
        if o.observation_type == "pitch_transition"
        and abs(o.value) >= NOTABLE_TRANSITION_SEMITONES
    ]


def _report_caveat(
    report: JournalEntry, regions: list,
) -> str | None:
    if report.scope != EntryScope.REGION or report.region is None:
        return None
    if any(report.region.overlaps(r) for r in regions if r is not None):
        return None
    return (
        f"report {report.entry_id!r} concerns a different region than the "
        "observed passage; the aid below is grounded in passage evidence only"
    )


def suggest_transition_practice(
    request: AssistanceRequest,
    observations: ObservationResult,
    reports: tuple[JournalEntry, ...] = (),
    *,
    method_id: str = AID_METHOD_ID,
    method_version: str = AID_METHOD_VERSION,
) -> AssistanceResult:
    """Build a traceable text-only aid (or an honest abstention) for `request`."""
    if not isinstance(request, AssistanceRequest):
        raise TypeError(
            f"request must be AssistanceRequest, got {type(request).__name__}"
        )
    if not isinstance(observations, ObservationResult):
        raise TypeError(
            "observations must be ObservationResult, "
            f"got {type(observations).__name__}"
        )
    if not isinstance(reports, tuple):
        raise TypeError("reports must be tuple")
    for report in reports:
        if not isinstance(report, JournalEntry):
            raise TypeError(
                f"reports must contain JournalEntry, got {type(report).__name__}"
            )
    need = request.question or request.intent.value
    passage_refs = (
        (request.investigation_ref,) if request.investigation_ref is not None else ()
    )
    report_refs = tuple(r.entry_id for r in reports)
    transitions = [
        o for o in observations.observations if o.observation_type == "pitch_transition"
    ]
    regions = [o.region for o in transitions]
    caveats = [
        caveat for caveat in
        (_report_caveat(r, regions) for r in reports)
        if caveat is not None
    ]
    base_limitations = [
        "Practice aid only; not a diagnosis of why the passage feels hard.",
        f"Effectiveness unproven (provenance: {AID_PROVENANCE}).",
    ]
    if not transitions:
        return AssistanceResult(
            result_id=f"{request.request_id}:transition-aid",
            request_ref=request.request_id,
            need=need,
            rationale=(
                "No pitch-transition observations were available, so no "
                "move-based aid can be grounded."
            ),
            limitations=tuple(
                ["Aid requires pitch-transition observations for the passage."]
                + base_limitations
            ),
            method_id=method_id,
            method_version=method_version,
            passage_refs=passage_refs,
            report_refs=report_refs,
        )
    notable = _notable(tuple(transitions))
    if not notable:
        peak = max(abs(o.value) for o in transitions)
        return AssistanceResult(
            result_id=f"{request.request_id}:transition-aid",
            request_ref=request.request_id,
            need=need,
            rationale=(
                f"Measured {len(transitions)} consecutive pitch moves; the largest "
                f"is {peak} semitones, below the {NOTABLE_TRANSITION_SEMITONES}-semitone "
                "notability threshold, so this aid does not apply."
            ),
            limitations=tuple(
                [
                    "No notable pitch moves; isolating moves is not indicated.",
                    f"Threshold ({NOTABLE_TRANSITION_SEMITONES} semitones) is "
                    "uncalibrated, not a validated difficulty claim.",
                ]
                + caveats
                + base_limitations
            ),
            method_id=method_id,
            method_version=method_version,
            passage_refs=passage_refs
            or tuple({o.passage_id for o in transitions}),
            report_refs=report_refs,
            observation_refs=tuple(o.observation_id for o in transitions),
        )
    largest = max(notable, key=lambda o: abs(o.value))
    moves = "; ".join(
        f"{o.value:+d} semitones {_direction_word(o.value)} "
        f"({o.observation_id})" for o in notable
    )
    framing = (
        f" Framed by learner report(s) {', '.join(report_refs)} (verbatim "
        "preserved; score facts unchanged)."
        if report_refs else ""
    )
    return AssistanceResult(
        result_id=f"{request.request_id}:transition-aid",
        request_ref=request.request_id,
        need=need,
        rationale=(
            f"Grounded in {len(notable)} notable consecutive pitch move(s) "
            f"(largest {largest.value:+d} semitones): {moves}. "
            f"Provenance: {AID_PROVENANCE}; effectiveness unproven.{framing}"
        ),
        limitations=tuple(caveats + base_limitations),
        method_id=method_id,
        method_version=method_version,
        passage_refs=passage_refs
        or tuple({o.passage_id for o in notable}),
        report_refs=report_refs,
        observation_refs=tuple(o.observation_id for o in notable),
        suggestion=(
            "Name and isolate each consecutive pitch move before practicing "
            f"tempo: {moves}. Practice each move separately, then reconnect "
            "the moves in order."
        ),
        objective=AID_OBJECTIVE,
    )


__all__ = [
    "AID_METHOD_ID",
    "AID_METHOD_VERSION",
    "AID_OBJECTIVE",
    "AID_PROVENANCE",
    "NOTABLE_TRANSITION_SEMITONES",
    "suggest_transition_practice",
]
