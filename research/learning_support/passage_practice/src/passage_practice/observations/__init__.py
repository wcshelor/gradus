"""Bounded semantic observations over passages — LS-06.

One family: consecutive-attack pitch intervals (signed semitones) resolved
through the existing source resolver. No diagnosis, no aid, no learner
concepts, no attribution records (ordinary observations per D-013).

Design refs: docs/contracts.md (Observation), first_slice.md N1,
prototype_v1.md (relocation/shape signals), WP-04 T04.3 (pitch evidence).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.investigation import PassageInvestigation
from passage_practice.models.observations import (
    OBSERVATION_RESULT_SCHEMA_VERSION,
    OBSERVATION_SCHEMA_VERSION,
    Observation,
    ObservationBasis,
    ObservationResult,
)
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref
from passage_practice.models.time import ScoreInterval, ScorePosition

TRANSITION_METHOD_ID = "pitch_transition_observation"
TRANSITION_METHOD_VERSION = "v1"
TRANSITION_TYPE = "pitch_transition"
OBSERVED_HANDS = frozenset({"left", "right"})


def _order_key(note: Any) -> tuple[Fraction, int, str]:
    xml_order = getattr(note, "xml_order", None)
    order = xml_order if isinstance(xml_order, int) else 10**9
    return (note.onset, order, note.note_id)


def _position_for(score: Any, note: Any) -> ScorePosition | None:
    for measure in getattr(score, "measures", []) or []:
        if getattr(measure, "measure_index", None) == note.measure_index:
            return ScorePosition(
                quarters=note.onset,
                measure_index=measure.measure_index,
                measure_number=measure.measure_number,
                offset_in_measure=note.onset - measure.start,
            )
    return None


def observe_pitch_transitions(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = TRANSITION_METHOD_ID,
    method_version: str = TRANSITION_METHOD_VERSION,
) -> ObservationResult:
    """Observe signed pitch intervals between consecutive passage attacks.

    Resolves the investigation passage's logical-note refs, orders them by
    onset, and emits one observation per consecutive pair. `hand` scopes to
    one hand and marks results INFERENCE (staff-inferred grouping); unscoped
    runs are FACT. Fewer than two usable attacks abstains with a diagnostic.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    resolved: list[Any] = []
    diagnostics: list[Diagnostic] = []
    skipped_non_logical = 0
    for ref in passage.event_refs:
        if ref.kind != SourceKind.LOGICAL_NOTE:
            skipped_non_logical += 1
            continue
        note = resolve_ref(score, ref)
        if note is None:
            diagnostics.append(
                Diagnostic(
                    code="unresolvable_attack_ref",
                    severity=Severity.WARNING,
                    message=f"passage ref {ref.id!r} does not resolve in this score",
                )
            )
            continue
        resolved.append(note)
    if skipped_non_logical:
        diagnostics.append(
            Diagnostic(
                code="non_logical_refs_skipped",
                severity=Severity.INFO,
                message=f"{skipped_non_logical} non-logical refs excluded from transitions",
            )
        )
    scoped = resolved
    basis = ObservationBasis.FACT
    if hand is not None:
        ambiguous = sum(1 for n in resolved if n.hand is None)
        excluded = sum(1 for n in resolved if n.hand != hand)
        scoped = [n for n in resolved if n.hand == hand]
        basis = ObservationBasis.INFERENCE
        diagnostics.append(
            Diagnostic(
                code="hand_scoped_inference",
                severity=Severity.INFO,
                message=(
                    f"hand={hand!r} filtering relies on staff-inferred hand labels; "
                    f"{len(scoped)} kept, {excluded} excluded, {ambiguous} ambiguous"
                ),
            )
        )
    scoped = sorted(scoped, key=_order_key)
    if len(scoped) < 2:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=(
                    f"need at least 2 usable attacks for transitions, "
                    f"found {len(scoped)}"
                ),
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    observations: list[Observation] = []
    for index, (first, second) in enumerate(zip(scoped, scoped[1:])):
        refs = (
            SourceRef(id=first.note_id, kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id=second.note_id, kind=SourceKind.LOGICAL_NOTE),
        )
        pos_a = _position_for(score, first)
        pos_b = _position_for(score, second)
        region: ScoreInterval | None = None
        obs_diagnostics: list[Diagnostic] = []
        if pos_a is None or pos_b is None:
            obs_diagnostics.append(
                Diagnostic(
                    code="unlocatable_pair",
                    severity=Severity.WARNING,
                    message="pair measure context missing; region omitted",
                )
            )
        elif pos_a.quarters < pos_b.quarters:
            region = ScoreInterval(start=pos_a, end=pos_b)
        else:
            obs_diagnostics.append(
                Diagnostic(
                    code="simultaneous_pair",
                    severity=Severity.INFO,
                    message="simultaneous attacks have zero temporal extent; region omitted",
                )
            )
        observations.append(
            Observation(
                observation_id=f"{passage.passage_id}:pitch-transition:{index:03d}",
                observation_type=TRANSITION_TYPE,
                passage_id=passage.passage_id,
                value=int(second.pitch_midi - first.pitch_midi),
                units="semitones",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                region=region,
                hand=first.hand if first.hand == second.hand else None,
                staff=first.staff if first.staff == second.staff else None,
                voice=first.voice if first.voice == second.voice else None,
                basis=basis,
                diagnostics=tuple(obs_diagnostics),
            )
        )
    return ObservationResult(
        observations=tuple(observations),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "OBSERVATION_RESULT_SCHEMA_VERSION",
    "OBSERVATION_SCHEMA_VERSION",
    "OBSERVED_HANDS",
    "TRANSITION_METHOD_ID",
    "TRANSITION_METHOD_VERSION",
    "TRANSITION_TYPE",
    "Observation",
    "ObservationBasis",
    "ObservationResult",
    "observe_pitch_transitions",
]
