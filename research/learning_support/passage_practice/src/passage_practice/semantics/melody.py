"""Melody salience detector v1 — S3.2.

Heuristic, deterministic, inspectable. Produces ranked ``role.melody``
hypotheses using register (is_onset_top_note), duration
(is_longest_in_passage), metric, accent/dynamic where available, contour
continuity, and accompaniment-pattern exclusion via texture.

Design refs:
- docs/practice_chunk_objects.md: semantic observations must remain
  evidence-backed when attached to a chunk
- S2.8 salience_view: per-event candidate factors (register, duration,
  metric, accent, dynamics, slur unavailable, pattern exclusion not
  available)
- S2.7 texture_grid: simultaneity and sustained_under_moving for
  accompaniment exclusion; cross-boundary sustain out of scope.
- S1.5/S-Q003: confidence bands, heuristic method, contradiction penalty.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.source import SourceKind, SourceRef
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.semantics.confidence import check_confidence
from passage_practice.semantics.contracts import SemanticHypothesis
from passage_practice.semantics.registry import BaseDetector, DetectorSpec

SPEC = DetectorSpec(
    detector_id="melody_salience.v1",
    detector_version="v1",
    hypothesis_types=("role.melody",),
    required_views=("salience_view",),
    optional_views=("texture_grid", "rhythm_grid"),
    supported_subset="top-voice, left-hand, and hidden-voice melody via salience + texture; stepwise contour",
    known_limitations=(
        "slur evidence unavailable (D-018 U1)",
        "pattern exclusion markers not computed in view (S3.4)",
        "no learned ranking",
    ),
)


def _pitch_range(events: list[Any]) -> tuple[int, int]:
    mids = [e.pitch_midi for e in events]
    return (min(mids), max(mids)) if mids else (0, 0)


def _sustain_counts(salience_events: list[Any], texture_view: Any | None) -> dict[str, int]:
    """How many slices each note sustains through (accompaniment proxy)."""
    counts: dict[str, int] = {}
    if texture_view is None:
        return counts
    for sl in getattr(texture_view, "slices", ()):
        for ref in getattr(sl, "sustained_refs", ()):
            counts[ref.id] = counts.get(ref.id, 0) + 1
    return counts


def _slice_for_onset(texture_view: Any | None, onset: Fraction) -> Any | None:
    if texture_view is None:
        return None
    for sl in getattr(texture_view, "slices", ()):
        if getattr(sl, "onset", None) == onset:
            return sl
    return None


class MelodySalienceDetector(BaseDetector):
    """Deterministic melody detector using salience + texture."""

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
        # views dict may also contain other keys; we ignore observations for v1 except diagnostics
        if salience is None:
            # Should have been caught by missing check, but guard
            return (), (
                Diagnostic(
                    code="missing_required_view",
                    severity=Severity.WARNING,
                    message="salience_view is required",
                ),
            )

        events: list[Any] = list(getattr(salience, "events", ()))
        if not events:
            return (), (
                Diagnostic(
                    code="no_salience_events",
                    severity=Severity.INFO,
                    message="no salience events to score",
                ),
            )

        # Diagnostics from views that indicate unavailable evidence
        diag_buffer: list[Diagnostic] = []
        for vd in getattr(salience, "diagnostics", ()):
            if getattr(vd, "code", "") in ("slur_evidence_unavailable", "pattern_exclusion_not_available"):
                diag_buffer.append(vd)
        if texture is not None:
            for vd in getattr(texture, "diagnostics", ()):
                diag_buffer.append(vd)

        min_midi, max_midi = _pitch_range(events)
        midi_range = max_midi - min_midi if max_midi != min_midi else 1
        sustain_counts = _sustain_counts(events, texture)

        # Per-hand longest duration for hand-specific bonus (left-hand melody case)
        hand_longest: dict[str, Fraction] = {}
        for e in events:
            h = getattr(e, "hand", None)
            if h is None:
                continue
            dur = getattr(e, "duration", Fraction(0))
            if h not in hand_longest or dur > hand_longest[h]:
                hand_longest[h] = dur

        # Hand-specific top per onset (for left-hand melody where global top is RH sustained)
        onset_hand_max: dict[tuple[Fraction, str], int] = {}
        for e in events:
            h = getattr(e, "hand", None)
            if h is None:
                continue
            key = (getattr(e, "onset", Fraction(0)), h)
            midi = getattr(e, "pitch_midi", 0)
            if key not in onset_hand_max or midi > onset_hand_max[key]:
                onset_hand_max[key] = midi

        # Score each event
        scored: list[tuple[Any, float, list[str], list[str]]] = []  # event, score, satisfied, contradictory
        for e in events:
            score_val = 0.0
            satisfied: list[str] = []
            contradictory: list[str] = []

            if getattr(e, "is_onset_top_note", False):
                score_val += 0.35
                satisfied.append("top_voice")
            else:
                contradictory.append("not_top_voice")

            if getattr(e, "is_longest_in_passage", False):
                # Penalize if this note is a sustained accompaniment (high sustain count)
                cnt = sustain_counts.get(getattr(e.source_ref, "id", ""), 0)
                if cnt >= 2:
                    score_val -= 0.30
                    contradictory.append("longest_is_sustained_accompaniment")
                else:
                    score_val += 0.20
                    satisfied.append("longest_duration")
            else:
                # Hand-specific longest bonus helps left-hand melody where global longest is RH sustained
                h = getattr(e, "hand", None)
                if h is not None and getattr(e, "duration", Fraction(0)) == hand_longest.get(h):
                    score_val += 0.12
                    satisfied.append("hand_longest_duration")

            # Hand-specific top bonus (left-hand melody hidden under RH sustained)
            h = getattr(e, "hand", None)
            if h is not None:
                key = (getattr(e, "onset", Fraction(0)), h)
                if getattr(e, "pitch_midi", 0) == onset_hand_max.get(key):
                    # Only add if not already counted as global top (to avoid double count)
                    if not getattr(e, "is_onset_top_note", False):
                        score_val += 0.18
                        satisfied.append("hand_top_voice")
                    else:
                        # Global top already counted; hand top is redundant but note it
                        if "top_voice" not in satisfied:
                            satisfied.append("top_voice")

            on_beat = getattr(e, "on_beat", None)
            if on_beat is True:
                score_val += 0.10
                satisfied.append("on_beat")
            elif on_beat is False:
                score_val -= 0.05
                contradictory.append("off_beat")

            if getattr(e, "accent_marks", ()):
                score_val += 0.15
                satisfied.append("accent")

            if getattr(e, "dynamic_levels", ()):
                score_val += 0.05
                satisfied.append("dynamic")

            # Relative register height (transposition invariant)
            rel = (getattr(e, "pitch_midi", min_midi) - min_midi) / midi_range
            score_val += rel * 0.07
            if rel > 0.7:
                satisfied.append("high_register")

            # Texture-based accompaniment exclusion / moving boost
            sl = _slice_for_onset(texture, getattr(e, "onset", Fraction(0)))
            if sl is not None:
                sustained_ids = {r.id for r in getattr(sl, "sustained_refs", ())}
                attack_ids = {r.id for r in getattr(sl, "attack_refs", ())}
                eid = getattr(e.source_ref, "id", None)
                if getattr(sl, "sustained_under_moving", False):
                    if eid in attack_ids:
                        score_val += 0.25
                        satisfied.append("moving_over_sustained")
                    if eid in sustained_ids:
                        score_val -= 0.10
                        contradictory.append("sustained_under_moving_is_accompaniment")
                # Chordal non-top penalty (likely inner chord tone)
                if getattr(sl, "chord_size", 1) > 1 and not getattr(e, "is_onset_top_note", False):
                    score_val -= 0.10
                    contradictory.append("inner_chord_tone")

            # Clamp score to [0,1] before contour bonus
            if score_val < 0:
                score_val = 0.0
            if score_val > 1:
                score_val = 1.0

            scored.append((e, score_val, satisfied, contradictory))

        # Contour continuity bonus: stepwise motion between successive candidates
        # Compute intervals between events sorted by onset; if interval is 1-3 semitones (stepwise), add bonus to both
        # This is transposition invariant (intervals preserved)
        # Apply bonus after initial scoring to keep deterministic
        ordered = sorted(scored, key=lambda x: (getattr(x[0], "onset", Fraction(0)), getattr(x[0].source_ref, "id", "")))
        for i in range(1, len(ordered)):
            prev_e, prev_s, _, _ = ordered[i - 1]
            cur_e, cur_s, sat, _ = ordered[i]
            # Only consider same-hand continuity for melody lines (avoid cross-hand interval)
            prev_hand = getattr(prev_e, "hand", None)
            cur_hand = getattr(cur_e, "hand", None)
            if prev_hand is not None and prev_hand == cur_hand:
                interval = abs(getattr(cur_e, "pitch_midi", 0) - getattr(prev_e, "pitch_midi", 0))
                if 1 <= interval <= 3:
                    # Small bonus to both events, reflects stepwise continuity
                    # We mutate scored list via ordered references — need to update scored as well
                    # Find indices in ordered and boost
                    ordered[i] = (cur_e, min(1.0, cur_s + 0.04), sat + ["stepwise_continuity"] if "stepwise_continuity" not in sat else sat, ordered[i][3])
                    # Also boost previous
                    prev_sat = ordered[i - 1][2]
                    ordered[i - 1] = (prev_e, min(1.0, prev_s + 0.02), prev_sat + ["stepwise_continuity"] if "stepwise_continuity" not in prev_sat else prev_sat, ordered[i - 1][3])
        # Rebuild scored from ordered for final selection (order by onset)
        scored = ordered

        # Determine melody candidates: threshold 0.30, fallback 0.20 if none
        threshold = 0.30
        candidates = [(e, s, sat, con) for e, s, sat, con in scored if s >= threshold]
        if not candidates:
            threshold = 0.20
            candidates = [(e, s, sat, con) for e, s, sat, con in scored if s >= threshold]
        if not candidates:
            # No candidate meets even low threshold → abstain with low confidence diagnostic
            diag_buffer.append(
                Diagnostic(
                    code="no_supported_melody",
                    severity=Severity.INFO,
                    message="no salience event met melody threshold; abstaining",
                )
            )
            return (), tuple(diag_buffer)

        # Rank candidates by score descending, then onset, then id for determinism
        candidates.sort(key=lambda x: (-x[1], getattr(x[0], "onset", Fraction(0)), getattr(x[0].source_ref, "id", "")))

        # For this v1, produce one hypothesis covering all candidates in onset order
        # (melody as distributed line). Covered events sorted by onset.
        covered_events = sorted([c[0] for c in candidates], key=lambda e: (getattr(e, "onset", Fraction(0)), getattr(e.source_ref, "id", "")))
        covered_refs = tuple(e.source_ref for e in covered_events)

        # Confidence as mean candidate score, with contradiction penalty if ambiguous
        mean_score = sum(c[1] for c in candidates) / len(candidates)
        # Ambiguity: if top two scores close (<0.08) and they belong to different voices/hands or overlapping onsets, penalize
        contradictory_all: list[str] = []
        for _, _, _, con in candidates:
            contradictory_all.extend(con)
        # Detect ambiguous top voice: if candidates span both hands with similar scores
        hand_scores: dict[str, list[float]] = {}
        for e, s, _, _ in candidates:
            h = getattr(e, "hand", None) or "unknown"
            hand_scores.setdefault(h, []).append(s)
        # If best right and best left close, add contradiction
        if "right" in hand_scores and "left" in hand_scores:
            best_r = max(hand_scores["right"])
            best_l = max(hand_scores["left"])
            if abs(best_r - best_l) < 0.12:
                contradictory_all.append("hand_ambiguity")
                mean_score = max(0.0, mean_score - 0.18)

        # If candidates include both top and non-top, mark contradiction but don't heavily penalize (hidden melody case)
        has_top = any(getattr(e, "is_onset_top_note", False) for e, _, _, _ in candidates)
        has_nontop = any(not getattr(e, "is_onset_top_note", False) for e, _, _, _ in candidates)
        if has_top and has_nontop:
            # Hidden melody vs top melody ambiguity
            contradictory_all.append("mixed_top_status")

        # Also if chordal ambiguity (paired attacks fixture) → low confidence
        # Detect if candidates include multiple events at same onset (chord) — melody should be one per onset
        onset_counts: dict[Fraction, int] = {}
        for e in covered_events:
            onset_counts[getattr(e, "onset", Fraction(0))] = onset_counts.get(getattr(e, "onset", Fraction(0)), 0) + 1
        if any(cnt > 1 for cnt in onset_counts.values()):
            contradictory_all.append("multiple_candidates_same_onset")

        confidence = check_confidence(mean_score)
        # Ensure heuristic method
        method = "heuristic"

        # Satisfied criteria aggregate
        satisfied_set: list[str] = []
        for _, _, sat, _ in candidates:
            for c in sat:
                if c not in satisfied_set:
                    satisfied_set.append(c)
        # Missing evidence: slur/pattern unavailable always
        missing = ["slur_evidence_unavailable", "pattern_exclusion_not_available"]
        # Deduplicate contradictory
        contradictory_set: list[str] = []
        for c in contradictory_all:
            if c not in contradictory_set:
                contradictory_set.append(c)

        # Build hypothesis
        # Covered region is passage interval
        passage_interval = getattr(passage, "start", None)
        # Use passage start/end directly for covered_region
        try:
            covered_region = ScoreInterval(start=passage.start, end=passage.end)
        except Exception:
            # fallback to first to last event onsets
            onsets = [getattr(e, "onset", Fraction(0)) for e in covered_events]
            if onsets:
                covered_region = ScoreInterval(
                    start=ScorePosition(quarters=min(onsets), measure_index=0),
                    end=ScorePosition(quarters=max(onsets) + Fraction(1, 4), measure_index=0),
                )
            else:
                covered_region = ScoreInterval(
                    start=ScorePosition(quarters=Fraction(0), measure_index=0),
                    end=ScorePosition(quarters=Fraction(1), measure_index=0),
                )

        # Supporting observation ids: we have no observation ids in this detector v1; leave empty
        # Could link to salience factors but none required for S3.2 tests

        hyp = SemanticHypothesis(
            hypothesis_id=f"{SPEC.detector_id}:{passage.passage_id}:melody:000",
            hypothesis_type="role.melody",
            source_passage_id=passage.passage_id,
            covered_region=covered_region,
            covered_event_ids=covered_refs,
            confidence=confidence,
            confidence_method=method,
            method_id=SPEC.detector_id,
            method_version=SPEC.detector_version,
            supporting_observation_ids=(),
            supporting_pattern_ids=(),
            satisfied_criteria=tuple(sorted(set(satisfied_set))),
            contradictory_criteria=tuple(sorted(set(contradictory_set))),
            missing_evidence=tuple(missing),
            diagnostics=tuple(),
        )

        # Bundle diagnostics: include those from views plus detector-specific
        # If confidence is low (<0.5) add low_confidence diagnostic
        if confidence < 0.5:
            diag_buffer.append(
                Diagnostic(
                    code="low_confidence_melody",
                    severity=Severity.INFO,
                    message=f"melody confidence {confidence:.2f} is low; ambiguous or weak salience",
                )
            )

        return (hyp,), tuple(diag_buffer)
