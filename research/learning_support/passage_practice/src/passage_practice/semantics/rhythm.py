"""Rhythm-layer detector v1 — S3.5.

Identifies independent hand rhythms, syncopated layer, common-attack
skeleton, and stable accompaniment rhythm. Heuristic, deterministic.

Design refs:
- S2.6 rhythm_grid, S2.7 texture_grid
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
    detector_id="rhythm_layer.v1",
    detector_version="v1",
    hypothesis_types=(
        "rhythm.independent_hands",
        "rhythm.syncopated_layer",
        "rhythm.common_attack_skeleton",
        "rhythm.stable_accompaniment",
    ),
    required_views=("rhythm_grid",),
    optional_views=("texture_grid", "salience_view"),
    supported_subset="independent hands, syncopation, common attacks, stable accompaniment (heuristic)",
    known_limitations=("no learned rhythm classifier", "tuplets flagged as unsupported in grid"),
)


class RhythmLayerDetector(BaseDetector):
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
        rhythm = views.get("rhythm_grid")
        if rhythm is None:
            return (), (Diagnostic(code="missing_required_view", severity=Severity.WARNING, message="rhythm_grid required"),)
        diag_buf: list[Diagnostic] = []
        for vd in getattr(rhythm, "diagnostics", ()):
            if getattr(vd, "code", "") in ("unknown_meter", "tuplet_subdivision"):
                diag_buf.append(vd)

        cells = list(getattr(rhythm, "cells", ()))
        onsets = list(getattr(rhythm, "onsets", ()))
        if not cells or not onsets:
            diag_buf.append(Diagnostic(code="no_rhythm_cells", severity=Severity.INFO, message="no rhythm cells"))
            return (), tuple(diag_buf)

        # Metrics
        total_onsets = len(onsets)
        both_hands_onsets = sum(1 for o in onsets if getattr(o, "both_hands", False))
        staggered_onsets = total_onsets - both_hands_onsets
        off_beat_cells = [c for c in cells if getattr(c, "on_beat", None) is False]
        sync_cells = [c for c in cells if getattr(c, "on_beat", False) is False and (getattr(c, "beat_boundaries_crossed", 0) or 0) > 0]
        # Stable accompaniment: repeated duration
        durations = [getattr(c, "duration", Fraction(0)) for c in cells]
        dur_counts = Counter(durations)
        most_common_dur, most_common_cnt = dur_counts.most_common(1)[0] if dur_counts else (Fraction(0), 0)
        stable_ratio = most_common_cnt / len(cells) if cells else 0
        # Mixed subdivision: check if hands have different durations at same onset
        # Use rhythm cells grouped by onset
        from collections import defaultdict

        by_onset: dict[Fraction, list[Any]] = defaultdict(list)
        for c in cells:
            by_onset[getattr(c, "onset", Fraction(0))].append(c)
        mixed_onsets = 0
        for group in by_onset.values():
            durs = {getattr(c, "duration", None) for c in group}
            if len(durs) > 1:
                mixed_onsets += 1

        hyps: list[SemanticHypothesis] = []
        # Helper to build hypothesis
        def _make_hyp(hyp_type: str, covered_refs: list[Any], conf: float, sat: list[str], contra: list[str]) -> SemanticHypothesis:
            try:
                covered_region = ScoreInterval(start=passage.start, end=passage.end)
            except Exception:
                covered_region = ScoreInterval(start=ScorePosition(quarters=Fraction(0), measure_index=0), end=ScorePosition(quarters=Fraction(4), measure_index=0))
            # Convert cell source_refs to SourceRef list
            refs = tuple(getattr(c, "source_ref", None) for c in covered_refs if getattr(c, "source_ref", None) is not None)
            if not refs:
                # fallback to first cell
                refs = (cells[0].source_ref,)
            return SemanticHypothesis(
                hypothesis_id=f"{SPEC.detector_id}:{passage.passage_id}:{hyp_type.split('.')[-1]}:000",
                hypothesis_type=hyp_type,
                source_passage_id=passage.passage_id,
                covered_region=covered_region,
                covered_event_ids=refs,
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

        # Independent hands: many staggered onsets
        # For aligned hands negative test, both_hands high → not independent
        indep_ratio = staggered_onsets / total_onsets if total_onsets else 0
        if indep_ratio >= 0.30:
            conf = 0.55 + indep_ratio * 0.30  # 0.55-0.85
            if indep_ratio >= 0.50:
                conf = min(0.85, conf)
            sat = ["staggered_onsets"]
            contra: list[str] = []
            if indep_ratio < 0.5:
                contra.append("partially_aligned")
            if stable_ratio > 0.7:
                contra.append("stable_rhythm_not_independent")
            # Covered refs: all staggered onset cells
            staggered_refs = []
            for o in onsets:
                if not getattr(o, "both_hands", False):
                    # find cells at this onset
                    onset = getattr(o, "onset", Fraction(0))
                    staggered_refs.extend([c for c in cells if getattr(c, "onset", None) == onset])
            hyps.append(_make_hyp("rhythm.independent_hands", staggered_refs or cells, conf, sat, contra))

        # Syncopated layer: off_beat and sync cells (sensitive to single off-beat)
        if off_beat_cells:
            off_ratio = len(off_beat_cells) / len(cells)
            sync_ratio = len(sync_cells) / len(cells) if cells else 0
            # Produce even for single off-beat (off_ratio 0.12) to capture syncopation
            conf = 0.50 + sync_ratio * 0.40 + off_ratio * 0.30
            conf = min(0.85, conf)
            sat = []
            if off_ratio >= 0.10:
                sat.append("off_beat_density")
            if sync_ratio >= 0.05:
                sat.append("syncopation_proxy")
            if not sat:
                sat.append("off_beat_density")
            contra = []
            if off_ratio < 0.25 and sync_ratio < 0.10:
                contra.append("low_syncopation")
            hyps.append(_make_hyp("rhythm.syncopated_layer", sync_cells or off_beat_cells, conf, sat, contra))

        # Common-attack skeleton: both_hands onsets
        if both_hands_onsets >= 1:
            both_ratio = both_hands_onsets / total_onsets if total_onsets else 0
            if both_ratio >= 0.25:
                conf = 0.55 + both_ratio * 0.30
                conf = min(0.85, conf)
                sat = ["common_attacks"]
                contra = []
                if both_ratio < 0.50:
                    contra.append("partially_independent")
                both_refs = []
                for o in onsets:
                    if getattr(o, "both_hands", False):
                        onset = getattr(o, "onset", None)
                        both_refs.extend([c for c in cells if getattr(c, "onset", None) == onset])
                hyps.append(_make_hyp("rhythm.common_attack_skeleton", both_refs or cells, conf, sat, contra))

        # Stable accompaniment rhythm: repeated duration
        if stable_ratio >= 0.60 and len(cells) >= 4:
            conf = 0.50 + stable_ratio * 0.30
            # Mixed subdivision contradicts stable
            if mixed_onsets > 0:
                conf = max(0.0, conf - 0.15)
                contra = ["mixed_subdivision"]
                sat = ["repeated_duration"]
            else:
                contra = []
                sat = ["repeated_duration", "stable_accompaniment"]
            # Only emit if not too mixed
            if mixed_onsets == 0 or stable_ratio >= 0.75:
                # Find cells with most common duration
                stable_refs = [c for c in cells if getattr(c, "duration", None) == most_common_dur]
                hyps.append(_make_hyp("rhythm.stable_accompaniment", stable_refs, conf, sat, contra))

        # Add low confidence diagnostics if no hypotheses
        if not hyps:
            # Check why: e.g., aligned hands negative case will have no independent, no sync, but maybe common_attack
            # For aligned hands negative, we expect no independent_hands hypothesis, but common_attack may exist
            # So no hyps means truly no rhythm pattern
            diag_buf.append(Diagnostic(code="no_supported_rhythm", severity=Severity.INFO, message="no rhythm layer met threshold"))
            return (), tuple(diag_buf)

        # Sort hyps by confidence descending, then type for determinism
        hyps_sorted = tuple(sorted(hyps, key=lambda h: (-h.confidence, h.hypothesis_type)))
        return hyps_sorted, tuple(diag_buf)
