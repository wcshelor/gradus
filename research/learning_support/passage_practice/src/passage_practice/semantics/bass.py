"""Bass-anchor detector v1 — S3.3.

Heuristic, deterministic. Identifies likely harmonic bass using lowest
material, duration, metric placement, recurrence, and pitch-class stability.

Design refs:
- S2.8 salience_view, S2.7 texture_grid
- S1.5 confidence heuristic
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.semantics.confidence import check_confidence
from passage_practice.semantics.contracts import SemanticHypothesis
from passage_practice.semantics.registry import BaseDetector, DetectorSpec

SPEC = DetectorSpec(
    detector_id="bass_anchor.v1",
    detector_version="v1",
    hypothesis_types=("role.bass",),
    required_views=("salience_view",),
    optional_views=("texture_grid", "rhythm_grid"),
    supported_subset="low-voice anchor via register, duration, metric, recurrence, pitch-class stability",
    known_limitations=(
        "slur evidence unavailable",
        "no learned ranking",
        "melodic left-hand may be lowest without being harmonic anchor",
    ),
)


def _pitch_range(events: list[Any]) -> tuple[int, int]:
    mids = [e.pitch_midi for e in events]
    return (min(mids), max(mids)) if mids else (0, 0)


def _lowest_per_onset(events: list[Any]) -> dict[Fraction, int]:
    """Min pitch per onset."""
    per_onset: dict[Fraction, int] = {}
    for e in events:
        onset = getattr(e, "onset", Fraction(0))
        midi = getattr(e, "pitch_midi", 0)
        if onset not in per_onset or midi < per_onset[onset]:
            per_onset[onset] = midi
    return per_onset


class BassAnchorDetector(BaseDetector):
    def __init__(self, spec: DetectorSpec = SPEC) -> None:
        super().__init__(spec)

    def detect(
        self,
        passage: Any,
        views: dict[str, Any],
        observations: dict[str, Any],
        *,
        investigation: Any | None = None,
        score: Any | None = None,
    ) -> tuple[tuple[SemanticHypothesis, ...], tuple[Diagnostic, ...]]:
        missing = self._missing_required_diagnostics(views)
        if missing is not None:
            return (), missing

        salience = views.get("salience_view")
        texture = views.get("texture_grid")
        if salience is None:
            return (), (
                Diagnostic(code="missing_required_view", severity=Severity.WARNING, message="salience_view required"),
            )
        events: list[Any] = list(getattr(salience, "events", ()))
        if not events:
            return (), (Diagnostic(code="no_salience_events", severity=Severity.INFO, message="no events"),)

        diag_buf: list[Diagnostic] = []
        for vd in getattr(salience, "diagnostics", ()):
            if getattr(vd, "code", "") in ("slur_evidence_unavailable", "pattern_exclusion_not_available"):
                diag_buf.append(vd)

        min_midi, max_midi = _pitch_range(events)
        midi_range = max_midi - min_midi if max_midi != min_midi else 1
        lowest_per_onset = _lowest_per_onset(events)

        # Pitch-class recurrence
        pc_counts = Counter(getattr(e, "pitch_midi", 0) % 12 for e in events)
        # For bass, stability means repeated pitch class (pedal) or stepwise walking with low register
        hand_longest: dict[str, Fraction] = {}
        for e in events:
            h = getattr(e, "hand", None)
            if h is None:
                continue
            dur = getattr(e, "duration", Fraction(0))
            if h not in hand_longest or dur > hand_longest[h]:
                hand_longest[h] = dur

        scored: list[tuple[Any, float, list[str], list[str]]] = []
        for e in events:
            score_val = 0.0
            satisfied: list[str] = []
            contradictory: list[str] = []

            onset = getattr(e, "onset", Fraction(0))
            pitch = getattr(e, "pitch_midi", 0)
            is_lowest = pitch == lowest_per_onset.get(onset, pitch)
            if is_lowest:
                score_val += 0.35
                satisfied.append("lowest_voice")
            else:
                contradictory.append("not_lowest")

            if getattr(e, "is_longest_in_passage", False):
                score_val += 0.20
                satisfied.append("longest_duration")
            else:
                h = getattr(e, "hand", None)
                if h is not None and getattr(e, "duration", Fraction(0)) == hand_longest.get(h):
                    score_val += 0.10
                    satisfied.append("hand_longest_duration")

            on_beat = getattr(e, "on_beat", None)
            if on_beat is True:
                score_val += 0.12
                satisfied.append("on_beat")
            elif on_beat is False:
                score_val -= 0.05
                contradictory.append("off_beat")

            # Left hand is typical bass register, but not exclusive
            if getattr(e, "hand", None) == "left":
                score_val += 0.08
                satisfied.append("left_hand")
            elif getattr(e, "hand", None) == "right":
                contradictory.append("right_hand_not_typical_bass")

            # Low register: lower pitch higher score (inverse of melody)
            rel_low = (max_midi - pitch) / midi_range
            score_val += rel_low * 0.07
            if rel_low > 0.7:
                satisfied.append("low_register")

            # Recurrence / pitch-class stability
            pc = pitch % 12
            if pc_counts[pc] >= 2:
                score_val += 0.10
                satisfied.append("pitch_class_recurrence")
            else:
                contradictory.append("no_pitch_class_recurrence")

            # Duration relative to median: longer than median suggests anchor
            # Median duration
            # (computed once, but for per-event we can check)
            # We will compute median later; for now just use is_longest

            # Texture: if event is part of chord and not lowest, penalize (inner chord tone not bass)
            if texture is not None:
                # Find slice for onset
                sl = None
                for s in getattr(texture, "slices", ()):
                    if getattr(s, "onset", None) == onset:
                        sl = s
                        break
                if sl is not None:
                    if getattr(sl, "chord_size", 1) > 1 and not is_lowest:
                        score_val -= 0.12
                        contradictory.append("inner_chord_tone_not_bass")

            if score_val < 0:
                score_val = 0.0
            if score_val > 1:
                score_val = 1.0
            scored.append((e, score_val, satisfied, contradictory))

        # Median duration for additional longest check
        durs = sorted([getattr(e, "duration", Fraction(0)) for e in events])
        median_dur = durs[len(durs)//2] if durs else Fraction(0)
        # Boost events with duration >= median
        for i, (e, s, sat, con) in enumerate(scored):
            if getattr(e, "duration", Fraction(0)) >= median_dur and "longest_duration" not in sat and "hand_longest_duration" not in sat:
                # slight boost for dur >= median
                ns = min(1.0, s + 0.04)
                if ns != s:
                    sat = sat + ["median_or_longer_duration"]
                scored[i] = (e, ns, sat, con)

        threshold = 0.45
        candidates = [(e, s, sat, con) for e, s, sat, con in scored if s >= threshold]
        if not candidates:
            # Try lower threshold for walking bass
            threshold = 0.35
            candidates = [(e, s, sat, con) for e, s, sat, con in scored if s >= threshold]
        if not candidates:
            diag_buf.append(Diagnostic(code="no_supported_bass", severity=Severity.INFO, message="no event met bass threshold"))
            return (), tuple(diag_buf)

        candidates.sort(key=lambda x: (-x[1], getattr(x[0], "onset", Fraction(0)), getattr(x[0].source_ref, "id", "")))
        # For bass, we expect anchor to be stable: if candidates include many different pitch classes without recurrence, lower confidence
        # Compute mean score
        mean_score = sum(c[1] for c in candidates) / len(candidates)
        # Ambiguity: if top two candidates have similar scores but different pitch classes, mark contradictory
        contradictory_all: list[str] = []
        for _, _, _, con in candidates:
            contradictory_all.extend(con)
        # Check pitch class diversity
        pcs = {getattr(e, "pitch_midi", 0) % 12 for e, _, _, _ in candidates}
        if len(pcs) > len(candidates) * 0.75 and all(pc_counts[pc] == 1 for pc in pcs):
            # Many unique pcs, low recurrence → ambiguous / melodic not anchor
            contradictory_all.append("low_pitch_class_stability")
            mean_score = max(0.0, mean_score - 0.15)

        # Anchor evidence: bass anchor should have at least one longest or pitch-class recurrence among candidates
        has_longest = any(getattr(e, "is_longest_in_passage", False) for e, _, _, _ in candidates)
        cand_pc_counts = Counter(getattr(e, "pitch_midi", 0) % 12 for e, _, _, _ in candidates)
        has_recurrence = any(v >= 2 for v in cand_pc_counts.values())
        has_sustained_anchor = any(
            # candidate that sustains through at least one later slice (pedal proxy)
            # We approximate via sustain_counts from texture if available
            False
            for _ in []
        )
        if not (has_longest or has_recurrence):
            contradictory_all.append("no_anchor_evidence_longest_or_recurrence")
            mean_score = max(0.0, mean_score - 0.30)

        # If candidates are not predominantly lowest, mark
        not_lowest_ratio = sum(1 for e, _, _, _ in candidates if getattr(e, "pitch_midi", 0) != lowest_per_onset.get(getattr(e, "onset", Fraction(0)), getattr(e, "pitch_midi", 0))) / len(candidates)
        if not_lowest_ratio > 0.5:
            contradictory_all.append("not_consistently_lowest")

        confidence = check_confidence(mean_score)
        # Clamp heuristic: bass anchor should be at least medium if it has longest or recurrence
        # Already scored

        covered_events = sorted([c[0] for c in candidates], key=lambda e: (getattr(e, "onset", Fraction(0)), getattr(e.source_ref, "id", "")))
        covered_refs = tuple(e.source_ref for e in covered_events)
        try:
            covered_region = ScoreInterval(start=passage.start, end=passage.end)
        except Exception:
            onsets = [getattr(e, "onset", Fraction(0)) for e in covered_events]
            covered_region = ScoreInterval(
                start=ScorePosition(quarters=min(onsets), measure_index=0),
                end=ScorePosition(quarters=max(onsets) + Fraction(1, 4), measure_index=0),
            )

        satisfied_set: list[str] = []
        for _, _, sat, _ in candidates:
            for c in sat:
                if c not in satisfied_set:
                    satisfied_set.append(c)
        contradictory_set: list[str] = []
        for c in contradictory_all:
            if c not in contradictory_set:
                contradictory_set.append(c)

        missing = ["slur_evidence_unavailable", "pattern_exclusion_not_available"]

        hyp = SemanticHypothesis(
            hypothesis_id=f"{SPEC.detector_id}:{passage.passage_id}:bass:000",
            hypothesis_type="role.bass",
            source_passage_id=passage.passage_id,
            covered_region=covered_region,
            covered_event_ids=covered_refs,
            confidence=confidence,
            confidence_method="heuristic",
            method_id=SPEC.detector_id,
            method_version=SPEC.detector_version,
            supporting_observation_ids=(),
            supporting_pattern_ids=(),
            satisfied_criteria=tuple(sorted(set(satisfied_set))),
            contradictory_criteria=tuple(sorted(set(contradictory_set))),
            missing_evidence=tuple(missing),
            diagnostics=tuple(),
        )
        if confidence < 0.5:
            diag_buf.append(Diagnostic(code="low_confidence_bass", severity=Severity.INFO, message=f"bass confidence {confidence:.2f} low"))
        return (hyp,), tuple(diag_buf)
