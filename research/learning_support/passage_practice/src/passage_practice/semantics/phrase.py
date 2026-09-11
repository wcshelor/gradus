"""S6.5 phrase-boundary heuristic v1.

Combines rests, long notes, slurs (unavailable), repeated motifs,
cadential candidates, and metric position to infer phrase boundaries.

Design refs:
- S6.1 harmony view (onsets, harmonic rhythm)
- S6.4 cadence candidates
- D-018 slur unavailable, D-011 SourceRef
- Task S6.5 tests: clear boundary, tie-over-boundary negative,
  phrase continuation ambiguity
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.passage import Passage
from passage_practice.models.source import SourceRef, resolve_ref

PHRASE_METHOD_ID = "phrase_boundary.v1"
PHRASE_METHOD_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class PhraseBoundary:
    onset: Fraction
    confidence: float
    diagnostics: tuple[Diagnostic, ...] = ()


def _locate_measure(measures: list[Any], onset: Fraction) -> Any | None:
    for m in measures:
        s = getattr(m, "start", None)
        e = getattr(m, "end", None)
        if isinstance(s, Fraction) and isinstance(e, Fraction):
            if s <= onset < e:
                return m
    return None


def _beat_length(measure: Any | None) -> Fraction | None:
    if measure is None:
        return None
    bt = getattr(measure, "time_beat_type", None)
    if not isinstance(bt, int) or bt <= 0:
        return None
    return Fraction(4, bt)


def detect_phrase_boundaries(
    passage: Passage,
    score: Any,
    *,
    cadence_onsets: tuple[Fraction, ...] = (),
    harmony_view: Any | None = None,
) -> tuple[tuple[PhraseBoundary, ...], tuple[Diagnostic, ...]]:
    """Detect phrase boundaries for passage.

    Returns (boundaries, diagnostics). Boundaries are a subset of gaps between
    onsets plus the passage end, scored via:
    - rest in gap → +0.35
    - long note (>=2 quarters) at strong position → +0.25
    - slur evidence unavailable → diagnostic, not scored
    - repeated motif (next 2 intervals repeat) → -0.20 (ambiguity)
    - cadential candidate within 1 quarter → +0.15
    - metric downbeat → +0.10
    - tie-over-boundary → not a boundary (score 0)

    Threshold for boundary is >=0.40. Ambiguity (multiple similar scores)
    yields low confidence and diagnostic.

    Tie-over-boundary negative test is enforced: a logical note sustaining
    over the boundary onset prevents a boundary.
    """
    if not isinstance(passage, Passage):
        raise TypeError(f"passage must be Passage, got {type(passage).__name__}")

    diagnostics: list[Diagnostic] = []
    # Slur unavailable is always noted (D-018)
    diagnostics.append(Diagnostic(code="slur_evidence_unavailable", severity=Severity.INFO, message="slur phrase-marking not supported upstream; unavailable, not zero"))

    # Resolve logical notes in passage order
    resolved: list[Any] = []
    for ref in passage.event_refs:
        from passage_practice.models.source import SourceKind
        if ref.kind != SourceKind.LOGICAL_NOTE:
            continue
        note = resolve_ref(score, ref)
        if note is not None:
            resolved.append(note)
    resolved.sort(key=lambda n: (getattr(n, "onset", Fraction(0)), getattr(n, "xml_order", 0) or 0, getattr(n, "note_id", "")))

    if not resolved:
        diagnostics.append(Diagnostic(code="insufficient_notes_for_phrase", severity=Severity.INFO, message="no notes in passage"))
        return (), tuple(diagnostics)

    # Build onset map and check for rests
    measures = getattr(score, "measures", []) or []
    rests = getattr(score, "rests", []) or []
    # For quick rest check: rest onset and duration
    # Potential boundaries are between consecutive onsets and at passage end
    onsets = sorted({getattr(n, "onset", Fraction(0)) for n in resolved})
    # Also consider passage end as potential boundary (phrase ends at end)
    passage_end = passage.end.quarters

    # Precompute pitch sequence for motif repetition check
    pitches = [int(n.pitch_midi) for n in resolved]
    intervals = [pitches[i+1]-pitches[i] for i in range(len(pitches)-1)]
    # Global repeated motif flag: any 2-interval pattern repeats
    has_global_repeated = False
    if len(intervals) >= 4:
        patterns = [tuple(intervals[i:i+2]) for i in range(len(intervals)-1)]
        if len(set(patterns)) < len(patterns):
            has_global_repeated = True
            diagnostics.append(Diagnostic(code="repeated_motif_ambiguity", severity=Severity.INFO, message="repeated interval pattern suggests phrase continuation ambiguity"))

    boundaries: list[PhraseBoundary] = []
    for idx in range(len(onsets)):
        onset = onsets[idx]
        # Potential boundary is at this onset's start? Actually phrase boundary is
        # at the gap after previous notes, i.e., at onset of next phrase.
        # For v1, we score boundaries at each onset (except first) and at passage_end.
        # We'll evaluate boundary at onset (start of new phrase) based on preceding gap.
        if idx == 0:
            continue  # first onset not a boundary after start
        prev_onset = onsets[idx-1]
        gap_start_candidates = [n for n in resolved if getattr(n, "onset", Fraction(0)) == prev_onset]
        gap_end_onset = onset
        # Compute gap duration: time between end of prev notes and gap_end_onset
        # For simplicity, use duration of prev notes: assume they end at prev_onset+duration
        prev_ends = [getattr(n, "onset", Fraction(0)) + getattr(n, "duration", Fraction(0)) for n in gap_start_candidates]
        gap = gap_end_onset - max(prev_ends) if prev_ends else Fraction(0)
        # If gap negative (overlap), no rest gap
        has_rest = False
        for r in rests:
            r_onset = getattr(r, "onset", None)
            r_dur = getattr(r, "duration", None)
            if isinstance(r_onset, Fraction) and isinstance(r_dur, Fraction):
                # Rest overlaps gap
                if max(prev_ends) <= r_onset < gap_end_onset or (gap_end_onset <= r_onset < gap_end_onset+Fraction(1,4)):
                    has_rest = True
                    break
                # Also check rest at exact gap
                if gap > Fraction(0) and r_onset == max(prev_ends):
                    has_rest = True
                    break

        # Tie-over-boundary: any logical note sustaining over gap_end_onset
        tie_over = False
        for n in resolved:
            n_onset = getattr(n, "onset", Fraction(0))
            n_dur = getattr(n, "duration", Fraction(0))
            if n_onset < gap_end_onset < n_onset + n_dur:
                tie_over = True
                break

        # Long note check: preceding notes contain a long note (>=2 quarters)
        has_long = any(getattr(n, "duration", Fraction(0)) >= Fraction(2, 1) for n in gap_start_candidates)

        # Metric position: gap_end_onset on downbeat?
        measure = _locate_measure(measures, gap_end_onset)
        beat_len = _beat_length(measure)
        on_downbeat = False
        if measure is not None and beat_len is not None:
            rel = gap_end_onset - measure.start
            # need to ensure gap_end_onset is within measure
            if rel >= Fraction(0):
                off = rel % beat_len
                on_downbeat = off == 0 and (rel // beat_len) == 0
        else:
            # Synthetic without measures: consider integer quarters as downbeat
            on_downbeat = gap_end_onset.denominator == 1 and gap_end_onset % 1 == 0

        # Repeated motif: check if next 2 intervals repeat previous pattern
        # For v1, look at intervals around gap: if intervals[idx-1:idx+1] repeats elsewhere, mark ambiguous
        has_repeated_motif = False
        if len(intervals) >= 4:
            # Take last 2 intervals before gap and next 2 after
            # Simplified: if overall pitch sequence has repetition, mark
            # Check if any 2-length interval pattern repeats
            patterns = [tuple(intervals[i:i+2]) for i in range(len(intervals)-1)]
            if len(set(patterns)) < len(patterns):
                # Some pattern repeats
                has_repeated_motif = True

        # Cadential candidate nearby
        has_cadence = any(abs(gap_end_onset - c) <= Fraction(1, 1) for c in cadence_onsets)

        # Score
        score_val = 0.0
        diag_codes: list[str] = []
        if tie_over:
            # Tie-over-boundary negative: never a boundary
            continue
        if has_rest:
            score_val += 0.35
            diag_codes.append("rest_boundary")
        if has_long:
            score_val += 0.25
            diag_codes.append("long_note_boundary")
        if on_downbeat:
            score_val += 0.10
            diag_codes.append("downbeat")
        if has_cadence:
            score_val += 0.15
            diag_codes.append("cadence_supports")
        if has_repeated_motif:
            score_val -= 0.20
            diag_codes.append("repeated_motif_ambiguity")

        # Threshold
        if score_val >= 0.40:
            conf = min(1.0, 0.50 + score_val * 0.5)
            # Ambiguity reduces confidence
            if has_repeated_motif:
                conf = max(0.30, conf - 0.15)
            boundaries.append(PhraseBoundary(onset=gap_end_onset, confidence=round(conf, 4), diagnostics=tuple(Diagnostic(code=c, severity=Severity.INFO, message=c) for c in diag_codes)))
        elif has_repeated_motif and score_val >= 0.20:
            # Ambiguous continuation: still record low confidence boundary for diagnostic
            diagnostics.append(Diagnostic(code="phrase_continuation_ambiguity", severity=Severity.INFO, message=f"onset {gap_end_onset} has repeated motif, ambiguous continuation"))

    # Also consider passage end as boundary if last notes are long or rest at end
    # For clear boundary test, passage ends with long note + rest should yield boundary at end
    # Check end gap: after last onset, does passage end with rest or long note?
    last_onset = onsets[-1] if onsets else None
    if last_onset is not None:
        last_notes = [n for n in resolved if getattr(n, "onset", Fraction(0)) == last_onset]
        has_long_end = any(getattr(n, "duration", Fraction(0)) >= Fraction(2, 1) for n in last_notes)
        has_rest_at_end = any(getattr(r, "onset", Fraction(0)) >= passage_end - Fraction(1, 4) for r in rests) if rests else False
        if (has_long_end or has_rest_at_end) and not any(b.onset == passage_end for b in boundaries):
            # Check tie over end
            tie_over_end = any(getattr(n, "onset", Fraction(0)) < passage_end < getattr(n, "onset", Fraction(0)) + getattr(n, "duration", Fraction(0)) for n in resolved)
            if not tie_over_end:
                # Score for end boundary
                score_val = 0.0
                if has_long_end:
                    score_val += 0.25
                if has_rest_at_end:
                    score_val += 0.35
                if score_val >= 0.40:
                    boundaries.append(PhraseBoundary(onset=passage_end, confidence=round(min(1.0, 0.60+score_val*0.3),4), diagnostics=()))

    # Sort by onset
    boundaries.sort(key=lambda b: b.onset)
    return tuple(boundaries), tuple(diagnostics)


__all__ = ["PhraseBoundary", "PHRASE_METHOD_ID", "PHRASE_METHOD_VERSION", "detect_phrase_boundaries"]
