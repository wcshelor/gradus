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
from passage_practice.views.rhythm_grid import build_rhythm_grid
from passage_practice.views.texture_grid import build_texture_grid
from passage_practice.views.written_stream import build_written_stream

TRANSITION_METHOD_ID = "pitch_transition_observation"
TRANSITION_METHOD_VERSION = "v1"
TRANSITION_TYPE = "pitch_transition"

RANGE_METHOD_ID = "pitch_range_observation"
RANGE_METHOD_VERSION = "v1"
RANGE_TYPE = "pitch_range"

LEAP_METHOD_ID = "leap_frequency_observation"
LEAP_METHOD_VERSION = "v1"
LEAP_TYPE = "leap_count"

REPEATED_METHOD_ID = "repeated_note_observation"
REPEATED_METHOD_VERSION = "v1"
REPEATED_TYPE = "repeated_note_count"

REGISTRAL_METHOD_ID = "registral_extreme_observation"
REGISTRAL_METHOD_VERSION = "v1"
REGISTRAL_HIGH_TYPE = "registral_high"
REGISTRAL_LOW_TYPE = "registral_low"

# --- S2.10 rhythm observations ---

ATTACK_DENSITY_METHOD_ID = "rhythm_attack_density_observation"
ATTACK_DENSITY_METHOD_VERSION = "v1"
ATTACK_DENSITY_TYPE = "attack_density"

SHORTEST_DURATION_METHOD_ID = "rhythm_shortest_duration_observation"
SHORTEST_DURATION_METHOD_VERSION = "v1"
SHORTEST_DURATION_TYPE = "shortest_duration"

OFF_BEAT_METHOD_ID = "rhythm_off_beat_observation"
OFF_BEAT_METHOD_VERSION = "v1"
OFF_BEAT_TYPE = "off_beat_count"

SYNCOPATION_METHOD_ID = "rhythm_syncopation_proxy_observation"
SYNCOPATION_METHOD_VERSION = "v1"
SYNCOPATION_TYPE = "syncopation_proxy_count"

HAND_ALIGNMENT_METHOD_ID = "rhythm_hand_alignment_observation"
HAND_ALIGNMENT_METHOD_VERSION = "v1"
HAND_ALIGNMENT_TYPE = "hand_alignment_ratio"

SUBDIVISION_MISMATCH_METHOD_ID = "rhythm_subdivision_mismatch_observation"
SUBDIVISION_MISMATCH_METHOD_VERSION = "v1"
SUBDIVISION_MISMATCH_TYPE = "subdivision_mismatch_count"

# --- S2.11 texture observations ---

MAX_SIMULTANEITY_METHOD_ID = "texture_max_simultaneity_observation"
MAX_SIMULTANEITY_METHOD_VERSION = "v1"
MAX_SIMULTANEITY_TYPE = "max_simultaneity"

CHORD_DENSITY_METHOD_ID = "texture_chord_density_observation"
CHORD_DENSITY_METHOD_VERSION = "v1"
CHORD_DENSITY_TYPE = "chordal_onset_count"

SUSTAINED_UNDER_MOVING_METHOD_ID = "texture_sustained_under_moving_observation"
SUSTAINED_UNDER_MOVING_METHOD_VERSION = "v1"
SUSTAINED_UNDER_MOVING_TYPE = "sustained_under_moving_count"

VOICE_COUNT_METHOD_ID = "texture_voice_count_observation"
VOICE_COUNT_METHOD_VERSION = "v1"
VOICE_COUNT_TYPE = "voice_count"

STAFF_CROSSING_METHOD_ID = "texture_staff_crossing_observation"
STAFF_CROSSING_METHOD_VERSION = "v1"
STAFF_CROSSING_TYPE = "staff_crossing_count"

# --- S2.12 notation-readability observations ---
# Design refs: docs/practice_chunk_objects.md (chunk-citable evidence),
# views/written_stream.py (notation facts while declaring omissions), D-018
# (no ScoreIR promotion needed). Readability observations consume written_stream
# facts and record missing layout data as unavailable, never as zero.

ACCIDENTAL_DENSITY_METHOD_ID = "notation_accidental_density_observation"
ACCIDENTAL_DENSITY_METHOD_VERSION = "v1"
ACCIDENTAL_DENSITY_TYPE = "accidental_count"

LEDGER_LINE_PROXY_METHOD_ID = "notation_ledger_line_proxy_observation"
LEDGER_LINE_PROXY_METHOD_VERSION = "v1"
LEDGER_LINE_PROXY_TYPE = "ledger_line_proxy_count"

CLEF_CHANGE_METHOD_ID = "notation_clef_change_observation"
CLEF_CHANGE_METHOD_VERSION = "v1"
CLEF_CHANGE_TYPE = "clef_change_count"

ARTICULATION_DENSITY_METHOD_ID = "notation_articulation_density_observation"
ARTICULATION_DENSITY_METHOD_VERSION = "v1"
ARTICULATION_DENSITY_TYPE = "articulation_count"

ORNAMENT_GRACE_METHOD_ID = "notation_ornament_grace_observation"
ORNAMENT_GRACE_METHOD_VERSION = "v1"
ORNAMENT_GRACE_TYPE = "grace_note_count"

OBSERVED_HANDS = frozenset({"left", "right"})

_LEAP_THRESHOLD = 2
_TICKS_PER_QUARTER = 480


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


def _resolve_passage_notes(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
) -> tuple[list[Any], list[Diagnostic], ObservationBasis]:
    """Resolve passage logical-note refs, optionally scoped to one hand."""
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
                message=f"{skipped_non_logical} non-logical refs excluded from observations",
            )
        )
    basis = ObservationBasis.FACT
    if hand is not None:
        excluded = sum(1 for n in resolved if n.hand != hand)
        ambiguous = sum(1 for n in resolved if n.hand is None)
        resolved = [n for n in resolved if n.hand == hand]
        basis = ObservationBasis.INFERENCE
        diagnostics.append(
            Diagnostic(
                code="hand_scoped_inference",
                severity=Severity.INFO,
                message=(
                    f"hand={hand!r} filtering relies on staff-inferred hand labels; "
                    f"{len(resolved)} kept, {excluded} excluded, {ambiguous} ambiguous"
                ),
            )
        )
    resolved = sorted(resolved, key=_order_key)
    return resolved, diagnostics, basis


def observe_pitch_range(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = RANGE_METHOD_ID,
    method_version: str = RANGE_METHOD_VERSION,
) -> ObservationResult:
    """Observe the pitch range (semitones) of the passage.

    Emits one observation whose value is the difference between the
    highest and lowest MIDI pitches among the resolved attacks. Source
    refs point at the extreme notes. Abstains with a diagnostic when
    fewer than one usable attack exists.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    resolved, diagnostics, basis = _resolve_passage_notes(investigation, score, hand=hand)
    if not resolved:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=(
                    f"need at least 1 usable attack for pitch range, "
                    f"found {len(resolved)}"
                ),
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    high_note = max(resolved, key=lambda n: n.pitch_midi)
    low_note = min(resolved, key=lambda n: n.pitch_midi)
    refs = (SourceRef(id=high_note.note_id, kind=SourceKind.LOGICAL_NOTE),)
    if high_note.note_id != low_note.note_id:
        refs = (
            SourceRef(id=high_note.note_id, kind=SourceKind.LOGICAL_NOTE),
            SourceRef(id=low_note.note_id, kind=SourceKind.LOGICAL_NOTE),
        )
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:pitch-range:000",
                observation_type=RANGE_TYPE,
                passage_id=passage.passage_id,
                value=int(high_note.pitch_midi - low_note.pitch_midi),
                units="semitones",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_leap_frequency(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = LEAP_METHOD_ID,
    method_version: str = LEAP_METHOD_VERSION,
) -> ObservationResult:
    """Observe the count of pitch leaps between consecutive attacks.

    A leap is a consecutive-pair interval whose absolute value exceeds
    two semitones. Emits one observation with value = leap count and
    source refs pointing at the notes involved in each leap. Abstains
    with a diagnostic when fewer than two usable attacks exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    resolved, diagnostics, basis = _resolve_passage_notes(investigation, score, hand=hand)
    if len(resolved) < 2:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=(
                    f"need at least 2 usable attacks for leap frequency, "
                    f"found {len(resolved)}"
                ),
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    leap_refs: list[SourceRef] = []
    for first, second in zip(resolved, resolved[1:]):
        interval = abs(second.pitch_midi - first.pitch_midi)
        if interval > _LEAP_THRESHOLD:
            leap_refs.append(SourceRef(id=first.note_id, kind=SourceKind.LOGICAL_NOTE))
            leap_refs.append(SourceRef(id=second.note_id, kind=SourceKind.LOGICAL_NOTE))
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:leap-count:000",
                observation_type=LEAP_TYPE,
                passage_id=passage.passage_id,
                value=len(leap_refs) // 2,
                units="count",
                source_refs=tuple(leap_refs) if leap_refs else (
                    SourceRef(id=resolved[0].note_id, kind=SourceKind.LOGICAL_NOTE),
                ),
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_repeated_notes(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = REPEATED_METHOD_ID,
    method_version: str = REPEATED_METHOD_VERSION,
) -> ObservationResult:
    """Observe the count of consecutive repeated pitches.

    Counts pairs of consecutive attacks with identical MIDI pitch.
    Emits one observation with value = repeated-note pair count and
    source refs pointing at the notes in each repeated pair. Abstains
    with a diagnostic when fewer than two usable attacks exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    resolved, diagnostics, basis = _resolve_passage_notes(investigation, score, hand=hand)
    if len(resolved) < 2:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=(
                    f"need at least 2 usable attacks for repeated notes, "
                    f"found {len(resolved)}"
                ),
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    repeat_refs: list[SourceRef] = []
    for first, second in zip(resolved, resolved[1:]):
        if first.pitch_midi == second.pitch_midi:
            repeat_refs.append(SourceRef(id=first.note_id, kind=SourceKind.LOGICAL_NOTE))
            repeat_refs.append(SourceRef(id=second.note_id, kind=SourceKind.LOGICAL_NOTE))
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:repeated-note-count:000",
                observation_type=REPEATED_TYPE,
                passage_id=passage.passage_id,
                value=len(repeat_refs) // 2,
                units="count",
                source_refs=tuple(repeat_refs) if repeat_refs else (
                    SourceRef(id=resolved[0].note_id, kind=SourceKind.LOGICAL_NOTE),
                ),
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_registral_extremes(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = REGISTRAL_METHOD_ID,
    method_version: str = REGISTRAL_METHOD_VERSION,
) -> ObservationResult:
    """Observe the highest and lowest pitches in the passage.

    Emits two observations: one for the registral high and one for the
    registral low. Each carries a single source ref pointing at the
    extreme note. Abstains with a diagnostic when fewer than one usable
    attack exists.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    resolved, diagnostics, basis = _resolve_passage_notes(investigation, score, hand=hand)
    if not resolved:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=(
                    f"need at least 1 usable attack for registral extremes, "
                    f"found {len(resolved)}"
                ),
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    high_note = max(resolved, key=lambda n: n.pitch_midi)
    low_note = min(resolved, key=lambda n: n.pitch_midi)
    observations: list[Observation] = [
        Observation(
            observation_id=f"{passage.passage_id}:registral-high:000",
            observation_type=REGISTRAL_HIGH_TYPE,
            passage_id=passage.passage_id,
            value=int(high_note.pitch_midi),
            units="midi",
            source_refs=(SourceRef(id=high_note.note_id, kind=SourceKind.LOGICAL_NOTE),),
            method_id=method_id,
            method_version=method_version,
            basis=basis,
        ),
    ]
    if low_note.note_id != high_note.note_id:
        observations.append(
            Observation(
                observation_id=f"{passage.passage_id}:registral-low:000",
                observation_type=REGISTRAL_LOW_TYPE,
                passage_id=passage.passage_id,
                value=int(low_note.pitch_midi),
                units="midi",
                source_refs=(SourceRef(id=low_note.note_id, kind=SourceKind.LOGICAL_NOTE),),
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            )
        )
    return ObservationResult(
        observations=tuple(observations),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def _rhythm_grid_with_hand(
    investigation: PassageInvestigation,
    score: Any,
    hand: str | None,
) -> tuple[Any, list[Diagnostic], ObservationBasis, list[Any]]:
    """Build rhythm grid and filter cells by hand, returning grid, diagnostics, basis, filtered cells."""
    passage = investigation.passage
    grid = build_rhythm_grid(passage, score)
    diagnostics: list[Diagnostic] = list(grid.diagnostics)
    cells = list(grid.cells)
    basis = ObservationBasis.FACT
    if hand is not None:
        excluded = sum(1 for c in cells if c.hand != hand)
        ambiguous = sum(1 for c in cells if c.hand is None)
        cells = [c for c in cells if c.hand == hand]
        basis = ObservationBasis.INFERENCE
        diagnostics.append(
            Diagnostic(
                code="hand_scoped_inference",
                severity=Severity.INFO,
                message=(
                    f"hand={hand!r} filtering relies on staff-inferred hand labels; "
                    f"{len(cells)} kept, {excluded} excluded, {ambiguous} ambiguous"
                ),
            )
        )
    # Tuplet diagnostic is already in grid; observation consumers should treat tuplet
    # subdivisions as unsupported for ratio calculations and surface a dedicated diagnostic.
    has_tuplet = any(c.from_tuplet for c in cells)
    if has_tuplet:
        diagnostics.append(
            Diagnostic(
                code="tuplet_subdivision_unsupported",
                severity=Severity.INFO,
                message="tuplet-derived subdivisions present; duration ratios not interpreted",
            )
        )
    return grid, diagnostics, basis, cells


def observe_attack_density(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = ATTACK_DENSITY_METHOD_ID,
    method_version: str = ATTACK_DENSITY_METHOD_VERSION,
) -> ObservationResult:
    """Observe attack density — count of sounding attacks in the passage.

    Value is the count of filtered rhythm cells. Density per quarter can be
    derived downstream as count / passage duration; this observation keeps an
    integer count to remain exact and reconstruction-friendly.
    Abstains with a diagnostic when no usable attacks exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis, cells = _rhythm_grid_with_hand(investigation, score, hand)
    if not cells:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=f"need at least 1 usable attack for attack density, found {len(cells)}",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:attack-density:000",
                observation_type=ATTACK_DENSITY_TYPE,
                passage_id=passage.passage_id,
                value=len(cells),
                units="count",
                source_refs=tuple(c.source_ref for c in cells),
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_shortest_duration(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = SHORTEST_DURATION_METHOD_ID,
    method_version: str = SHORTEST_DURATION_METHOD_VERSION,
) -> ObservationResult:
    """Observe the shortest sounding duration in the passage.

    Value is the minimal cell duration scaled to integer ticks at
    480 ticks per quarter (exact: duration * 480). This preserves
    exactness for common subdivisions including triplets (1/3 -> 160).
    Source ref points at the minimal-duration cell(s). Abstains when
    no usable attacks exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis, cells = _rhythm_grid_with_hand(investigation, score, hand)
    if not cells:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=f"need at least 1 usable attack for shortest duration, found {len(cells)}",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    min_duration = min(c.duration for c in cells)
    min_cells = [c for c in cells if c.duration == min_duration]
    ticks = int(min_duration * _TICKS_PER_QUARTER)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:shortest-duration:000",
                observation_type=SHORTEST_DURATION_TYPE,
                passage_id=passage.passage_id,
                value=ticks,
                units="ticks_480_per_quarter",
                source_refs=tuple(c.source_ref for c in min_cells),
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_off_beat_density(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = OFF_BEAT_METHOD_ID,
    method_version: str = OFF_BEAT_METHOD_VERSION,
) -> ObservationResult:
    """Observe off-beat density — count of attacks not on the beat.

    Counts cells where on_beat is False. Cells with unknown meter
    (on_beat is None) are excluded from the count and noted via the
    grid's unknown_meter diagnostic. Abstains when no usable attacks exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis, cells = _rhythm_grid_with_hand(investigation, score, hand)
    if not cells:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=f"need at least 1 usable attack for off-beat density, found {len(cells)}",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    off_cells = [c for c in cells if c.on_beat is False]
    # Provide at least one ref for zero case to satisfy non-empty source_refs.
    if off_cells:
        refs = tuple(c.source_ref for c in off_cells)
    else:
        refs = (cells[0].source_ref,)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:off-beat-count:000",
                observation_type=OFF_BEAT_TYPE,
                passage_id=passage.passage_id,
                value=len(off_cells),
                units="count",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_syncopation_proxy(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = SYNCOPATION_METHOD_ID,
    method_version: str = SYNCOPATION_METHOD_VERSION,
) -> ObservationResult:
    """Observe a syncopation proxy — off-beat attacks that sound through the next beat.

    Counts cells where on_beat is False and beat_boundaries_crossed > 0,
    i.e. off-beat notes sustaining across a beat line. Tuplet-derived cells
    are counted but flagged via the tuplet diagnostic; duration interpretation
    for tuplets is unsupported. Abstains when no usable attacks exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis, cells = _rhythm_grid_with_hand(investigation, score, hand)
    if not cells:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=f"need at least 1 usable attack for syncopation proxy, found {len(cells)}",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    sync_cells = [
        c for c in cells
        if c.on_beat is False and (c.beat_boundaries_crossed or 0) > 0
    ]
    if sync_cells:
        refs = tuple(c.source_ref for c in sync_cells)
    else:
        refs = (cells[0].source_ref,)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:syncopation-proxy-count:000",
                observation_type=SYNCOPATION_TYPE,
                passage_id=passage.passage_id,
                value=len(sync_cells),
                units="count",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_hand_alignment_ratio(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = HAND_ALIGNMENT_METHOD_ID,
    method_version: str = HAND_ALIGNMENT_METHOD_VERSION,
) -> ObservationResult:
    """Observe hand alignment — percent of attack times where both hands sound together.

    Value is integer percent (0-100): both_hands_onsets * 100 // total_onsets.
    Uses the rhythm grid's per-onset both_hands flag, which is derived from
    co-attack hand presence. Abstains when no onsets exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis, cells = _rhythm_grid_with_hand(investigation, score, hand)
    # For alignment we need onsets; filter onsets to those containing filtered cells.
    if not grid.onsets or not cells:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 onset for hand alignment, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    # If hand filtered, recompute alignment over filtered cells only.
    if hand is not None:
        # Build filtered onset map: onset -> hands among filtered cells
        from collections import defaultdict

        onset_hands: dict[Any, set[str]] = defaultdict(set)
        cell_onset = {c.source_ref.id: c.onset for c in cells}
        # Need to map cells to onsets; use grid.onsets membership
        filtered_ids = {c.source_ref.id for c in cells}
        for onset in grid.onsets:
            filtered_refs = [r for r in onset.cell_refs if r.id in filtered_ids]
            if filtered_refs:
                hs = {c.hand for c in cells if c.source_ref.id in {r.id for r in filtered_refs} and c.hand is not None}
                onset_hands[onset.onset] = hs
        total = len(onset_hands)
        both = sum(1 for hs in onset_hands.values() if hs == {"left", "right"})
        if total == 0:
            diagnostics.append(
                Diagnostic(
                    code="insufficient_attacks",
                    severity=Severity.INFO,
                    message="need at least 1 onset for hand alignment, found 0",
                )
            )
            return ObservationResult(
                observations=(), method_id=method_id,
                method_version=method_version, diagnostics=tuple(diagnostics),
            )
        percent = (both * 100) // total
        refs = tuple(c.source_ref for c in cells[:1])
        return ObservationResult(
            observations=(
                Observation(
                    observation_id=f"{passage.passage_id}:hand-alignment-ratio:000",
                    observation_type=HAND_ALIGNMENT_TYPE,
                    passage_id=passage.passage_id,
                    value=percent,
                    units="percent",
                    source_refs=refs,
                    method_id=method_id,
                    method_version=method_version,
                    basis=basis,
                ),
            ),
            method_id=method_id,
            method_version=method_version,
            diagnostics=tuple(diagnostics),
        )
    total = len(grid.onsets)
    both = sum(1 for o in grid.onsets if o.both_hands)
    percent = (both * 100) // total if total else 0
    refs = tuple(c.source_ref for c in cells[:1])
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:hand-alignment-ratio:000",
                observation_type=HAND_ALIGNMENT_TYPE,
                passage_id=passage.passage_id,
                value=percent,
                units="percent",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_subdivision_mismatch(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = SUBDIVISION_MISMATCH_METHOD_ID,
    method_version: str = SUBDIVISION_MISMATCH_METHOD_VERSION,
) -> ObservationResult:
    """Observe subdivision mismatch — onsets where simultaneous cells have different durations.

    Counts distinct onset times where at least two cells share the onset but
    have differing durations (e.g. one hand holds while the other moves).
    Abstains when no usable attacks exist or fewer than one onset with
    multiple cells.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis, cells = _rhythm_grid_with_hand(investigation, score, hand)
    if not cells:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message=f"need at least 1 usable attack for subdivision mismatch, found {len(cells)}",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    # Group filtered cells by onset
    from collections import defaultdict

    by_onset: dict[Any, list[Any]] = defaultdict(list)
    for c in cells:
        by_onset[c.onset].append(c)
    mismatch_onsets = []
    mismatch_refs: list[SourceRef] = []
    for onset, group in by_onset.items():
        if len(group) < 2:
            continue
        durations = {c.duration for c in group}
        if len(durations) > 1:
            mismatch_onsets.append(onset)
            mismatch_refs.extend(c.source_ref for c in group)
    if mismatch_refs:
        refs = tuple(mismatch_refs)
    else:
        refs = (cells[0].source_ref,)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:subdivision-mismatch-count:000",
                observation_type=SUBDIVISION_MISMATCH_TYPE,
                passage_id=passage.passage_id,
                value=len(mismatch_onsets),
                units="count",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def _texture_grid_for(
    investigation: PassageInvestigation,
    score: Any,
    hand: str | None,
) -> tuple[Any, list[Diagnostic], ObservationBasis]:
    """Build texture grid filtered by hand, returning grid, diagnostics, basis.

    If hand is None, uses the passage as-is (FACT). If hand is set, builds a
    filtered passage containing only that hand's logical notes so simultaneity
    and sustained-under-moving are scoped to the hand (INFERENCE). Cross-boundary
    sustained material remains out of scope per texture_grid semantics.
    """
    passage = investigation.passage
    if hand is None:
        grid = build_texture_grid(passage, score)
        diagnostics: list[Diagnostic] = list(grid.diagnostics)
        return grid, diagnostics, ObservationBasis.FACT
    # Resolve to determine which refs belong to the requested hand.
    filtered_refs: list[SourceRef] = []
    excluded = 0
    ambiguous = 0
    for ref in passage.event_refs:
        if ref.kind != SourceKind.LOGICAL_NOTE:
            continue
        note = resolve_ref(score, ref)
        if note is None:
            continue
        note_hand = getattr(note, "hand", None)
        if note_hand is None:
            ambiguous += 1
            excluded += 1
            continue
        if note_hand != hand:
            excluded += 1
            continue
        filtered_refs.append(ref)
    # Build a filtered passage (same identity interval, only filtered refs).
    from passage_practice.models.passage import Passage

    filtered_passage = Passage(
        passage_id=passage.passage_id,
        score_id=passage.score_id,
        start=passage.start,
        end=passage.end,
        purpose=passage.purpose,
        method_id=passage.method_id,
        method_version=passage.method_version,
        event_refs=tuple(filtered_refs),
        parent_id=passage.parent_id,
        omissions=passage.omissions,
        diagnostics=passage.diagnostics,
    )
    grid = build_texture_grid(filtered_passage, score)
    diagnostics = list(grid.diagnostics)
    diagnostics.append(
        Diagnostic(
            code="hand_scoped_inference",
            severity=Severity.INFO,
            message=(
                f"hand={hand!r} filtering relies on staff-inferred hand labels; "
                f"{len(filtered_refs)} kept, {excluded} excluded, {ambiguous} ambiguous"
            ),
        )
    )
    return grid, diagnostics, ObservationBasis.INFERENCE


def observe_max_simultaneity(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = MAX_SIMULTANEITY_METHOD_ID,
    method_version: str = MAX_SIMULTANEITY_METHOD_VERSION,
) -> ObservationResult:
    """Observe maximum simultaneity — largest chord size in the passage.

    Value is max chord size (1 = monophonic, >1 = chordal). Source refs are
    the attack refs of the maximal slice(s). Abstains when no slices exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis = _texture_grid_for(investigation, score, hand)
    if not grid.slices:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 slice for max simultaneity, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    summary = grid.summary()
    max_size = summary["max_chord_size"]
    # Collect attack refs from slices achieving max.
    max_refs: list[SourceRef] = []
    for s in grid.slices:
        if s.chord_size == max_size:
            max_refs.extend(s.attack_refs)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:max-simultaneity:000",
                observation_type=MAX_SIMULTANEITY_TYPE,
                passage_id=passage.passage_id,
                value=int(max_size),
                units="count",
                source_refs=tuple(max_refs) if max_refs else (grid.slices[0].attack_refs[0],),
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_chord_density(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = CHORD_DENSITY_METHOD_ID,
    method_version: str = CHORD_DENSITY_METHOD_VERSION,
) -> ObservationResult:
    """Observe chord density — count of onsets where chord size > 1."""
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis = _texture_grid_for(investigation, score, hand)
    if not grid.slices:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 slice for chord density, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    summary = grid.summary()
    count = summary["chordal_onset_count"]
    if count > 0:
        refs: list[SourceRef] = []
        for s in grid.slices:
            if s.chord_size > 1:
                refs.extend(s.attack_refs)
        source_refs = tuple(refs)
    else:
        source_refs = (grid.slices[0].attack_refs[0],)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:chord-density:000",
                observation_type=CHORD_DENSITY_TYPE,
                passage_id=passage.passage_id,
                value=int(count),
                units="count",
                source_refs=source_refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_sustained_under_moving(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = SUSTAINED_UNDER_MOVING_METHOD_ID,
    method_version: str = SUSTAINED_UNDER_MOVING_METHOD_VERSION,
) -> ObservationResult:
    """Observe sustained-under-moving count — slices where earlier attacks sound through.

    Uses the texture_grid's sustained_under_moving flag, which is computed
    from passage attacks only (cross-boundary sustain from before the passage
    is out of scope and never counted). Value is the count of such slices.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis = _texture_grid_for(investigation, score, hand)
    if not grid.slices:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 slice for sustained-under-moving, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    summary = grid.summary()
    count = summary["sustained_under_moving_count"]
    if count > 0:
        refs: list[SourceRef] = []
        for s in grid.slices:
            if s.sustained_under_moving:
                refs.extend(s.attack_refs)
                refs.extend(s.sustained_refs)
        source_refs = tuple(refs)
    else:
        source_refs = (grid.slices[0].attack_refs[0],)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:sustained-under-moving:000",
                observation_type=SUSTAINED_UNDER_MOVING_TYPE,
                passage_id=passage.passage_id,
                value=int(count),
                units="count",
                source_refs=source_refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_voice_count(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = VOICE_COUNT_METHOD_ID,
    method_version: str = VOICE_COUNT_METHOD_VERSION,
) -> ObservationResult:
    """Observe voice count — number of distinct encoded voices in the passage.

    Voice facts are encoded MusicXML voices, not musical roles (D-015). Two
    encoded voices that move together still count as two. Abstains when no
    slices exist.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    grid, diagnostics, basis = _texture_grid_for(investigation, score, hand)
    if not grid.slices:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 slice for voice count, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    summary = grid.summary()
    voices = summary["voices"]
    value = len(voices)
    # Source refs: all attack refs (voice is a property of attacks+sustained)
    all_refs: list[SourceRef] = []
    for s in grid.slices:
        all_refs.extend(s.attack_refs)
    # If no voices (all None), value 0 but keep refs.
    if value == 0:
        diagnostics.append(
            Diagnostic(
                code="ambiguous_voice",
                severity=Severity.INFO,
                message="no encoded voice facts present; voice count is 0, not proof of monophony",
            )
        )
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:voice-count:000",
                observation_type=VOICE_COUNT_TYPE,
                passage_id=passage.passage_id,
                value=int(value),
                units="count",
                source_refs=tuple(all_refs) if all_refs else (grid.slices[0].attack_refs[0],),
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_staff_crossing(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = STAFF_CROSSING_METHOD_ID,
    method_version: str = STAFF_CROSSING_METHOD_VERSION,
) -> ObservationResult:
    """Observe staff crossing — notes where hand assignment contradicts staff.

    A crossing is counted when a logical note's inferred hand (staff-based)
    is left but staff is 1 (upper), or right but staff is 2 (lower). Notes
    with unknown hand are not counted and are noted via an ambiguous-hand
    diagnostic. Where staff is unavailable the note is ignored.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    # For staff crossing we need the resolved notes themselves, not just grid.
    # Reuse pitch helper to get filtered notes and basis, but also build grid
    # diagnostics for consistency.
    grid, diagnostics, basis = _texture_grid_for(investigation, score, hand)
    if not grid.slices:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 slice for staff crossing, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    # Collect resolved notes for the (possibly hand-filtered) passage.
    # Use the same filtered_refs logic as _texture_grid_for to ensure consistency.
    notes: list[Any] = []
    ambiguous_hand = 0
    for ref in passage.event_refs:
        if ref.kind != SourceKind.LOGICAL_NOTE:
            continue
        note = resolve_ref(score, ref)
        if note is None:
            continue
        note_hand = getattr(note, "hand", None)
        note_staff = getattr(note, "staff", None)
        if hand is not None and note_hand != hand:
            if note_hand is None:
                ambiguous_hand += 1
            continue
        notes.append(note)
    if ambiguous_hand:
        diagnostics.append(
            Diagnostic(
                code="ambiguous_hand_for_crossing",
                severity=Severity.INFO,
                message=f"{ambiguous_hand} notes with unknown hand excluded from staff-crossing check",
            )
        )
    crossing_refs: list[SourceRef] = []
    for note in notes:
        h = getattr(note, "hand", None)
        s = getattr(note, "staff", None)
        if h is None or s is None:
            continue
        if (h == "left" and s == 1) or (h == "right" and s == 2):
            crossing_refs.append(SourceRef(id=note.note_id, kind=SourceKind.LOGICAL_NOTE))
    # Ensure source_refs non-empty: use first attack ref if no crossing.
    if crossing_refs:
        source_refs = tuple(crossing_refs)
    else:
        source_refs = (grid.slices[0].attack_refs[0],)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:staff-crossing-count:000",
                observation_type=STAFF_CROSSING_TYPE,
                passage_id=passage.passage_id,
                value=len(crossing_refs),
                units="count",
                source_refs=source_refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def _written_stream_with_hand(
    investigation: PassageInvestigation,
    score: Any,
    hand: str | None,
) -> tuple[Any, list[Diagnostic], ObservationBasis, list[Any]]:
    """Build written stream and filter notes by hand, returning stream, diagnostics, basis, filtered notes.

    Uses ``build_written_stream`` facts; omissions (directions/clefs/layout) are preserved.
    Layout-dependent measures remain unavailable, never zeroed.
    """
    passage = investigation.passage
    stream = build_written_stream(passage, score)
    diagnostics: list[Diagnostic] = list(stream.diagnostics)
    notes = list(stream.notes)
    basis = ObservationBasis.FACT
    if hand is not None:
        excluded = sum(1 for n in notes if n.hand != hand)
        ambiguous = sum(1 for n in notes if n.hand is None)
        notes = [n for n in notes if n.hand == hand]
        basis = ObservationBasis.INFERENCE
        diagnostics.append(
            Diagnostic(
                code="hand_scoped_inference",
                severity=Severity.INFO,
                message=(
                    f"hand={hand!r} filtering relies on staff-inferred hand labels; "
                    f"{len(notes)} kept, {excluded} excluded, {ambiguous} ambiguous"
                ),
            )
        )
    return stream, diagnostics, basis, notes


def _needs_ledger_midi(note: Any) -> bool:
    """Proxy for ledger-line burden using pitch_midi and staff.

    Thresholds are heuristic reading-load proxies, not engraving truth:
    - staff 1 (upper): midi < 60 (C4) low ledger, or midi > 84 (C6) high ledger
    - staff 2 (lower): midi < 36 (C2) low ledger, or midi > 60 (C4) high ledger
    - unknown staff: use generic 48-84 window.
    Layout geometry itself is unavailable by design.
    """
    midi = getattr(note, "pitch_midi", None)
    staff = getattr(note, "staff", None)
    if not isinstance(midi, int):
        return False
    if staff == 1:
        return midi < 60 or midi > 84
    if staff == 2:
        return midi < 36 or midi > 60
    return midi < 48 or midi > 84


def observe_accidental_density(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = ACCIDENTAL_DENSITY_METHOD_ID,
    method_version: str = ACCIDENTAL_DENSITY_METHOD_VERSION,
) -> ObservationResult:
    """Observe accidental density — count of written notes carrying an accidental.

    Counts notes where ``accidental`` is set or ``alter`` is non-zero. Value is
    the count of such notes. Source refs point at those notes; when zero, the
    first note is used as a placeholder to satisfy non-empty refs while value
    remains 0.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    stream, diagnostics, basis, notes = _written_stream_with_hand(investigation, score, hand)
    if not notes:
        # No written notes: abstain, but note that rest-only passages are valid
        # empty written-note case, not a silent zero.
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 written note for accidental density, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    accidental_notes = [
        n for n in notes if n.accidental is not None or (n.alter is not None and n.alter != 0)
    ]
    if accidental_notes:
        refs = tuple(n.source_ref for n in accidental_notes)
    else:
        refs = (notes[0].source_ref,)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:accidental-count:000",
                observation_type=ACCIDENTAL_DENSITY_TYPE,
                passage_id=passage.passage_id,
                value=len(accidental_notes),
                units="count",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_ledger_line_proxy(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = LEDGER_LINE_PROXY_METHOD_ID,
    method_version: str = LEDGER_LINE_PROXY_METHOD_VERSION,
) -> ObservationResult:
    """Observe ledger-line proxy — count of notes likely needing ledger lines.

    Uses the midi/staff heuristic in ``_needs_ledger_midi``. Layout geometry
    itself is unavailable and never interpolated; this is an explicit proxy with
    its own diagnostic note, not engraving truth.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    stream, diagnostics, basis, notes = _written_stream_with_hand(investigation, score, hand)
    if not notes:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 written note for ledger-line proxy, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    diagnostics.append(
        Diagnostic(
            code="ledger_line_proxy_heuristic",
            severity=Severity.INFO,
            message="ledger-line count is a midi/staff proxy, not engraving layout; layout data remains unavailable",
        )
    )
    ledger_notes = [n for n in notes if _needs_ledger_midi(n)]
    if ledger_notes:
        refs = tuple(n.source_ref for n in ledger_notes)
    else:
        refs = (notes[0].source_ref,)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:ledger-line-proxy-count:000",
                observation_type=LEDGER_LINE_PROXY_TYPE,
                passage_id=passage.passage_id,
                value=len(ledger_notes),
                units="count",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_clef_change_presence(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = CLEF_CHANGE_METHOD_ID,
    method_version: str = CLEF_CHANGE_METHOD_VERSION,
) -> ObservationResult:
    """Observe clef-change presence — intentionally unavailable.

    Clef changes are part of the written_stream's declared omissions
    (directions/clefs/layout). Missing layout data is recorded as
    unavailable with a diagnostic, never as zero.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    # Build stream to propagate its omissions/diagnostics, but do not fabricate a value.
    _, base_diagnostics, _, _ = _written_stream_with_hand(investigation, score, hand)
    diagnostics = list(base_diagnostics)
    diagnostics.append(
        Diagnostic(
            code="clef_data_unavailable",
            severity=Severity.INFO,
            message="clef-change data is omitted from written_stream (layout/clef omission); count remains unavailable, not zero",
        )
    )
    diagnostics.append(
        Diagnostic(
            code="layout_data_unavailable",
            severity=Severity.INFO,
            message="page layout geometry is unavailable; no layout metric is zeroed",
        )
    )
    return ObservationResult(
        observations=(),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_articulation_density(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = ARTICULATION_DENSITY_METHOD_ID,
    method_version: str = ARTICULATION_DENSITY_METHOD_VERSION,
) -> ObservationResult:
    """Observe articulation density — count of notes carrying articulations."""
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    stream, diagnostics, basis, notes = _written_stream_with_hand(investigation, score, hand)
    if not notes:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 written note for articulation density, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    articulated = [n for n in notes if n.articulations]
    if articulated:
        refs = tuple(n.source_ref for n in articulated)
    else:
        refs = (notes[0].source_ref,)
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:articulation-count:000",
                observation_type=ARTICULATION_DENSITY_TYPE,
                passage_id=passage.passage_id,
                value=len(articulated),
                units="count",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


def observe_ornament_grace_notes(
    investigation: PassageInvestigation,
    score: Any,
    *,
    hand: str | None = None,
    method_id: str = ORNAMENT_GRACE_METHOD_ID,
    method_version: str = ORNAMENT_GRACE_METHOD_VERSION,
) -> ObservationResult:
    """Observe ornament/grace notes — count of grace-note heads.

    Uses ``is_grace`` as the available proxy; tuplets/ornaments beyond grace
    are noted as unavailable where relevant in other views, not zeroed here.
    """
    if not isinstance(investigation, PassageInvestigation):
        raise TypeError("investigation must be PassageInvestigation")
    if hand is not None and hand not in OBSERVED_HANDS:
        raise ValueError(
            f"hand must be one of {sorted(OBSERVED_HANDS)} or None, got {hand!r}"
        )
    passage = investigation.passage
    stream, diagnostics, basis, notes = _written_stream_with_hand(investigation, score, hand)
    if not notes:
        diagnostics.append(
            Diagnostic(
                code="insufficient_attacks",
                severity=Severity.INFO,
                message="need at least 1 written note for grace-note count, found 0",
            )
        )
        return ObservationResult(
            observations=(), method_id=method_id,
            method_version=method_version, diagnostics=tuple(diagnostics),
        )
    grace_notes = [n for n in notes if n.is_grace]
    if grace_notes:
        refs = tuple(n.source_ref for n in grace_notes)
    else:
        refs = (notes[0].source_ref,)
    # Grace detection is limited to is_grace; other ornaments remain unavailable.
    if not grace_notes:
        diagnostics.append(
            Diagnostic(
                code="ornament_data_limited",
                severity=Severity.INFO,
                message="only is_grace ornaments are counted; other ornament types remain unavailable, not zero",
            )
        )
    return ObservationResult(
        observations=(
            Observation(
                observation_id=f"{passage.passage_id}:grace-note-count:000",
                observation_type=ORNAMENT_GRACE_TYPE,
                passage_id=passage.passage_id,
                value=len(grace_notes),
                units="count",
                source_refs=refs,
                method_id=method_id,
                method_version=method_version,
                basis=basis,
            ),
        ),
        method_id=method_id,
        method_version=method_version,
        diagnostics=tuple(diagnostics),
    )


__all__ = [
    "ACCIDENTAL_DENSITY_METHOD_ID",
    "ACCIDENTAL_DENSITY_METHOD_VERSION",
    "ACCIDENTAL_DENSITY_TYPE",
    "ARTICULATION_DENSITY_METHOD_ID",
    "ARTICULATION_DENSITY_METHOD_VERSION",
    "ARTICULATION_DENSITY_TYPE",
    "ATTACK_DENSITY_METHOD_ID",
    "ATTACK_DENSITY_METHOD_VERSION",
    "ATTACK_DENSITY_TYPE",
    "CHORD_DENSITY_METHOD_ID",
    "CHORD_DENSITY_METHOD_VERSION",
    "CHORD_DENSITY_TYPE",
    "CLEF_CHANGE_METHOD_ID",
    "CLEF_CHANGE_METHOD_VERSION",
    "CLEF_CHANGE_TYPE",
    "HAND_ALIGNMENT_METHOD_ID",
    "HAND_ALIGNMENT_METHOD_VERSION",
    "HAND_ALIGNMENT_TYPE",
    "LEAP_METHOD_ID",
    "LEAP_METHOD_VERSION",
    "LEAP_TYPE",
    "LEDGER_LINE_PROXY_METHOD_ID",
    "LEDGER_LINE_PROXY_METHOD_VERSION",
    "LEDGER_LINE_PROXY_TYPE",
    "MAX_SIMULTANEITY_METHOD_ID",
    "MAX_SIMULTANEITY_METHOD_VERSION",
    "MAX_SIMULTANEITY_TYPE",
    "OBSERVATION_RESULT_SCHEMA_VERSION",
    "OBSERVATION_SCHEMA_VERSION",
    "OBSERVED_HANDS",
    "OFF_BEAT_METHOD_ID",
    "OFF_BEAT_METHOD_VERSION",
    "OFF_BEAT_TYPE",
    "ORNAMENT_GRACE_METHOD_ID",
    "ORNAMENT_GRACE_METHOD_VERSION",
    "ORNAMENT_GRACE_TYPE",
    "RANGE_METHOD_ID",
    "RANGE_METHOD_VERSION",
    "RANGE_TYPE",
    "REGISTRAL_HIGH_TYPE",
    "REGISTRAL_LOW_TYPE",
    "REGISTRAL_METHOD_ID",
    "REGISTRAL_METHOD_VERSION",
    "REPEATED_METHOD_ID",
    "REPEATED_METHOD_VERSION",
    "REPEATED_TYPE",
    "SHORTEST_DURATION_METHOD_ID",
    "SHORTEST_DURATION_METHOD_VERSION",
    "SHORTEST_DURATION_TYPE",
    "STAFF_CROSSING_METHOD_ID",
    "STAFF_CROSSING_METHOD_VERSION",
    "STAFF_CROSSING_TYPE",
    "SUBDIVISION_MISMATCH_METHOD_ID",
    "SUBDIVISION_MISMATCH_METHOD_VERSION",
    "SUBDIVISION_MISMATCH_TYPE",
    "SUSTAINED_UNDER_MOVING_METHOD_ID",
    "SUSTAINED_UNDER_MOVING_METHOD_VERSION",
    "SUSTAINED_UNDER_MOVING_TYPE",
    "SYNCOPATION_METHOD_ID",
    "SYNCOPATION_METHOD_VERSION",
    "SYNCOPATION_TYPE",
    "TRANSITION_METHOD_ID",
    "TRANSITION_METHOD_VERSION",
    "TRANSITION_TYPE",
    "VOICE_COUNT_METHOD_ID",
    "VOICE_COUNT_METHOD_VERSION",
    "VOICE_COUNT_TYPE",
    "Observation",
    "ObservationBasis",
    "ObservationResult",
    "observe_accidental_density",
    "observe_articulation_density",
    "observe_attack_density",
    "observe_chord_density",
    "observe_clef_change_presence",
    "observe_hand_alignment_ratio",
    "observe_leap_frequency",
    "observe_ledger_line_proxy",
    "observe_max_simultaneity",
    "observe_off_beat_density",
    "observe_ornament_grace_notes",
    "observe_pitch_range",
    "observe_pitch_transitions",
    "observe_registral_extremes",
    "observe_repeated_notes",
    "observe_shortest_duration",
    "observe_staff_crossing",
    "observe_subdivision_mismatch",
    "observe_sustained_under_moving",
    "observe_syncopation_proxy",
    "observe_voice_count",
]
