"""S6.6 sequence/repetition heuristic v1.

Detects local contour/rhythm recurrence under transposition or register
change. Heuristic, deterministic, and testable via musical invariants
rather than string matching.

Design refs:
- S6.1 harmony view (not needed directly, but sibling)
- Task S6.6 tests: transposed sequence, exact repetition,
  similar rhythm different contour, too-short negative
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import Passage
from passage_practice.models.source import SourceKind, SourceRef, resolve_ref

SEQUENCE_METHOD_ID = "sequence_repetition.v1"
SEQUENCE_METHOD_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class SequenceCandidate:
    start_onset: Fraction
    end_onset: Fraction
    transposition_semitones: int
    confidence: float
    is_exact: bool
    diagnostics: tuple[Diagnostic, ...] = ()


def _order_key(note: Any) -> tuple[Fraction, int, str]:
    order = getattr(note, "xml_order", None)
    order = order if isinstance(order, int) else 10**9
    return (getattr(note, "onset", Fraction(0)), order, getattr(note, "note_id", ""))


def detect_sequence_repetition(
    passage: Passage,
    score: Any,
    *,
    min_motif_notes: int = 3,
    min_motif_intervals: int = 2,
) -> tuple[tuple[SequenceCandidate, ...], tuple[Diagnostic, ...]]:
    """Detect transposed or exact repetitions.

    - ``min_motif_notes``: motif must have at least this many notes (S6.6 too-short negative)
    - Checks interval pattern (contour) and rhythm pattern (duration sequence) for recurrence.
    - Transposed sequence: interval pattern identical, absolute pitch shifted by constant semitones.
    - Exact repetition: pitch and interval pattern identical (transposition 0).
    - Similar rhythm different contour: same durations but different intervals → not a repetition.
    - Too-short: motif < min_motif_notes → no candidate, diagnostic.

    Returns (candidates, diagnostics). Candidates are sorted by start_onset.
    """
    if not isinstance(passage, Passage):
        raise TypeError(f"passage must be Passage, got {type(passage).__name__}")

    resolved: list[Any] = []
    for ref in passage.event_refs:
        if ref.kind != SourceKind.LOGICAL_NOTE:
            continue
        note = resolve_ref(score, ref)
        if note is not None:
            resolved.append(note)
    resolved.sort(key=_order_key)

    diagnostics: list[Diagnostic] = []

    if len(resolved) < min_motif_notes * 2 - 1:
        diagnostics.append(Diagnostic(code="too_short_for_sequence", severity=Severity.INFO, message=f"only {len(resolved)} notes; need >= {min_motif_notes*2-1} for repetition"))
        return (), tuple(diagnostics)

    if len(resolved) < min_motif_notes:
        diagnostics.append(Diagnostic(code="too_short_motif", severity=Severity.INFO, message=f"motif too short: {len(resolved)} < {min_motif_notes}"))
        return (), tuple(diagnostics)

    # Build per-note pitch and duration sequences
    pitches = [int(n.pitch_midi) for n in resolved]
    durations = [getattr(n, "duration", Fraction(1, 4)) for n in resolved]
    onsets = [getattr(n, "onset", Fraction(0)) for n in resolved]
    intervals = [pitches[i+1]-pitches[i] for i in range(len(pitches)-1)]

    # Motif length in notes
    motif_len = min_motif_notes
    # Search for repetitions: compare every window of motif_len to later windows
    candidates: list[SequenceCandidate] = []
    seen: set[tuple[Fraction, Fraction]] = set()

    for start in range(len(pitches) - motif_len + 1):
        motif_intervals = tuple(intervals[start:start+motif_len-1])
        motif_durs = tuple(durations[start:start+motif_len])
        motif_pitches = tuple(pitches[start:start+motif_len])
        motif_start_onset = onsets[start]
        motif_end_onset = onsets[start+motif_len-1] + durations[start+motif_len-1]

        for other in range(start+1, len(pitches) - motif_len + 1):
            other_intervals = tuple(intervals[other:other+motif_len-1])
            other_durs = tuple(durations[other:other+motif_len])
            # Rhythm must match exactly for v1
            if other_durs != motif_durs:
                continue
            # Contour must match: intervals identical for transposed/ exact
            if other_intervals != motif_intervals:
                continue
            # Transposition check: other pitches = motif pitches + constant
            trans = pitches[other] - pitches[start]
            other_pitches = tuple(pitches[other:other+motif_len])
            expected = tuple(p+trans for p in motif_pitches)
            if other_pitches != expected:
                continue
            # Check for register change: transposition may be large (octave)
            # For v1, any constant transposition is considered, but confidence
            # is higher for small transposition (<=12) and exact (0) highest
            is_exact = trans == 0
            # Confidence: base 0.75 for exact, 0.65 for transposed, penalize large transposition
            conf = 0.80 if is_exact else 0.70
            if abs(trans) > 12:
                conf -= 0.10
            # Avoid duplicate candidates with same start/end
            key = (motif_start_onset, onsets[other])
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                SequenceCandidate(
                    start_onset=motif_start_onset,
                    end_onset=onsets[other] + durations[other],
                    transposition_semitones=trans,
                    confidence=round(conf, 4),
                    is_exact=is_exact,
                    diagnostics=(),
                )
            )
            # For v1, report first other match per start only
            break

    if not candidates:
        # Check if similar rhythm but different contour exists -> diagnostic for that case
        # Look for any pair with same rhythm but different intervals
        for start in range(len(pitches) - motif_len + 1):
            motif_durs = tuple(durations[start:start+motif_len])
            motif_intervals = tuple(intervals[start:start+motif_len-1])
            for other in range(start+1, len(pitches) - motif_len + 1):
                other_durs = tuple(durations[other:other+motif_len])
                other_intervals = tuple(intervals[other:other+motif_len-1])
                if other_durs == motif_durs and other_intervals != motif_intervals:
                    diagnostics.append(Diagnostic(code="similar_rhythm_different_contour", severity=Severity.INFO, message=f"rhythm at {onsets[start]} repeats at {onsets[other]} but contour differs"))
                    break
            if any(d.code == "similar_rhythm_different_contour" for d in diagnostics):
                break

    candidates.sort(key=lambda c: c.start_onset)
    return tuple(candidates), tuple(diagnostics)


__all__ = ["SequenceCandidate", "SEQUENCE_METHOD_ID", "SEQUENCE_METHOD_VERSION", "detect_sequence_repetition"]
