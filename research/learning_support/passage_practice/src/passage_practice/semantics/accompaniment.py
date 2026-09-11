"""Accompaniment-pattern detector v1 — S3.4.

Detects repeated broken chord, block chord support, Alberti-like shape,
ostinato, tremolo-like alternation when supported. Heuristic, deterministic.

Design refs:
- S2.7 texture_grid, S2.6 rhythm_grid, S2.4 attack_stream / S2.8 salience_view
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
    detector_id="accompaniment_pattern.v1",
    detector_version="v1",
    hypothesis_types=("role.accompaniment", "texture.arpeggiated", "texture.ostinato"),
    required_views=("texture_grid",),
    optional_views=("rhythm_grid", "salience_view", "attack_stream"),
    supported_subset="repeated broken chord / block chord / Alberti-like / ostinato / tremolo (heuristic, 4+ onsets)",
    known_limitations=(
        "no learned pattern classifier",
        "slur evidence unavailable",
        "requires 4+ onsets for high confidence",
    ),
)


def _pitch_sequence(events: list[Any]) -> list[int]:
    return [getattr(e, "pitch_midi", 0) for e in events]


def _intervals(pitches: list[int]) -> list[int]:
    return [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]


class AccompanimentPatternDetector(BaseDetector):
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

        texture = views.get("texture_grid")
        if texture is None:
            return (), (Diagnostic(code="missing_required_view", severity=Severity.WARNING, message="texture_grid required"),)

        diag_buf: list[Diagnostic] = []
        for vd in getattr(texture, "diagnostics", ()):
            diag_buf.append(vd)

        salience = views.get("salience_view")
        # Prefer salience events for pitch sequence (already sorted, includes all attacks), fallback to texture slices
        if salience is not None and getattr(salience, "events", None):
            events = list(getattr(salience, "events"))
            pitches = _pitch_sequence(events)
            # Map event source_ref for covered ids
            event_refs = [getattr(e, "source_ref", None) for e in events]
        else:
            # Fallback: use texture slices attack refs order; need pitch lookup via score if available
            # For v1, if no salience, we cannot score pitch, so produce low confidence
            pitches = []
            event_refs = []

        summary = texture.summary() if hasattr(texture, "summary") else {}
        total_attacks = summary.get("total_attacks", 0)
        onset_count = summary.get("onset_count", 0)
        max_chord = summary.get("max_chord_size", 0)
        chordal = summary.get("chordal_onset_count", 0)
        sustained = summary.get("sustained_under_moving_count", 0)

        # Too-short pattern check
        if onset_count < 4:
            diag_buf.append(
                Diagnostic(
                    code="too_short_pattern",
                    severity=Severity.INFO,
                    message=f"onset_count {onset_count} <4; pattern too short for high confidence",
                )
            )

        # Texture-based score
        texture_score = 0.0
        satisfied: list[str] = []
        contradictory: list[str] = []

        if sustained >= 3:
            texture_score += 0.30
            satisfied.append("sustained_under_moving")
        else:
            contradictory.append("no_sustained_accompaniment")

        if max_chord > 1 and chordal >= 1:
            texture_score += 0.20
            satisfied.append("block_chord_support")

        if onset_count >= 5:
            texture_score += 0.10
            satisfied.append("sufficient_onsets")
        elif onset_count >= 4:
            texture_score += 0.05
            satisfied.append("minimal_onsets")

        # Pitch-based score
        pitch_score = 0.0
        intervals = _intervals(pitches) if len(pitches) >= 2 else []
        if pitches:
            pitch_range = max(pitches) - min(pitches) if pitches else 0
            avg_abs_interval = sum(abs(i) for i in intervals) / len(intervals) if intervals else 0
            if pitch_range >= 7 and avg_abs_interval >= 3:
                pitch_score += 0.20
                satisfied.append("arpeggiated_range_and_leaps")
            elif avg_abs_interval <= 2 and pitch_range <= 5:
                # Scalar-like
                pitch_score -= 0.15
                contradictory.append("scalar_stepwise_small_range")
            # Repeated pattern: check if interval sequence repeats every 2 or 4
            if len(intervals) >= 4:
                # Check for repeated interval pattern length 2
                pattern2 = intervals[:2]
                if len(intervals) >= 6 and intervals[2:4] == pattern2:
                    pitch_score += 0.15
                    satisfied.append("repeated_interval_pattern")
                # Check Alberti-like: intervals like +4,+3,-3,-4 repeating
                # Simple check: intervals alternate sign and similar magnitude
                alt = all(intervals[i] * intervals[i + 1] < 0 for i in range(len(intervals) - 1) if abs(intervals[i]) >= 2 and abs(intervals[i + 1]) >= 2)
                if alt and pitch_range >= 7:
                    pitch_score += 0.10
                    satisfied.append("alberti_like_alternation")
            # Ostinato / repeated note: many zero intervals
            zero_intervals = sum(1 for i in intervals if i == 0)
            if zero_intervals >= len(intervals) * 0.5 and len(intervals) >= 2:
                # Ambiguous: repeated note could be tremolo or just repeated pitch, not accompaniment
                pitch_score -= 0.10
                contradictory.append("repeated_note_ambiguity")
                diag_buf.append(
                    Diagnostic(
                        code="repeated_note_ambiguity",
                        severity=Severity.INFO,
                        message="repeated pitch intervals dominate; accompaniment vs repeated-note ambiguous",
                    )
                )
            # Ostinato: repeated pitch class
            if pitches:
                pc_counts = Counter(p % 12 for p in pitches)
                if max(pc_counts.values(), default=0) >= 3:
                    pitch_score += 0.10
                    satisfied.append("pitch_class_ostinato")

        total_score = texture_score + pitch_score
        # Clamp
        if total_score < 0:
            total_score = 0.0
        if total_score > 1:
            total_score = 1.0

        # Determine hypothesis
        # Too-short should be low confidence even if score moderate
        if onset_count < 4 and total_score >= 0.5:
            total_score = min(total_score, 0.45)

        # No pattern if score too low
        if total_score < 0.35:
            diag_buf.append(
                Diagnostic(
                    code="no_supported_accompaniment",
                    severity=Severity.INFO,
                    message=f"accompaniment score {total_score:.2f} below threshold",
                )
            )
            # For scalar negative, we return no hypothesis
            return (), tuple(diag_buf)

        confidence = check_confidence(total_score)
        # Choose hypothesis type based on dominant cue
        if "block_chord_support" in satisfied and "sustained_under_moving" not in satisfied:
            hyp_type = "texture.block_chord"
        elif "alberti_like_alternation" in satisfied or "arpeggiated_range_and_leaps" in satisfied:
            hyp_type = "texture.arpeggiated"
        elif "pitch_class_ostinato" in satisfied:
            hyp_type = "texture.ostinato"
        else:
            hyp_type = "role.accompaniment"

        # Covered refs: all attack refs in texture order (deterministic)
        covered_refs = []
        for sl in getattr(texture, "slices", ()):
            covered_refs.extend(list(getattr(sl, "attack_refs", ())))
            covered_refs.extend(list(getattr(sl, "sustained_refs", ())))
        # Deduplicate preserving order and keep only those that are in passage event_refs (if passage provided)
        if passage is not None:
            allowed = {r.id for r in getattr(passage, "event_refs", ())}
            covered_refs = [r for r in covered_refs if r.id in allowed]
        # Deduplicate
        seen = set()
        dedup = []
        for r in covered_refs:
            if r.id not in seen:
                seen.add(r.id)
                dedup.append(r)
        # Fallback to event_refs if dedup empty
        if not dedup and hasattr(passage, "event_refs"):
            dedup = list(getattr(passage, "event_refs"))
        # Ensure non-empty
        if not dedup:
            # Use salience event refs
            dedup = [r for r in event_refs if r is not None][:1]

        try:
            covered_region = ScoreInterval(start=passage.start, end=passage.end)
        except Exception:
            from passage_practice.models.time import ScorePosition

            covered_region = ScoreInterval(
                start=ScorePosition(quarters=Fraction(0), measure_index=0),
                end=ScorePosition(quarters=Fraction(4), measure_index=0),
            )

        missing_evidence = ["slur_evidence_unavailable", "pattern_exclusion_not_available"] if salience is not None else ["salience_view_missing_some_factors"]

        hyp = SemanticHypothesis(
            hypothesis_id=f"{SPEC.detector_id}:{passage.passage_id}:accompaniment:000",
            hypothesis_type=hyp_type,
            source_passage_id=passage.passage_id,
            covered_region=covered_region,
            covered_event_ids=tuple(dedup),
            confidence=confidence,
            confidence_method="heuristic",
            method_id=SPEC.detector_id,
            method_version=SPEC.detector_version,
            supporting_observation_ids=(),
            supporting_pattern_ids=(),
            satisfied_criteria=tuple(sorted(set(satisfied))),
            contradictory_criteria=tuple(sorted(set(contradictory))),
            missing_evidence=tuple(missing_evidence),
            diagnostics=tuple(),
        )

        # Low confidence diagnostic if too short or ambiguous
        if confidence < 0.5:
            diag_buf.append(
                Diagnostic(
                    code="low_confidence_accompaniment",
                    severity=Severity.INFO,
                    message=f"accompaniment confidence {confidence:.2f} low",
                )
            )

        return (hyp,), tuple(diag_buf)
