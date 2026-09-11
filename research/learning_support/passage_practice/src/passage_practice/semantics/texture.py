"""Texture classifier v1 — S3.6.

Ranks monophonic, homophonic block, melody-plus-accompaniment, arpeggiated,
and polyphonic candidates. Heuristic, deterministic.

Depends on S3.2-S3.5 (uses salience/morph but not detector outputs directly;
reads texture_grid + salience_view).
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from passage_practice.models.diagnostics import Diagnostic, Severity
from passage_practice.models.time import ScoreInterval, ScorePosition
from passage_practice.semantics.confidence import check_confidence
from passage_practice.semantics.contracts import SemanticHypothesis
from passage_practice.semantics.registry import BaseDetector, DetectorSpec

SPEC = DetectorSpec(
    detector_id="texture_classifier.v1",
    detector_version="v1",
    hypothesis_types=(
        "texture.monophonic",
        "texture.homophonic_block",
        "texture.melody_plus_accompaniment",
        "texture.arpeggiated",
        "texture.polyphonic",
    ),
    required_views=("texture_grid",),
    optional_views=("salience_view", "rhythm_grid"),
    supported_subset="5-class texture ranking via texture_grid summary",
    known_limitations=("no voice-role inference beyond encoded voices",),
)


class TextureClassifier(BaseDetector):
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

        summary = texture.summary() if hasattr(texture, "summary") else {}
        total = summary.get("total_attacks", 0)
        onsets = summary.get("onset_count", 0)
        max_chord = summary.get("max_chord_size", 0)
        chordal = summary.get("chordal_onset_count", 0)
        sustained = summary.get("sustained_under_moving_count", 0)
        voices = summary.get("voices", [])
        hands = summary.get("hands", [])

        if total == 0:
            diag_buf.append(Diagnostic(code="no_texture_slices", severity=Severity.INFO, message="no texture slices"))
            return (), tuple(diag_buf)

        # Compute per-class confidence
        candidates: list[tuple[str, float, list[str], list[str]]] = []  # type, conf, sat, contra

        # Monophonic: all chord_size ==1, sustained 0, voices single
        # Score high if max_chord==1 and chordal==0 and sustained==0
        mono_score = 0.0
        mono_sat: list[str] = []
        mono_contra: list[str] = []
        if max_chord == 1:
            mono_score += 0.50
            mono_sat.append("max_chord_one")
        else:
            mono_contra.append("has_chords")
        if chordal == 0:
            mono_score += 0.20
            mono_sat.append("no_chordal_onsets")
        else:
            mono_contra.append("has_chordal_onsets")
        if sustained == 0:
            mono_score += 0.20
            mono_sat.append("no_sustained")
        else:
            mono_contra.append("has_sustained")
        if len(voices) <= 1:
            mono_score += 0.05
            mono_sat.append("single_voice")
        # monophonic confidence
        mono_conf = min(0.85, mono_score)
        if mono_conf >= 0.35:
            candidates.append(("texture.monophonic", mono_conf, mono_sat, mono_contra))
        elif mono_score >= 0.25:
            # low confidence monophonic still considered for ambiguous cases
            candidates.append(("texture.monophonic", 0.35, mono_sat, mono_contra + ["low_confidence"]))

        # Homophonic block: chordal many, sustained 0 or low, voices maybe 1 but chord size >1
        homo_score = 0.0
        homo_sat: list[str] = []
        homo_contra: list[str] = []
        if max_chord > 1:
            homo_score += 0.40
            homo_sat.append("has_chords")
        else:
            homo_contra.append("no_chords")
        if chordal / max(onsets, 1) >= 0.5:
            homo_score += 0.30
            homo_sat.append("many_chordal_onsets")
        elif chordal > 0:
            homo_score += 0.10
        if sustained == 0:
            homo_score += 0.10
            homo_sat.append("no_sustained_block")
        else:
            homo_contra.append("has_sustained_not_block")
        if homo_score >= 0.35:
            candidates.append(("texture.homophonic_block", min(0.85, homo_score), homo_sat, homo_contra))

        # Melody-plus-accompaniment: sustained >=1, with both hands, and top vs sustained distinction
        mpa_score = 0.0
        mpa_sat: list[str] = []
        mpa_contra: list[str] = []
        if sustained >= 1:
            mpa_score += 0.40
            mpa_sat.append("sustained_under_moving")
        else:
            mpa_contra.append("no_sustained")
        if len(hands) >= 2:
            mpa_score += 0.15
            mpa_sat.append("both_hands")
        if max_chord <= 2 and sustained >= 1:
            mpa_score += 0.15
            mpa_sat.append("single_moving_over_sustained")
        if sustained >= 3:
            mpa_score += 0.10
        if mpa_score >= 0.35:
            candidates.append(("texture.melody_plus_accompaniment", min(0.85, mpa_score), mpa_sat, mpa_contra))

        # Arpeggiated: similar to melody-plus but with many single onsets and sustained bass, and large pitch range
        arp_score = 0.0
        arp_sat: list[str] = []
        arp_contra: list[str] = []
        if sustained >= 3 and max_chord <= 2:
            arp_score += 0.35
            arp_sat.append("sustained_many_single_onsets")
        if onsets >= 5 and max_chord <= 2:
            arp_score += 0.20
            arp_sat.append("many_onsets")
        if sustained == 0:
            arp_contra.append("no_sustained_for_arpeggiated")
        # Use salience for pitch range if available
        salience = views.get("salience_view")
        if salience is not None:
            events = list(getattr(salience, "events", ()))
            if events:
                mids = [getattr(e, "pitch_midi", 0) for e in events]
                prange = max(mids) - min(mids) if mids else 0
                if prange >= 7:
                    arp_score += 0.15
                    arp_sat.append("large_pitch_range")
        if arp_score >= 0.35:
            candidates.append(("texture.arpeggiated", min(0.85, arp_score), arp_sat, arp_contra))

        # Polyphonic: two encoded voices both active, with overlapping or independent
        poly_score = 0.0
        poly_sat: list[str] = []
        poly_contra: list[str] = []
        if len(voices) >= 2:
            poly_score += 0.40
            poly_sat.append("two_encoded_voices")
        else:
            poly_contra.append("single_voice_not_polyphonic")
        if onsets >= 3 and len(voices) >= 2:
            poly_score += 0.20
            poly_sat.append("multiple_onsets_with_two_voices")
        if chordal >= 2 and len(voices) >= 2:
            poly_score += 0.10
            poly_sat.append("chordal_with_two_voices")
        # Polyphonic often has no sustained or has overlapping voices
        if poly_score >= 0.35:
            candidates.append(("texture.polyphonic", min(0.85, poly_score), poly_sat, poly_contra))

        if not candidates:
            diag_buf.append(Diagnostic(code="no_supported_texture", severity=Severity.INFO, message="no texture class met threshold"))
            return (), tuple(diag_buf)

        # Build hypotheses, keep contradictions visible, sort by confidence then type
        try:
            covered_region = ScoreInterval(start=passage.start, end=passage.end)
        except Exception:
            covered_region = ScoreInterval(start=ScorePosition(quarters=Fraction(0), measure_index=0), end=ScorePosition(quarters=Fraction(4), measure_index=0))

        # For each candidate, produce hypothesis covering all events (texture is passage-level)
        # Use all attack refs as covered
        all_refs = []
        for sl in getattr(texture, "slices", ()):
            all_refs.extend(list(getattr(sl, "attack_refs", ())))
        # Deduplicate
        seen = set()
        dedup = []
        for r in all_refs:
            if r.id not in seen:
                seen.add(r.id)
                dedup.append(r)
        if not dedup and hasattr(passage, "event_refs"):
            dedup = list(getattr(passage, "event_refs"))

        hyps: list[SemanticHypothesis] = []
        for hyp_type, conf, sat, contra in candidates:
            # Adjust confidence for ambiguous: if multiple candidates close, keep as is but mark contradictory
            hyp = SemanticHypothesis(
                hypothesis_id=f"{SPEC.detector_id}:{passage.passage_id}:{hyp_type.split('.')[-1]}:000",
                hypothesis_type=hyp_type,
                source_passage_id=passage.passage_id,
                covered_region=covered_region,
                covered_event_ids=tuple(dedup) if dedup else (passage.event_refs[0],) if getattr(passage, "event_refs", ()) else (),
                confidence=check_confidence(conf),
                confidence_method="heuristic",
                method_id=SPEC.detector_id,
                method_version=SPEC.detector_version,
                supporting_observation_ids=(),
                supporting_pattern_ids=(),
                satisfied_criteria=tuple(sorted(set(sat))),
                contradictory_criteria=tuple(sorted(set(contra))),
                missing_evidence=tuple(),
                diagnostics=tuple(),
            )
            hyps.append(hyp)

        # If ambiguous (multiple candidates with similar confidence within 0.15), keep all and add diagnostic
        if len(hyps) >= 2:
            confs = sorted([h.confidence for h in hyps], reverse=True)
            if confs[0] - confs[1] < 0.15:
                diag_buf.append(Diagnostic(code="ambiguous_texture", severity=Severity.INFO, message="multiple texture classes with similar confidence"))

        hyps_sorted = tuple(sorted(hyps, key=lambda h: (-h.confidence, h.hypothesis_type)))
        return hyps_sorted, tuple(diag_buf)
