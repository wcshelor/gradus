"""Event labeling: metrics say where, notes confirm what."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from piano_difficulty.difficulty_analysis.dynamics.models import DifficultyProfile
from piano_difficulty.normalize.schema import ScoreIR
from piano_difficulty.temporal.windows import ScoreRegion

from .models import DifficultyEvent, MetricEvidence, EVENT_TYPE_LABELS
from .note_inspection import inspect_span
from .segmentation import SegmentCandidate, segment_by_metrics


def _feature_supports_for_indices(profile: DifficultyProfile, indices: tuple[int, ...]) -> list[MetricEvidence]:
    evidences: list[MetricEvidence] = []
    for fid, series in profile.series.items():
        # Collect best supporting window inside indices
        best_idx = None
        best_norm = None
        for idx in indices:
            try:
                nv = series.normalized_values[idx]
            except Exception:
                nv = None
            if nv is None:
                continue
            if best_norm is None or nv > best_norm:
                best_norm = nv
                best_idx = idx
        if best_idx is None or best_norm is None or best_norm < 0.35:
            continue
        # delta vs previous window outside segment if possible
        delta = None
        try:
            prev = series.normalized_values[best_idx - 1] if best_idx > 0 else None
            if prev is not None and best_norm is not None:
                delta = float(best_norm - prev)
        except Exception:
            pass
        # contribution share not available without composite; leave None
        evidences.append(
            MetricEvidence(
                feature_id=fid,
                window_index=int(best_idx),
                raw_value=series.raw_values[best_idx] if best_idx < len(series.raw_values) else None,
                normalized_value=float(best_norm) if best_norm is not None else None,
                smoothed_value=series.smoothed_values[best_idx] if best_idx < len(series.smoothed_values) else None,
                delta_normalized=float(delta) if delta is not None else None,
                is_peak_support=any(p.contributing_feature_id == fid for p in profile.passages if p.region.window_index == best_idx),
            )
        )
    # sort by normalized desc
    evidences.sort(key=lambda e: (-(e.normalized_value or 0), e.feature_id))
    return evidences[:6]


def _infer_type(candidate: SegmentCandidate, note_ev: Any, evidences: list[MetricEvidence]) -> tuple[str, str, float, bool, str | None]:
    """Return (difficulty_type, label, confidence, uncertain, reason)."""
    fids = {e.feature_id for e in evidences}
    has_leap = any(f.startswith("leaps.") for f in fids)
    has_span = any(f.startswith("pitch_geometry.") for f in fids)
    has_texture = any(f.startswith("texture.") for f in fids)
    has_density = any(f in ("rhythm.attack_density", "rhythm.note_density") for f in fids)
    has_coord = any(f.startswith("coordination.") for f in fids)
    has_pitch_range = "metadata.pitch_range" in fids or any("register" in f for f in fids)

    extra = getattr(note_ev, "extra", {}) if note_ev is not None else {}

    # Priority mapping — note evidence confirms metric hints
    # 1. Repeated ascending right-hand pattern (exact interval repetition)
    if has_density or has_texture:
        if extra.get("has_repeated_ascending_pattern"):
            return (
                "repeated_ascending_pattern",
                EVENT_TYPE_LABELS["repeated_ascending_pattern"],
                0.78,
                False,
                None,
            )
    # 2. Large arpeggiated arrival (prioritized over metric-only pattern fallback)
    if has_span or has_leap or has_pitch_range:
        if extra.get("is_arpeggiated_arrival"):
            return (
                "arpeggiated_arrival",
                EVENT_TYPE_LABELS["arpeggiated_arrival"],
                0.80,
                False,
                None,
            )
        # Metric-only arpeggiated arrival: wide span + leap spike
        if has_span and has_leap:
            span_ev = [e for e in evidences if e.feature_id.startswith("pitch_geometry.")]
            leap_ev = [e for e in evidences if e.feature_id.startswith("leaps.")]
            if span_ev and leap_ev and (span_ev[0].normalized_value or 0) >= 0.6 and (leap_ev[0].normalized_value or 0) >= 0.6:
                return (
                    "arpeggiated_arrival",
                    EVENT_TYPE_LABELS["arpeggiated_arrival"],
                    0.68,
                    False,
                    None,
                )
    # 3. Repeated pattern fallback (metric + two-voice)
    if has_density or has_texture:
        if has_density and extra.get("has_two_voice_texture") and any((e.normalized_value or 0) >= 0.6 for e in evidences if e.feature_id in ("rhythm.attack_density", "rhythm.note_density")):
            return (
                "repeated_ascending_pattern",
                EVENT_TYPE_LABELS["repeated_ascending_pattern"],
                0.62,
                False,
                None,
            )
    # 4. Two-voice texture inside pattern
    if has_texture:
        if extra.get("has_two_voice_texture"):
            return (
                "two_voice_texture",
                EVENT_TYPE_LABELS["two_voice_texture"],
                0.72,
                False,
                None,
            )
    # 4. Left-hand relocation
    if has_leap:
        if extra.get("has_left_relocation"):
            return (
                "hand_relocation",
                EVENT_TYPE_LABELS["hand_relocation"],
                0.75,
                False,
                None,
            )
    # 5. Dense two-hand coordination
    if has_coord or (has_density and has_texture):
        if extra.get("has_dense_coordination"):
            return (
                "dense_two_hand_coordination",
                EVENT_TYPE_LABELS["dense_two_hand_coordination"],
                0.74,
                False,
                None,
            )
        if has_coord:
            return (
                "dense_two_hand_coordination",
                EVENT_TYPE_LABELS["dense_two_hand_coordination"],
                0.62,
                False,
                None,
            )
    # Generic fallbacks based on strongest metric
    if has_span:
        return ("wide_span", EVENT_TYPE_LABELS["wide_span"], 0.55, False, None)
    if has_leap:
        return ("rapid_leaps", EVENT_TYPE_LABELS["rapid_leaps"], 0.55, False, None)
    if has_texture:
        return ("polyphonic_texture", EVENT_TYPE_LABELS["polyphonic_texture"], 0.52, False, None)
    if has_density:
        return ("high_density", EVENT_TYPE_LABELS["high_density"], 0.50, False, None)
    # Uncertain
    return (
        "uncertain",
        EVENT_TYPE_LABELS["uncertain"],
        0.35,
        True,
        "no metric exceeded threshold and note inspection inconclusive — manual review suggested",
    )


def explain_flagged_span(
    score: ScoreIR,
    profile: DifficultyProfile,
    flagged_region: ScoreRegion,
    *,
    use_note_inspection: bool = True,
) -> list[DifficultyEvent]:
    """Divide one flagged passage into labeled difficulty events.

    May return 1..N events.  Events may overlap when a texture spans
    the whole passage while an arrival/relocation occupies the tail.
    """
    candidates: list[SegmentCandidate] = segment_by_metrics(profile, flagged_region)
    if not candidates:
        note_ev = inspect_span(score, flagged_region) if use_note_inspection else None
        evidences = _feature_supports_for_indices(profile, (flagged_region.window_index,))
        dtype, label, conf, unc, reason = _infer_type(
            SegmentCandidate(
                window_indices=(flagged_region.window_index,),
                span=flagged_region,
                boundary_reason="fallback_single",
                supporting_feature_ids=tuple(e.feature_id for e in evidences),
                confidence=conf if 'conf' in locals() else 0.35,
            ),
            note_ev,
            evidences,
        )
        return [
            DifficultyEvent(
                event_id=f"{flagged_region.score_id or 'score'}:e:{flagged_region.window_index}:0:{dtype}",
                span=flagged_region,
                difficulty_type=dtype,
                label=label,
                confidence=conf,
                supporting_metric_evidence=tuple(evidences),
                note_evidence=note_ev if not unc or True else note_ev,
                uncertainty=unc,
                uncertainty_reason=reason,
                diagnostics=("fallback: no segmentation candidates",),
                window_indices=(flagged_region.window_index,),
                measure_start=flagged_region.measure_start,
                measure_end=flagged_region.measure_end,
            )
        ]

    events: list[DifficultyEvent] = []
    # First pass: one event per candidate segment
    for idx, cand in enumerate(candidates):
        note_ev = inspect_span(score, cand.span) if use_note_inspection else None
        evidences = _feature_supports_for_indices(profile, cand.window_indices)
        # Boost evidences to include candidate supporting ids even if not top
        for fid in cand.supporting_feature_ids:
            if fid not in {e.feature_id for e in evidences} and fid in profile.series:
                series = profile.series[fid]
                # add with value at best window in candidate
                best = None
                best_nv = None
                for wi in cand.window_indices:
                    try:
                        nv = series.normalized_values[wi]
                    except Exception:
                        nv = None
                    if nv is not None and (best_nv is None or nv > best_nv):
                        best_nv = nv
                        best = wi
                if best is not None:
                    evidences.append(
                        MetricEvidence(
                            feature_id=fid,
                            window_index=int(best),
                            raw_value=series.raw_values[best] if best < len(series.raw_values) else None,
                            normalized_value=float(best_nv) if best_nv is not None else None,
                            smoothed_value=series.smoothed_values[best] if best < len(series.smoothed_values) else None,
                        )
                    )
        dtype, label, conf, unc, reason = _infer_type(cand, note_ev, evidences)
        # Adjust confidence by candidate confidence
        conf = min(0.92, max(0.20, (conf + cand.confidence) / 2))
        if unc:
            conf = min(conf, 0.42)
        events.append(
            DifficultyEvent(
                event_id=f"{flagged_region.score_id or 'score'}:e:{flagged_region.window_index}:{idx}:{dtype}",
                span=cand.span,
                difficulty_type=dtype,
                label=label,
                confidence=float(conf),
                supporting_metric_evidence=tuple(sorted(evidences, key=lambda e: (-(e.normalized_value or 0), e.feature_id))[:6]),
                note_evidence=note_ev,
                uncertainty=unc,
                uncertainty_reason=reason,
                diagnostics=tuple(list(cand.diagnostics) + [f"boundary_reason={cand.boundary_reason}"]),
                window_indices=cand.window_indices,
                measure_start=cand.span.measure_start,
                measure_end=cand.span.measure_end,
            )
        )

    # Overlap refinement: if a sustained texture event spans almost the whole flagged
    # region and an arrival/relocation occupies the tail, keep both overlapping
    # (they already overlap slightly via _build_span).  Also add explicit overlap
    # for two-voice texture inside repeated pattern:
    # If first event is repeated_ascending_pattern and note evidence shows two-voice,
    # add an overlapping two_voice_texture event covering the same span but with
    # texture evidence.  Only if not already present.
    has_repeated = any(e.difficulty_type == "repeated_ascending_pattern" for e in events)
    has_two_voice = any(e.difficulty_type == "two_voice_texture" for e in events)
    if has_repeated and not has_two_voice:
        # check note evidence of first repeated event
        for e in events:
            if e.difficulty_type == "repeated_ascending_pattern" and e.note_evidence is not None:
                if e.note_evidence.extra.get("has_two_voice_texture"):
                    # Create overlapping two-voice event on same span
                    two_voice_evidences = [ev for ev in e.supporting_metric_evidence if ev.feature_id.startswith("texture.")]
                    if not two_voice_evidences:
                        # fallback: texture evidences from profile
                        two_voice_evidences = _feature_supports_for_indices(profile, e.window_indices)
                        two_voice_evidences = [ev for ev in two_voice_evidences if ev.feature_id.startswith("texture.")]
                    if two_voice_evidences:
                        overlap = DifficultyEvent(
                            event_id=f"{flagged_region.score_id or 'score'}:e:{flagged_region.window_index}:overlap:two_voice_texture",
                            span=e.span,
                            difficulty_type="two_voice_texture",
                            label=EVENT_TYPE_LABELS["two_voice_texture"],
                            confidence=0.62,
                            supporting_metric_evidence=tuple(two_voice_evidences[:3]),
                            note_evidence=e.note_evidence,
                            uncertainty=False,
                            diagnostics=("overlapping texture inside repeated pattern",),
                            window_indices=e.window_indices,
                            measure_start=e.measure_start,
                            measure_end=e.measure_end,
                        )
                        events.append(overlap)
                    break

    # Ensure deterministic order by span start
    events.sort(key=lambda ev: (ev.span.start_offset if ev.span.start_offset is not None else Fraction(0), ev.confidence * -1))
    return events
