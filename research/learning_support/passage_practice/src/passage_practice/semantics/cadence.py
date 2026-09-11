"""S6.4 cadence candidate heuristic v1.

Detects coarse cadential arrivals using bass motion, local key, metric
position, duration, and optional phrase-boundary evidence.

Design refs:
- S6.1 harmony view (local_key_candidates, bass_refs, onsets)
- S6.2 local key, S6.3 harmonic rhythm
- D-011 SourceRef, D-018 no ScoreIR promotion
- Task S6.4 tests: simple cadence positive, cadence-like negative,
  low-key-confidence abstention
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.source import SourceRef, resolve_ref
from passage_practice.views.harmony_view import HarmonyView

CADENCE_METHOD_ID = "cadence_candidate.v1"
CADENCE_METHOD_VERSION = "v1"

_KEY_TO_TONIC_PC = {
    "C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11,
}


@dataclass(frozen=True, slots=True)
class CadenceCandidate:
    onset: Fraction
    confidence: float
    method_id: str = CADENCE_METHOD_ID
    method_version: str = CADENCE_METHOD_VERSION
    diagnostics: tuple[Diagnostic, ...] = ()


def _pitch_class(midi: int) -> int:
    return midi % 12


def _beat_length(measure: Any | None) -> Fraction | None:
    if measure is None:
        return None
    beat_type = getattr(measure, "time_beat_type", None)
    if not isinstance(beat_type, int) or beat_type <= 0:
        return None
    return Fraction(4, beat_type)


def _locate_measure(measures: list[Any], onset: Fraction) -> Any | None:
    for m in measures:
        start = getattr(m, "start", None)
        end = getattr(m, "end", None)
        if isinstance(start, Fraction) and isinstance(end, Fraction):
            if start <= onset < end:
                return m
    return None


def detect_cadence_candidates(
    view: HarmonyView,
    passage: Any,
    score: Any,
    *,
    phrase_boundaries: tuple[Fraction, ...] = (),
) -> tuple[tuple[CadenceCandidate, ...], tuple[Diagnostic, ...]]:
    """Detect coarse cadential arrivals.

    - Uses view.local_key_candidates top confidence: if <0.65, abstains with
      diagnostic ``low_key_confidence_abstention`` (S6.4 test).
    - Checks bass motion V->I relative to top key's tonic/dominant, metric
      position on downbeat, and duration length.
    - ``phrase_boundaries`` is optional S6.5 evidence; when provided and the
      final onset is near a phrase boundary (within 1 quarter), confidence is
      boosted, but not required for v1.
    - Returns (candidates, diagnostics). Empty candidates with abstention
      diagnostic is a valid abstention, not an error.
    """
    if not isinstance(view, HarmonyView):
        raise TypeError(f"view must be HarmonyView, got {type(view).__name__}")
    diagnostics: list[Diagnostic] = list(view.diagnostics)

    if not view.local_key_candidates:
        diagnostics.append(Diagnostic(code="low_key_confidence_abstention", severity=Severity.INFO, message="no local key candidates; abstaining"))
        return (), tuple(diagnostics)

    top_key, top_conf = view.local_key_candidates[0]
    if top_conf < 0.65:
        diagnostics.append(Diagnostic(code="low_key_confidence_abstention", severity=Severity.INFO, message=f"top key {top_key!r} confidence {top_conf:.2f} <0.65; abstaining"))
        return (), tuple(diagnostics)

    if len(view.onsets) < 2 or len(view.bass_refs) < 2:
        diagnostics.append(Diagnostic(code="insufficient_bass_motion", severity=Severity.INFO, message="need at least 2 onsets with bass for cadence"))
        return (), tuple(diagnostics)

    # Resolve bass notes for last two onsets
    # view.bass_refs is per onset in order of onsets
    # Map onset -> bass ref
    onset_to_bass: dict[Fraction, SourceRef] = {}
    for onset, ref in zip(view.onsets, view.bass_refs):
        onset_to_bass[onset] = ref

    # Get last two onsets
    penult_onset = view.onsets[-2]
    final_onset = view.onsets[-1]
    penult_ref = onset_to_bass.get(penult_onset)
    final_ref = onset_to_bass.get(final_onset)
    if penult_ref is None or final_ref is None:
        diagnostics.append(Diagnostic(code="missing_bass_ref", severity=Severity.WARNING, message="missing bass ref for cadence check"))
        return (), tuple(diagnostics)

    penult_note = resolve_ref(score, penult_ref)
    final_note = resolve_ref(score, final_ref)
    if penult_note is None or final_note is None:
        diagnostics.append(Diagnostic(code="unresolvable_bass_ref", severity=Severity.WARNING, message="bass ref not in score"))
        return (), tuple(diagnostics)

    tonic_pc = _KEY_TO_TONIC_PC.get(top_key, 0)
    dominant_pc = (tonic_pc + 7) % 12
    penult_pc = _pitch_class(int(penult_note.pitch_midi))
    final_pc = _pitch_class(int(final_note.pitch_midi))

    # Bass motion V->I check
    bass_ok = (penult_pc == dominant_pc and final_pc == tonic_pc)
    # Also accept interval 5 or 7 mod12 as generic V-I motion when key is ambiguous
    interval = (final_pc - penult_pc) % 12
    generic_ok = interval in (5, 7)
    # Require at least one of specific or generic
    if not (bass_ok or generic_ok):
        diagnostics.append(Diagnostic(code="cadence_bass_motion_not_dominant_tonic", severity=Severity.INFO, message=f"bass {penult_pc}->{final_pc} not V->I for key {top_key} (dominant {dominant_pc}->tonic {tonic_pc})"))
        return (), tuple(diagnostics)

    # Metric position: final onset should be on strong beat (downbeat)
    measures = getattr(score, "measures", []) or []
    final_measure = _locate_measure(measures, final_onset)
    beat_len = _beat_length(final_measure)
    on_beat = None
    beat_index = None
    if final_measure is not None and beat_len is not None:
        rel = final_onset - final_measure.start
        beat_index = int(rel // beat_len)
        offset = rel - Fraction(beat_index) * beat_len
        on_beat = offset == 0
        if not on_beat or beat_index != 0:
            diagnostics.append(Diagnostic(code="cadence_not_on_downbeat", severity=Severity.INFO, message=f"final onset at beat {beat_index} on_beat={on_beat}, not downbeat; cadence-like negative"))
            return (), tuple(diagnostics)
    else:
        # If no measure info, we cannot verify downbeat; treat as insufficient but not abstention for v1
        # For synthetic scores without measures, we consider on_beat true if onset is integer
        if final_onset.denominator != 1 or final_onset % 1 != 0:
            diagnostics.append(Diagnostic(code="cadence_not_on_downbeat", severity=Severity.INFO, message="final onset not on integer quarter without measure info"))
            return (), tuple(diagnostics)

    # Duration: final note should be relatively long (>= quarter)
    final_dur = getattr(final_note, "duration", Fraction(0))
    final_ticks = int(final_dur * 480) if isinstance(final_dur, Fraction) else 0
    if final_ticks < 360:  # less than dotted eighth? Require at least quarter-ish
        diagnostics.append(Diagnostic(code="cadence_duration_too_short", severity=Severity.INFO, message=f"final duration {final_dur} < quarter; too short for cadence arrival"))
        return (), tuple(diagnostics)

    # Phrase boundary boost (optional S6.5 evidence)
    confidence = 0.78
    if phrase_boundaries and any(abs(final_onset - pb) <= Fraction(1, 1) for pb in phrase_boundaries):
        confidence = min(1.0, confidence + 0.10)
        diagnostics.append(Diagnostic(code="phrase_boundary_supports_cadence", severity=Severity.INFO, message="phrase boundary near cadence boosts confidence"))

    # Also boost if bass motion is exact V->I for top key
    if bass_ok:
        confidence = min(1.0, confidence + 0.05)

    candidate = CadenceCandidate(onset=final_onset, confidence=round(confidence, 4), diagnostics=tuple())
    diagnostics.append(Diagnostic(code="cadence_detected", severity=Severity.INFO, message=f"cadence at {final_onset} with confidence {confidence:.2f} in key {top_key}"))
    return (candidate,), tuple(diagnostics)


__all__ = ["CadenceCandidate", "CADENCE_METHOD_ID", "CADENCE_METHOD_VERSION", "detect_cadence_candidates"]
