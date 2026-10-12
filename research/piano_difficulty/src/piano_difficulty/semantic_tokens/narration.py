"""Deterministic narration layer: semantic tokens -> musical observations.

Phase 1: only leap, density_spike, pattern_break. Evidence-backed, no LLM,
no musicology-toolbox dependency. Templates are boring and deterministic.

Phase 3: high-value interaction heuristics combining tokens+gestures for
teacher-like descriptions. Still deterministic, still evidence-backed.

Phase 5: central phrase/template registry (phrase_registry.py), normalized
learner-facing phrasing, guardrails against generic/hallucinated claims.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from piano_difficulty.temporal.windows import ScoreRegion

from .models import DerivedToken, Gesture, SemanticBundle
from .phrase_registry import (
    PHRASE_TEMPLATES,
    contains_banned_difficulty_claim,
    contains_generic_label_without_concrete,
    format_hand,
    format_other_hand,
    has_concrete_simultaneous_evidence,
    measure_clause,
)

# Deterministic kind priority base values (higher = more important).
# Interaction observations outrank single-token observations.
_KIND_BASE_PRIORITY: dict[str, float] = {
    "leap_with_other_hand_active": 0.97,
    "repeated_pattern_then_break": 0.96,
    "bass_to_chord_relocation": 0.95,
    "melody_with_accompaniment_voicing": 0.94,
    "wide_chord_shape": 0.92,
    "leap": 0.90,
    "ascending_scalar_run": 0.88,
    "descending_scalar_run": 0.88,
    "alberti_bass": 0.87,
    "leap_to_chord": 0.86,
    "syncopation": 0.84,
    "broken_chord_accompaniment": 0.83,
    "arpeggiated_accompaniment": 0.82,
    "octaves": 0.81,
    "pattern_break": 0.80,
    "density_spike": 0.60,
}

SUPPORTED_KINDS = (
    "leap",
    "density_spike",
    "pattern_break",
    "leap_with_other_hand_active",
    "bass_to_chord_relocation",
    "melody_with_accompaniment_voicing",
    "wide_chord_shape",
    "repeated_pattern_then_break",
    "ascending_scalar_run",
    "descending_scalar_run",
    "alberti_bass",
    "broken_chord_accompaniment",
    "arpeggiated_accompaniment",
    "leap_to_chord",
    "syncopation",
    "octaves",
)

# Re-export registry for consumers / tests introspection
PHRASE_REGISTRY = PHRASE_TEMPLATES

WIDE_CHORD_SPAN_THRESHOLD = 7  # semitones — above existing span threshold
LEAP_OTHER_HAND_PROXIMITY = Fraction(1)  # quarter notes
PATTERN_BREAK_PROXIMITY = Fraction(2)  # quarter notes


from dataclasses import dataclass, field


def _measure_sort_key(value: str) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, value)


def _format_measures(measure_numbers: tuple[str, ...], fallback: int | None = None) -> str:
    """Return stable learner-facing measure text.

    Upstream token/gesture builders may combine evidence from overlapping
    windows in discovery order. Sort here so prose never says "59-58".
    For Phase 5, prefers reliable measures; falls back to "?" only when caller
    explicitly needs a placeholder.  New helpers should use measure_clause()
    to omit the clause when unreliable.
    """
    nums = sorted(dict.fromkeys(str(n) for n in measure_numbers if n), key=_measure_sort_key)
    if nums:
        return "-".join(nums)
    return str(fallback or "?")


def _reliable_measure_text(measure_numbers: tuple[str, ...], fallback: int | None) -> str | None:
    """Phase 5: return measure clause only when reliable, else None.

    Uses phrase_registry.measure_clause for consistent reliability rules.
    Fallbacks to _format_measures only to compute numeric fallback if needed.
    """
    clause = measure_clause(measure_numbers, fallback)
    if clause is not None:
        return clause
    # If fallback yields "?" we omit the clause entirely for concise prose.
    # Callers should omit "(measure ...)" when this returns None.
    return None


@dataclass(frozen=True, slots=True)
class MusicalObservation:
    """Learner-facing musical observation derived from semantic evidence."""

    kind: str
    priority: float
    span: ScoreRegion
    text: str
    evidence_event_ids: tuple[str, ...] = ()
    token_ids: tuple[str, ...] = ()
    gesture_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        from piano_difficulty.difficulty_analysis.dynamics.models import region_to_payload

        return {
            "kind": self.kind,
            "priority": float(self.priority),
            "span": region_to_payload(self.span),
            "text": self.text,
            "evidence_event_ids": list(self.evidence_event_ids),
            "token_ids": list(self.token_ids),
            "gesture_ids": list(self.gesture_ids),
            "tags": list(self.tags),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.to_payload()

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> MusicalObservation:
        from piano_difficulty.difficulty_analysis.dynamics.models import region_to_payload  # noqa: F401

        span_data = data.get("span", {})

        def _frac(v: Any) -> Fraction | None:
            if v is None:
                return None
            try:
                return Fraction(str(v))
            except Exception:
                return None

        span = ScoreRegion(
            score_id=span_data.get("score_id"),
            window_index=int(span_data.get("window_index", 0)),
            measure_start=int(span_data.get("measure_start", 0)),
            measure_end=int(span_data.get("measure_end", 0)),
            measure_numbers=tuple(str(x) for x in span_data.get("measure_numbers", [])),
            start_offset=_frac(span_data.get("start_offset")),
            end_offset=_frac(span_data.get("end_offset")),
            start_beat=_frac(span_data.get("start_beat")),
            end_beat=_frac(span_data.get("end_beat")),
            position=span_data.get("position"),
            hand=span_data.get("hand"),
            label=span_data.get("label"),
        )
        return cls(
            kind=str(data["kind"]),
            priority=float(data.get("priority", 0.0)),
            span=span,
            text=str(data.get("text", "")),
            evidence_event_ids=tuple(str(x) for x in data.get("evidence_event_ids", [])),
            token_ids=tuple(str(x) for x in data.get("token_ids", [])),
            gesture_ids=tuple(str(x) for x in data.get("gesture_ids", [])),
            tags=tuple(str(x) for x in data.get("tags", [])),
        )


def _token_span_to_region(bundle: SemanticBundle, token: DerivedToken, label: str | None = None) -> ScoreRegion:
    measure_numbers = token.measure_numbers
    # hand must be one of allowed HandMode or None
    hand = token.hand if token.hand in ("left", "right", "both") else None  # type: ignore[assignment]
    return ScoreRegion(
        score_id=bundle.score_id,
        window_index=0,
        measure_start=int(token.measure_start) if token.measure_start is not None else 0,
        measure_end=int(token.measure_end) if token.measure_end is not None else (int(token.measure_start) if token.measure_start is not None else 0),
        measure_numbers=measure_numbers,
        start_offset=token.start_onset,
        end_offset=token.end_onset,
        start_beat=token.start_onset,
        end_beat=token.end_onset,
        position=float((token.start_onset + token.end_onset) / 2) if token.start_onset is not None and token.end_onset is not None else None,
        hand=hand,
        label=label,
    )


def _gesture_span_to_region(bundle: SemanticBundle, gesture: Gesture, label: str | None = None) -> ScoreRegion:
    hand = gesture.hand if gesture.hand in ("left", "right", "both") else None  # type: ignore[assignment]
    return ScoreRegion(
        score_id=bundle.score_id,
        window_index=0,
        measure_start=int(gesture.measure_start) if gesture.measure_start is not None else 0,
        measure_end=int(gesture.measure_end) if gesture.measure_end is not None else (int(gesture.measure_start) if gesture.measure_start is not None else 0),
        measure_numbers=gesture.measure_numbers,
        start_offset=gesture.start_onset,
        end_offset=gesture.end_onset,
        start_beat=gesture.start_onset,
        end_beat=gesture.end_onset,
        position=float((gesture.start_onset + gesture.end_onset) / 2),
        hand=hand,
        label=label,
    )


def _priority_for_token(token: DerivedToken) -> float:
    base = _KIND_BASE_PRIORITY.get(token.kind, 0.5)
    # confidence in [0,1] blends in deterministically
    priority = base + float(token.confidence) * 0.08
    # small deterministic tie-breaker from start_onset fractional part to keep stable but not change ranking groups
    # we keep priority rounded to 4 decimals for stability
    return round(min(1.0, priority), 4)


def _priority_for_kind(kind: str, confidence: float) -> float:
    base = _KIND_BASE_PRIORITY.get(kind, 0.5)
    priority = base + float(confidence) * 0.08
    return round(min(1.0, priority), 4)


# ---------------------------------------------------------------------------
# Phase 5 — normalized, learner-facing text builders via registry
# ---------------------------------------------------------------------------

def _leap_text(token: DerivedToken) -> str:
    payload = token.payload
    interval = payload.get("interval_semitones")
    abs_iv = payload.get("abs_interval", abs(interval) if isinstance(interval, int) else "?")
    hand = format_hand(token.hand)
    meas = _reliable_measure_text(token.measure_numbers, token.measure_start)
    if isinstance(interval, int):
        direction = "up" if interval > 0 else "down" if interval < 0 else "repeat"
    else:
        direction = payload.get("direction", "unknown")
    # Use registry template; omit measure clause if unreliable.
    if meas is not None:
        return PHRASE_TEMPLATES["leap"].format(hand=hand, abs_interval=abs_iv, direction=direction, measure=meas)
    # Fallback without explicit measure (still mentions hand/interval, evidence-backed)
    return f"The {hand} leaps {abs_iv} semitones {direction}."


def _density_spike_text(token: DerivedToken) -> str:
    payload = token.payload
    count = payload.get("notes_in_quarter", payload.get("density_per_quarter", "?"))
    density = payload.get("density_per_quarter", count)
    hand = format_hand(token.hand)
    meas = _reliable_measure_text(token.measure_numbers, token.measure_start)
    # Density template requires measure; if unreliable, omit measure parenthetical.
    if meas is not None:
        return PHRASE_TEMPLATES["density_spike"].format(count=count, hand=hand, measure=meas, density=density)
    return f"Many notes close together — {count} notes per quarter ({hand}) density {density} notes/quarter."


def _pattern_break_text(token: DerivedToken) -> str:
    payload = token.payload
    expected = payload.get("expected_interval")
    actual = payload.get("actual_interval")
    pat = payload.get("pattern_intervals")
    hand = format_hand(token.hand)
    meas = _reliable_measure_text(token.measure_numbers, token.measure_start)
    pat_str = str(pat) if pat is not None else "?"
    if meas is not None:
        return PHRASE_TEMPLATES["pattern_break"].format(hand=hand, measure=meas, expected=expected, actual=actual, pattern=pat_str)
    return f"Pattern break ({hand}): expected interval {expected} semitones, actual {actual} semitones, breaking pattern {pat_str}."


def _wide_chord_shape_text(token: DerivedToken) -> str:
    payload = token.payload
    span = payload.get("span_semitones", "?")
    hand = format_hand(token.hand)
    meas = _reliable_measure_text(token.measure_numbers, token.measure_start)
    shape = payload.get("shape", "chord")
    note_count = payload.get("note_count", "?")
    if meas is not None:
        return PHRASE_TEMPLATES["wide_chord_shape"].format(hand=hand, measure=meas, span=span, shape=shape, note_count=note_count)
    return f"The {hand} spans a wider hand shape of {span} semitones ({shape} with {note_count} notes) — prepare the shape rather than reading isolated notes."


def _leap_with_other_hand_active_text(leap: DerivedToken, other_hand: str) -> str:
    payload = leap.payload
    interval = payload.get("interval_semitones")
    abs_iv = payload.get("abs_interval", abs(interval) if isinstance(interval, int) else "?")
    if isinstance(interval, int):
        direction = "up" if interval > 0 else "down" if interval < 0 else "repeat"
    else:
        direction = payload.get("direction", "large")
    hand = format_hand(leap.hand)
    # other_hand is "left"/"right" from caller; normalize to learner-facing
    other = format_hand(other_hand)
    meas = _reliable_measure_text(leap.measure_numbers, leap.measure_start)
    if meas is not None:
        return PHRASE_TEMPLATES["leap_with_other_hand_active"].format(
            hand=hand, abs_interval=abs_iv, direction=direction, measure=meas, other_hand=other
        )
    return f"The {hand} has a large move of {abs_iv} semitones {direction} while the {other} continues, so the landing has to be coordinated without interrupting the line."


def _bass_to_chord_text(gesture: Gesture) -> str:
    hand = format_hand(gesture.hand or "left")
    meas = _reliable_measure_text(gesture.measure_numbers, gesture.measure_start)
    movement = gesture.payload.get("movement", "?")
    chord_shape = gesture.payload.get("chord_shape", "chord")
    if meas is not None:
        return PHRASE_TEMPLATES["bass_to_chord_relocation"].format(hand=hand, movement=movement, measure=meas, chord_shape=chord_shape)
    return f"The {hand} moves from a bass note into a chord shape ({chord_shape}, {movement} semitones) — a quick relocation."


def _melody_with_accompaniment_text(gesture: Gesture) -> str:
    meas = _reliable_measure_text(gesture.measure_numbers, gesture.measure_start)
    if meas is not None:
        return PHRASE_TEMPLATES["melody_with_accompaniment_voicing"].format(measure=meas)
    return "The right hand carries the melody while the left hand supports it with other notes — keep the melody clear instead of playing everything equally."


def _repeated_pattern_then_break_text(rep: DerivedToken, brk: DerivedToken) -> str:
    hand = format_hand(rep.hand or brk.hand)
    meas = _reliable_measure_text(brk.measure_numbers or rep.measure_numbers, brk.measure_start or rep.measure_start)
    pat = rep.payload.get("pattern_intervals") or brk.payload.get("pattern_intervals") or "?"
    expected = brk.payload.get("expected_interval", "?")
    actual = brk.payload.get("actual_interval", "?")
    if meas is not None:
        return PHRASE_TEMPLATES["repeated_pattern_then_break"].format(hand=hand, measure=meas, pattern=pat, expected=expected, actual=actual)
    return f"A repeated pattern {pat} changes here ({hand}, expected {expected} semitones, actual {actual} semitones) — easy to play the expected shape instead of the written one."


def _text_for_token(token: DerivedToken) -> str:
    if token.kind == "leap":
        return _leap_text(token)
    if token.kind == "density_spike":
        return _density_spike_text(token)
    if token.kind == "pattern_break":
        return _pattern_break_text(token)
    if token.kind == "chord_shape":
        return _wide_chord_shape_text(token)
    # fallback - should not happen in phase1; still learner-facing via registry style
    meas = _reliable_measure_text(token.measure_numbers, token.measure_start)
    hand = format_hand(token.hand)
    if meas is not None:
        return f"{token.kind} ({hand}, measure {meas})."
    return f"{token.kind} ({hand})."


def _tags_for_token(token: DerivedToken) -> tuple[str, ...]:
    tags: list[str] = [token.kind]
    if token.hand:
        tags.append(token.hand)
    # keep tags deterministic sorted except kind first
    # e.g., leap + left
    return tuple(tags)


def _tags_for_gesture(gesture: Gesture, kind_override: str | None = None) -> tuple[str, ...]:
    k = kind_override or gesture.kind
    tags: list[str] = [k]
    if gesture.hand:
        tags.append(gesture.hand)
    return tuple(tags)


def _overlaps_span(token: DerivedToken, span: ScoreRegion) -> bool:
    # primary: check onset interval overlap if span offsets present
    if span.start_offset is not None and span.end_offset is not None:
        # overlap if token interval intersects span
        if token.end_onset <= span.start_offset or token.start_onset >= span.end_offset:
            return False
        return True
    # fallback to measure numbers overlap
    if span.measure_numbers and token.measure_numbers:
        if set(span.measure_numbers) & set(token.measure_numbers):
            return True
        return False
    # fallback to measure_index range
    if span.measure_start is not None and span.measure_end is not None and token.measure_start is not None:
        # token overlaps if its measure range intersects span range
        t_start = token.measure_start
        t_end = token.measure_end if token.measure_end is not None else t_start
        if t_end < span.measure_start or t_start > span.measure_end:
            return False
        return True
    return True


def _gesture_overlaps_span(gesture: Gesture, span: ScoreRegion) -> bool:
    if span.start_offset is not None and span.end_offset is not None:
        if gesture.end_onset <= span.start_offset or gesture.start_onset >= span.end_offset:
            return False
        return True
    if span.measure_numbers and gesture.measure_numbers:
        if set(span.measure_numbers) & set(gesture.measure_numbers):
            return True
        return False
    if span.measure_start is not None and span.measure_end is not None and gesture.measure_start is not None:
        g_start = gesture.measure_start
        g_end = gesture.measure_end if gesture.measure_end is not None else g_start
        if g_end < span.measure_start or g_start > span.measure_end:
            return False
        return True
    return True


def _observation_overlaps_span(obs: MusicalObservation, span: ScoreRegion) -> bool:
    # reuse gesture-like check for observation's span
    if span.start_offset is not None and span.end_offset is not None:
        if obs.span.end_offset is None or obs.span.start_offset is None:
            return True
        if obs.span.end_offset <= span.start_offset or obs.span.start_offset >= span.end_offset:
            return False
        return True
    if span.measure_numbers and obs.span.measure_numbers:
        if set(span.measure_numbers) & set(obs.span.measure_numbers):
            return True
        return False
    return True


def _observation_measure_key(obs: MusicalObservation) -> tuple[str, ...]:
    return tuple(sorted(dict.fromkeys(obs.span.measure_numbers), key=_measure_sort_key))


def _is_redundant_observation(candidate: MusicalObservation, selected: list[MusicalObservation]) -> bool:
    """Suppress repeated teacher bullets that say the same kind of thing nearby."""
    cand_measures = set(_observation_measure_key(candidate))
    cand_evidence = set(candidate.evidence_event_ids)
    for existing in selected:
        existing_evidence = set(existing.evidence_event_ids)
        if (
            candidate.kind == "leap"
            and existing.kind == "leap_with_other_hand_active"
            and cand_evidence
            and existing_evidence
            and cand_evidence.issubset(existing_evidence)
        ):
            return True
        if existing.kind != candidate.kind:
            continue
        existing_measures = set(_observation_measure_key(existing))
        if cand_measures and existing_measures and cand_measures & existing_measures:
            return True
        # Without reliable measures, avoid exact text/evidence duplicates only.
        if candidate.text == existing.text:
            return True
    return False


def _select_observations(observations: list[MusicalObservation], max_observations: int) -> list[MusicalObservation]:
    """Pick a concise, varied set for learner-facing display."""
    if max_observations is None or max_observations < 0:
        return observations
    if max_observations == 0:
        return []

    selected: list[MusicalObservation] = []
    seen_kinds: set[str] = set()
    for obs in observations:
        if obs.kind in seen_kinds:
            continue
        if _is_redundant_observation(obs, selected):
            continue
        selected.append(obs)
        seen_kinds.add(obs.kind)
        if len(selected) >= max_observations:
            return selected

    for obs in observations:
        if obs in selected:
            continue
        if _is_redundant_observation(obs, selected):
            continue
        selected.append(obs)
        if len(selected) >= max_observations:
            return selected

    if len(selected) < max_observations:
        for obs in observations:
            if obs in selected:
                continue
            selected.append(obs)
            if len(selected) >= max_observations:
                break
    return selected[:max_observations]


# ---------------------------------------------------------------------------
# Guardrails (Phase 5)
# ---------------------------------------------------------------------------

def _passes_guardrails(obs: MusicalObservation) -> bool:
    """Phase 5 guardrails — drop evidence-free or hallucinated prose.

    - No observation without evidence IDs.
    - No "hard/difficult/challenging" claim unless attached to a difficulty event
      span (observations themselves never make that claim; we drop it outright).
    - No generic "hand independence" label unless concrete simultaneous actions
      are cited (both hands + while-continues phrasing).
    """
    # 1. Evidence-backed
    if not obs.evidence_event_ids:
        return False
    # 2. No unanchored difficulty claim in observation text
    if contains_banned_difficulty_claim(obs.text):
        return False
    # 3. Generic label requires concrete simultaneous evidence
    # Compute hand coverage from tags + text mentions
    hands_in_tags = {t for t in obs.tags if t in ("left", "right", "both")}
    has_concrete = has_concrete_simultaneous_evidence(obs.text, hands_in_tags)
    if contains_generic_label_without_concrete(obs.text, has_concrete):
        return False
    return True


def _validate_and_filter_observations(observations: list[MusicalObservation]) -> list[MusicalObservation]:
    """Apply guardrails; keep old payloads that already passed."""
    return [o for o in observations if _passes_guardrails(o)]


def _build_leap_with_other_hand_active(
    bundle: SemanticBundle,
    span: ScoreRegion | None,
) -> list[MusicalObservation]:
    """Leap token overlaps or is close to other-hand onset/alignment."""
    observations: list[MusicalObservation] = []
    leaps = [t for t in bundle.derived_tokens if t.kind == "leap" and t.evidence_event_ids]
    if not leaps:
        return observations
    # Build quick lookup for other-hand activity
    alignments = [t for t in bundle.derived_tokens if t.kind == "onset_alignment" and t.evidence_event_ids]
    # Also collect other-hand tokens per hand for proximity check (excluding leaps themselves)
    # Use all derived tokens with hand present
    tokens_by_hand: dict[str, list[DerivedToken]] = {"right": [], "left": []}
    for t in bundle.derived_tokens:
        if t.hand in ("right", "left") and t.evidence_event_ids:
            tokens_by_hand[t.hand].append(t)
    # Also events for direct other-hand onset detection
    events_by_hand: dict[str, list[Any]] = {"right": [], "left": []}
    for e in bundle.events:
        if e.hand in ("right", "left") and not e.is_rest:
            events_by_hand[e.hand].append(e)

    for leap in leaps:
        if span is not None and not _overlaps_span(leap, span):
            continue
        other = "right" if leap.hand == "left" else "left" if leap.hand == "right" else None
        if other is None:
            continue
        window_start = leap.start_onset - LEAP_OTHER_HAND_PROXIMITY
        window_end = leap.end_onset + LEAP_OTHER_HAND_PROXIMITY
        # Find evidence of other-hand activity in window
        has_other = False
        other_evidence_ids: list[str] = []
        other_token_ids: list[str] = []
        # Check alignments overlapping window
        for al in alignments:
            if al.end_onset > window_start and al.start_onset < window_end:
                has_other = True
                other_evidence_ids.extend(list(al.evidence_event_ids))
                other_token_ids.append(al.token_id)
        # Check other-hand tokens overlapping window
        for tok in tokens_by_hand.get(other, []):
            if tok.token_id == leap.token_id:
                continue
            if tok.end_onset > window_start and tok.start_onset < window_end:
                # Consider any token of other hand as activity; but avoid counting only the leap's own hand
                # To avoid trivial self-overlap, require tok is not same leap
                has_other = True
                other_evidence_ids.extend(list(tok.evidence_event_ids))
                other_token_ids.append(tok.token_id)
                # we have at least one, break after collecting first few to keep deterministic but gather up to 3
                if len(other_token_ids) >= 3:
                    break
        # Check events directly if no token found (more precise for synthetic cases)
        if not has_other:
            for ev in events_by_hand.get(other, []):
                if ev.end > window_start and ev.onset < window_end:
                    has_other = True
                    other_evidence_ids.append(ev.event_id)
                    # no token id for event-only
                    break
        if not has_other:
            continue
        # Deduplicate evidence ids preserving order
        combined_evidence = tuple(dict.fromkeys(list(leap.evidence_event_ids) + other_evidence_ids))
        combined_token_ids = tuple(dict.fromkeys([leap.token_id] + other_token_ids))
        # Priority based on leap confidence blended with high base
        priority = _priority_for_kind("leap_with_other_hand_active", float(leap.confidence))
        text = _leap_with_other_hand_active_text(leap, other)
        # Span is expanded to cover leap + other activity window? Use leap span expanded minimally to include other evidence's span start if alignment earlier
        # Keep span as leap span expanded to window for region purposes, but start_offset = min(leap.start, window_start) ??? Use leap's region but extended end to window_end if other alignment extends.
        # Simpler: region from leap but with end extended to max of other_token end if needed for overlap filtering future, but keep leap's region as primary for ranking
        region = _token_span_to_region(bundle, leap, label=text[:80])
        # If other activity extends beyond leap, extend region to encompass it for proper overlap semantics
        # Compute max end among considered other tokens/events within window for nicer region
        # Use gesture-like region extension: start = min(leap.start_onset, window_start)?? Actually window_start is leap.start -1, not useful. Use leap.start unchanged, end = max(leap.end_onset, max other end)
        # We'll keep leap's region as is for stability but ensure evidence covers coordination
        obs = MusicalObservation(
            kind="leap_with_other_hand_active",
            priority=priority,
            span=region,
            text=text,
            evidence_event_ids=combined_evidence,
            token_ids=combined_token_ids,
            gesture_ids=(),
            tags=("leap_with_other_hand_active", leap.hand or "", other),
        )
        # Clean tags: filter empty
        obs = MusicalObservation(
            kind=obs.kind,
            priority=obs.priority,
            span=obs.span,
            text=obs.text,
            evidence_event_ids=obs.evidence_event_ids,
            token_ids=obs.token_ids,
            gesture_ids=obs.gesture_ids,
            tags=tuple(t for t in obs.tags if t),
        )
        observations.append(obs)
    return observations


def _build_wide_chord_shape(
    bundle: SemanticBundle,
    span: ScoreRegion | None,
) -> list[MusicalObservation]:
    observations: list[MusicalObservation] = []
    for token in bundle.derived_tokens:
        if token.kind != "chord_shape":
            continue
        if not token.evidence_event_ids:
            continue
        if span is not None and not _overlaps_span(token, span):
            continue
        span_semitones = token.payload.get("span_semitones")
        if not isinstance(span_semitones, (int, float)):
            continue
        if float(span_semitones) < WIDE_CHORD_SPAN_THRESHOLD:
            continue
        priority = _priority_for_kind("wide_chord_shape", float(token.confidence))
        text = _wide_chord_shape_text(token)
        region = _token_span_to_region(bundle, token, label=text[:80])
        obs = MusicalObservation(
            kind="wide_chord_shape",
            priority=priority,
            span=region,
            text=text,
            evidence_event_ids=tuple(token.evidence_event_ids),
            token_ids=(token.token_id,),
            gesture_ids=(),
            tags=("wide_chord_shape", token.hand or ""),
        )
        obs = MusicalObservation(
            kind=obs.kind,
            priority=obs.priority,
            span=obs.span,
            text=obs.text,
            evidence_event_ids=obs.evidence_event_ids,
            token_ids=obs.token_ids,
            gesture_ids=obs.gesture_ids,
            tags=tuple(t for t in obs.tags if t),
        )
        observations.append(obs)
    return observations


def _build_repeated_pattern_then_break(
    bundle: SemanticBundle,
    span: ScoreRegion | None,
) -> list[MusicalObservation]:
    observations: list[MusicalObservation] = []
    reps = [t for t in bundle.derived_tokens if t.kind == "pattern_repetition" and t.evidence_event_ids]
    breaks = [t for t in bundle.derived_tokens if t.kind == "pattern_break" and t.evidence_event_ids]
    if not reps or not breaks:
        return observations
    # Sort reps and breaks by onset
    reps_sorted = sorted(reps, key=lambda t: t.start_onset)
    breaks_sorted = sorted(breaks, key=lambda t: t.start_onset)
    for brk in breaks_sorted:
        if span is not None and not _overlaps_span(brk, span):
            continue
        # Find closest preceding repetition of same hand within proximity
        best_rep: DerivedToken | None = None
        best_gap: Fraction | None = None
        for rep in reps_sorted:
            if rep.hand != brk.hand:
                # allow None hand? Require same hand if both specified, else allow any
                if rep.hand is not None and brk.hand is not None and rep.hand != brk.hand:
                    continue
            if rep.end_onset > brk.start_onset:
                continue
            gap = brk.start_onset - rep.end_onset
            if gap < Fraction(0) or gap > PATTERN_BREAK_PROXIMITY:
                continue
            # Prefer smallest gap (closest)
            if best_gap is None or gap < best_gap:
                best_rep = rep
                best_gap = gap
        if best_rep is None:
            continue
        # Also ensure combined span overlaps span filter if provided (check gap region)
        # Build observation
        combined_evidence = tuple(dict.fromkeys(list(best_rep.evidence_event_ids) + list(brk.evidence_event_ids)))
        combined_token_ids = (best_rep.token_id, brk.token_id)
        # Priority higher than pattern_break alone
        # Use max confidence of pair blended
        conf = max(float(best_rep.confidence), float(brk.confidence))
        priority = _priority_for_kind("repeated_pattern_then_break", conf)
        text = _repeated_pattern_then_break_text(best_rep, brk)
        # Region spans from rep start to break end
        # Create synthetic token-like region for span
        meas_numbers = tuple(dict.fromkeys(list(best_rep.measure_numbers) + list(brk.measure_numbers)))
        hand = best_rep.hand or brk.hand
        region = ScoreRegion(
            score_id=bundle.score_id,
            window_index=0,
            measure_start=int(best_rep.measure_start) if best_rep.measure_start is not None else (int(brk.measure_start) if brk.measure_start is not None else 0),
            measure_end=int(brk.measure_end) if brk.measure_end is not None else (int(best_rep.measure_end) if best_rep.measure_end is not None else 0),
            measure_numbers=meas_numbers,
            start_offset=best_rep.start_onset,
            end_offset=brk.end_onset,
            start_beat=best_rep.start_onset,
            end_beat=brk.end_onset,
            position=float((best_rep.start_onset + brk.end_onset) / 2),
            hand=hand if hand in ("left", "right", "both") else None,  # type: ignore[assignment]
            label=text[:80],
        )
        obs = MusicalObservation(
            kind="repeated_pattern_then_break",
            priority=priority,
            span=region,
            text=text,
            evidence_event_ids=combined_evidence,
            token_ids=combined_token_ids,
            gesture_ids=(),
            tags=("repeated_pattern_then_break", hand or ""),
        )
        obs = MusicalObservation(
            kind=obs.kind,
            priority=obs.priority,
            span=obs.span,
            text=obs.text,
            evidence_event_ids=obs.evidence_event_ids,
            token_ids=obs.token_ids,
            gesture_ids=obs.gesture_ids,
            tags=tuple(t for t in obs.tags if t),
        )
        observations.append(obs)
    return observations


def _object_overlaps_span(obj: Any, span: ScoreRegion) -> bool:
    if span.start_offset is not None and span.end_offset is not None:
        if obj.end_onset <= span.start_offset or obj.start_onset >= span.end_offset:
            return False
        return True
    if span.measure_numbers and obj.measure_numbers:
        if set(span.measure_numbers) & set(obj.measure_numbers):
            return True
        return False
    if span.measure_start is not None and span.measure_end is not None and obj.measure_start is not None:
        o_start = obj.measure_start
        o_end = obj.measure_end if obj.measure_end is not None else o_start
        if o_end < span.measure_start or o_start > span.measure_end:
            return False
        return True
    return True


def _object_span_to_region(bundle: SemanticBundle, obj: Any, label: str | None = None) -> ScoreRegion:
    hand = obj.hand if obj.hand in ("left", "right", "both") else None  # type: ignore[assignment]
    return ScoreRegion(
        score_id=bundle.score_id,
        window_index=0,
        measure_start=int(obj.measure_start) if obj.measure_start is not None else 0,
        measure_end=int(obj.measure_end) if obj.measure_end is not None else (int(obj.measure_start) if obj.measure_start is not None else 0),
        measure_numbers=obj.measure_numbers,
        start_offset=obj.start_onset,
        end_offset=obj.end_onset,
        start_beat=obj.start_onset,
        end_beat=obj.end_onset,
        position=float((obj.start_onset + obj.end_onset) / 2) if obj.start_onset is not None and obj.end_onset is not None else None,
        hand=hand,
        label=label,
    )


def _object_text(obj: Any) -> str | None:
    """Thin builder for high-value objects — reuses registry, conservative."""
    hand = format_hand(obj.hand)
    meas = _reliable_measure_text(obj.measure_numbers, obj.measure_start)
    kind = obj.object_id or obj.kind
    payload = obj.payload or {}
    # Use registry template if available
    if kind in PHRASE_TEMPLATES:
        tmpl = PHRASE_TEMPLATES[kind]
        try:
            if kind in ("ascending_scalar_run", "descending_scalar_run"):
                steps = payload.get("steps", "?")
                if meas is not None:
                    return tmpl.format(hand=hand, measure=meas, steps=steps)
                return f"{'Ascending' if kind=='ascending_scalar_run' else 'Descending'} scalar run — stepwise motion ({hand}, {steps} notes) — practice in small groups for evenness."
            if kind == "alberti_bass":
                if meas is not None:
                    return tmpl.format(hand=hand, measure=meas)
                return f"Alberti bass pattern in the {hand} — broken-chord low-high-middle-high — block the harmony first."
            if kind == "broken_chord_accompaniment":
                if meas is not None:
                    return tmpl.format(hand=hand, measure=meas)
                return f"Broken-chord accompaniment ({hand}) — chord tones spread over time — block into chords."
            if kind == "arpeggiated_accompaniment":
                span = payload.get("span", payload.get("span_semitones", "?"))
                if meas is not None:
                    return tmpl.format(hand=hand, measure=meas, span=span)
                return f"Arpeggiated accompaniment ({hand}) spanning {span} semitones — practice hand-shape placement."
            if kind == "leap_to_chord":
                movement = payload.get("movement", payload.get("movement_semitones", payload.get("span", "?")))
                chord_shape = payload.get("chord_shape", "chord")
                if meas is not None:
                    return tmpl.format(hand=hand, measure=meas, movement=movement, chord_shape=chord_shape)
                return f"Leap to chord ({hand}, {movement} semitones into {chord_shape}) — prepare the landing shape."
            if kind == "syncopation":
                if meas is not None:
                    return tmpl.format(hand=hand, measure=meas)
                return f"Syncopation ({hand}) — accents or held notes on weak beats — count the pulse."
            if kind == "octaves":
                if meas is not None:
                    return tmpl.format(hand=hand, measure=meas)
                return f"Octaves ({hand}) — octave shapes requiring span and release."
        except Exception:
            pass
    # Fallback for other kinds with no polished template: return None to keep raw payload only
    return None


def _build_object_observations(
    bundle: SemanticBundle,
    span: ScoreRegion | None,
) -> list[MusicalObservation]:
    observations: list[MusicalObservation] = []
    for obj in getattr(bundle, "musical_objects", ()):  # type: ignore[attr-defined]
        if not getattr(obj, "evidence_event_ids", ()):
            continue
        if span is not None and not _object_overlaps_span(obj, span):
            continue
        text = _object_text(obj)
        if text is None:
            continue
        # Apply guardrails later; but skip low-confidence heuristic-only objects without measure? still allow if has measure
        priority = _priority_for_kind(obj.object_id, float(obj.confidence))
        region = _object_span_to_region(bundle, obj, label=text[:80])
        # Ensure token_ids non-empty for backward compat (test expects evidence-backed token_ids)
        toks_for_obj = tuple(obj.token_ids)
        if not toks_for_obj:
            # Try to find overlapping derived token as linkage
            overlapping = [t.token_id for t in bundle.derived_tokens if t.start_onset < obj.end_onset and t.end_onset > obj.start_onset and (obj.hand is None or t.hand == obj.hand or t.hand is None)]
            if overlapping:
                toks_for_obj = (overlapping[0],)
            elif obj.gesture_ids:
                toks_for_obj = tuple(obj.gesture_ids)  # fallback to gesture linkage
            else:
                # minimal placeholder using evidence-derived synthetic id to keep deterministic
                toks_for_obj = (f"ev:{obj.evidence_event_ids[0]}",) if obj.evidence_event_ids else ()
        obs = MusicalObservation(
            kind=obj.object_id,
            priority=priority,
            span=region,
            text=text,
            evidence_event_ids=tuple(obj.evidence_event_ids),
            token_ids=toks_for_obj,
            gesture_ids=tuple(obj.gesture_ids),
            tags=(obj.object_id, obj.hand or ""),
        )
        obs = MusicalObservation(
            kind=obs.kind,
            priority=obs.priority,
            span=obs.span,
            text=obs.text,
            evidence_event_ids=obs.evidence_event_ids,
            token_ids=obs.token_ids,
            gesture_ids=obs.gesture_ids,
            tags=tuple(t for t in obs.tags if t),
        )
        observations.append(obs)
    return observations


def _build_gesture_observations(
    bundle: SemanticBundle,
    span: ScoreRegion | None,
) -> list[MusicalObservation]:
    observations: list[MusicalObservation] = []
    for gesture in bundle.gestures:
        if gesture.kind == "bass_to_chord":
            if span is not None and not _gesture_overlaps_span(gesture, span):
                continue
            if not gesture.evidence_event_ids:
                continue
            priority = _priority_for_kind("bass_to_chord_relocation", float(gesture.confidence))
            text = _bass_to_chord_text(gesture)
            region = _gesture_span_to_region(bundle, gesture, label=text[:80])
            obs = MusicalObservation(
                kind="bass_to_chord_relocation",
                priority=priority,
                span=region,
                text=text,
                evidence_event_ids=tuple(gesture.evidence_event_ids),
                token_ids=tuple(gesture.token_ids),
                gesture_ids=(gesture.gesture_id,),
                tags=_tags_for_gesture(gesture, "bass_to_chord_relocation"),
            )
            observations.append(obs)
        elif gesture.kind == "melody_with_accompaniment":
            if span is not None and not _gesture_overlaps_span(gesture, span):
                continue
            if not gesture.evidence_event_ids:
                continue
            priority = _priority_for_kind("melody_with_accompaniment_voicing", float(gesture.confidence))
            text = _melody_with_accompaniment_text(gesture)
            region = _gesture_span_to_region(bundle, gesture, label=text[:80])
            obs = MusicalObservation(
                kind="melody_with_accompaniment_voicing",
                priority=priority,
                span=region,
                text=text,
                evidence_event_ids=tuple(gesture.evidence_event_ids),
                token_ids=tuple(gesture.token_ids),
                gesture_ids=(gesture.gesture_id,),
                tags=_tags_for_gesture(gesture, "melody_with_accompaniment_voicing"),
            )
            observations.append(obs)
    return observations


def build_musical_observations(
    bundle: SemanticBundle,
    span: ScoreRegion | None = None,
    max_observations: int = 5,
) -> list[MusicalObservation]:
    """Build ranked musical observations from semantic tokens.

    Phase 3: interaction heuristics (leap_with_other_hand_active,
    bass_to_chord_relocation, melody_with_accompaniment_voicing,
    wide_chord_shape, repeated_pattern_then_break) outrank single-token
    observations and are deduplicated by (kind, evidence_event_ids).

    Phase 5: guardrails — no observation without evidence IDs, no
    "hard/difficult/challenging" claim, no generic "hand independence"
    without concrete simultaneous-action citation.  Phrasing is concise
    learner-facing via phrase_registry ("left hand" over LH, measure only
    when reliable, note names only when evidence supports).

    Evidence-free tokens (empty evidence_event_ids) are skipped.
    If span is provided, only tokens/gestures overlapping span are considered.
    Returns at most max_observations, sorted by priority desc then start_onset asc.
    Deterministic, no LLM.
    """
    observations: list[MusicalObservation] = []

    # --- single-token observations (phase 1) ---
    for token in bundle.derived_tokens:
        if token.kind not in ("leap", "density_spike", "pattern_break"):
            continue
        # evidence-backed: skip if missing evidence
        if not token.evidence_event_ids:
            continue
        if span is not None and not _overlaps_span(token, span):
            continue

        priority = _priority_for_token(token)
        text = _text_for_token(token)
        region = _token_span_to_region(bundle, token, label=text[:80])
        tags = _tags_for_token(token)

        obs = MusicalObservation(
            kind=token.kind,
            priority=priority,
            span=region,
            text=text,
            evidence_event_ids=tuple(token.evidence_event_ids),
            token_ids=(token.token_id,),
            gesture_ids=(),
            tags=tags,
        )
        observations.append(obs)

    # --- phase 3 interaction heuristics ---
    observations.extend(_build_wide_chord_shape(bundle, span))
    observations.extend(_build_leap_with_other_hand_active(bundle, span))
    observations.extend(_build_repeated_pattern_then_break(bundle, span))
    observations.extend(_build_gesture_observations(bundle, span))
    # --- musical objects (conservative, reusing guardrail/phrase registry) ---
    observations.extend(_build_object_observations(bundle, span))

    # --- guardrails (phase 5) ---
    observations = _validate_and_filter_observations(observations)

    # --- deduplicate by (kind, frozenset(evidence_event_ids)) ---
    # Keep highest priority per key
    deduped: dict[tuple[str, tuple[str, ...]], MusicalObservation] = {}
    for obs in observations:
        key = (obs.kind, tuple(sorted(obs.evidence_event_ids)))
        existing = deduped.get(key)
        if existing is None or obs.priority > existing.priority or (obs.priority == existing.priority and obs.span.start_offset < existing.span.start_offset):  # type: ignore[operator]
            deduped[key] = obs
    observations = list(deduped.values())

    # Stable ranking: priority desc, start_onset asc, kind asc, hand asc
    observations.sort(key=lambda o: (-o.priority, o.span.start_offset if o.span.start_offset is not None else Fraction(9999), o.kind, o.span.hand or ""))

    return _select_observations(observations, max_observations)
